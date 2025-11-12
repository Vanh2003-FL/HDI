
odoo.define('ngsc_utils.basic_fields', function (require) {
    "use strict";

    var FieldColorPicker = require('web.basic_fields').FieldColorPicker;

    FieldColorPicker.include({

        _highlightSelectedColor: function () {
            try {
                $(this.$('li')[parseInt(this.value)]).css('border', '2px solid teal');
                $(this.$('li')[parseInt(this.value)]).css('position', 'relative');
                $(this.$('li')[parseInt(this.value)]).append('<span class="color-checked">✓</span>');
            } catch (err) {
            }
        },
    });
});