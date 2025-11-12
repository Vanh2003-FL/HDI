odoo.define('ngsc_project.form_renderer', function (require) {
    "use strict";

    const rpc = require('web.rpc');
    const FormRenderer = require('web.FormRenderer');
    const FormController = require('web.FormController');

    FormRenderer.include({
        async _renderView() {
            const _super = this._super.bind(this);
            if (this.state.model === 'project.project') {
                const stage_id = this.state.data.stage_id?.data?.id;
                if (stage_id) {
                    try {
                        this._requiredFieldsFromStage = await rpc.query({
                            model: 'project.project.stage',
                            method: 'get_required_fields',
                            args: [[stage_id]],
                        });
                    } catch (e) {
                        console.error(e);
                    }
                } else {
                    this._requiredFieldsFromStage = [];
                }
            }
            const res = await _super(...arguments);
            if (this._requiredFieldsFromStage?.length) {
                this._requiredFieldsFromStage.forEach(fieldName => {
                    const $widget = this.$el.find(`.o_field_widget[name="${fieldName}"]`);
                    $widget.addClass('o_required_modifier o_dynamic_required');
                });
            }
            return res;
        },

        confirmChange: function () {
            return this._super.apply(this, arguments).then(async (resetWidgets) => {
                if (this.state.model === 'project.project') {
                    const stage_id = this.state.data.stage_id?.data?.id;
                    await this.updateDynamicRequiredFields(stage_id);
                }
                return resetWidgets;
            });
        },

        async updateDynamicRequiredFields(stage_id) {
            if (this._lastRequiredFields?.length) {
                this.applyRequiredFieldClasses(this._lastRequiredFields);
            }

            if (!stage_id) return;

            try {
                const requiredFields = await rpc.query({
                    model: 'project.project.stage',
                    method: 'get_required_fields',
                    args: [[stage_id]],
                });
                this._lastRequiredFields = requiredFields;
                this.applyRequiredFieldClasses(requiredFields);
            } catch (e) {
                console.error(e);
            }
        },

        applyRequiredFieldClasses(requiredFields) {
            this.$el.find('.o_dynamic_required')
                .removeClass('o_required_modifier o_dynamic_required');
            requiredFields.forEach(fieldName => {
                const $widget = this.$el.find(`.o_field_widget[name="${fieldName}"]`);
                if ($widget.length) {
                    $widget.addClass('o_required_modifier o_dynamic_required');
                }
            });
        }
    });

    FormController.include({
        async saveRecord() {
            if (this.modelName !== 'project.project') {
                return this._super.apply(this, arguments);
            }
            const _super = this._super.bind(this);
            const stage_id = this.renderer.state.data.stage_id?.data?.id;
            if (!stage_id) {
                return _super(...arguments);
            }
            const requiredFields = await rpc.query({
                model: 'project.project.stage',
                method: 'get_required_fields',
                args: [[stage_id]],
            });
            const missingFields = [];
            for (const fieldName of requiredFields) {
                if (!(fieldName in this.renderer.state.data)) continue;
                const field = this.renderer.state.data[fieldName];
                const value = field?.value ?? field?.data ?? null;
                const isEmpty = (
                    value === null ||
                    value === false ||
                    (typeof value === 'string' && value.trim() === '') ||
                    (Array.isArray(value) && value.length === 0)
                );
                if (isEmpty) {
                    missingFields.push(fieldName);
                }
            }
            if (missingFields.length > 0) {
                this._notifyInvalidFields(missingFields);
                return Promise.reject();
            }
            return _super(...arguments);
        }
    });
});
