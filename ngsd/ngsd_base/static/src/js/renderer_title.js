odoo.define('planning.renderer_title', function (require) {
    "use strict";

    var ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        // render lại title để hiển thị hạn mức còn lại
        _renderBodyCell: function (record, node, colIndex, options) {
            var $td = this._super.apply(this, arguments);
            if (record.model === 'project.status.report') {
                $td.attr('title', '');
            }
            return $td
        },

    });
});