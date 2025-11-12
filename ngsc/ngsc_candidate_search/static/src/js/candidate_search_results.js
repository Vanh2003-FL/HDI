odoo.define('ngsc_candidate_search.WeightWidget', function (require) {
    "use strict";

    const field_registry = require('web.field_registry');
    const FieldMany2One = require('web.relational_fields').FieldMany2One;

    const WeightWidget = FieldMany2One.extend({
        supportedFieldTypes: ['many2one'],

        _renderReadonly: function () {
            const value = this.record.data.weight;
            let color_code = '#000000';
            if (value < 50) {
                color_code = '#ffcccc';
            } else if (value < 70) {
                color_code = '#ffffcc';
            } else {
                color_code = '#ccffcc';
            }
            this.$el.html(
                '<div style="text-align: center; background-color: ' + color_code + ';">' + value + '</div>'
            );
        },
    });

    field_registry.add('custom_weight', WeightWidget);
    return WeightWidget;
});
