odoo.define('x2many_search_advance.list_search', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');
    const view_dialogs = require('web.view_dialogs');

    ListRenderer.include({
        events: Object.assign({}, ListRenderer.prototype.events, {
            'click .search_record a': '_open_search_wizard',
        }),

        _renderRows: function () {
            const $rows = this._super.apply(this, arguments);
            const classList = (this.arch.attrs.class || "").split(/\s+/);
            const hasSearch = classList.includes('x2many_search');
            if (hasSearch && this.state.data && this.state.data.length > 0 && this.__parentedParent.record) {
                const $tr = $('<tr>');
                let colspan = this.columns.length;
                this.columns.forEach(node => {
                    if (node.tag !== 'field') {
                        colspan -= 1;
                    }
                });
                if (this.handleField) {
                    colspan -= 1;
                    $tr.append('<td>');
                }
                const $td = $('<td>')
                    .attr('colspan', colspan)
                    .addClass('search_record')
                    .css({
                        'background-color': 'white',
                        'font-size': 14,
                        'text-align': 'center',
                        'font-weight': 'bold'
                    });
                $tr.append($td);
                const $a = $('<a style="' +
                    '    border: 1px solid #828b93;\n' +
                    '    padding: 2px 5px;\n' +
                    '    border-radius: 5px;\n' +
                    '    display: inline-block;\n' +
                    '    text-decoration: none;" href="#" role="button">').text("Tìm kiếm / Lọc dữ liệu");
                $td.append($a);
                $rows.unshift($tr);
            }
            return $rows;
        },

        _open_search_wizard: function (ev) {
            ev.preventDefault();
            let treeViewRef = null;
            let formViewRef = null;
            let searchViewRef = null;

            try {
                const rawContext = this.__parentedParent?.attrs?.context || '';
                if (typeof rawContext === 'string') {
                    const treeMatch = rawContext.match(/['"]tree_view_ref['"]\s*:\s*['"]([^'"]+)['"]/);
                    const formMatch = rawContext.match(/['"]form_view_ref['"]\s*:\s*['"]([^'"]+)['"]/);
                    const searchMatch = rawContext.match(/['"]search_view_ref['"]\s*:\s*['"]([^'"]+)['"]/);

                    if (treeMatch) treeViewRef = treeMatch[1];
                    if (formMatch) formViewRef = formMatch[1];
                    if (searchMatch) searchViewRef = searchMatch[1];
                }
            } catch (error) {
                console.warn(error);
            }
            new view_dialogs.SelectCreateDialog(this, {
                title: "Tìm kiếm / Lọc dữ liệu",
                res_model: this.state.model,
                domain: [['id', 'in', this.state.res_ids]],
                no_create: true,
                readonly: true,
                target: 'new',
                disable_multiple_selection: true,
                on_selected: false,
                context: {
                    'tree_view_ref': treeViewRef,
                    'form_view_ref': formViewRef,
                    'search_view_ref': searchViewRef,
                    'x2many_search': true,
                    'default_res_id': this.state.res_ids && this.state.res_ids.length ? this.state.res_ids[0] : false,
                },
            }).open();
        }

    });
});
