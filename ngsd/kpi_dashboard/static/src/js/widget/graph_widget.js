/*
global nv, d3
*/
odoo.define("kpi_dashboard.GraphWidget", function (require) {
    "use strict";

    var AbstractWidget = require("kpi_dashboard.AbstractWidget");
    var registry = require("kpi_dashboard.widget_registry");
    var core = require("web.core");
    var qweb = core.qweb;

    var GraphWidget = AbstractWidget.extend({
        template: "kpi_dashboard.graph",
        jsLibs: [
            "/kpi_dashboard/static/lib/nvd3/d3.v3.js",
            "/kpi_dashboard/static/lib/nvd3/nv.d3.js",
            "/kpi_dashboard/static/src/js/lib/nvd3.js",
        ],
        cssLibs: ["/kpi_dashboard/static/lib/nvd3/nv.d3.css"],
        start: function () {
            this._onResize = this._onResize.bind(this);
            nv.utils.windowResize(this._onResize);
            return this._super.apply(this, arguments);
        },
        destroy: function () {
            if ("nv" in window && nv.utils && nv.utils.offWindowResize) {
                // If the widget is destroyed before the lazy loaded libs (nv) are
                // actually loaded (i.e. after the widget has actually started),
                // nv is undefined, but the handler isn't bound yet anyway
                nv.utils.offWindowResize(this._onResize);
            }
            this._super.apply(this, arguments);
        },
        _getChartOptions: function () {
            return {
                x: function (d) {
                    return d.label;
                },
                y: function (d) {
                    return d.value;
                },
                margin: {left: 70, right: 10, top: 5, bottom: 50},
                showYAxis: true,
                showXAxis: true,
                showLegend: true,
                height: this.widget_size_y - 50,
                width: this.widget_size_x,
            };
        },
        _chartConfiguration: function (values) {
            // this.chart.forceY([0]);
            // this.chart.xAxis.tickFormat(function (d) {
            //     return d;
            // });
            this.chart.yAxis.tickFormat(d3.format(",.0f"));
            this.chart.showControls(false);
            this.chart.stacked(true);
            this.chart.xAxis.axisLabel(values.value.title)
        },
        _addGraph: function (values) {
            var data = values.value.graphs;
            this.$svg.addClass("o_graph_linechart");
            this.chart = nv.models.multiBarChart();
            this.chart.options(this._getChartOptions(values));
            this._chartConfiguration(values);
            d3.select(this.$("svg")[0])
                .datum(data)
                .transition()
                .duration(600)
                .call(this.chart);
            this.$("svg").css("height", this.widget_size_y - 50);
            this._customizeChart();
        },
        fillWidget: function (values) {
            var self = this;
            var element = this.$el.find('[data-bind="value"]');
            element.empty();
            element.css("padding-left", 10).css("padding-right", 10);
            this.chart = null;
            nv.addGraph(function () {
                self.$svg = self.$el
                    .find('[data-bind="value"]')
                    .append("<svg width=" + (self.widget_size_x - 20) + ">");
                self._addGraph(values);
            });
        },
        _customizeChart: function () {
            // Hook function
        },
        _onResize: function () {
            if (this.chart) {
                this.chart.update();
                this._customizeChart();
            }
        },
    });

    registry.add("graph", GraphWidget);
    return GraphWidget;
});
