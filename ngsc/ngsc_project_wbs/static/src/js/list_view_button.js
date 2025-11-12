odoo.define('ngsc_project_wbs.ListViewButton', function (require) {
    "use strict";

    var ListView = require('web.ListView');
    var viewRegistry = require('web.view_registry');

    var ListViewButton = ListView.extend({
        config: _.extend({}, ListView.prototype.config, {
            Controller: require('web.ListController').extend({
                events: _.extend({}, ListView.prototype.config.Controller.prototype.events, {
                    'click .o_list_import_nonproject_task': '_onClickImportNonProjectTask',
                    'click .o_list_button_download_nonproject_task_template': '_onClickDownloadNonProjectTaskTemplate',
                }),

                _onClickImportNonProjectTask: function () {
                    this.do_action({
                        type: 'ir.actions.client',
                        tag: 'import',
                        params: {
                            model: 'en.nonproject.task',
                            context: this.initialState.context,
                        },
                    });
                },

                _onClickDownloadNonProjectTaskTemplate: function() {
                    var fileUrl = '/ngsc_project_wbs/static/src/files/template_cong_viec_ngoai_du_an.xlsx';
                    var link = document.createElement('a');
                    link.setAttribute('href', fileUrl);
                    link.setAttribute('download', 'template_cong_viec_ngoai_du_an.xlsx');
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                }
            }),
        }),
    });

    viewRegistry.add('ngsc_project_wbs_list_view_button', ListViewButton);
});