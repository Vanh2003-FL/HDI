odoo.define('ngsd_base.TimesheetGeneral', function (require) {
    'use strict';

    const viewRegistry = require('web.view_registry');

    const CalendarRenderer = require('web.CalendarRenderer');
    const CalendarPopover = require('web.CalendarPopover');
    const CalendarView = require('web.CalendarView');

    const TSCalendarPopover = CalendarPopover.extend({
        isEventEditable() {
            return false;
        },
    })

    const TSCalendarRenderer = CalendarRenderer.extend({
        config: _.extend({}, CalendarRenderer.prototype.config, {
            CalendarPopover: TSCalendarPopover,
        }),
    })

    const TSCalendarView = CalendarView.extend({
        config: Object.assign({}, CalendarView.prototype.config, {
            Renderer: TSCalendarRenderer,
        }),
    });

    viewRegistry.add('timesheet_general', TSCalendarView);
    return CalendarView;
});
