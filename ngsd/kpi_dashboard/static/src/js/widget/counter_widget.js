odoo.define("kpi_dashboard.CounterWidget", function (require) {
    "use strict";

    import { IntegerWidget } from 'kpi_dashboard.IntegerWidget';
    import { registry } from 'kpi_dashboard.widget_registry';

    var CounterWidget = IntegerWidget.extend({
        shortList: [],
    });

    registry.add("counter", CounterWidget);
    return CounterWidget;
});
