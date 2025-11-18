/** @odoo-module **/

import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

/**
 * HDI Attendance - Block Double Click
 * Prevent users from clicking check in/out button multiple times
 */

let isProcessing = false;

// Patch the action service to prevent double clicks
const actionService = {
    dependencies: ["action"],
    start(env, { action: actionService }) {
        const originalDoAction = actionService.doAction.bind(actionService);
        
        actionService.doAction = async (actionRequest, options = {}) => {
            // Check if this is an attendance action
            if (actionRequest && 
                (actionRequest.tag === 'hr_attendance_kiosk_mode' || 
                 actionRequest.context?.attendance_action)) {
                
                if (isProcessing) {
                    console.log('HDI Attendance: Blocking duplicate request');
                    return Promise.reject(new Error('Request already in progress'));
                }
                
                isProcessing = true;
                
                try {
                    const result = await originalDoAction(actionRequest, options);
                    return result;
                } finally {
                    // Reset after 3 seconds
                    setTimeout(() => {
                        isProcessing = false;
                    }, 3000);
                }
            }
            
            return originalDoAction(actionRequest, options);
        };
        
        console.log('HDI Attendance: Block click protection loaded');
        return actionService;
    },
};

registry.category("services").add("hdi_attendance_block_click", actionService);

