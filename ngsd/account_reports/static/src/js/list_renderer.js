 odoo.define('galle_account_report.get_report_info', function (require) {"use strict";

import { ListController } from 'web.ListController';
    ListController.include({

        _startRenderer: function () {
            var self = this
            var res = this._super.apply(this, arguments);
            if (this.modelName === 'busy.rate.report'){
                self.get_popup_info().then(function(data){
                    self.$('.o_content').prepend(self.buildHtmlTable(data))
                });
            }
            return res
        },

        _updateRendererState: function () {
            var self = this
            var res = this._super.apply(this, arguments);
            if (this.modelName === 'busy.rate.report'){
                self.get_popup_info().then(function(data){
                    var content = self.$('.o_content')[0]
                    while (document.getElementsByClassName("get_popup_info").length) {
                        content.removeChild(content.firstElementChild);
                    }
                    self.$('.o_content').prepend(self.buildHtmlTable(data))
                });
            }
            return res
        },

        get_popup_info: function () {
            var domain = this.model.get(this.handle, {raw: true}).getDomain()
            var def = this._rpc({
                "model": this.modelName,
                "method": "get_total_data",
                "args": [],
                "kwargs": {
                    "domain": domain
                }
            });
            return def;
        },

        buildHtmlTable: function (data) {
            if (!data) return
            var table = document.createElement('table').cloneNode(false)
            table.setAttribute("class","get_popup_info table")
            table.setAttribute("style","border-collapse: separate;border-spacing: 10px 0;")
            var tr = document.createElement('tr').cloneNode(false);
            tmp = `<td style="td_style">td_title<br/>td_rate</td>`
            tr.appendChild($(tmp.replace('td_style', 'background-color: #50a5f1;color:white; width: 17%;').replace('td_title', 'Busy Rate dự án (%)').replace('td_rate',  (data.project_rate || 0).toFixed(2)))[0]);
            tr.appendChild($(tmp.replace('td_style', 'background-color: #34c38f;color:white; width: 17%;').replace('td_title', 'Busy Rate khác (%)').replace('td_rate', (data.other_rate || 0).toFixed(2)))[0]);
            tr.appendChild($(tmp.replace('td_style', 'background-color: #556ee6;color:white; width: 17%;').replace('td_title', 'Busy Rate công việc kinh doanh (%)').replace('td_rate', (data.kd_rate || 0).toFixed(2)))[0]);
            tr.appendChild($(tmp.replace('td_style', 'background-color: #556ee6;color:white; width: 17%;').replace('td_title', 'Busy Rate presale (%)').replace('td_rate', (data.presale_rate || 0).toFixed(2)))[0]);
            tr.appendChild($(tmp.replace('td_style', 'background-color: #556ee6;color:white; width: 17%;').replace('td_title', 'Busy Rate hỗ trợ dự án (%)').replace('td_rate', (data.support_project_rate || 0).toFixed(2)))[0]);
            tr.appendChild($(tmp.replace('td_style', 'background-color: #74788d;color:white; width: 17%;').replace('td_title', 'Busy Rate chung (%)').replace('td_rate', (data.all_rate || 0).toFixed(2)))[0]);

            table.appendChild(tr);
            return table;
        },

    });
})