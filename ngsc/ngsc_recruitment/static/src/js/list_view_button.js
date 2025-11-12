odoo.define('ngsc_recruitment.ListViewButton', function (require) {
    "use strict";

    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListViewButton = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: require('web.ListController').extend({
                events: _.extend({}, ListView.prototype.config.Controller.prototype.events, {
                    'click .o_list_button_search_personnel': '_onClickSearchPersonnel',
                    'click .o_list_button_import_personnel': '_onClickImportData',
                    'click .o_list_button_download_personnel': '_onClickDownloadTemplate',
                }),
                _onClickSearchPersonnel: function () {
                    this.do_action({
                        type: 'ir.actions.act_window',
                        res_model: 'hr.applicant.search',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new',
                        context: {'form_view_ref': 'ngsc_recruitment.hr_applicant_search_form'},
                    });
                },

                _onClickImportData: function () {
                    this.do_action({
                        type: 'ir.actions.client',
                        tag: 'import',
                        params: {
                            model: 'hr.applicant',
                            context: this.initialState.context,
                        },
                    });
                },

                _onClickDownloadTemplate: function() {
                    var fileUrl = '/ngsc_recruitment/static/src/files/template_ho_so_ung_vien.xlsx';
                    var link = document.createElement('a');
                    link.setAttribute('href', fileUrl);
                    link.setAttribute('download', 'template_hs_nguon.xlsx');
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            }),
        }),
    });

    viewRegistry.add('ngsc_recruitment_list_view_button', ListViewButton);
});