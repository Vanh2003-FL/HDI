odoo.define("web_remember_tree_column_width.ListRenderer", function (require) {
    "use strict";

    const ListRenderer = require("web.ListRenderer");
    ListRenderer.include({
        events: Object.assign({}, ListRenderer.prototype.events, {
            "pointerdown th .o_resize": "_onMouseDownResize",
            mouseup: "_onMouseUpResize",
        }),
        _onMouseDownResize: function () {
            this.resizeInProgress = true;
        },
        _getLocalStorageWidthColumnName: function (model, field) {
            return "odoo.columnWidth." + model + "." + field;
        },
        _onMouseUpResize: function (ev) {
            if (this.resizeInProgress) {
                this.resizeInProgress = false;
                const target = $(ev.target);
                const $th = target.is("th") ? target : target.parent("th");
                const fieldName = $th.length ? $th.data("name") : undefined;
                if (
                    this.state &&
                    this.state.model &&
                    fieldName &&
                    window.localStorage
                ) {
                    window.localStorage.setItem(
                        this._getLocalStorageWidthColumnName(
                            this.state.model,
                            fieldName
                        ),
                        parseInt(($th[0].style.width || "0").replace("px", "")) || 0
                    );
                }
            }
        },
        _squeezeTable: function () {
            const columnWidths = this._super.apply(this, arguments);

            const table = this.el.getElementsByTagName("table")[0];
            const thead = table.getElementsByTagName("thead")[0];
            const thElements = [...thead.getElementsByTagName("th")];

            const self = this;
            thElements.forEach(function (el, elIndex) {
                const fieldName = $(el).data("name");
                if (
                    self.state &&
                    self.state.model &&
                    fieldName &&
                    window.localStorage
                ) {
                    const storedWidth = window.localStorage.getItem(
                        self._getLocalStorageWidthColumnName(
                            self.state.model,
                            fieldName
                        )
                    );
                    if (storedWidth) {
                        columnWidths[elIndex] = parseInt(storedWidth);
                    }
                }
            });

            return columnWidths;
        },
        _renderRow: function (record, index) {
            var $row = this._super.apply(this, arguments);
            if (record.data?.en_state !== 'new' && record.model === "account.analytic.line") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.state !== 'active' && record.model === "resource.project") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.en_wbs_old_id && record.model === "project.task") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.wbs_version_old && record.model === "en.project.stage") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.wbs_version_old && record.model === "en.workpackage") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.state !== 'new' && record.model === "en.lender.employee.detail") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            if (record.data?.no_delete_line && record.model === "en.resource.detail") {
                var row = $row[0]
                while (row.getElementsByClassName("o_list_record_remove").length) {
                    row.removeChild(row.lastElementChild);
                }
            }
            return $row;
        },
        // confirm xóa line
        // _onRemoveIconClick: function (event){
        //     event.stopPropagation();
        //     var $row = $(event.target).closest('tr');
        //     var id = $row.data('id');
        //     if ($row.hasClass('o_selected_row')) {
        //         this.trigger_up('list_record_remove', {id: id});
        //     } else {
        //         var self = this;
        //         this.unselectRow().then(function () {
        //             self.trigger_up('list_record_remove', {id: id});
        //         });
        //     }
        // },
    });
});