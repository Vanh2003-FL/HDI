odoo.define('ngsc_hr_skill.skill_level_bar', function (require) {
    "use strict";

    var AbstractField = require('web.AbstractField');
    var fieldRegistry = require('web.field_registry');

    var StepProgressBar = AbstractField.extend({
        template: 'StepProgressBar', supportedFieldTypes: ['integer'],

        _render: function () {
            var expectedLevel = this.recordData.expected_level_id && this.recordData.expected_level_id.data
                ? String(this.recordData.expected_level_id.data.display_name)
                : null;
            var currentLevel = this.recordData.current_level_id && this.recordData.current_level_id.data
                ? String(this.recordData.current_level_id.data.display_name)
                : null;
            var level_steps = this.recordData.level_steps
                ? this.recordData.level_steps.split(",").map(String)
                : [];
            var currentIndex = currentLevel ? level_steps.indexOf(currentLevel) : -1;
            var expectedIndex = expectedLevel ? level_steps.indexOf(expectedLevel) : -1;
            var html = '<div class="progress-container">';
            for (var i = 0; i < level_steps.length; i++) {
                var stepClass = (currentIndex >= i && currentIndex !== -1) ? "step-active" : "step-inactive";
                var expectedMarker = (expectedIndex == i) ? '<div class="expected-marker">🔺</div><div class="expected-text">Kỳ vọng</div>' : "";

                html += `<div class="step ${stepClass}">${level_steps[i]}${expectedMarker}</div>`;
                if (i < level_steps.length - 1) {
                    var connectorClass = (currentIndex > i && currentIndex !== -1) ? "connector-active" : "connector-inactive";
                    html += `<div class="connector ${connectorClass}"></div>`;
                }
            }
            html += '</div>';
            this.$el.html(html);
        }
    });

    fieldRegistry.add('step_progress_bar', StepProgressBar);
});