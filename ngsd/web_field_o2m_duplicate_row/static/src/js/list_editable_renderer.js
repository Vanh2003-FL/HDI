odoo.define('web_field_o2m_duplicate_row.ListRenderer', function (require) {
    "use strict";

    const pyUtils = require('web.py_utils');

    const ListRenderer = require('web.ListRenderer');

    ListRenderer.include({

        events: _.extend({}, ListRenderer.prototype.events, {
            'click tr .o_list_record_copy': '_onDuplicateIconClick',
        }),

        init: function (parent, state, params) {
            this._super.apply(this, arguments);

            this.rawCopyFields = []
            const fieldsArch = this.arch.children.filter(child => child.tag === 'field');
            for (const arch of fieldsArch) {
                const attrs = arch.attrs;
                const options = attrs && attrs.options ? pyUtils.py_eval(attrs.options) : {};
                if (options['raw_copy']) {
                    this.rawCopyFields.push(attrs.name);
                }
            }
        },

        _getNumberOfCols: function () {
            let n = this._super();
            if (this.addCopyIcon) {
                n++;
            }
            return n;
        },

        _renderHeader: function () {
            const $thead = this._super.apply(this, arguments);
            if (this.addCopyIcon) {
                $thead.find('tr').append($('<th>', {class: 'o_list_record_copy_header'}));
            }
            return $thead;
        },

        _renderRow: function (record, index) {
            const $row = this._super.apply(this, arguments);
            if (this.addCopyIcon && !this.isMany2Many) {
                const $icon =
                    $('<button>', {
                        'class': 'fa fa-copy',
                        'name': 'copy_data',
                    });
                const $td = $('<td>', {class: 'o_list_record_copy'}).append($icon);
                if ($row.find('.o_list_record_remove').length > 0){
                    $td.insertBefore($row.find('.o_list_record_remove'))
                } else {
                    $row.append($td);
                }
            }
            return $row;
        },

        _renderFooter: function () {
            const $footer = this._super.apply(this, arguments);
            if (this.addCopyIcon) {
                $footer.find('tr').append($('<td>'));
            }
            return $footer;
        },

        async _onDuplicateIconClick(e) {
            e.stopPropagation();
            const $row = $(e.target).closest('tr');
            const id = $row.data('id');
            const state = this.state;
            const origin_record = state.data.find(rec => rec.id === id);
            // Lấy danh sách field được phép copy từ context (nếu có)
            const allowedFields = this.state.data?.[0]?.context?.copy_fields ?? [];
            const context = {'raw_copy_fields': this.rawCopyFields};
            if (allowedFields.length > 0) {
                Object.keys(origin_record.data).forEach(key => {
                    // Nếu allowedFields có giá trị thì chỉ copy những field trong danh sách, nếu không có thì copy tất cả
                    if (!allowedFields || allowedFields.includes(key)) {
                        const field_type = origin_record.fields[key].type;
                        if (field_type === 'many2one') {
                            context[`default_${key}`] = origin_record.data[key].res_id || false;
                        } else if (field_type === 'many2many') {
                            context[`default_${key}`] = [[6, 0, origin_record.data[key].res_ids]];
                        } else if (field_type === 'one2many') {
                            console.log('no default one2many field');
                        } else {
                            context[`default_${key}`] = origin_record.data[key];
                        }
                    }
                });
            } else {
                Object.keys(origin_record.data).forEach(key => {
                    const field_type = origin_record.fields[key].type;
                    if (field_type === 'many2one') {
                        context[`default_${key}`] = origin_record.data[key].res_id || false;
                    } else if (field_type === 'many2many') {
                        context[`default_${key}`] = [[6, 0, origin_record.data[key].res_ids]];
                    } else if (field_type === 'one2many') {
                        console.log('no default one2many field');
                    } else {
                        context[`default_${key}`] = origin_record.data[key];
                    }
                })
            }
            if ($row.hasClass('o_selected_row')) {
                this.trigger_duplicate(context);
            } else {
                await this.unselectRow();
                this.trigger_duplicate(context);
            }
        },

        trigger_duplicate: function (context) {
            this.trigger_up('list_record_duplicate', {
                context: context && [context],
            });
        }
    })

});
