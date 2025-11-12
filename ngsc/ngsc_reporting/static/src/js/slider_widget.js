/** @odoo-module **/

import {NumericField} from 'web.basic_fields';
import registry from 'web.field_registry';
import {py_eval} from 'web.py_utils'

export const SliderField = NumericField.extend({

    tagName: 'input',

    init: function () {
        this._super.apply(this, arguments);
        this._doDebouncedAction = this._doAction;
    },

    _prepareInput: function ($input) {
        const result = this._super.apply(this, arguments);
        const {step, min, max} = this.nodeOptions;
        console.log('---- _prepareInput')
        console.log(this._getValue())
        const currentValue = +this._getValue() || 0;
        this.$input.attr({
            type: 'range',
            step: step ?? 1,
            min: min ?? 0,
            max: max ?? 100,
        });
        this.$input.val(currentValue);
        this.$input.addClass('w-100');
        this.$input[0].setSelectionRange = undefined;
        return result;
    },

    _render() {
        this._prepareInput();
        const isReadonly = this.mode === 'readonly';
        const $el = $('<div>').addClass('d-flex w-100');
        this.$el.replaceWith($el);
        this.$el = $el;
        this.$input.appendTo(this.$el);
        const $value = $('<span>')
        if (!isReadonly) {
            $value.addClass('ml-2');
        }
        if (this.$value) {
            this.$value.remove();
        }
        this.$value = $value.appendTo(this.$el);
        this._onInput();
        this.$input.prop('disabled', isReadonly);
        this.$input.css('display', isReadonly ? 'none' : 'block');
        this.$input
            .on('input', this._onInput.bind(this))
            .on('change', this._onChange.bind(this));
    },

    _onInput() {
        let {prefix, subfix} = this.nodeOptions
        prefix = prefix || ''
        subfix = subfix || ''
        this.$value.text(prefix + this._formatValue(+this._getValue()) + subfix);
    },

})

registry.add('slider', SliderField);
