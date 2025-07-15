# -*- coding: utf-8 -*-
"""
Modelos de métricas de encuestas: revisados, cumplimiento, satisfacción, participación.
Incluye: SurveyRevisedItems, SurveyCompliance, SurveySatisfaction, SurveyParticipation.
"""
from odoo import models, fields, api

class SurveyRevisedItems(models.Model):
    _name = 'survey.revised.items'
    _description = 'Métricas de Items Revisados'

    calculate_report_id = fields.Many2one('survey.calculate.report', string='Reporte de Cálculo', ondelete='cascade')
    page_id = fields.Many2one('survey.question', string='Sección', domain=[('is_page', '=', True)], ondelete='set null')
    page_name = fields.Char(string='Nombre de Sección')
    total_items_revisados = fields.Integer(string='Total Items Revisados')
    total_items_sin_novedad = fields.Integer(string='Total Items Sin Novedad')
    porcentaje_cumplimiento = fields.Float(string='Porcentaje de Cumplimiento', group_operator='avg')
    observations = fields.Text(string='Observaciones')

    survey_id = fields.Many2one(
        'survey.survey',
        string='Encuesta',
        related='calculate_report_id.user_input_id.survey_id',
        store=True
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Participante',
        related='calculate_report_id.user_input_id.partner_id',
        store=True
    )
    department_id = fields.Many2one(
        'hr.department',
        string='Departamento',
        related='campaign_id.department_id',
        store=True
    )
    campaign_id = fields.Many2one(
        'in.survey.campaign',
        string='Campaña',
        related='calculate_report_id.user_input_id.campaign_id',
        store=True
    )

class SurveyCompliance(models.Model):
    _name = 'survey.compliance'
    _description = 'Métricas de Cumplimiento'
    calculate_report_id = fields.Many2one('survey.calculate.report', string='Reporte de Cálculo', ondelete='cascade')
    page_id = fields.Many2one('survey.question', string='Sección', domain=[('is_page', '=', True)], ondelete='set null')
    page_name = fields.Char(string='Nombre de Sección')
    compliance_status = fields.Selection([
        ('cumple', 'Cumple'),
        ('no_cumple', 'No Cumple'),
        ('na', 'N/A')
    ], string='Estado')
    observations = fields.Text(string='Observaciones')
    porcentaje_cumplimiento = fields.Float(
        string='Porcentaje de Cumplimiento',
        compute='_compute_porcentaje_cumplimiento',
        store=True,
        group_operator='avg'
    )
    survey_id = fields.Many2one('survey.survey', string='Encuesta', related='calculate_report_id.user_input_id.survey_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Participante', related='calculate_report_id.user_input_id.partner_id', store=True)
    department_id = fields.Many2one('hr.department', string='Departamento', related='campaign_id.department_id', store=True)
    campaign_id = fields.Many2one(
        'in.survey.campaign',
        string='Campaña',
        related='calculate_report_id.user_input_id.campaign_id',
        store=True
    )

    @api.depends('compliance_status')
    def _compute_porcentaje_cumplimiento(self):
        for record in self:
            if record.compliance_status == 'cumple':
                record.porcentaje_cumplimiento = 100.0
            elif record.compliance_status == 'no_cumple':
                record.porcentaje_cumplimiento = 0.0
            else:
                record.porcentaje_cumplimiento = 0.0

class SurveySatisfaction(models.Model):
    _name = 'survey.satisfaction'
    _description = 'Métricas de Satisfacción'
    calculate_report_id = fields.Many2one('survey.calculate.report', string='Reporte de Cálculo', ondelete='cascade')
    page_id = fields.Many2one('survey.question', string='Sección', domain=[('is_page', '=', True)], ondelete='set null')
    page_name = fields.Char(string='Nombre de Sección')
    total_encuestas = fields.Integer(string='Total Encuestas')
    encuestas_positivas = fields.Integer(string='Encuestas Positivas')
    satisfaccion = fields.Float(string='Satisfacción')
    porcentaje_satisfaccion = fields.Float(string='Porcentaje de Satisfacción', group_operator='avg')
    survey_id = fields.Many2one('survey.survey', string='Encuesta', related='calculate_report_id.user_input_id.survey_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Participante', related='calculate_report_id.user_input_id.partner_id', store=True)
    department_id = fields.Many2one('hr.department', string='Departamento', related='campaign_id.department_id', store=True)
    anonymous_token = fields.Char()
    campaign_id = fields.Many2one(
        'in.survey.campaign',
        string='Campaña',
        related='calculate_report_id.user_input_id.campaign_id',
        store=True
    )
    observations = fields.Text(string='Observaciones')

class SurveyParticipation(models.Model):
    _name = 'survey.participation'
    _description = 'Métricas de Participación (Sí/No/No respondió)'
    calculate_report_id = fields.Many2one('survey.calculate.report', string='Reporte de Cálculo', ondelete='cascade')
    page_id = fields.Many2one('survey.question', string='Sección', domain=[('is_page', '=', True)], ondelete='set null')
    page_name = fields.Char(string='Nombre de Sección')
    respuestas_si = fields.Integer(string='Sí', default=0)
    respuestas_no = fields.Integer(string='No', default=0)
    no_respondieron = fields.Integer(string='No respondió', default=0)
    total_respuestas = fields.Integer(string='Total Respuestas', compute='_compute_totals', store=True)
    porcentaje_participacion = fields.Float(string='% de Participación', compute='_compute_porcentaje_participacion', store=True, group_operator='avg')
    survey_id = fields.Many2one('survey.survey', string='Encuesta', related='calculate_report_id.user_input_id.survey_id', store=True)
    partner_id = fields.Many2one('res.partner', string='Participante', related='calculate_report_id.user_input_id.partner_id', store=True)
    department_id = fields.Many2one('hr.department', string='Departamento', related='campaign_id.department_id', store=True)
    employee_id = fields.Many2one('hr.employee', string='Empleado', related='calculate_report_id.user_input_id.employee_id', store=True)
    anonymous_token = fields.Char()
    campaign_id = fields.Many2one(
        'in.survey.campaign',
        string='Campaña',
        related='calculate_report_id.user_input_id.campaign_id',
        store=True
    )

    @api.depends('respuestas_si', 'respuestas_no', 'no_respondieron')
    def _compute_totals(self):
        for record in self:
            record.total_respuestas = record.respuestas_si + record.respuestas_no + record.no_respondieron

    @api.depends('respuestas_si', 'respuestas_no', 'total_respuestas')
    def _compute_porcentaje_participacion(self):
        for record in self:
            if record.total_respuestas > 0:
                participaron = record.respuestas_si + record.respuestas_no
                record.porcentaje_participacion = (participaron / record.total_respuestas) * 100
            else:
                record.porcentaje_participacion = 0.0

