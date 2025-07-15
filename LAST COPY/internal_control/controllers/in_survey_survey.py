from odoo import http
from odoo.http import request
from odoo.addons.survey.controllers.main import Survey
import logging

_logger = logging.getLogger(__name__)

class InSurveySurvey(Survey):
    @http.route(['/survey/start/<string:survey_token>'], type='http', auth='public', website=True, sitemap=False)
    def survey_start(self, survey_token=None, answer_token=None, **post):
        _logger.info(f"[CONTROLLER DEBUG] survey_start called with survey_token: {survey_token}, answer_token: {answer_token}")
        # Captura los parámetros extra
        campaign_id = request.params.get('campaign_id')
        assignment_id = request.params.get('assignment_id')
        if campaign_id or assignment_id:
            request.context = dict(request.context)
            if campaign_id:
                request.context['default_campaign_id'] = int(campaign_id)
            if assignment_id:
                request.context['default_assignment_id'] = int(assignment_id)
        return super(InSurveySurvey, self).survey_start(survey_token=survey_token, answer_token=answer_token, **post)

    @http.route('/survey/<string:survey_token>/<string:answer_token>', type='http', auth='public', website=True)
    def survey_display_page(self, survey_token, answer_token, **post):
        _logger.info(f"[CONTROLLER DEBUG] survey_display_page called with survey_token: {survey_token}, answer_token: {answer_token}")
        _logger.info(f"[CONTROLLER DEBUG] POST data keys: {list(post.keys())}")
        _logger.info(f"[CONTROLLER DEBUG] Files in request: {list(request.httprequest.files.keys()) if request.httprequest.files else 'No files'}")
        
        # Log more details about the POST data
        for key, value in post.items():
            _logger.info(f"[CONTROLLER DEBUG] POST[{key}]: type={type(value)}, value={value}")
        
        # Log file details
        if request.httprequest.files:
            for key, file_obj in request.httprequest.files.items():
                _logger.info(f"[CONTROLLER DEBUG] FILE[{key}]: filename={file_obj.filename}, content_type={file_obj.content_type}")
            # Merge uploaded files into post data for image questions
            for key, file_obj in request.httprequest.files.items():
                post[key] = file_obj
        
        # Let the parent handle everything, including image uploads
        return super(InSurveySurvey, self).survey_display_page(survey_token, answer_token, **post)

    @http.route('/survey/get_answer_image/<string:survey_token>/<string:answer_token>/<int:question_id>', type='http', auth='public', website=True, sitemap=False)
    def survey_get_answer_image(self, survey_token, answer_token, question_id):
        """Display uploaded images from survey answers"""
        access_data = self._get_access_data(survey_token, answer_token, ensure_token=True)
        if access_data['validity_code'] is not True:
            return http.request.not_found()
        
        survey_sudo, answer_sudo = access_data['survey_sudo'], access_data['answer_sudo']
        
        # Find the answer line for this question
        answer_line = answer_sudo.user_input_line_ids.filtered(
            lambda l: l.question_id.id == int(question_id) and l.value_image
        )
        
        if not answer_line:
            return http.request.not_found()
        
        return request.env['ir.binary']._get_image_stream_from(answer_line[0], 'value_image').get_response() 