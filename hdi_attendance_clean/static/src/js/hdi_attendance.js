/** @odoo-module **/

import { MyAttendances } from "@hr_attendance/views/my_attendances";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(MyAttendances.prototype, {
    async willStart() {
        await super.willStart(...arguments);
        const self = this;
        
        // Get working locations
        this.locations = await this.orm.call(
            'hr.employee',
            'get_working_locations',
            [[this.employee.id]]
        );
        
        // Check if user can checkout at different location
        this.en_checked_diff_ok = await this.orm.call(
            'hr.employee',
            'get_en_checked_diff_ok',
            [[this.employee.id]]
        );
    },

    async _manual_attendance(position) {
        const self = this;
        const locations = document.getElementById('hdi_location_id');
        
        let ctx = Object.assign({}, session.user_context, {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
        });
        
        if (locations) {
            ctx = Object.assign(ctx, {
                hdi_location_id: document.getElementById('hdi_location_id').selectedOptions[0].value,
            });
        }
        
        try {
            const result = await this.orm.call(
                "hr.employee",
                "attendance_manual",
                [[self.employee.id], "hr_attendance.hr_attendance_action_my_attendances"],
                { context: ctx }
            );
            
            const button = document.querySelector('.o_hr_attendance_sign_in_out_icon');
            if (button && button.classList.contains('oe-processing')) {
                button.classList.remove('oe-processing');
            }
            
            if (result.action) {
                await this.actionService.doAction(result.action);
            } else if (result.warning) {
                this.showPositionError(result.warning);
            }
        } catch (error) {
            const button = document.querySelector('.o_hr_attendance_sign_in_out_icon');
            if (button && button.classList.contains('oe-processing')) {
                button.classList.remove('oe-processing');
            }
            throw error;
        }
    },
});
