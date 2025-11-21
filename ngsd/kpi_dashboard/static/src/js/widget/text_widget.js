odoo.define("kpi_dashboard.TextWidget", function (require) {
    "use strict";

    import { AbstractWidget } from 'kpi_dashboard.AbstractWidget';
    import { registry } from 'kpi_dashboard.widget_registry';

    var TextWidget = AbstractWidget.extend({
        template: "kpi_dashboard.base_text",
        fillWidget: function () {
            return;
        },
    });

    registry.add("base_text", TextWidget);
    return TextWidget;
});
