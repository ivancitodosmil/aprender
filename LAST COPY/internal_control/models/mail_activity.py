# -*- coding: utf-8 -*-
from odoo import models, api

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    def action_open_survey_from_activity(self):
        self.ensure_one()
        if self.res_model == 'in.survey.campaign.assignment':
            assignment = self.env['in.survey.campaign.assignment'].browse(self.res_id)
            if assignment.exists():
                return assignment.action_open_survey()
        return False 