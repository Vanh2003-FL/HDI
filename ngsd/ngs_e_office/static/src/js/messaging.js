/** @odoo-module **/

import {
    registerInstancePatchModel,
} from '@mail/model/model_core';

registerInstancePatchModel('mail.messaging', 'ngs_e_office_message_special_url', {
    async openDocument({ id, model }){
        if (model === 'approval.request') {
            const baseHref = this.env.session.url('/web');
            this.env.bus.trigger('do-action', {
                action: {type: 'ir.actions.act_url', url: `${baseHref}_view_action/${model}/${id}`},
            });
            if (this.messaging.device.isMobile) {
                // When opening documents chat windows need to be closed
                this.messaging.chatWindowManager.closeAll();
                // messaging menu has a higher z-index than views so it must
                // be closed to ensure the visibility of the view
                this.messaging.messagingMenu.close();
            }
            return
        }
        return this._super.bind(this, ...arguments);
    }
});
