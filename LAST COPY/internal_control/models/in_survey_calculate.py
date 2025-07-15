# -*- coding: utf-8 -*-
"""
Reporte de cálculo y métodos asociados.
Incluye: SurveyCalculateReport y lógica asociada.
"""
from odoo import models, fields, api, _
import logging

_logger = logging.getLogger(__name__)

class SurveyCalculateReport(models.Model):
    _name = 'survey.calculate.report'
    _description = 'Reporte de Cálculo'
    _rec_name = 'name'

    name = fields.Char(string="Nombre del Reporte", required=True, readonly=True)
    user_input_id = fields.Many2one('survey.user_input', string='Respuesta de la Encuesta', ondelete='cascade')
    category_id = fields.Many2one('survey.category', string='Categoría', ondelete='set null')
    calculated_date = fields.Date(string='Fecha de Cálculo', default=fields.Date.context_today)

    def compute_metrics(self):
        for report in self:
            try:
                category = report.category_id
                if not category:
                    _logger.warning(f"No se encontró categoría para el reporte {report.id}")
                    continue
                

                if category.name == 'revision_items':
                    self._compute_metrics_for_revised_items(report)
                elif category.name == 'compliance':
                    self._compute_metrics_for_compliance(report)
                elif category.name == 'satisfaction':
                    self._compute_metrics_for_satisfaction(report)
                elif category.name == 'participation':
                    self._compute_metrics_for_participation(report)
                else:
                    _logger.warning(f"Categoría no reconocida: {category.name}")
                    
            except Exception as e:
                _logger.error(f"Error al calcular métricas para el reporte {report.id}: {str(e)}")

    def _compute_metrics_for_revised_items(self, report):
        user_input = report.user_input_id
        if not user_input:
            _logger.error("No se encontró user_input")
            return

        # Obtener todas las páginas (secciones) de la encuesta
        pages = self.env['survey.question'].search([
            ('survey_id', '=', user_input.survey_id.id),
            ('is_page', '=', True)
        ])

        # Eliminar registros existentes si los hay
        existing_items = self.env['survey.revised.items'].search([
            ('calculate_report_id', '=', report.id)
        ])
        if existing_items:
            existing_items.unlink()

        for page in pages:
            total_revisados = 0
            total_sin_novedad = 0

            # Buscar todas las respuestas de la encuesta para esta sección
            respuestas = self.env['survey.user_input.line'].search([
                ('user_input_id', '=', user_input.id),
                ('question_id.question_type', '=', 'numerical_box'),
                ('question_id.page_id', '=', page.id)
            ])

            for resp in respuestas:
                # Obtener el título de la pregunta
                pregunta = resp.question_id.title
                if isinstance(pregunta, dict):
                    pregunta = pregunta.get('es_EC', '')
                pregunta = pregunta.lower()

                if resp.value_numerical_box is not None:
                    valor = float(resp.value_numerical_box)

                    # Clasificar según el tipo de pregunta
                    if "revisados" in pregunta and "sin novedad" in pregunta:
                        total_sin_novedad += valor
                    elif "revisados" in pregunta:
                        total_revisados += valor

            # Calcular el porcentaje de cumplimiento
            porcentaje = 0
            if total_revisados > 0:
                porcentaje = (total_sin_novedad / total_revisados) * 100

            # Obtener el título de la página
            page_title = page.title
            if isinstance(page_title, dict):
                page_title = page_title.get('es_EC', '')

            # Crear el registro de métricas para esta sección
            try:
                vals = {
                    'calculate_report_id': report.id,
                    'page_id': page.id,
                    'page_name': page_title,
                    'total_items_revisados': total_revisados,
                    'total_items_sin_novedad': total_sin_novedad,
                    'porcentaje_cumplimiento': porcentaje
                }
                self.env['survey.revised.items'].create(vals)
            except Exception as e:
                _logger.error(f"Error al crear registro para sección {page_title}: {str(e)}")
                raise

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = f"Reporte #{vals.get('user_input_id', 'Nuevo')}"
        record = super().create(vals)
        return record

    def _compute_metrics_for_compliance(self, report):
        user_input = report.user_input_id
        if not user_input:
            _logger.error("No se encontró user_input")
            return
        pages = self.env['survey.question'].search([
            ('survey_id', '=', user_input.survey_id.id),
            ('is_page', '=', True)
        ])
        existing_compliance = self.env['survey.compliance'].search([
            ('calculate_report_id', '=', report.id)
        ])
        if existing_compliance:
            existing_compliance.unlink()
        for page in pages:
            preguntas = self.env['survey.question'].search([
                ('page_id', '=', page.id),
                ('is_page', '=', False)
            ])
            respuesta_cumplimiento = self.env['survey.user_input.line'].search([
                ('user_input_id', '=', user_input.id),
                ('question_id', 'in', preguntas.filtered(lambda q: q.question_type == 'simple_choice').ids)
            ], limit=1)
            respuesta_observaciones = self.env['survey.user_input.line'].search([
                ('user_input_id', '=', user_input.id),
                ('question_id', 'in', preguntas.filtered(lambda q: q.question_type == 'text_box').ids)
            ], limit=1)
            estado = 'na'
            if respuesta_cumplimiento and respuesta_cumplimiento.answer_type == 'suggestion':
                suggested_answer = self.env['survey.question.answer'].search([
                    ('id', '=', respuesta_cumplimiento.suggested_answer_id.id)
                ], limit=1)
                if suggested_answer and suggested_answer.value:
                    try:
                        valor_raw = suggested_answer.value
                        valor = valor_raw.get('es_EC', '') if isinstance(valor_raw, dict) else valor_raw
                        if valor == 'Cumple':
                            estado = 'cumple'
                        elif valor == 'No Cumple':
                            estado = 'no_cumple'
                    except Exception as e:
                        _logger.error(f"Error al procesar el valor: {str(e)}")
                        _logger.error(f"Valor que causó el error: {suggested_answer.value}")
            observaciones = ''
            if respuesta_observaciones and respuesta_observaciones.answer_type == 'text_box':
                observaciones = respuesta_observaciones.value_text_box or ''
            page_title = page.title
            if isinstance(page_title, dict):
                page_title = page_title.get('es_EC', '')
            self.env['survey.compliance'].create({
                'calculate_report_id': report.id,
                'page_id': page.id,
                'page_name': page_title,
                'compliance_status': estado,
                'observations': observaciones
            })

    def _compute_metrics_for_satisfaction(self, report):
        user_input = report.user_input_id
        if not user_input:
            _logger.error("No se encontró user_input")
            return
        pages = self.env['survey.question'].search([
            ('survey_id', '=', user_input.survey_id.id),
            ('is_page', '=', True),
            ('title', 'in', ['Departamento', 'Preguntas'])
        ])
        if len(pages) != 2:
            _logger.error(f"Se esperaban 2 secciones (Departamento y Preguntas), se encontraron {len(pages)}")
            return
        departamento_page = pages.filtered(lambda p: p.title == 'Departamento')
        preguntas_page = pages.filtered(lambda p: p.title == 'Preguntas')
        if not departamento_page or not preguntas_page:
            _logger.error("No se encontraron las secciones requeridas")
            return
        existing_satisfaction = self.env['survey.satisfaction'].search([
            ('calculate_report_id', '=', report.id)
        ])
        if existing_satisfaction:
            existing_satisfaction.unlink()
        respuestas = self.env['survey.user_input.line'].search([
            ('user_input_id', '=', user_input.id),
            ('question_id.page_id', '=', preguntas_page.id),
            ('answer_type', '=', 'suggestion')
        ])
        total_respuestas = len(respuestas)
        suma_calificaciones = 0
        respuestas_positivas = 0
        for respuesta in respuestas:
            suggested_answer = self.env['survey.question.answer'].search([
                ('id', '=', respuesta.suggested_answer_id.id)
            ], limit=1)
            if suggested_answer:
                valor = suggested_answer.value
                if isinstance(valor, dict):
                    valor = valor.get('es_EC', '')
                try:
                    calificacion = int(valor)
                    if 1 <= calificacion <= 5:
                        suma_calificaciones += calificacion
                        if calificacion >= 4:
                            respuestas_positivas += 1
                except (ValueError, TypeError):
                    _logger.warning(f"Valor no numérico encontrado: {valor}")
        promedio_satisfaccion = 0
        porcentaje_satisfaccion = 0
        if total_respuestas > 0:
            promedio_satisfaccion = suma_calificaciones / total_respuestas
            porcentaje_satisfaccion = (respuestas_positivas / total_respuestas) * 100
        try:
            vals = {
                'calculate_report_id': report.id,
                'page_id': preguntas_page.id,
                'page_name': 'Preguntas',
                'total_encuestas': total_respuestas,
                'encuestas_positivas': respuestas_positivas,
                'satisfaccion': promedio_satisfaccion,  
                'porcentaje_satisfaccion': porcentaje_satisfaccion  
            }
            self.env['survey.satisfaction'].create(vals)
        except Exception as e:
            _logger.error(f"Error al crear registro de satisfacción: {str(e)}")
            raise

    def _compute_metrics_for_participation(self, report):
        user_input = report.user_input_id
        if not user_input:
            _logger.error("No se encontró user_input")
            return
        pages = self.env['survey.question'].search([
            ('survey_id', '=', user_input.survey_id.id),
            ('is_page', '=', True)
        ])
        existing_participation = self.env['survey.participation'].search([
            ('calculate_report_id', '=', report.id)
        ])
        if existing_participation:
            existing_participation.unlink()
        for page in pages:
            preguntas_si_no = self.env['survey.question'].search([
                ('page_id', '=', page.id),
                ('is_page', '=', False),
                ('question_type', '=', 'simple_choice')
            ])
            respuestas_si = 0
            respuestas_no = 0
            no_respondieron = 0
            for pregunta in preguntas_si_no:
                respuesta = self.env['survey.user_input.line'].search([
                    ('user_input_id', '=', user_input.id),
                    ('question_id', '=', pregunta.id)
                ], limit=1)
                if respuesta:
                    if respuesta.answer_type == 'suggestion':
                        suggested_answer = self.env['survey.question.answer'].search([
                            ('id', '=', respuesta.suggested_answer_id.id)
                        ], limit=1)
                        valor = None
                        if suggested_answer and suggested_answer.value:
                            valor_raw = suggested_answer.value
                            valor = valor_raw.get('es_EC', '') if isinstance(valor_raw, dict) else valor_raw
                        if valor == 'Sí':
                            respuestas_si += 1
                        elif valor == 'No':
                            respuestas_no += 1
                        else:
                            no_respondieron += 1
                    else:
                        no_respondieron += 1
                else:
                    no_respondieron += 1
            total_respuestas = respuestas_si + respuestas_no + no_respondieron
            porcentaje_participacion = ((respuestas_si + respuestas_no) / total_respuestas) * 100 if total_respuestas > 0 else 0.0
            self.env['survey.participation'].create({
                'calculate_report_id': report.id,
                'page_id': page.id,
                'page_name': page.title,
                'respuestas_si': respuestas_si,
                'respuestas_no': respuestas_no,
                'no_respondieron': no_respondieron,
                'total_respuestas': total_respuestas,
                'porcentaje_participacion': porcentaje_participacion,
            })

    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not record.name:
            record.name = f"Participación #{record.id}"
        return record