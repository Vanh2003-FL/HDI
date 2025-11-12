odoo.define('ngsc_utils.list_tooltip_fields', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');

    const ListRendererTooltipFields = ListRenderer.include({

        _renderBodyCell: function (record, node, colIndex, options) {
            const $td = this._super.apply(this, arguments);
            let node_options = {};
            if (node && node.attrs && node.attrs.options) {
                try {
                    node_options = JSON.parse(node.attrs.options.replace(/'/g, '"'));
                } catch (e) {
                    console.warn("Lỗi parse options:", node.attrs.options, e);
                }
            }

            const tooltipField = node_options.tooltip_field;

            if (tooltipField && record.data[tooltipField]) {
                const tooltipHtml = record.data[tooltipField];
                $td.tooltip('dispose');
                $td.tooltip({
                    html: true,
                    title: tooltipHtml,
                    placement: 'top',
                    container: 'body',
                });
            }
            return $td;
        },
    });

    return ListRendererTooltipFields;
});
