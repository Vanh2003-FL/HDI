odoo.define('ngsc_competency.BadgeWidget', function (require) {
    "use strict";

    const field_registry = require('web.field_registry');
    const FieldMany2One = require('web.relational_fields').FieldMany2One;

    const BadgeWidget = FieldMany2One.extend({
        supportedFieldTypes: ['many2one'],

        _renderReadonly: function () {
            const value = this.value ? this.value.data.display_name : '';
            const color_code = this.record.data.tag_color_code || 0;
            this.$el.html('<span class="custom-badge badge badge-pill o_tag_color_' + color_code + '"><span class="o_tag_badge_text">' + value + '</span></span>');
        },
    });

    field_registry.add('custom_badge', BadgeWidget);

    return BadgeWidget;
});
