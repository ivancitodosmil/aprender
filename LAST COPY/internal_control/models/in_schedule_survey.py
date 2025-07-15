# -*- coding: utf-8 -*-
"""
Modelos y lógica relacionada a fechas de encuestas y cron jobs.
Incluye: SurveyDates y métodos de envío programado.
"""
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class SurveyDates(models.Model):
    _name = 'survey.dates'
    _description = 'Survey Dates'

    name = fields.Char(string='Nombre', required=True)
    start_date = fields.Date(string='Fecha de Inicio', required=True)
    end_date = fields.Date(string='Fecha de Fin', required=True)
    state = fields.Selection(
        [('draft', 'Borrador'), ('open', 'Abierto'), ('closed', 'Cerrado')],
        string='Estado',
    )
    survey_id = fields.Many2one('survey.survey', string='Encuesta', required=True)
    department_id = fields.Many2one('hr.department', string='Departamento', required=True)
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Empleados a Invitar',
        domain="[('department_id', '=', department_id)]",
        help='Empleados que recibirán la invitación a la encuesta en este periodo.'
    )

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for record in self:
            if record.start_date > record.end_date:
                raise ValidationError(_("The start date cannot be after the end date."))

    @api.onchange('department_id')
    def _onchange_department_id(self):
        """Limpiar empleados seleccionados cuando cambia el departamento"""
        if self.department_id:
            self.employee_ids = [(5, 0, 0)]  # Limpiar selección actual

    @classmethod
    def send_scheduled_survey(cls, env):
        today = fields.Date.today()
        survey_dates = env['survey.dates'].search([
            ('state', '=', 'open'),
            ('start_date', '<=', today),
            ('end_date', '>=', today)
        ])
        for survey_date in survey_dates:
            try:
                survey = survey_date.survey_id
                if not survey:
                    _logger.warning(f"No se encontró la encuesta para survey_date {survey_date.id}")
                    continue
                template = env.ref('survey.mail_template_user_input_invite')
                if not template:
                    _logger.warning("No se encontró el template de invitación de encuesta")
                    continue
                partner_ids = survey_date.employee_ids.mapped('user_id.partner_id').ids
                if not partner_ids:
                    _logger.warning(f"No hay empleados asignados para la encuesta {survey.name} en este periodo")
                    continue
                local_context = dict(
                    env.context,
                    default_survey_id=survey.id,
                    default_use_template=bool(template),
                    default_template_id=template and template.id or False,
                    notif_layout='mail.mail_notification_light',
                )
                record = env["survey.invite"].sudo().with_context(local_context).create({
                    'partner_ids': [(4, contact_id) for contact_id in partner_ids],
                    'survey_id': survey.id,
                    'subject': f"Invitación a participar en: {survey.title}",
                    'body': f"""
                    <p>Hola,</p>
                    <p>Has sido invitado a participar en la encuesta: <strong>{survey.title}</strong></p>
                    <p>Esta encuesta estará disponible desde: {survey_date.start_date} hasta: {survey_date.end_date}</p>
                    <p>Por favor, completa la encuesta antes de la fecha de cierre.</p>
                    <p>Gracias por tu participación.</p>
                    """
                })
                record.action_invite()
                if survey_date.end_date == today:
                    survey_date.write({'state': 'closed'})
            except Exception as e:
                _logger.error(f"Error al enviar invitación para survey_date {survey_date.id}: {str(e)}")
                continue

