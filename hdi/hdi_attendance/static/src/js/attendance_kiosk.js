/** @odoo-module **/

import { MyAttendances } from "@hr_attendance/components/my_attendances/my_attendances";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { onWillStart } from "@odoo/owl";

patch(MyAttendances.prototype, {
    setup() {
        super.setup();
        this.orm = useService("orm");
        
        onWillStart(async () => {
            await this.loadWorkLocations();
        });
    },
    
    async loadWorkLocations() {
        const employeeId = this.props.employee_id || this.state.employee.id;
        
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
    },
    
    async _onAttendanceButtonClick(ev) {
        ev.preventDefault();
        const button = ev.currentTarget;
        
        // Prevent double click
        if (button.classList.contains('oe-processing')) {
            return;
        }
        button.classList.add('oe-processing');
        
        try {
            // Get geolocation
            const position = await new Promise((resolve, reject) => {
                if (navigator.geolocation) {
                    navigator.geolocation.getCurrentPosition(resolve, reject);
                } else {
                    reject(new Error('Geolocation not supported'));
                }
            });
            
            // Get selected location
            const locationSelect = document.getElementById('hdi_location_id');
            const locationId = locationSelect ? parseInt(locationSelect.value) : false;
            
            // Manual attendance with context
            const context = {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            };
            
            if (locationId) {
                context.en_location_id = locationId;
            }
            
            const result = await this.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.state.employee.id], 'hr_attendance.hr_attendance_action_my_attendances'],
                { context }
            );
            
            button.classList.remove('oe-processing');
            
            if (result.action) {
                await this.action.doAction(result.action);
            } else if (result.warning) {
                this.notification.add(result.warning, { type: 'warning' });
            }
        } catch (error) {
            button.classList.remove('oe-processing');
            this.notification.add(
                error.message || 'Không thể lấy vị trí GPS. Vui lòng bật GPS và thử lại.',
                { type: 'danger' }
            );
        }
    },
});
