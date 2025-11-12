odoo.define("kpi_dashboard.MeterWidget", function (require) {
    "use strict";

    var AbstractWidget = require("kpi_dashboard.AbstractWidget");
    var registry = require("kpi_dashboard.widget_registry");
    var field_utils = require("web.field_utils");

    var MeterWidget = AbstractWidget.extend({
        template: "kpi_dashboard.meter",
        jsLibs: ["/kpi_dashboard/static/lib/gauge/GaugeMeter.js"],
        digits: [3, 0],
        shortList: [
            [1000000000000, "T", [3, 1]],
            [1000000000, "B", [3, 1]],
            [1000000, "M", [3, 1]],
            [1000, "K", [3, 1]],
        ],
        fillWidget: function (values) {
            var percent = 0
            if (values.value.value_max) {
                percent = values.value.value / values.value.value_max * 100
            }
            var options = this._getMeterOptions(values, percent);
            var margin = (this.widget_dimension_x - options.size) / 2;
            var input = this.$el.find('.percent-value');
            input.gaugeMeter(options);
            input.parent().css("padding-left", margin);
            var widget = this.$el;
            var meter_title = values.value.meter_title;
            if (meter_title === undefined) {
            } else {
                var $meter_title = widget.find(".meter-title");
                $meter_title.text(meter_title);
            }
            var meter_value = values.value.value;
            meter_value = this.shortNumber(meter_value)
            if (meter_value === undefined) {
            } else {
                var $meter_value = widget.find(".meter-value");
                $meter_value.text(meter_value);
            }
        },
        _getMeterOptions: function (values, percent) {
            var size = Math.min(this.widget_size_x, this.widget_size_y - 40) - 50;
            return {
                percent: percent,
                style: "Arch",
                width: 10,
                size: size,
                prepend: values.prefix === undefined ? "" : values.prefix,
                append: values.suffix === undefined ? "" : values.suffix,
                color: values.font_color,
                animate_text_colors: true,
            };
        },
        shortNumber: function (num) {
            var suffix = "";
            var shortened = false;
            var digits = this.digits;
            var result = num;
            _.each(this.shortList, function (shortItem) {
                if (!shortened && Math.abs(num) >= shortItem[0]) {
                    shortened = true;
                    suffix = shortItem[1];
                    result /= shortItem[0];
                    digits = shortItem[2];
                }
            });
            return (
                field_utils.format.float(result, false, {
                    digits: digits,
                }) + suffix
            );
        },
    });

    registry.add("meter", MeterWidget);
    return MeterWidget;
});
