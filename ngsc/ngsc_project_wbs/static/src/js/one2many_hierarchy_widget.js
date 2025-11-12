odoo.define('ngsc_project_wbs.one2many_hierarchy_widget', function (require) {
    'use strict';

    const fieldRegistry = require('web.field_registry');
    const FieldOne2Many = require('web.relational_fields').FieldOne2Many;
    const ListRenderer = require('web.ListRenderer');
    const dom = require('web.dom');
    const core = require('web.core');
    const {WidgetAdapterMixin} = require('web.OwlCompatibility');

    const SESSION_STORAGE_KEY = 'one2many_hierarchy_state';

    const HierarchyRenderer = ListRenderer.extend({
        init: function () {
            this._super(...arguments);
            this.expandedNodes = this._getExpandedStateFromSessionStorage();
        },

        start: function () {
            this._reorderHierarchyRendererList();
            return this._super(...arguments).then(() => {
                this._setupHierarchyRendererList();
                this.$el.find('tr.o_data_row').removeClass('o_tree_hidden');
                this._applySavedExpandedState();
                const savedPosition = this._getScrollPositionFromSessionStorage();
                if (savedPosition) {
                    const $scrollableElement = this.$el.find('.o_list_table_grouped').closest('.table-responsive');
                    if ($scrollableElement.length) {
                        $scrollableElement.scrollLeft(savedPosition.left);
                        $scrollableElement.scrollTop(savedPosition.top);
                    }
                }
            });
        },

        _getExpandedStateFromSessionStorage: function () {
            try {
                const savedState = sessionStorage.getItem(SESSION_STORAGE_KEY);
                return savedState ? JSON.parse(savedState) : [];
            } catch (e) {
                console.error("Failed to parse expanded tree state from session storage", e);
                return [];
            }
        },

        _saveExpandedStateToSessionStorage: function () {
            sessionStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(this.expandedNodes));
        },

        _applySavedExpandedState: function () {
            const $rows = this.$el.find('tr.o_data_row');
            const expandedIds = new Set(this.expandedNodes.map(id => String(id)));

            $rows.each((_, row) => {
                const $row = $(row);
                const rawId = $row.attr('data-res-id');
                const parentId = $row.attr('data-parent-id');
                const level = parseInt($row.attr('data-level'), 10) || 0;

                if (level > 0 && parentId) {
                    let shouldHide = false;
                    const parentChain = $row.attr('data-parent-chain')?.split(',') || [];
                    parentChain.unshift(parentId);

                    for (const parent of parentChain) {
                        if (!expandedIds.has(parent)) {
                            shouldHide = true;
                            break;
                        }
                    }
                    if (shouldHide) {
                        $row.addClass('o_tree_hidden');
                    }
                }

                const countSubtask = parseInt($row.attr('data-count-subtask'), 10) || 0;
                if (countSubtask > 0) {
                    const $toggle = $row.find('.o_tree_toggle');
                    if (expandedIds.has(rawId)) {
                        $row.addClass('open');
                        $toggle.html('<i class="fa fa-caret-down"></i>');
                    } else {
                        $row.removeClass('open');
                        $toggle.html('<i class="fa fa-caret-right"></i>');
                    }
                }
            });
        },

        _reorderHierarchyRendererList: function () {
            const recordMap = {};
            const childrenMap = {};

            this.state.data.forEach(record => {
                const id = record.data.id;
                const parentId = record.data.parent_id?.data?.id;
                recordMap[id] = record;
                if (!childrenMap[parentId ?? null]) {
                    childrenMap[parentId ?? null] = [];
                }
                childrenMap[parentId ?? null].push(record);
            });
            const sortFn = (a, b) => {
                const codeA = (a.data.full_code || a.data.code || '').toString();
                const codeB = (b.data.full_code || b.data.code || '').toString();
                return codeA.localeCompare(codeB, undefined, {numeric: true});
            };

            Object.values(childrenMap).forEach(children => children.sort(sortFn));

            const ordered = [];

            function appendWithChildren(record) {
                ordered.push(record);
                (childrenMap[record.data.id] || []).forEach(appendWithChildren);
            }

            (childrenMap[null] || []).forEach(appendWithChildren);

            this.state.data = ordered;
        },

        confirmUpdate: function (state, id, fields, ev) {
            var self = this;
            this._saveScrollPositionToSessionStorage();
            var oldData = this.state.data;
            this._setState(state);
            this._reorderTaskTree();
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
                this._setupHierarchyRendererList();
                this._applySavedExpandedState();
            });
        },

        on_attach_callback: function () {
            this._super.apply(this, arguments);
            var self = this;
            const $form = this.$el.closest('.o_form_view');
            $form.find('.task-collapse-button').off('click').on('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                self.expandedNodes = []; // Reset the state
                self._saveExpandedStateToSessionStorage();
                self._collapseChildrenRecursive(null);
            });
            $form.find('.task-expand-button').off('click').on('click', function (ev) {
                ev.preventDefault();
                ev.stopPropagation();
                self.expandedNodes = self.state.data.map(rec => rec.data.id); // Expand all
                self._saveExpandedStateToSessionStorage();
                self._expandChildrenRecursive(null);
            });
        },

        _expandChildrenRecursive: function (parentId) {
            const $rows = this.$el.find('tr.o_data_row');
            $rows.each((_, row) => {
                const $row = $(row);
                const rowParentId = $row.attr('data-parent-id');
                const isChild = parentId === null || (rowParentId && (rowParentId === String(parentId) || $row.attr('data-parent-chain')?.includes(parentId)));

                if (isChild) {
                    $row.removeClass('o_tree_hidden');
                    const countSubtask = parseInt($row.attr('data-count-subtask'), 10) || 0;
                    if (countSubtask > 0) {
                        $row.addClass('open');
                        const $toggle = $row.find('.o_tree_toggle');
                        if ($toggle.length) {
                            $toggle.html('<i class="fa fa-caret-down"></i>');
                        }
                    }
                }
            });
        },

        _collapseChildrenRecursive: function () {
            const $rows = this.$el.find('tr.o_data_row');
            $rows.each((_, row) => {
                const $row = $(row);
                const level = parseInt($row.attr('data-level'), 10) || 0;
                const countSubtask = parseInt($row.attr('data-count-subtask'), 10) || 0;
                const $toggle = $row.find('.o_tree_toggle');
                if (level === 0) {
                    $row.removeClass('o_tree_hidden');
                    if (countSubtask > 0) {
                        $row.addClass('open');
                        if ($toggle.length) {
                            $toggle.html('<i class="fa fa-caret-right"></i>');
                        }
                    }
                } else {
                    $row.addClass('o_tree_hidden').removeClass('open');
                    if (countSubtask > 0 && $toggle.length) {
                        $toggle.html('<i class="fa fa-caret-right"></i>');
                    }
                }
            });
        },

        _setupHierarchyRendererList: function () {
            const $rows = this.$el.find('tr.o_data_row');
            $rows.each((index, row) => {
                const $row = $(row);
                const rawId = $row.attr('data-id');
                const record = this._getRecordByResId(rawId);
                if (!record) return;
                const level = this._getRecordLevel(record);
                $row.attr('data-level', level);
                const $td = $row.find('td:nth-child(2)');
                $td.css('padding-left', `${level * 30}px`);
                const parentId = record.data.parent_id?.data?.id;
                $row.attr('data-res-id', record.data.id);
                if (parentId) {
                    $row.attr('data-parent-id', parentId);
                    const parentChain = this._buildParentChain(record);
                    if (parentChain.length > 0) {
                        $row.attr('data-parent-chain', parentChain.join(','));
                    }
                }
                const countSubtask = record.data.count_subtask || 0;
                $row.attr('data-count-subtask', countSubtask);
                if (countSubtask > 0) {
                    const $toggle = $('<span class="o_tree_toggle" style="cursor:pointer;margin-right:5px;"><i class="fa fa-caret-down"></i></span>');
                    $td.prepend($toggle);
                    $row.addClass('open');
                    $td.css('font-weight', 'bold');
                    $toggle.on('click', (ev) => {
                        ev.stopPropagation();
                        const isOpen = $row.hasClass('open');
                        const nodeId = record.data.id;
                        if (isOpen) {
                            this._collapseAllChildRows(nodeId);
                            $toggle.html('<i class="fa fa-caret-right"></i>');
                            $row.removeClass('open');
                            // Remove ID from array and save to session storage
                            this.expandedNodes = this.expandedNodes.filter(id => id !== nodeId);
                            this._saveExpandedStateToSessionStorage();
                        } else {
                            this._expandDirectChildRows(nodeId);
                            $toggle.html('<i class="fa fa-caret-down"></i>');
                            $row.addClass('open');
                            if (!this.expandedNodes.includes(nodeId)) {
                                this.expandedNodes.push(nodeId);
                            }
                            // Add ID to array and save to session storage
                            this._saveExpandedStateToSessionStorage();
                        }
                    });
                }
            });
            return $rows;
        },

        _buildParentChain: function (record) {
            const parentChain = [];
            let parent = record.data.parent_id?.data;
            while (parent) {
                parentChain.push(parent.id);
                const parentRecord = this.state.data.find(r => r.data.id === parent.id);
                if (parentRecord) {
                    parent = parentRecord.data.parent_id?.data;
                } else {
                    break;
                }
            }
            return parentChain;
        },

        _getRecordLevel: function (record) {
            let level = 0;
            let parent = record.data.parent_id?.data;
            while (parent) {
                level++;
                const parentRecord = this.state.data.find(r => r.data.id === parent.id);
                if (parentRecord) {
                    parent = parentRecord.data.parent_id?.data;
                } else {
                    break;
                }
            }
            return level;
        },

        _expandDirectChildRows: function (parentId) {
            const $directChildren = this.$el.find(`tr[data-parent-id="${parentId}"]`);
            $directChildren.each((_, child) => {
                const $child = $(child);
                const countSubtask = parseInt($child.attr('data-count-subtask'), 10) || 0;
                $child.removeClass('o_tree_hidden');
                if (countSubtask > 0) {
                    const $toggle = $child.find('.o_tree_toggle');
                    if ($toggle.length) {
                        $toggle.html('<i class="fa fa-caret-right"></i>');
                    }
                    $child.removeClass('open');
                }
            });
        },

        _collapseAllChildRows: function (parentId) {
            const $rows = this.$el.find('tr.o_data_row');
            $rows.each((_, row) => {
                const $row = $(row);
                const directParentId = $row.attr('data-parent-id');
                const parentChain = $row.attr('data-parent-chain');
                const isDirectChild = directParentId === String(parentId);
                const isDescendant = parentChain && parentChain.split(',').includes(String(parentId));
                if (isDirectChild || isDescendant) {
                    $row.addClass('o_tree_hidden').removeClass('open');
                    const countSubtask = parseInt($row.attr('data-count-subtask'), 10) || 0;
                    if (countSubtask > 0) {
                        const $toggle = $row.find('.o_tree_toggle');
                        if ($toggle.length) {
                            $toggle.html('<i class="fa fa-caret-right"></i>');
                        }
                    }
                }
            });
        },

        _expandChildren: function (parentId) {
            const $children = this.$el.find(`tr[data-parent-id="${parentId}"]`);
            $children.each((_, el) => {
                const $child = $(el);
                const childId = $child.attr('data-id');
                const countSubtask = parseInt($child.attr('data-count-subtask'), 10) || 0;
                $child.removeClass('o_tree_hidden');
                if (countSubtask > 0) {
                    $child.addClass('open');
                    const $toggle = $child.find('.o_tree_toggle');
                    if ($toggle.length) {
                        $toggle.html('<i class="fa fa-caret-down"></i>');
                    }
                }

                this._expandChildren(childId);
            });
        },

        _collapseChildren: function (parentId) {
            const $children = this.$el.find(`tr[data-parent-id="${parentId}"]`);
            $children.each((_, el) => {
                const $child = $(el);
                const childId = $child.attr('data-id');
                const countSubtask = parseInt($child.attr('data-count-subtask'), 10) || 0;

                this._collapseChildren(childId);

                $child.addClass('o_tree_hidden').removeClass('open');
                if (countSubtask > 0) {
                    const $toggle = $child.find('.o_tree_toggle');
                    if ($toggle.length) {
                        $toggle.html('<i class="fa fa-caret-right"></i>');
                    }
                }
            });
        },

        _getRecordByResId: function (rawId) {
            return this.state.data.find(record => record.id === rawId);
        },

        setRowMode: function (recordID, mode) {
            var self = this;
            var record = self._getRecord(recordID);
            if (!record) {
                return Promise.resolve();
            }

            var editMode = (mode === 'edit');
            var $row = this._getRow(recordID);
            this.currentRow = editMode ? $row.prop('rowIndex') - 1 : null;
            var $tds = $row.children('.o_data_cell');
            var oldWidgets = _.clone(this.allFieldWidgets[record.id]);

            var options = {
                renderInvisible: editMode,
                renderWidgets: editMode,
            };
            options.mode = editMode ? 'edit' : 'readonly';
            var defs = [];
            this.defs = defs;
            _.each(this.columns, function (node, colIndex) {
                var $td = $tds.eq(colIndex);
                var $newTd = self._renderBodyCell(record, node, colIndex, options);

                if ($td.hasClass('o_list_button')) {
                    self._unregisterModifiersElement(node, recordID, $td.children());
                }

                if (editMode) {
                    $td.empty().append($newTd.contents());
                } else {
                    self._unregisterModifiersElement(node, recordID, $td);
                    $td.replaceWith($newTd);
                }
            });
            delete this.defs;
            _.each(oldWidgets, this._destroyFieldWidget.bind(this, recordID));
            $row.toggleClass('o_selected_row', editMode);
            if (editMode) {
                this._disableRecordSelectors();
            } else {
                this._enableRecordSelectors();
            }

            return Promise.all(defs).then(function () {
                WidgetAdapterMixin.on_attach_callback.call(self);

                core.bus.trigger('DOM_updated');
            }).finally(function () {
                self._setupTreeStructureForRow(recordID);
            });
        },

        _setupTreeStructureForRow: function (recordID) {
            const $row = this._getRow(recordID);
            if (!$row.length) return;

            const record = this._getRecord(recordID);
            if (!record) return;

            const level = this._getRecordLevel(record);
            $row.attr('data-level', level);

            const $td = $row.find('td:nth-child(2)');
            $td.css('padding-left', `${level * 20}px`);

            const parentId = record.data.parent_id?.data?.id;
            if (parentId) {
                $row.attr('data-parent-id', parentId);
                const parentChain = this._buildParentChain(record);
                if (parentChain.length > 0) {
                    $row.attr('data-parent-chain', parentChain.join(','));
                }
            }

            const countSubtask = record.data.count_subtask || 0;
            $row.attr('data-count-subtask', countSubtask);

            if (countSubtask > 0) {
                $td.find('.o_tree_toggle').remove();

                const $toggle = $('<span class="o_tree_toggle" style="cursor:pointer;margin-right:5px;"><i class="fa fa-caret-down"></i></span>');
                $td.prepend($toggle);
                $row.addClass('open');
                $td.css('font-weight', 'bold');

                $toggle.on('click', (ev) => {
                    ev.stopPropagation();
                    const isOpen = $row.hasClass('open');
                    const nodeId = record.data.id;
                    if (isOpen) {
                        this._collapseAllChildRows(nodeId);
                        $toggle.html('<i class="fa fa-caret-right"></i>');
                        $row.removeClass('open');
                        this.expandedNodes = this.expandedNodes.filter(id => id !== nodeId);
                        // Save to session storage
                        this._saveExpandedStateToSessionStorage();
                    } else {
                        this._expandDirectChildRows(nodeId);
                        $toggle.html('<i class="fa fa-caret-down"></i>');
                        $row.addClass('open');
                        if (!this.expandedNodes.includes(nodeId)) {
                            this.expandedNodes.push(nodeId);
                        }
                        // Save to session storage
                        this._saveExpandedStateToSessionStorage();
                    }
                });
            }
            this._applySavedExpandedState();
        },

        async _onRowClicked(event) {
            event.preventDefault();
            const recordId = event.currentTarget?.dataset?.resId;
            if (!recordId) {
                return;
            }
            if (recordId) {
                var viewId = await this._rpc({
                    model: 'project.task',
                    method: 'get_ref_form_view_id',
                    args: [],
                });
                this.trigger_up('do_action', {
                    action: {
                        type: 'ir.actions.act_window',
                        res_model: this.state.model,
                        res_id: parseInt(recordId),
                        views: [[viewId, 'form']],
                        target: 'new',
                    }
                });
            }
        },

        _renderView: function () {
            var res = this._super();
            this.$el.children(":first").css({cursor: "auto"});
            return res;
        },

        updateState: function (state, params) {
            let result = this._super.apply(this, arguments);
            this.start();
            return result;
        },

        _getScrollPositionFromSessionStorage: function () {
            try {
                const savedPosition = sessionStorage.getItem('one2many_hierarchy_scroll');
                return savedPosition ? JSON.parse(savedPosition) : null;
            } catch (e) {
                console.error("Failed to parse scroll position from session storage", e);
                return null;
            }
        },

        _saveScrollPositionToSessionStorage: function () {
            const $scrollableElement = this.$el.find('.o_list_table_grouped').closest('.table-responsive');
            if ($scrollableElement.length) {
                const scrollPosition = {
                    left: $scrollableElement.scrollLeft(),
                    top: $scrollableElement.scrollTop()
                };
                sessionStorage.setItem('one2many_hierarchy_scroll', JSON.stringify(scrollPosition));
            }
        },

        onDestroy: function () {
            this._saveScrollPositionToSessionStorage();
            this._super.apply(this, arguments);
        },
    });

    const HierarchyFieldOne2Many = FieldOne2Many.extend({
        _getRenderer: function () {
            return HierarchyRenderer;
        },
    });

    fieldRegistry.add('one2many_hierarchy_widget', HierarchyFieldOne2Many);

    return {
        HierarchyRenderer,
    };
});