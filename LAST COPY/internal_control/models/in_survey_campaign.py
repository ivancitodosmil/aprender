from odoo import models, fields, api
from odoo import _, exceptions

class InSurveyCampaign(models.Model):
    _name = 'in.survey.campaign'
    _description = 'Campaña de Encuesta'
    _rec_name = 'name'

    name = fields.Char(string='Nombre', required=True)
    survey_id = fields.Many2one('survey.survey', string='Encuesta base', required=True)
    department_id = fields.Many2one('hr.department', string='Departamento', required=True)
    date_start = fields.Date(string='Fecha de inicio', required=True)
    date_end = fields.Date(string='Fecha de fin', required=True)
    job_ids = fields.Many2many('hr.job', string='Cargos filtrados')
    employee_ids = fields.Many2many(
        'hr.employee', 
        string='Empleados específicos',
        domain="[('department_id', '=', department_id)]",
        help='Empleados que recibirán la asignación de la encuesta en esta campaña.'
    )
    assignment_ids = fields.One2many('in.survey.campaign.assignment', 'campaign_id', string='Asignaciones')
    state = fields.Selection([
        ('draft', 'Borrador'),
        ('active', 'Activa'),
        ('closed', 'Cerrada'),
        ('cancelled', 'Cancelada'),
    ], string='Estado', default='draft')

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Limpiar empleados seleccionados cuando cambia el departamento"""
        if self.department_id:
            self.employee_ids = [(5, 0, 0)]  # Limpiar selección actual

    def _get_employees_to_assign(self):
        self.ensure_one()
        Employee = self.env['hr.employee']
        # Si hay empleados específicos, solo esos
        if self.employee_ids:
            return self.employee_ids
        # Si hay cargos, empleados del departamento con esos cargos
        elif self.job_ids:
            return Employee.search([
                ('department_id', '=', self.department_id.id),
                ('job_id', 'in', self.job_ids.ids)
            ])
        # Si no hay filtros, todos los empleados del departamento
        else:
            return Employee.search([
                ('department_id', '=', self.department_id.id)
            ])

    def action_confirm(self):
        for campaign in self:
            employees = campaign._get_employees_to_assign()
            Assignment = self.env['in.survey.campaign.assignment']
            for employee in employees:
                # Evitar duplicados
                if not Assignment.search_count([('campaign_id', '=', campaign.id), ('employee_id', '=', employee.id)]):
                    assignment = Assignment.create({
                        'campaign_id': campaign.id,
                        'employee_id': employee.id,
                        'state': 'pending',
                    })
            campaign.state = 'active'

class InSurveyCampaignAssignment(models.Model):
    _name = 'in.survey.campaign.assignment'
    _description = 'Asignación de Campaña de Encuesta'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    campaign_id = fields.Many2one('in.survey.campaign', string='Campaña', required=True, ondelete='cascade')
    employee_id = fields.Many2one('hr.employee', string='Empleado', required=True)
    state = fields.Selection([
        ('pending', 'Pendiente'),
        ('answered', 'Respondida'),
        ('expired', 'Vencida'),
    ], string='Estado', default='pending')
    user_input_id = fields.Many2one('survey.user_input', string='Respuesta')
    
    # Related fields to access campaign data
    survey_id = fields.Many2one(related='campaign_id.survey_id', string='Encuesta', readonly=True)
    date_start = fields.Date(related='campaign_id.date_start', string='Fecha de inicio', readonly=True)
    date_end = fields.Date(related='campaign_id.date_end', string='Fecha de fin', readonly=True)

    def name_get(self):
        """Personalizar el nombre mostrado para las asignaciones"""
        result = []
        for assignment in self:
            name = f"{assignment.campaign_id.name} - {assignment.employee_id.name}"
            result.append((assignment.id, name))
        return result

    @api.model
    def create(self, vals):
        assignment = super().create(vals)
        employee = assignment.employee_id
        campaign = assignment.campaign_id
        if employee and employee.user_id:
            activity_type = self.env.ref('mail.mail_activity_data_todo')
            # Enlace al formulario de la asignación
            assignment_url = '/web#id=%d&model=in.survey.campaign.assignment&view_type=form' % assignment.id
            # Crear actividad con el nombre de la campaña
            survey_url = f'/survey/start/{campaign.survey_id.access_token}' if campaign.survey_id.access_token else assignment_url
            activity_vals = {
                'res_model_id': self.env['ir.model']._get_id('in.survey.campaign.assignment'),
                'res_id': assignment.id,
                'user_id': employee.user_id.id,
                'activity_type_id': activity_type.id,
                'date_deadline': campaign.date_end,
                'summary': _('Completar encuesta: %s', campaign.name),
                'note': _('''Por favor, complete la encuesta asignada.

<strong>Encuesta:</strong> %s
<strong>Fecha límite:</strong> %s

<a href="%s" class="btn btn-primary" style="background-color: #875A7B; color: white; padding: 8px 16px; text-decoration: none; border-radius: 4px; display: inline-block; margin: 10px 0;">
    📝 Responder Encuesta
</a>

O ir a la asignación: <a href="%s">Ver detalles</a>''' % (campaign.name, campaign.date_end, survey_url, assignment_url)),
            }
            self.env['mail.activity'].create(activity_vals)
            # Enviar correo si tiene email laboral
            if employee.work_email:
                mail_values = {
                    'subject': _('Encuesta asignada: %s', campaign.name),
                    'email_to': employee.work_email,
                    'body_html': f'''
                        <div style="margin: 0px; padding: 0px;">
                            <p>Hola {employee.name},</p>
                            <p>Se te ha asignado una nueva encuesta: <strong>{campaign.name}</strong></p>
                            <p><strong>Fecha límite:</strong> {campaign.date_end}</p>
                            <br/>
                            <p style="text-align: center;">
                                <a href="{assignment_url}" 
                                   style="background-color: #875A7B; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                                    Ver Asignación de Encuesta
                                </a>
                            </p>
                            <br/>
                            <p>O copia y pega este enlace en tu navegador:</p>
                            <p>{assignment_url}</p>
                            <br/>
                            <p>Gracias por tu participación.</p>
                        </div>
                    ''',
                }
                self.env['mail.mail'].create(mail_values).send()
        return assignment

    def action_open_survey(self):
        self.ensure_one()
        # Usar sudo() para acceder a la campaña sin restricciones de permisos
        campaign = self.sudo().campaign_id
        survey = campaign.survey_id
        if not survey or not survey.access_token:
            raise exceptions.UserError('La encuesta base no tiene token público.')
        
        # Validar vigencia de la campaña
        from datetime import date
        today = date.today()
        if campaign.state != 'active' or not (campaign.date_start <= today <= campaign.date_end):
            raise exceptions.UserError(_('No puede responder la encuesta fuera del periodo de vigencia.'))
        
        # Buscar participación existente
        UserInput = self.env['survey.user_input']
        user_input = UserInput.search([
            ('survey_id', '=', survey.id),
            ('partner_id', '=', self.employee_id.user_id.partner_id.id),
            ('assignment_id', '=', self.id)
        ], limit=1)
        
        # Solo crear participación si no existe
        if not user_input:
            user_input = UserInput.create({
                'survey_id': survey.id,
                'partner_id': self.employee_id.user_id.partner_id.id,
                'employee_id': self.employee_id.id,
                'campaign_id': campaign.id,
                'assignment_id': self.id,
                'state': 'new',  # Estado inicial cuando empieza
                'email': self.employee_id.user_id.email or self.employee_id.work_email,
                'is_admin_assigned': True,
                'assigned_by_id': self.env.user.id,
                'assigned_to_ids': [(4, self.employee_id.user_id.partner_id.id)],
            })
            # Actualizar la asignación con la participación
            self.write({'user_input_id': user_input.id})
        
        url = f'/survey/start/{survey.access_token}'
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'self',
        }

    def action_open_survey_from_activity(self):
        return self.action_open_survey()
    
    def update_assignment_state(self):
        """Actualizar el estado de la asignación basado en la participación"""
        for assignment in self:
            if assignment.user_input_id:
                if assignment.user_input_id.state == 'done':
                    assignment.write({'state': 'answered'})
                elif assignment.user_input_id.state == 'new':
                    assignment.write({'state': 'pending'})
    
    def check_and_update_state(self):
        """Verificar y actualizar el estado de la asignación"""
        for assignment in self:
            if assignment.user_input_id:
                if assignment.user_input_id.state == 'done':
                    assignment.write({'state': 'answered'})
                elif assignment.user_input_id.state in ['new', 'skip']:
                    assignment.write({'state': 'pending'})
    
    @api.model
    def update_all_assignment_states(self):
        """Actualizar el estado de todas las asignaciones basado en sus participaciones"""
        assignments = self.search([])
        for assignment in assignments:
            assignment.check_and_update_state() 