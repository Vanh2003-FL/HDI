/** @odoo-module **/

import ListController from 'web.ListController';

const rpc = require('web.rpc');

ListController.include({
    _onSelectionChanged: function () {
        this._super.apply(this, arguments);
        if (this.modelName !== "ngsc.hr.performance.evaluation") {
            return;
        }
        const $btnToApprove = this.$('.o_performance_evaluation_to_approve');
        const $btnAgainApprove = this.$('.o_performance_evaluation_again_approve');
        const $btnApprove = this.$('.o_performance_evaluation_approve');
        const $btnReject = this.$('.o_performance_evaluation_reject');
        const selectedIds = this.getSelectedIds();
        if (!selectedIds.length) {
            $btnToApprove.hide();
            $btnAgainApprove.hide();
            $btnApprove.hide();
            $btnReject.hide();
            return;
        }
        const selectedRecords = this.model.get(this.handle).data.filter(r =>
            selectedIds.includes(r.res_id)
        );

        const allDirect = selectedRecords.every(r => r.data.approval_state === 'direct_manager');
        const allIndirect = selectedRecords.every(r => r.data.approval_state === 'indirect_manager');

        $btnToApprove.toggle(allDirect);
        $btnAgainApprove.toggle(allDirect);
        $btnApprove.toggle(allIndirect);
        $btnReject.toggle(allIndirect);
    },

    renderButtons: function () {
        this._super.apply(this, arguments);
        if (this.modelName === "ngsc.hr.performance.evaluation") {
            let btnPerformance = this.$buttons.find('.o_list_update_performance_evaluation');
            let btnRemindPerformance = this.$buttons.find('.o_list_remind_performance_evaluation');
            this.getSession().user_has_group('hr.group_hr_manager').then(function (has_group) {
                if (!has_group) {
                    btnPerformance.remove();
                    btnRemindPerformance.remove();
                }
            });
            this.$buttons.on("click", ".o_list_update_performance_evaluation", (event) => this._updatePerformanceEvaluation(event));
            this.$buttons.on("click", ".o_list_remind_performance_evaluation", (event) => this._remindPerformanceEvaluation(event));
        }
        if (this.modelName === "task.evaluation") {
            let btnEvaluation = this.$buttons.find('.o_list_update_task_evaluation');
            let btnRemindEvaluation = this.$buttons.find('.o_list_remind_task_evaluation');
            this.getSession().user_has_group('hr.group_hr_manager').then(function (has_group) {
                if (!has_group) {
                    btnEvaluation.remove();
                    btnRemindEvaluation.remove();
                }
            });
            this.$buttons.on("click", ".o_list_update_task_evaluation", (event) => this._updateTaskEvaluation(event));
            this.$buttons.on("click", ".o_list_remind_task_evaluation", (event) => this._remindTaskEvaluation(event));
        }
    },

    _updatePerformanceEvaluation: function (ev) {
        let self = this;
        let loading = document.getElementById("sync_performance");
        loading.classList.add("fa-spin");
        rpc.query({
            model: 'ngsc.hr.performance.evaluation',
            method: 'action_update_performance_evaluation',
            args: [],
        }).then(res => {
            self.call('notification', 'notify', {
                title: "Cập nhật thành công",
                message: 'Vui lòng kiểm tra lại dữ liệu đánh giá hiệu suất',
                type: 'success',
            });
            self.reload();
            loading.classList.remove("fa-spin");
        });
    },

    _updateTaskEvaluation: function (ev) {
        let self = this;
        let loading = document.getElementById("sync_evaluation");
        loading.classList.add("fa-spin");
        rpc.query({
            model: 'task.evaluation',
            method: 'action_update_task_evaluation',
            args: [],
        }).then(res => {
            self.call('notification', 'notify', {
                title: "Cập nhật thành công",
                message: 'Vui lòng kiểm tra lại dữ liệu đánh giá chất lượng công việc',
                type: 'success',
            });
            self.reload();
            loading.classList.remove("fa-spin");
        });
    },

    _remindPerformanceEvaluation: function (ev) {
        const selectedIds = this.getSelectedIds();
        this.do_action({
            name: 'Nhắc nhở hoàn thành đánh giá',
            type: 'ir.actions.act_window',
            res_model: 'remind.evaluation.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_evaluation_type': 'performance_evaluation',
                'active_ids': selectedIds,
                'active_model': 'ngsc.hr.performance.evaluation',
            },
        });
    },

    _remindTaskEvaluation: function (ev) {
        const selectedIds = this.getSelectedIds();
        this.do_action({
            name: 'Nhắc nhở hoàn thành đánh giá',
            type: 'ir.actions.act_window',
            res_model: 'remind.evaluation.wizard',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
            context: {
                'default_evaluation_type': 'task_evaluation',
                'active_ids': selectedIds,
                'active_model': 'task.evaluation',
            },
        });
    },
});