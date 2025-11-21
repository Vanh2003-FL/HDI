 odoo.define('ngsd_crm.hide_create_button', function (require) {

"use strict";

import { ListController } from 'web.ListController';
    ListController.include({
        renderButtons: function($node) {
        this._super.apply(this, arguments);
            if (this.$buttons) {
                if (this.modelName === 'hr.boundary') {
                    this.$buttons.find('.o_list_button_add').hide();
                }
            }
        },
    });
});