odoo.define('ngsc_project_wbs.list_hierarchy_wbs', function (require) {
    'use strict';

    const ListView = require('web.ListView');
    const ListController = require('web.ListController');
    const HierarchyRenderer = require('ngsc_project_wbs.one2many_hierarchy_widget').HierarchyRenderer;

    ListView.include({
        init: function (viewInfo, params) {
            let result = this._super.apply(this, arguments);
            const classList = (this?.arch?.attrs?.class || "").split(/\s+/);
            const hasWbsHierarchy = classList.includes('wbs_hierarchy_list');
            const context = params?.context || {};
            const hasX2manySearch = Object.prototype.hasOwnProperty.call(context, 'x2many_search');
            if (this?.controllerParams?.modelName === "project.task" && hasWbsHierarchy && hasX2manySearch) {
                this.config = Object.assign({}, this.config || {}, {
                    Renderer: HierarchyRenderer,
                });
            }
            return result
        },
    });

    ListController.include({
        renderButtons: function () {
            this._super.apply(this, arguments);
            const classList = (this?.renderer.arch?.attrs?.class || "").split(/\s+/);
            const hasWbsHierarchy = classList.includes('wbs_hierarchy_list');
            const context = this.renderer?.state?.context || {};
            const hasX2manySearch = Object.prototype.hasOwnProperty.call(context, 'x2many_search');
            if (hasWbsHierarchy && hasX2manySearch)
                if (this.modelName === 'project.task' && this.$buttons && hasWbsHierarchy && hasX2manySearch) {
                    const $collapseBtn = $('<button type="button" style="margin-right:2px;" class="btn btn-secondary fa fa-compress task-collapse-button">Đóng tất cả</button>');
                    const $expandBtn = $('<button type="button" style="margin-right:2px;" class="btn btn-secondary fa fa-expand task-expand-button">Mở tất cả</button>');

                    $collapseBtn.on('click', () => {
                        if (this.renderer && typeof this.renderer._collapseChildrenRecursive === 'function') {
                            this.renderer._collapseChildrenRecursive(null);  // collapse toàn bộ
                        }
                    });

                    $expandBtn.on('click', () => {
                        if (this.renderer && typeof this.renderer._expandChildrenRecursive === 'function') {
                            this.renderer._expandChildrenRecursive(null);  // expand toàn bộ
                        }
                    });

                    this.$buttons.append($collapseBtn);
                    this.$buttons.append($expandBtn);
                }
        },
    });
});