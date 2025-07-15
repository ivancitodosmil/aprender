# -*- coding: utf-8 -*-
"""
Modelos y lógica para exportación de reportes de encuestas.
Incluye: wizard de exportar reportes.
"""
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import logging

_logger = logging.getLogger(__name__)

class SurveyExportReport(models.TransientModel):
    _name = 'survey.export.report'
    _description = 'Exportar Reporte de Encuesta'
    survey_id = fields.Many2one('survey.survey', string='Encuesta', required=True)
    observations = fields.Text(string='Observaciones', help='Observaciones adicionales para el reporte')

    def action_export_pdf(self):
        self.ensure_one()
        category = self.survey_id.category_id
        if not category:
            raise UserError(_("La encuesta no tiene categoría asignada."))
        if category.name == 'revision_items':
            return self._export_revised_items_report()
        elif category.name == 'compliance':
            return self._export_compliance_report()
        elif category.name == 'satisfaction':
            return self._export_satisfaction_report()
        elif category.name == 'participation':
            return self._export_participation_report()
        else:
            raise UserError(_("Categoría de encuesta no soportada para reportes: %s") % category.name)

    def _export_revised_items_report(self):
        try:
            metrics = self.env['survey.revised.items'].search([
                ('survey_id', '=', self.survey_id.id)
            ])
            if self.observations:
                metrics.write({'observations': self.observations})
            report = self.env.ref('internal_control.action_report_survey_revised_items')
            pdf_content, content_type = report.with_context(discard_logo_check=True)._render_qweb_pdf(
                report.id, metrics.ids
            )
            if not pdf_content:
                raise UserError(_("Failed to generate PDF. Please try again."))
            filename = f"Reporte_Items_Revisados_{self.survey_id.title}.pdf"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("PDF Export Error: %s", str(e))
            raise UserError(_("Failed to export PDF: %s") % str(e))

    def _export_compliance_report(self):
        try:
            metrics = self.env['survey.compliance'].search([
                ('survey_id', '=', self.survey_id.id)
            ])
            if self.observations:
                metrics.write({'observations': self.observations})
            report = self.env.ref('internal_control.action_report_survey_compliance')
            pdf_content, content_type = report.with_context(discard_logo_check=True)._render_qweb_pdf(
                report.id, metrics.ids
            )
            if not pdf_content:
                raise UserError(_("Failed to generate PDF. Please try again."))
            filename = f"Reporte_Cumplimiento_{self.survey_id.title}.pdf"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("PDF Export Error: %s", str(e))
            raise UserError(_("Failed to export PDF: %s") % str(e))

    def _export_satisfaction_report(self):
        try:
            metrics = self.env['survey.satisfaction'].search([
                ('survey_id', '=', self.survey_id.id)
            ])
            if self.observations:
                metrics.write({'observations': self.observations})
            report = self.env.ref('internal_control.action_report_survey_satisfaction')
            pdf_content, content_type = report.with_context(discard_logo_check=True)._render_qweb_pdf(
                report.id, metrics.ids
            )
            if not pdf_content:
                raise UserError(_("Failed to generate PDF. Please try again."))
            filename = f"Reporte_Satisfaccion_{self.survey_id.title}.pdf"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("PDF Export Error: %s", str(e))
            raise UserError(_("Failed to export PDF: %s") % str(e))

    def _export_participation_report(self):
        try:
            metrics = self.env['survey.participation'].search([
                ('survey_id', '=', self.survey_id.id)
            ])
            if self.observations:
                metrics.write({'observations': self.observations})
            report = self.env.ref('internal_control.action_report_survey_participation')
            pdf_content, content_type = report.with_context(discard_logo_check=True)._render_qweb_pdf(
                report.id, metrics.ids
            )
            if not pdf_content:
                raise UserError(_("Failed to generate PDF. Please try again."))
            filename = f"Reporte_Participacion_{self.survey_id.title}.pdf"
            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/pdf'
            })
            return {
                'type': 'ir.actions.act_url',
                'url': f'/web/content/{attachment.id}?download=true',
                'target': 'self',
            }
        except Exception as e:
            _logger.error("PDF Export Error: %s", str(e))
            raise UserError(_("Failed to export PDF: %s") % str(e))

