/** @odoo-module **/

import { CalendarRenderer } from '@web/views/calendar/calendar_renderer';
import { CalendarPopover } from '@web/views/calendar/calendar_popover';
import { CalendarView } from '@web/views/calendar/calendar_view';
import { registry } from '@web/core/registry';

const viewRegistry = registry.category('views');

export class TSCalendarPopover extends CalendarPopover {
    isEventEditable() {
        return false;
    }
}

export class TSCalendarRenderer extends CalendarRenderer {
    static components = {
        ...CalendarRenderer.components,
        CalendarPopover: TSCalendarPopover,
    };
}

export class TSCalendarView extends CalendarView {
    static components = {
        ...CalendarView.components,
        Renderer: TSCalendarRenderer,
    };
}

viewRegistry.add('timesheet_general', {
    ...TSCalendarView,
});
