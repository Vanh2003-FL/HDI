/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";

/**
 * HDI Attendance - Block Double Click
 * Prevent users from clicking check in/out button multiple times
 */

let isProcessing = false;

// Override the attendance action to prevent double clicks
const originalAttendanceAction = odoo.__DEBUG__.services["action"].doAction;

if (originalAttendanceAction) {
    odoo.__DEBUG__.services["action"].doAction = function (action, options) {
        // Check if this is an attendance check in/out action
        if (action && action.type === 'ir.actions.client' && 
            (action.tag === 'hr_attendance_kiosk_mode' || 
             action.context?.attendance_action)) {
            
            if (isProcessing) {
                console.log('HDI Attendance: Blocking duplicate request');
                return Promise.reject('Request already in progress');
            }
            
            isProcessing = true;
            
            return originalAttendanceAction.call(this, action, options).finally(() => {
                // Reset after 3 seconds to prevent issues
                setTimeout(() => {
                    isProcessing = false;
                }, 3000);
            });
        }
        
        return originalAttendanceAction.call(this, action, options);
    };
}

console.log('HDI Attendance: Block click protection loaded');
