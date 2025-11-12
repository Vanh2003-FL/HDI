/** @odoo-module **/

import ListController from 'web.ListController';

ListController.include({
    renderButtons: function ($node) {
        var self = this;
        const action = this.controlPanelProps.action;
        if (action.context?.show_export_odoo_button) {
            this.activeActions.export_xlsx = false
        }
        const res = this._super.apply(this, arguments);
        this.renderCustomButtons()
        if (this.$buttons) {
            let button = this.$buttons.find('.open_recent_button_report_button');
            if (button) {
                if (action.context?.report_info_popup_id) {
                    button.click(self.proxy('open_recent_button_report'));
                } else {
                    button.hide()
                }
            }

        }
        return res
    },

    renderCustomButtons: function () {
        const action = this.controlPanelProps.action;
        if (action.context?.show_export_odoo_button) {
            const self = this;
            const $button = $('<button>', {
                type: 'button',
                text: ' Tải xuống dữ liệu',
                class: `btn btn-secondary fa fa-file-text o_list_export_xlsx`,
                title: ' Tải xuống dữ liệu',
            })
            let $target = self.$buttons
            $button.prependTo($target);
        }
    },

    open_recent_button_report: function (env) {
        var self = this;
        self._rpc({
            model: 'report.info.popup',
            method: 'open_recent',
            args: [this.model.get(this.handle, {raw: true}).context.report_info_popup_id || false],
        }).then(function (result){
            if (result) self.do_action(result);
        });
    }
})
