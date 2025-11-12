odoo.define('web_notify.form_controller', function (require) {
    "use strict";

    const FormController = require('web.FormController');

    FormController.include({
        init: function (parent, model, renderer, params) {
            this._super.apply(this, arguments);
            this._onRefresh = (payload) => {
                 this.reload()
            };

            this.call('bus_service', 'onNotification', this, (notifications) => {
                for (const {payload, type} of notifications) {
                    if (type === "web.refresh") {
                        this._onRefresh(payload);
                    }
                }
            });
        },
    });
});
