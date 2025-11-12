/** @odoo-module **/

import ListController from 'web.ListController';

ListController.include({
    renderButtons: function ($node) {
        const modelName = this.modelName || null;
        var self = this;
        const action = this.controlPanelProps.action;
        const res = this._super.apply(this, arguments);

        if (modelName !== 'ngsc.candidate.search.result') {
            // this.$buttons.find('.open_compare_candidate_button').remove();
            this.$buttons.find('.open_recent_candidate_search_button').remove();
            return res;
        }

        if (this.$buttons) {
            // Lấy ra các nút (nếu có sẵn trong template)
            // let $compareBtn = this.$buttons.find('.open_compare_candidate_button');
            let $searchBtn = this.$buttons.find('.open_recent_candidate_search_button');

            // Xóa hết các nút gốc
            this.$buttons.empty();

            // Thêm lại theo thứ tự: So sánh → Tải dữ liệu → Tìm kiếm
            // if ($compareBtn.length) {
            //     this.$buttons.append($compareBtn);
            //     $compareBtn.click(self.proxy('open_recent_button_candidate_search'));
            // }

            if ($searchBtn.length) {
                this.$buttons.append($searchBtn);
                $searchBtn.click(self.proxy('open_recent_button_candidate_search'));
            }
        }

        return res;
    },

    open_recent_button_candidate_search: function (env) {
        var self = this;
        self._rpc({
            model: 'ngsc.candidate.search',
            method: 'open_recent',
            args: [this.model.get(this.handle, {raw: true}).context.candidate_search_id || false],
        }).then(function (result){
            if (result) self.do_action(result);
        });
    },

    download_candidate_search_result: function () {
        this._rpc({
            model: 'ngsc.candidate.search.result',
            method: 'action_export_excel',
            args: [this.model.get(this.handle, {raw: true}).context.candidate_search_id || false],
        }).then((result) => {
            if (result) this.do_action(result);
        });
    }
})
