odoo.define('internal_control.survey_image_upload', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');

    var QWeb = core.qweb;

    publicWidget.registry.SurveyImageUpload = publicWidget.Widget.extend({
        selector: '.o_survey_question_image_upload',

        events: {
            'change': '_onFileChange',
        },

        /**
         * @override
         */
        start: function () {
            this._super.apply(this, arguments);
            this._setupFileUpload();
        },

        /**
         * Setup file upload handling
         */
        _setupFileUpload: function () {
            var self = this;
            
            // Add event listener for file change
            this.$el.on('change', function (ev) {
                self._onFileChange(ev);
            });
        },

        /**
         * Handle file selection
         */
        _onFileChange: function (ev) {
            var file = ev.target.files[0];
            if (file) {
                console.log('File selected:', file.name, file.size, file.type);
                
                // Validate file type
                if (!file.type.startsWith('image/')) {
                    alert('Please select an image file.');
                    this.$el.val('');
                    return;
                }

                // Validate file size (max 5MB)
                if (file.size > 5 * 1024 * 1024) {
                    alert('File size must be less than 5MB.');
                    this.$el.val('');
                    return;
                }

                // Show preview
                this._showPreview(file);
            }
        },

        /**
         * Show image preview
         */
        _showPreview: function (file) {
            var self = this;
            var reader = new FileReader();
            
            reader.onload = function (e) {
                // Remove existing preview
                self.$el.siblings('.image-preview').remove();
                
                // Create preview element
                var preview = $('<div class="image-preview mt-2"></div>');
                var img = $('<img src="' + e.target.result + '" style="max-width: 300px; max-height: 200px;" class="img-thumbnail"/>');
                
                preview.append(img);
                self.$el.after(preview);
            };
            
            reader.readAsDataURL(file);
        },
    });

    // Extend the survey form widget to handle image uploads
    publicWidget.registry.SurveyFormWidget.include({
        /**
         * Override _prepareSubmitValues to handle image uploads
         */
        _prepareSubmitValues: function (formData, params) {
            var self = this;
            
            // Handle image upload fields
            this.$('.o_survey_question_image_upload').each(function () {
                var $input = $(this);
                var questionId = $input.attr('name');
                var file = $input[0].files[0];
                
                if (file) {
                    console.log('Processing image upload for question:', questionId);
                    
                    // Add the file to formData
                    formData.append(questionId, file);
                }
            });
            
            // Call the original method
            this._super.apply(this, arguments);
        },
    });

    return publicWidget.registry.SurveyImageUpload;
}); 