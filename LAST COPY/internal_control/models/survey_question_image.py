from odoo import models, fields, api, _
import logging
import base64

_logger = logging.getLogger(__name__)

class SurveyQuestion(models.Model):
    _inherit = 'survey.question'

    question_type = fields.Selection(
        selection_add=[('image_upload', 'Image Upload')]
    )

class SurveyUserInputLine(models.Model):
    _inherit = 'survey.user_input.line'

    value_image = fields.Binary('Image Answer', attachment=True)
    value_image_filename = fields.Char('Image Filename')

class SurveyUserInput(models.Model):
    _inherit = 'survey.user_input'

    def _save_lines(self, question, answer, comment=None, overwrite_existing=True):
        _logger.info(f"[IMAGE UPLOAD DEBUG] _save_lines called for question {question.id} ({question.question_type})")
        
        if question.question_type == 'image_upload':
            _logger.info(f"[IMAGE UPLOAD DEBUG] Processing image_upload question")
            _logger.info(f"[IMAGE UPLOAD DEBUG] Answer type: {type(answer)}")
            _logger.info(f"[IMAGE UPLOAD DEBUG] Answer value: {answer}")
            
            # Handle image upload using the same pattern as simple answers
            old_answers = self.env['survey.user_input.line'].search([
                ('user_input_id', '=', self.id),
                ('question_id', '=', question.id)
            ])
            
            if old_answers and not overwrite_existing:
                _logger.info(f"[IMAGE UPLOAD DEBUG] Skipping - existing line and overwrite_existing=False")
                return
            
            # For file uploads, answer should be a file object from FormData
            if answer and hasattr(answer, 'read'):
                _logger.info(f"[IMAGE UPLOAD DEBUG] Valid file upload detected")
                
                # Read the file and encode as base64
                image_data = base64.b64encode(answer.read())
                filename = answer.filename if hasattr(answer, 'filename') else 'image.jpg'
                
                _logger.info(f"[IMAGE UPLOAD DEBUG] Filename: {filename}")
                _logger.info(f"[IMAGE UPLOAD DEBUG] Image data length: {len(image_data)}")
                
                vals = {
                    'user_input_id': self.id,
                    'question_id': question.id,
                    'skipped': False,
                    'answer_type': 'char_box',  # Use char_box for compatibility
                    'value_image': image_data,
                    'value_image_filename': filename,
                }
                
                if old_answers:
                    _logger.info(f"[IMAGE UPLOAD DEBUG] Updating existing line {old_answers[0].id}")
                    old_answers.write(vals)
                else:
                    _logger.info(f"[IMAGE UPLOAD DEBUG] Creating new line")
                    new_line = self.env['survey.user_input.line'].create(vals)
                    _logger.info(f"[IMAGE UPLOAD DEBUG] Created new line {new_line.id}")
                return
            elif answer and isinstance(answer, str) and answer.startswith('data:image'):
                # Handle base64 data URL
                _logger.info(f"[IMAGE UPLOAD DEBUG] Base64 data URL detected")
                
                # Extract base64 data from data URL
                import re
                match = re.match(r'data:image/([^;]+);base64,(.+)', answer)
                if match:
                    image_type = match.group(1)
                    base64_data = match.group(2)
                    filename = f'image.{image_type}'
                    
                    _logger.info(f"[IMAGE UPLOAD DEBUG] Filename: {filename}")
                    _logger.info(f"[IMAGE UPLOAD DEBUG] Image data length: {len(base64_data)}")
                    
                    vals = {
                        'user_input_id': self.id,
                        'question_id': question.id,
                        'skipped': False,
                        'answer_type': 'char_box',
                        'value_image': base64_data,
                        'value_image_filename': filename,
                    }
                    
                    if old_answers:
                        _logger.info(f"[IMAGE UPLOAD DEBUG] Updating existing line {old_answers[0].id}")
                        old_answers.write(vals)
                    else:
                        _logger.info(f"[IMAGE UPLOAD DEBUG] Creating new line")
                        new_line = self.env['survey.user_input.line'].create(vals)
                        _logger.info(f"[IMAGE UPLOAD DEBUG] Created new line {new_line.id}")
                    return
            else:
                _logger.info(f"[IMAGE UPLOAD DEBUG] No valid file upload detected")
                return
        else:
            _logger.info(f"[IMAGE UPLOAD DEBUG] Not image_upload type, calling parent")
            # Call parent for other question types
            return super(SurveyUserInput, self)._save_lines(question, answer, comment, overwrite_existing) 