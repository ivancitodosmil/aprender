# -*- coding: utf-8 -*-
"""
Herencia de survey.survey, modelos de categoría y etiquetas de encuestas.
Incluye: SurveySurvey, SurveyCategory, SurveyTag.
"""
from odoo import models, fields, api, _
import logging
from odoo.exceptions import UserError
import base64
import json
import re

_logger = logging.getLogger(__name__)

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    category_id = fields.Many2one('survey.category', string='Categoría', required=False)
    tag_ids = fields.Many2many('survey.tag', string='Etiquetas')
    # group_ids = fields.Many2many('res.groups', string='Assigned Groups')
    is_anonymous = fields.Boolean(string='Encuesta Anónima', default=False)
    department_id = fields.Many2one('hr.department', string='Departamento', required=False)

    start_date = fields.Datetime(string='Fecha de Inicio')
    end_date = fields.Datetime(string='Fecha de Fin')

    def is_active(self):
        """Verificar si la encuesta está activa según las fechas"""
        self.ensure_one()
        now = fields.Datetime.now()
        
        # Si no hay fechas, está activa
        if not self.start_date and not self.end_date:
            return True
            
        # Verificar fecha de inicio
        if self.start_date and now < self.start_date:
            return False
            
        # Verificar fecha de fin
        if self.end_date and now > self.end_date:
            return False
            
        return True
    
    @api.model
    def send_scheduled_survey(self):
        """Send emails for scheduled survey runs"""

        today = fields.Date.today()
        
        survey_dates = self.env['survey.dates'].search([
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
                
                # Obtener el template de invitación
                template = self.env.ref('survey.mail_template_user_input_invite')
                if not template:
                    _logger.warning("No se encontró el template de invitación de encuesta")
                    continue
                
                # Obtener los partners de los empleados seleccionados en survey_date
                partner_ids = survey_date.employee_ids.mapped('user_id.partner_id').ids
                if not partner_ids:
                    _logger.warning(f"No hay empleados asignados para la encuesta {survey.name} en este periodo")
                    continue
                
                # Crear el contexto para la invitación
                local_context = dict(
                    self.env.context,
                    default_survey_id=survey.id,
                    default_use_template=bool(template),
                    default_template_id=template and template.id or False,
                    notif_layout='mail.mail_notification_light',
                )
                
                # Crear y enviar la invitación
                record = self.env["survey.invite"].sudo().with_context(local_context).create({
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
                
                # Enviar la invitación
                record.action_invite()
                
                # Opcional: Cambiar el estado a 'closed' si la fecha de fin es hoy
                if survey_date.end_date == today:
                    survey_date.write({'state': 'closed'})

            except Exception as e:
                _logger.error(f"Error al enviar invitación para survey_date {survey_date.id}: {str(e)}")
                continue

    def action_export_results(self):
        """Abre el wizard para exportar resultados de la encuesta"""
        self.ensure_one()
        return {
            'name': _('Exportar Resultados'),
            'type': 'ir.actions.act_window',
            'res_model': 'survey.export.report',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_survey_id': self.id,
            }
        }

    def action_exportar_estructura(self):
        """Exporta la estructura de la encuesta como JSON (sin respuestas de usuarios)"""
        self.ensure_one()
        datos = {}
        datos['encuesta'] = {
            'title': self.title,
            'description': self.description,
            'category': self.category_id and {
                'name': self.category_id.name,
                'code': self.category_id.code,
                'description': self.category_id.description,
            } or {},
            'tags': [
                {'name': tag.name, 'color': tag.color}
                for tag in self.tag_ids
            ],
            'questions': []
        }
        questions = self.env['survey.question'].search([('survey_id', '=', self.id)])
        for q in questions:
            question_data = {
                'title': q.title,
                'description': q.description,
                'question_type': q.question_type,
                'sequence': q.sequence,
                'is_page': q.is_page,
                'matrix_subtype': q.matrix_subtype,
                'question_placeholder': q.question_placeholder,
                'comments_message': q.comments_message,
                'validation_error_msg': q.validation_error_msg,
                'constr_error_msg': q.constr_error_msg,
                'is_scored_question': q.is_scored_question,
                'save_as_email': q.save_as_email,
                'save_as_nickname': q.save_as_nickname,
                'is_time_limited': q.is_time_limited,
                'comments_allowed': q.comments_allowed,
                'comment_count_as_answer': q.comment_count_as_answer,
                'validation_required': q.validation_required,
                'validation_email': q.validation_email,
                'constr_mandatory': q.constr_mandatory,
                'answer_numerical_box': q.answer_numerical_box,
                'answer_score': q.answer_score,
                'validation_length_min': q.validation_length_min,
                'validation_length_max': q.validation_length_max,
                'validation_min_date': q.validation_min_date,
                'validation_max_date': q.validation_max_date,
                'validation_min_float_value': q.validation_min_float_value,
                'validation_max_float_value': q.validation_max_float_value,
                'answers': []
            }
            answers = self.env['survey.question.answer'].search([('question_id', '=', q.id)])
            for a in answers:
                answer_data = {
                    'value': a.value,
                    'is_correct': getattr(a, 'is_correct', False),
                    'suggested_score': getattr(a, 'suggested_score', 0),
                    'sequence': a.sequence,
                }
                question_data['answers'].append(answer_data)
            datos['encuesta']['questions'].append(question_data)
        # Generar archivo JSON
        json_data = json.dumps(datos, ensure_ascii=False, indent=2, default=str)
        # Nombre del archivo: solo el nombre de la encuesta, sin espacios, minúsculas
        nombre = self.title
        if isinstance(nombre, dict):
            nombre = nombre.get('es_EC') or nombre.get('en_US') or list(nombre.values())[0]
        nombre_archivo = re.sub(r'\W+', '_', nombre).lower() + '.json'
        # Crear adjunto temporal
        adjunto = self.env['ir.attachment'].create({
            'name': nombre_archivo,
            'type': 'binary',
            'datas': base64.b64encode(json_data.encode('utf-8')),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/json',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{adjunto.id}?download=true',
            'target': 'self',
        }

    def action_abrir_importar_estructura(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'importar.estructura.encuesta.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def create(self, vals):
        vals['survey_type'] = 'survey'
        return super(SurveySurvey, self).create(vals)

    def write(self, vals):
        vals['survey_type'] = 'survey'
        return super(SurveySurvey, self).write(vals)


class SurveyCategory(models.Model):
    _name = 'survey.category'
    _description = 'Categoría de Encuesta'

    name = fields.Char(string='Nombre', required=True)
    code = fields.Char(string='Código')
    description = fields.Text(string='Descripción')
    active = fields.Boolean(string='Activo', default=True)
    require_metrics = fields.Boolean(string='Requiere Métricas', default=False)

class SurveyTag(models.Model):
    _name = 'survey.tag'
    _description = 'Etiqueta de Encuesta'

    name = fields.Char(string='Nombre', required=True)
    color = fields.Integer(string='Índice de Color')
    active = fields.Boolean(string='Activo', default=True)

class ImportarEstructuraEncuestaWizard(models.TransientModel):
    _name = 'importar.estructura.encuesta.wizard'
    _description = 'Importar estructura de encuesta desde JSON'

    archivo_json = fields.Binary('Archivo JSON', required=True)
    nombre_archivo = fields.Char('Nombre del archivo')

    def action_importar(self):
        self.ensure_one()
        if not self.archivo_json:
            raise UserError('Debe seleccionar un archivo JSON.')
        try:
            contenido = base64.b64decode(self.archivo_json)
            datos = json.loads(contenido)
            datos_encuesta = datos.get('encuesta')
            if not datos_encuesta:
                raise UserError('El archivo no contiene la estructura esperada.')
            # --- Categoría ---
            categoria = None
            cat_data = datos_encuesta.get('category')
            if cat_data and cat_data.get('name'):
                categoria = self.env['survey.category'].search([('name', '=', cat_data['name'])], limit=1)
                if not categoria:
                    categoria = self.env['survey.category'].create({
                        'name': cat_data['name'],
                        'code': cat_data.get('code', ''),
                        'description': cat_data.get('description', ''),
                        'active': True,
                    })
            # --- Etiquetas ---
            tag_ids = []
            for tag in datos_encuesta.get('tags', []):
                tag_obj = self.env['survey.tag'].search([('name', '=', tag['name'])], limit=1)
                if not tag_obj:
                    tag_obj = self.env['survey.tag'].create({
                        'name': tag['name'],
                        'color': tag.get('color', 0),
                        'active': True,
                    })
                tag_ids.append(tag_obj.id)
            # --- Encuesta ---
            nueva_encuesta = self.env['survey.survey'].create({
                'title': datos_encuesta.get('title'),
                'description': datos_encuesta.get('description'),
                'category_id': categoria and categoria.id or False,
                'tag_ids': [(6, 0, tag_ids)],
                'active': True,
            })
            # --- Preguntas y respuestas ---
            for pregunta in datos_encuesta.get('questions', []):
                nueva_pregunta = self.env['survey.question'].create({
                    'survey_id': nueva_encuesta.id,
                    'title': pregunta.get('title'),
                    'description': pregunta.get('description'),
                    'question_type': pregunta.get('question_type'),
                    'sequence': pregunta.get('sequence'),
                    'is_page': pregunta.get('is_page'),
                    'matrix_subtype': pregunta.get('matrix_subtype'),
                    'question_placeholder': pregunta.get('question_placeholder'),
                    'comments_message': pregunta.get('comments_message'),
                    'validation_error_msg': pregunta.get('validation_error_msg'),
                    'constr_error_msg': pregunta.get('constr_error_msg'),
                    'is_scored_question': pregunta.get('is_scored_question'),
                    'save_as_email': pregunta.get('save_as_email'),
                    'save_as_nickname': pregunta.get('save_as_nickname'),
                    'is_time_limited': pregunta.get('is_time_limited'),
                    'comments_allowed': pregunta.get('comments_allowed'),
                    'comment_count_as_answer': pregunta.get('comment_count_as_answer'),
                    'validation_required': pregunta.get('validation_required'),
                    'validation_email': pregunta.get('validation_email'),
                    'constr_mandatory': pregunta.get('constr_mandatory'),
                    'answer_numerical_box': pregunta.get('answer_numerical_box'),
                    'answer_score': pregunta.get('answer_score'),
                    'validation_length_min': pregunta.get('validation_length_min'),
                    'validation_length_max': pregunta.get('validation_length_max'),
                    'validation_min_date': pregunta.get('validation_min_date'),
                    'validation_max_date': pregunta.get('validation_max_date'),
                    'validation_min_float_value': pregunta.get('validation_min_float_value'),
                    'validation_max_float_value': pregunta.get('validation_max_float_value'),
                })
                for respuesta in pregunta.get('answers', []):
                    self.env['survey.question.answer'].create({
                        'question_id': nueva_pregunta.id,
                        'value': respuesta.get('value'),
                        'is_correct': respuesta.get('is_correct', False),
                        'sequence': respuesta.get('sequence'),
                    })
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Importación exitosa',
                    'message': 'La encuesta fue importada correctamente.',
                    'type': 'success',
                    'sticky': False,
                }
            }
        except Exception as e:
            raise UserError(f'Error al importar la encuesta: {str(e)}')