odoo.define('ngsc_project_wbs.one2many_header_group', function (require) {
    "use strict";

    const ListRenderer = require('web.ListRenderer');
    const FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    const fieldRegistry = require('web.field_registry');
    const dom = require('web.dom');
    const rpc = require('web.rpc');

    const GroupedListRenderer = ListRenderer.extend({
        setValue: function (name, value) {
            this._super.apply(this, arguments);
            this._renderBody();
        },

        _renderBody: function () {
            let currentGroup = null;
            const data = [...this.state.data];

            const sortedData = data.sort((a, b) => {
                const aStageId = a.data?.project_stage_code || '';
                const bStageId = b.data?.project_stage_code || '';
                if (aStageId !== bStageId) return aStageId - bStageId;

                const aEmpId = a.data.employee_id?.data?.id || 0;
                const bEmpId = b.data.employee_id?.data?.id || 0;
                if (aEmpId !== bEmpId) return aEmpId - bEmpId;

                const aStart = new Date(a.data.start_date) || new Date();
                const bStart = new Date(b.data.start_date) || new Date();
                return aStart - bStart;
            });

            this.state.data = sortedData;
            const $body = this._super.apply(this, arguments);
            const grouped = new Set();

            sortedData.forEach(record => {
                const stage = record.data.project_task_stage_id?.data?.display_name;
                const stage_id = record.data.project_stage_code;
                if (!stage_id || grouped.has(stage_id)) {
                    return;
                }
                grouped.add(stage_id);
                const $groupRow = $('<label class="o_group_stage_header" style="display: block; background: #ddd; padding: 5px;">')
                    .append(
                        $('<span style="color: #000; font-weight: bold; display: block; width: 100%;">')
                            .text(`Giai đoạn ${stage}`)
                    );
                $body.find(`tr[data-id="${record.id}"]`).before($groupRow);
            });

            return $body;
        },

        confirmUpdate: function (state, id, fields, ev) {
            if (!this.el.classList.contains('grouped_by_stage')) {
                return this._super.apply(this, arguments);
            }
            var self = this;
            var oldData = this.state.data;
            this._setState(state);
            return this.confirmChange(state, id, fields, ev).then(function () {
                var record = self._getRecord(id);
                if (!record) {
                    return;
                }
                _.each(oldData, function (rec) {
                    if (rec.id !== id) {
                        self._updateAllModifiers(rec);
                        self._destroyFieldWidgets(rec.id);
                    }
                });
                const currentRowFieldWidgets = self.allFieldWidgets[id];
                delete self.allFieldWidgets[id];
                self.defs = [];
                var $newBody = self._renderBody();
                var defs = self.defs;
                delete self.defs;
                return Promise.all(defs).then(function () {
                    self._destroyFieldWidgets(id);
                    self.allFieldWidgets[id] = currentRowFieldWidgets;
                    _.each(self.columns, function (node) {
                        self._registerModifiers(node, record, null, {
                            mode: 'edit'
                        });
                    });
                    var currentRowID;
                    var currentWidget;
                    var focusedElement;
                    var selectionRange;
                    if (self.currentRow !== null) {
                        currentRowID = self._getRecordID(self.currentRow);
                        currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                        if (currentWidget) {
                            focusedElement = currentWidget.getFocusableElement().get(0);
                            if (currentWidget.formatType !== 'boolean' && focusedElement) {
                                selectionRange = dom.getSelectionRange(focusedElement);
                            }
                        }
                    }
                    var $editedRow = self._getRow(id);
                    $editedRow.nextAll('.o_data_row').remove();
                    $editedRow.prevAll('.o_data_row').remove();
                    var $newRow = $newBody.find('.o_data_row[data-id="' + id + '"]');
                    $newRow.prevAll('.o_data_row').get().reverse().forEach(function (row) {
                        $(row).insertBefore($editedRow);
                    });
                    $newRow.nextAll('.o_data_row').get().reverse().forEach(function (row) {
                        $(row).insertAfter($editedRow);
                    });
                    if (self._isInDom) {
                        for (const handle in self.allFieldWidgets) {
                            if (handle !== id) {
                                self.allFieldWidgets[handle].forEach(widget => {
                                        if (widget.on_attach_callback) {
                                            widget.on_attach_callback();
                                        }
                                    }
                                );
                            }
                        }
                    }
                    if (self.currentRow !== null) {
                        var newRowIndex = $editedRow.prop('rowIndex') - 1;
                        self.currentRow = newRowIndex;
                        return self._selectCell(newRowIndex, self.currentFieldIndex, {
                            force: true
                        }).then(function () {
                            currentWidget = self.allFieldWidgets[currentRowID][self.currentFieldIndex];
                            if (currentWidget) {
                                focusedElement = currentWidget.getFocusableElement().get(0);
                                if (selectionRange) {
                                    dom.setSelectionRange(focusedElement, selectionRange);
                                }
                            }
                        });
                    }
                });
            }).finally(() => {
                const $body = self.$el.find('tbody');
                $body.find('.o_group_stage_header').remove();
                self.renderGroupHeaders($body);
            });
        },

        renderGroupHeaders: function ($body) {
            const data = [...this.state.data];
            const grouped = new Set();

            data.forEach(record => {
                const stage = record.data.project_stage_id?.data?.display_name;
                const stage_id = record.data.project_stage_code;

                // ✅ Bỏ qua nếu không có stage_id
                if (!stage_id || grouped.has(stage_id)) {
                    return;
                }

                grouped.add(stage_id);
                const $groupRow = $('<label class="o_group_stage_header" style="display: block; background: #ddd; padding: 5px;">')
                    .append(
                        $('<span style="color: #000; font-weight: bold; display: block; width: 100%;">')
                            .text(`Giai đoạn ${stage}`)
                    );
                $body.find(`tr[data-id="${record.id}"]`).before($groupRow);
            });
        }
    });

    const One2ManyGroupedWidget = FieldOne2Many.extend({
        _getRenderer: function () {
            return GroupedListRenderer;
        },
    });

    fieldRegistry.add('one2many_header_group', One2ManyGroupedWidget);
});