odoo.define("kpi_dashboard.DashboardView", function (require) {
    "use strict";

    import { BasicView } from 'web.BasicView';
    import { DashboardController } from 'kpi_dashboard.DashboardController';
    import { DashboardModel } from 'kpi_dashboard.DashboardModel';
    import { DashboardRenderer } from 'kpi_dashboard.DashboardRenderer';
    import { view_registry } from 'web.view_registry';
    import { core } from 'web.core';

    var _lt = core._lt;

    var DashboardView = BasicView.extend({
        jsLibs: ["/kpi_dashboard/static/lib/gridster/jquery.dsmorse-gridster.min.js"],
        cssLibs: ["/kpi_dashboard/static/lib/gridster/jquery.dsmorse-gridster.min.css"],
        accesskey: "d",
        display_name: _lt("Dashboard"),
        icon: "fa-tachometer",
        viewType: "dashboard",
        config: _.extend({}, BasicView.prototype.config, {
            Controller: DashboardController,
            Renderer: DashboardRenderer,
            Model: DashboardModel,
        }),
        multi_record: false,
        searchable: false,
        init: function () {
            this._super.apply(this, arguments);
            this.controllerParams.mode = "readonly";
            this.loadParams.type = "record";
            if (!this.loadParams.res_id && this.loadParams.context.res_id) {
                this.loadParams.res_id = this.loadParams.context.res_id;
            }
        },
    });

    view_registry.add("dashboard", DashboardView);

    return DashboardView;
});
