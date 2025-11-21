odoo.define("ngsd_base.relational_fields", function (require) {
    "use strict";
    var core = require('web.core');
    var _t = core._t;
    var concurrency = require('web.concurrency');
    const RelationalFields = require('web.relational_fields');
    RelationalFields.FieldMany2One.include({
    init: function (parent, name, record, options) {
        this._super.apply(this, arguments);
        this.can_create = false;
        if (this.model == 'business.estimate_expense' && this.field.relation == "business.category") {
            this.can_create = true
        }
    },
    _manageSearchMore: function (values, search_val, domain, context) {
        var self = this;
        values = values.slice(0, this.limit);
        if (context.view_all_res_partner === true || context.view_all_employee === true || context.view_all_project === true) {
            return values
        } else {
            values.push({
                label: _t("Search More..."),
                action: function () {
                    var prom;
                    if (search_val !== '') {
                        prom = self._rpc({
                            model: self.field.relation,
                            method: 'name_search',
                            kwargs: {
                                name: search_val,
                                args: domain,
                                operator: "ilike",
                                limit: self.SEARCH_MORE_LIMIT,
                                context: context,
                            },
                        });
                    }
                    Promise.resolve(prom).then(function (results) {
                        var dynamicFilters;
                        if (results) {
                            var ids = _.map(results, function (x) {
                                return x[0];
                            });
                            dynamicFilters = [{
                                description: _.str.sprintf(_t('Quick search: %s'), search_val),
                                domain: [['id', 'in', ids]],
                            }];
                        }
                        self._searchCreatePopup("search", false, {}, dynamicFilters);
                    });
                },
                classname: 'o_m2o_dropdown_option',
            });
        }

        return values;
    },
});


});
