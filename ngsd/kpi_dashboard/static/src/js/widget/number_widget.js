odoo.define("kpi_dashboard.NumberWidget", function (require) {
    "use strict";

    var IntegerWidget = require("kpi_dashboard.IntegerWidget");
    var registry = require("kpi_dashboard.widget_registry");
    var field_utils = require("web.field_utils");

    var NumberWidget = IntegerWidget.extend({
        digits: [3, 1],
        shortNumber: function (num) {
            if (Math.abs(num) < 10) {
                return field_utils.format.float(num, false, {
                    digits: [3, 2],
                });
            }
            return this._super.apply(this, arguments);
        },
        fillWidget: function (values) {
            var widget = this.$el;
            var value = values.value.value;
            if (value === undefined) {
                value = 0;
            }
            var item = widget.find('[data-bind="value"]');
            if (item) {
                item.text(this.shortNumber(value));
            }

            var date_text = values.value.apply_date.string;
            if (date_text === undefined) {
            } else {
                var $date_text = widget.find(".date-text");
                $date_text.text(date_text);
            }

            var start_date = values.value.apply_date.start_date;
            if (start_date === undefined) {
            } else {
                var $date_start = widget.find(".date-start");
                $date_start.text(start_date);
            }

            var end_date = values.value.apply_date.end_date;
            if (end_date === undefined) {
            } else {
                var $date_end = widget.find(".date-end");
                $date_end.text(end_date);
            }
        },
    });

    registry.add("number", NumberWidget);
    return NumberWidget;
});
