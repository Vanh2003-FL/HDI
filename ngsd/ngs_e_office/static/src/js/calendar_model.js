odoo.define('ngs_e_office.CalendarModel', function (require) {
"use strict";

const CalendarModel = require('web.CalendarModel');
import { Context } from 'web.Context';
import { core } from 'web.core';
import { fieldUtils } from 'web.field_utils';
import { session } from 'web.session';

var _t = core._t;

CalendarModel.include({

    _loadFilter: function (filter) {
        if (!filter.write_model) {
            return Promise.resolve();
        }

        var field = this.fields[filter.fieldName];
        var fields = [filter.write_field];
        if (filter.filter_field) {
            fields.push(filter.filter_field);
        }
        return this._rpc({
                model: filter.write_model,
                method: 'search_read',
                domain: [["user_id", "=", session.uid]],
                fields: fields,
            })
            .then(function (res) {
                var records = _.map(res, function (record) {
                    var _value = record[filter.write_field];
                    var value = _.isArray(_value) ? _value[0] : _value;
                    var f = _.find(filter.filters, function (f) {return f.value === value;});
                    var formater = fieldUtils.format[_.contains(['many2many', 'one2many'], field.type) ? 'many2one' : field.type];
                    // By default, only current user partner is checked.
                    return {
                        'id': record.id,
                        'value': value,
                        'label': formater(_value, field),
                        'active': (f && f.active) || (filter.filter_field && record[filter.filter_field]),
                    };
                });
                records.sort(function (f1,f2) {
                    return _.string.naturalCmp(f2.label, f1.label);
                });

                // add my profile
                if (field.relation === 'res.partner' || field.relation === 'res.users') {
                    var value = field.relation === 'res.partner' ? session.partner_id : session.uid;
                    var me = _.find(records, function (record) {
                        return record.value === value;
                    });
                    if (me) {
                        records.splice(records.indexOf(me), 1);
                    } else {
                        var f = _.find(filter.filters, function (f) {return f.value === value;});
                        me = {
                            'value': value,
                            'label': session.name,
                            'active': !f || f.active,
                        };
                    }
                    records.unshift(me);
                }
                if (filter.all === undefined){
                    filter.all = true;
                }

                // add all selection
                records.push({
                    'value': 'all',
                    'label': field.relation === 'res.partner' || field.relation === 'res.users' ? _t("Everybody's calendars") : _t("Everything"),
                    'active': filter.all,
                });

                filter.filters = records;

            });
    },

});

});