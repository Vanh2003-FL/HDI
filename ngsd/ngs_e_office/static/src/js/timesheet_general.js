odoo.define('ngs_e_office.room_booking', function (require) {
    'use strict';

    const viewRegistry = require('web.view_registry');

    const CalendarRenderer = require('web.CalendarRenderer');
    const CalendarPopover = require('web.CalendarPopover');
    const CalendarView = require('web.CalendarView');

    const RoomBookingCalendarPopover = CalendarPopover.extend({
        template: 'Calendar.room.booking.popover',
        events: _.extend({}, CalendarPopover.prototype.events, {
            'click .o_cw_popover_cancel': '_onClickTSCancel'
        }),

        _onClickTSCancel(ev) {
             ev.preventDefault();
             const self = this;
            return this._rpc({
                model: self.modelName,
                method: 'button_cancel',
                args: [[parseInt(this.event.id)]],
            }).then( function (action) {
                if (action) self.do_action(action);
                self.__parentedParent.__parentedParent.reload();
            });
        },
    })

    const RoomBookingCalendarRenderer = CalendarRenderer.extend({
        config: _.extend({}, CalendarRenderer.prototype.config, {
            CalendarPopover: RoomBookingCalendarPopover,
        }),
    })

    const RoomBookingCalendarView = CalendarView.extend({
        config: Object.assign({}, CalendarView.prototype.config, {
            Renderer: RoomBookingCalendarRenderer,
        }),
    });

    viewRegistry.add('room_booking', RoomBookingCalendarView);
    return CalendarView;
});
