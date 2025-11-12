/** @odoo-module **/

import ListController from 'web.ListController';

ListController.include({
    async _onButtonClicked(ev) {
        ev.stopPropagation();
        const recordId = this.renderer.getEditableRecordID && this.renderer.getEditableRecordID();
        if (recordId && this.saveRecord) {
            await this.saveRecord(recordId);
        }
        this._callButtonAction(ev.data.attrs, ev.data.record);
    },
});