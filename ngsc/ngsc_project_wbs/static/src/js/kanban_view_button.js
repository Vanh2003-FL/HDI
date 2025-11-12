odoo.define('ngsc_project_wbs.CustomKanbanView', function (require) {
    "use strict";

    var KanbanController = require('web.KanbanController');
    var KanbanView = require('web.KanbanView');
    var viewRegistry = require('web.view_registry');

    KanbanController.include({
        events: _.extend({}, KanbanController.prototype.events, {}),

        renderButtons: function () {
            this._super.apply(this, arguments);
            if (this.modelName === "project.project") {
                if (this.$buttons) {
                    this.$buttons.on("click", ".o_list_import_project_task", (event) => this._onImportProjectTask(event));
                    this.$buttons.on("click", ".o_list_button_download_import_task_template", (event) => this._onDownloadTemplate(event));
                } else {
                    if (this.$el.find('.o_list_import_project_task').length === 0) {
                        // Tạo các nút mới
                        var $importButton = $('<button>', {
                            class: 'btn btn-primary o_list_import_project_task mr-2',
                            type: 'button',
                            html: '<i class="fa fa-upload"></i> Nhập công việc'
                        }).on('click', (event) => this._onImportProjectTask(event));

                        var $downloadButton = $('<button>', {
                            class: 'btn btn-secondary o_list_button_download_import_task_template',
                            type: 'button',
                            html: '<i class="fa fa-download"></i> Tải file mẫu'
                        }).on('click', (event) => this._onDownloadTemplate(event));

                        var $div = $('<div></div>')
                        $div.append($importButton, $downloadButton)

                        this.$el.find('.o_cp_buttons').append($div)
                    }
                }
            }
        },

        _onImportProjectTask: function(ev) {
            this.do_action({
                type: 'ir.actions.act_window',
                res_model: 'project.task.import.wizard',
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new', // Mở wizard dưới dạng popup
                res_id: false, // Không cần ID vì là wizard mới
            });
        },

        _onDownloadTemplate: function () {
            var fileUrl = '/ngsc_project_wbs/static/src/files/template_cong_viec_du_an.xlsx';
            var link = document.createElement('a');
            link.setAttribute('href', fileUrl);
            link.setAttribute('download', 'template_cong_viec_du_an.xlsx');
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    });

    var CustomKanbanView = KanbanView.extend({
        config: _.extend({}, KanbanView.prototype.config, {
            Controller: KanbanController,
        }),
    });

    viewRegistry.add('ngsc_project_wbs_custom_kanban_button', CustomKanbanView);
});