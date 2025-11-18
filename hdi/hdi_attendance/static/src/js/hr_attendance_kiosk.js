/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component } from "@odoo/owl";

/**
 * HDI Attendance Kiosk Enhancement
 * Add geolocation and custom features to attendance kiosk
 */

class HDIAttendanceKiosk extends Component {
    setup() {
        this.orm = useService("orm");
        this.notification = useService("notification");
    }

    /**
     * Get current geolocation
     */
    async getGeolocation() {
        return new Promise((resolve, reject) => {
            if (!navigator.geolocation) {
                reject(new Error("Geolocation is not supported by this browser."));
                return;
            }

            navigator.geolocation.getCurrentPosition(
                (position) => {
                    resolve({
                        latitude: position.coords.latitude,
                        longitude: position.coords.longitude,
                        accuracy: position.coords.accuracy,
                    });
                },
                (error) => {
                    reject(error);
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 0,
                }
            );
        });
    }

    /**
     * Enhanced check in/out with geolocation
     */
    async checkInOut() {
        try {
            // Get geolocation if required
            const settings = await this.orm.call(
                'ir.config_parameter',
                'get_param',
                ['hdi_attendance.require_geolocation']
            );

            let location = null;
            if (settings === 'True') {
                try {
                    location = await this.getGeolocation();
                } catch (error) {
                    this.notification.add(
                        "Không thể lấy vị trí GPS. Vui lòng bật GPS và thử lại.",
                        { type: "danger" }
                    );
                    return;
                }
            }

            // Perform check in/out with location data
            const result = await this.orm.call(
                'hr.attendance',
                'attendance_action_change',
                [],
                { location: location }
            );

            if (result) {
                this.notification.add(
                    result.action === 'check_in' ? "Chấm công vào thành công!" : "Chấm công ra thành công!",
                    { type: "success" }
                );
            }
        } catch (error) {
            this.notification.add(
                "Có lỗi xảy ra: " + error.message,
                { type: "danger" }
            );
        }
    }
}

HDIAttendanceKiosk.template = "hdi_attendance.KioskTemplate";

registry.category("actions").add("hdi_attendance_kiosk", HDIAttendanceKiosk);

console.log('HDI Attendance: Kiosk enhancement loaded');
