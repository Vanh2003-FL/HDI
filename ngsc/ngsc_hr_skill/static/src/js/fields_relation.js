odoo.define('ngsc_hr_skill.FieldRelation', function (require) {
    "use strict";

    import { dialogs } from 'web.view_dialogs';
    import { relational_fields } from 'web.relational_fields';
    var FieldMany2One = relational_fields.FieldMany2One;
    import { core } from 'web.core';

    var _t = core._t;

    FieldMany2One.include({
        // # open search more with options search_more: True in fields
        _onInputClick: function (event) {
            if (this.field.type !== 'many2one' && this.field.type !== 'many2many') {
                return this._super.apply(this, arguments);
            }
            var searchMore = this.attrs.options && this.attrs.options.search_more;
            if (searchMore) {
                event.preventDefault();
                this._openSearchMore();
            } else {
                return this._super.apply(this, arguments);
            }
        },

        _openSearchMore: function () {
            var self = this;
            if (this.field.type == 'many2many') {
                self._searchCreatePopup("search", false, {}, []);
            }
            if (this.field.type == 'many2one') {
                var dialog = new dialogs.SelectCreateDialog(this, {
                    res_model: this.field.relation,
                    domain: this.record.getDomain({fieldName: this.name}),
                    context: this.record.getContext(this.recordParams),
                    title: _t("Tìm: ") + this.string,
                    disable_multiple_selection: true,
                    disable_create: true,
                    no_create: true,
                    on_selected: function (records) {
                        self.reinitialize(records[0]);
                    }
                });
                dialog.opened().then(function () {
                    dialog.$el.find('.o_data_row').on('click', function () {
                        var recordID = $(this).data('id');
                        if (recordID) {
                            self.reinitialize({id: recordID});
                            dialog.close();
                        }
                    });
                    dialog.$el.find('.o_list_record_selector').remove();
                });
                dialog.open();
            }
        },
    });
});
