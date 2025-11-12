odoo.define('web_field_o2m_duplicate_row.relational_fields', function (require) {
    "use strict";

    const FieldOne2Many = require('web.relational_fields').FieldOne2Many;

    FieldOne2Many.include({
        custom_events: _.extend({}, FieldOne2Many.prototype.custom_events, {
            list_record_duplicate: '_onAddRecord',
        }),

        _render: function () {
            const res = this._super.apply(this, arguments);
            const arch = this.view?.arch;
            if (!arch) {
                return res;
            }
            if (arch.tag === 'tree' && this.renderer) {
                this.renderer.addCopyIcon = !this.isReadonly && !arch['no_copy'] && arch.attrs?.class?.includes('allow_list_copy');
            }
            return res;
        },
    })

});
