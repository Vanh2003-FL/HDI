odoo.define('ngsc_utils.form_controller', function (require) {
    "use strict";

    const FormController = require('web.FormController');
    const {evaluateExpr} = require('@web/core/py_js/py');

    FormController.include({
        // * Override to conditionally hide 'Edit' and 'Create' buttons
        // * Example: <form show_edit="state in ['draft']"/>
        updateButtons: function () {
            this._super.apply(this, arguments);
            if (this.$buttons && this.mode === 'readonly') {
                const attrs = this.renderer.arch.attrs || {};
                const evalContext = this.renderer.state.evalContext || {};
                const actions = ['edit', 'create'];
                actions.forEach(action => {
                    const expr = attrs[`show_${action}`];
                    let result = this.activeActions[action];
                    if (expr) {
                        try {
                            result = evaluateExpr(expr, evalContext);
                        } catch (e) {
                            console.warn(`Error evaluating show_${action}="${expr}"`, e);
                            result = false;
                        }
                    }
                    this.$buttons.find(`.o_form_button_${action}`).toggleClass('o_hidden', !result);
                });
            }
        },
    });
});
