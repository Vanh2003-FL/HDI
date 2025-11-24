/** @odoo-module **/

import { MyAttendances } from "@hr_attendance/components/my_attendances/my_attendances";
import { patch } from "@web/core/utils/patch";
import { onWillStart, useState } from "@odoo/owl";

patch(MyAttendances.prototype, {
    setup() {
        super.setup(...arguments);

        // Initialize locations state
        if (!this.state.locations) {
            this.state.locations = [];
        }
        if (!this.state.en_checked_diff_ok) {
            this.state.en_checked_diff_ok = false;
        }

        onWillStart(async () => {
            await this.loadWorkLocations();
        });
    },

    async loadWorkLocations() {
        try {
            const employeeId = this.props.employeeId || this.employee?.id;
            if (!employeeId) return;

            // Load work locations
            const locations = await this.orm.call(
                'hr.employee',
                'get_working_locations',
                [employeeId]
            );
            this.state.locations = locations || [];

            // Check if can check in at different location
            const canCheckDiff = await this.orm.call(
                'hr.employee',
                'get_en_checked_diff_ok',
                [employeeId]
            );
            this.state.en_checked_diff_ok = canCheckDiff || false;
        } catch (error) {
            console.error('Error loading work locations:', error);
        }
    },
});
