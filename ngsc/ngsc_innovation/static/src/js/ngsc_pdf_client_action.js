/** @odoo-module **/

import AbstractAction from 'web.AbstractAction';
import core from 'web.core';

const PDFClientAction = AbstractAction.extend({
    start: function () {
        const pdfUrl = '/ngsc/innovation/preview/info#toolbar=0&navpanes=0&scrollbar=0';
        const iframe = document.createElement('iframe');
        iframe.src = pdfUrl;
        iframe.style.width = '100%';
        iframe.style.height = '100vh';
        iframe.style.border = 'none';
        iframe.style.padding = '0px';
        iframe.style.margin = '0px';
        iframe.style.backgroundColor = '#fff';
        this.$el.empty().append(iframe);
        return this._super.apply(this, arguments);
    },
});

core.action_registry.add('ngsc_pdf_client_action', PDFClientAction);

export default PDFClientAction;