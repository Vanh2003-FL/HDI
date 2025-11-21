odoo.define('ngsc_utils.list_editable_renderer', function (require) {
    "use strict";

    import { ListRenderer } from 'web.ListRenderer';

    ListRenderer.include({

        _renderHeader: function () {
            var $thead = this._super.apply(this, arguments);
            var addTrashIcon = this.__parentedParent && this.__parentedParent.mode === 'edit';
            // Hide the trash icon in the header if not in edit mode
            if (!addTrashIcon) {
                $thead.find('th.o_list_record_remove_header').addClass('o_hidden_trash_header');

            }
            return $thead;
        },

        _renderRow: function (record, index) {
            var $row = this._super.apply(this, arguments);
            var addTrashIcon = this.__parentedParent && this.__parentedParent.mode === 'edit';
            // Hide the trash icon in the row if not in edit mode
            if (!addTrashIcon) {
                $row.find('td.o_list_record_remove').hide();
            }
            return $row;
        },
    });
});