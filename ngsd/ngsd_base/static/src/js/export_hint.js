odoo.define('ngsd_base.export_hint', function (require) {
    "use strict";

    const ListController = require('web.ListController');
    const ListView = require('web.ListView');
    const viewRegistry = require('web.view_registry');

    const ListControllerWithHint = ListController.extend({
        init: function () {
            this._super.apply(this, arguments);
            console.log("NGSD: ListControllerWithHint init", this.props);

            this.displayNotification({
                title: "Hướng dẫn",
                message: "Tích chọn bản ghi sau đó nhấn nút Hành động → Xuất để tải file Excel.",
                type: "info",
            });
        },
    });

    const ListViewWithHint = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: ListControllerWithHint,
        }),
    });

    viewRegistry.add('list_with_export_hint', ListViewWithHint);
});
