odoo.define('website_theme_config.color_popup', function(require){
    "use strict";

    import { FormController } from 'web.FormController';

    FormController.include({
        renderButtons: function($node){
            this._super.apply(this, arguments);
            var self = this;

            // Click vào ô màu
            $('.color-field').off('click').on('click', function(e){
                var offset = $(this).offset();
                $('#color-popup').css({top: offset.top + $(this).height(), left: offset.left, display:'flex'});
                $('#color-popup').data('target', $(this));
            });

            // Chọn màu trong popup
            $('.color-swatch').off('click').on('click', function(){
                var color = $(this).data('color');
                var $field = $('#color-popup').data('target');
                $field.val(color);

                // update giá trị vào field model
                var field_name = $field.attr('name');
                var state_field = self.renderer.state.fields[field_name];
                if(state_field){
                    state_field._setValue(color);
                }

                $('#color-popup').hide();
            });

            // Click ra ngoài ẩn popup
            $(document).off('click.colorPopup').on('click.colorPopup', function(e){
                if(!$(e.target).closest('.color-field, #color-popup').length){
                    $('#color-popup').hide();
                }
            });
        }
    });
});
