/** @odoo-module **/

import ListController from 'web.ListController';

ListController.include({
    renderButtons: function () {
        this._super.apply(this, arguments);
        if (this.modelName === 'ngsc.candidate.search.result') {
            const $button = this.$('.candidate_compare_button');
            const selectedCount = this.getSelectedIds().length;
            $button.prop('disabled', !(selectedCount >= 2 && selectedCount <= 4));
        }
    },
    _onSelectionChanged: function () {
        this._super.apply(this, arguments);
        if (this.modelName === 'ngsc.candidate.search.result') {
            const $button = this.$('.candidate_compare_button');
            const selectedCount = this.getSelectedIds().length;
            $button.prop('disabled', !(selectedCount >= 2 && selectedCount <= 4));
        }
    },
});