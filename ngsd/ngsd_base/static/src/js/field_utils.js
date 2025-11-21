odoo.define('ngsd_base.remove_decimal_zero_trailing.field_utils', function (require) {
    "use strict";

import { core } from 'web.core';
import { field_utils } from 'web.field_utils';
import { utils } from 'web.utils';

var countDecimals = function (value) {
    if(Math.floor(value) === value) return 0;
    if (value.toString().split(".").length < 2) return 0;
    return value.toString().split(".")[1].length || 0;
}

function formatFloat(value, field, options) {
    options = options || {};
    if (value === false) {
        return "";
    }
    if (options.humanReadable && options.humanReadable(value)) {
        return utils.human_number(value, options.decimals, options.minDigits, options.formatterCallback);
    }
    var l10n = core._t.database.parameters;
    var precision;
    if (options.digits) {
        precision = options.digits[1];
    } else if (field && field.digits) {
        precision = field.digits[1];
    } else {
        precision = 2;
    }
    precision = Math.min(countDecimals(value), precision);
    var formatted = _.str.sprintf('%.' + precision + 'f', value || 0).split('.');
    formatted[0] = utils.insert_thousand_seps(formatted[0]);
    return formatted.join(l10n.decimal_point);

}

field_utils.format.float = formatFloat;

import { odoo_session } from 'web.session';
import { basic_fields } from 'web.basic_fields';
basic_fields.FieldDateTime.include({
    getSession: function () {
        var session;
        this.trigger_up('get_session', {
            callback: function (result) {
                session = result;
            }
        });
        if (!session) {
            session = odoo_session
        }
        return session;
    },
})

});
