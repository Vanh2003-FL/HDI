odoo.define('web_field_o2m_duplicate_row.BasicModel', function (require) {
    "use strict";

    const BasicModel = require('web.BasicModel');

    BasicModel.include({

        _removeRawCopyFieldsFromPerformOnChange: function (value, fields) {
            for (const field of fields) {
                delete value[fields];
            }
        },

        async _performOnChange(record, fields, options = {}) {
            const firstOnChange = options.firstOnChange;
            let {
                hasOnchange,
                onchangeSpec
            } = this._buildOnchangeSpecs(record, options.viewType);
            if (!firstOnChange && !hasOnchange) {
                return;
            }
            const idList = record.data.id ? [record.data.id] : [];
            const ctxOptions = {
                full: true,
            };
            if (fields.length === 1) {
                fields = fields[0];
                // if only one field changed, add its context to the RPC context
                ctxOptions.fieldName = fields;
            }
            const context = this._getContext(record, ctxOptions);
            const currentData = this._generateOnChangeData(record, {
                changesOnly: false,
                firstOnChange,
            });

            const result = await this._rpc({
                model: record.model,
                method: 'onchange',
                args: [idList, currentData, fields, onchangeSpec],
                context: context,
            });
            const rawCopyFields = context['raw_copy_fields'];
            if (rawCopyFields && rawCopyFields.length) {
                this._removeRawCopyFieldsFromPerformOnChange(result.value, rawCopyFields);
            }
            if (!record._changes) {
                // if the _changes key does not exist anymore, it means that
                // it was removed by discarding the changes after the rpc
                // to onchange. So, in that case, the proper response is to
                // ignore the onchange.
                return;
            }
            if (result.warning) {
                this.trigger_up('warning', result.warning);
                record._warning = true;
            }
            if (result.domain) {
                record._domains = Object.assign(record._domains, result.domain);
            }
            await this._applyOnChange(result.value, record, {firstOnChange});
            return result;
        },
    })

});
