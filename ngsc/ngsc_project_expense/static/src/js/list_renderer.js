odoo.define('ngsc_project_expense.merged_tree_header', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');

    ListRenderer.include({
        _renderView: async function () {
            const res = await this._super(...arguments);
            if (this.state.model !== "ngsc.resource.expense"){
                return res
            }
            setTimeout(() => this._insertMergedHeader(), 150);
            return res;
        },

        _insertMergedHeader: function () {
            const $thead = this.$el.find('thead');
            const $headerCells = $thead.find('tr').last().find('th');
            if (!$headerCells.length || $thead.find('.merged-header-row').length) return;
            const headerRow = $('<tr>', {
                class: 'merged-header-row',
                style: 'text-align: center;'
            });

            const columnGroups = [
                {label: 'Giai đoạn', span: 1},
                {label: 'Budget', span: 2},
                {label: 'Plan', span: 2},
                {label: 'Actual', span: 2},
            ];
            let colIndex = 0;
            for (const group of columnGroups) {
                let totalWidth = 0;
                for (let i = 0; i < group.span; i++) {
                    const th = $headerCells.get(colIndex);
                    if (th) {
                        const width = th.getBoundingClientRect().width;
                        totalWidth += width;
                    }
                    colIndex++;
                }

                headerRow.append(
                    $('<th>', {
                        colspan: group.span,
                        class: 'merged-header-cell',
                        css: {width: totalWidth + 'px'}
                    }).text(group.label)
                );
            }

            $thead.prepend(headerRow);
        }
    });
});

