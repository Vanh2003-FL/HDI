
/** @odoo-module **/

import { registry } from '@web/core/registry';
import { DateField } from '@web/views/fields/date/date_field';
import { DatePicker } from '@web/core/datepicker/datepicker';
import { formatDate, parseDate } from '@web/core/l10n/dates';

const fieldRegistry = registry.category('fields');

// Modified DatePicker to be used for month and years
class MonthYearDatePicker extends DatePicker {

    _parseMonthYearDate(value, field, options) {
        if (!value) {
            return false;
        }
        const datePattern = this.options.format;
        const datePatternWoZero = datePattern.replace('MM','M');
        let date;
        if (options && options.isUTC) {
            date = moment.utc(value);
        } else {
            date = moment.utc(value, [datePattern, datePatternWoZero, moment.ISO_8601], true);
        }
        if (date.isValid()) {
            if (date.year() === 0) {
                date.year(moment.utc().year());
            }
            if (date.year() >= 1900) {
                date.toJSON = function () {
                    return this.clone().locale('en').format('YYYY-MM-DD');
                };
                return date;
            }
        }
        throw new Error(`'${value}' is not a correct date`);
    }

    _parseClient(v) {
        return this._parseMonthYearDate(v, null, {timezone: false});
    }
}

// Widget 'month_year_format' to be added from the xml at field declaration
export class MonthYearFormatFieldDate extends DateField {
    static supportedTypes = ['date'];
            this._super.apply(this, arguments);
            this.datepickerOptions = _.defaults(
                {},
                this.nodeOptions.datepicker || {},
                {
                    defaultDate: this.value,
                    format: this._convertMonthYearDateFormat(time.getLangDateFormat()),
                    viewMode: 'months'
                }
            );
        },

        _convertMonthYearDateFormat: function (dateFormat) {
            var isletter = /[a-zA-Z]/;
            dateFormat = dateFormat
            .replace("Do", "")
            .replace(/D/g, "")
            .replace("//", "/")
            .replace("..", ".")
            .replace("--", "-");
            if (!isletter.test(dateFormat[0])){
                // If we have some . or / or - at the beggining of the string, remove it.
                dateFormat = dateFormat.substring(1);
            }
            return dateFormat;
        },

        _formatMonthYearDate: function (value, field, options) {
            if (value === false) {
                return "";
            }
            return value.format(this.datepickerOptions.format);
        },

        _formatValue: function (value) {
            var options = _.extend({}, this.nodeOptions, { data: this.recordData }, this.formatOptions);
            return this._formatMonthYearDate(value, this.field, options);
        },

        _makeDatePicker: function () {
            return new MonthYearDateWidget(this, this.datepickerOptions);
        }

    });

    fieldRegistry.add('month_year_format', MonthYearFormatFieldDate);

    return {
        MonthYearDateWidget: MonthYearDateWidget
    }

});
