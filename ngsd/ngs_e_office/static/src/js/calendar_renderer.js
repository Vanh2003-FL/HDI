odoo.define('ngs_e_office.CalendarPopover', function (require) {
"use strict";

const AttendeeCalendarPopover = require('calendar.CalendarRenderer').AttendeeCalendarPopover;

AttendeeCalendarPopover.include({
    _isEventPrivate() {
        return this.event.extendedProps.record.is_private_booking;
    },
});

});