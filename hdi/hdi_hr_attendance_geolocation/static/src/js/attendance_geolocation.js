/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MyAttendances } from "@hr_attendance/components/my_attendances/my_attendances";
import { KioskConfirm } from "@hr_attendance/components/kiosk_confirm/kiosk_confirm";
import { useService } from "@web/core/utils/hooks";

// Geolocation options
const GEO_OPTIONS = {
    enableHighAccuracy: true,
    timeout: 60000, // 60 seconds
    maximumAge: 0
};

/**
 * Patch MyAttendances component để thêm geolocation
 */
patch(MyAttendances.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.dialog = useService("dialog");
    },

    /**
     * Override update_attendance để lấy GPS trước khi check-in/out
     */
    async update_attendance() {
        const isGeolocationEnabled = await this.orm.call(
            'ir.config_parameter',
            'get_param',
            ['hdi_hr_attendance_geolocation.enabled', 'True']
        );

        const isGeolocationRequired = await this.orm.call(
            'ir.config_parameter',
            'get_param',
            ['hdi_hr_attendance_geolocation.required', 'False']
        );

        if (isGeolocationEnabled === 'False') {
            // Nếu tắt geolocation, gọi hàm gốc
            return super.update_attendance();
        }

        // Kiểm tra hỗ trợ geolocation
        if (!navigator.geolocation) {
            if (isGeolocationRequired === 'True') {
                this.notification.add(
                    this.env._t("Trình duyệt không hỗ trợ định vị GPS. Vui lòng sử dụng trình duyệt khác!"),
                    { type: "danger" }
                );
                return;
            } else {
                // Không bắt buộc, cho phép chấm công không có GPS
                return super.update_attendance();
            }
        }

        // Lấy vị trí GPS
        try {
            const position = await this._getCurrentPosition();
            await this._manual_attendance(position);
        } catch (error) {
            console.error("Geolocation error:", error);
            
            if (isGeolocationRequired === 'True') {
                this._showPositionError(error);
            } else {
                // Không bắt buộc GPS, hỏi người dùng có muốn tiếp tục không
                this.dialog.add(
                    {
                        title: this.env._t("Không lấy được vị trí GPS"),
                        body: this.env._t(
                            "Không thể xác định vị trí của bạn. Bạn có muốn tiếp tục chấm công mà không có thông tin vị trí không?"
                        ),
                        confirmLabel: this.env._t("Tiếp tục"),
                        confirm: async () => {
                            await super.update_attendance();
                        },
                        cancel: () => {},
                    }
                );
            }
        }
    },

    /**
     * Lấy vị trí hiện tại từ GPS
     */
    _getCurrentPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, GEO_OPTIONS);
        });
    },

    /**
     * Thực hiện check-in/out với thông tin GPS
     */
    async _manual_attendance(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;
        const accuracy = position.coords.accuracy;

        console.log("GPS Position:", {
            latitude: latitude,
            longitude: longitude,
            accuracy: accuracy
        });

        try {
            // Gọi server với context chứa tọa độ GPS
            const result = await this.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.employee.id]],
                {
                    context: {
                        latitude: latitude,
                        longitude: longitude,
                        gps_accuracy: accuracy
                    }
                }
            );

            if (result.action) {
                this.action.doAction(result.action);
            } else if (result.warning) {
                this.notification.add(result.warning, { type: "warning" });
            }

            // Reload để cập nhật trạng thái
            await this._loadData();
        } catch (error) {
            console.error("Error in manual attendance:", error);
            this.notification.add(
                this.env._t("Lỗi khi chấm công: ") + error.message,
                { type: "danger" }
            );
        }
    },

    /**
     * Hiển thị lỗi geolocation
     */
    _showPositionError(error) {
        let errorMessage = this.env._t("Không thể xác định vị trí của bạn.");

        switch (error.code) {
            case error.PERMISSION_DENIED:
                errorMessage = this.env._t(
                    "Bạn đã từ chối quyền truy cập vị trí. Vui lòng cho phép truy cập vị trí trong cài đặt trình duyệt."
                );
                break;
            case error.POSITION_UNAVAILABLE:
                errorMessage = this.env._t(
                    "Thông tin vị trí không khả dụng. Vui lòng kiểm tra kết nối GPS/WiFi."
                );
                break;
            case error.TIMEOUT:
                errorMessage = this.env._t(
                    "Hết thời gian chờ lấy vị trí. Vui lòng thử lại."
                );
                break;
        }

        this.dialog.add({
            title: this.env._t("Lỗi Định vị GPS"),
            body: errorMessage,
            confirmLabel: this.env._t("Đóng"),
            confirm: () => {},
        });
    },
});

/**
 * Patch KioskConfirm component để thêm geolocation cho kiosk mode
 */
patch(KioskConfirm.prototype, {
    setup() {
        super.setup(...arguments);
        this.notification = useService("notification");
        this.dialog = useService("dialog");
        this._attendanceDebounce = null;
    },

    /**
     * Override update_attendance cho kiosk mode
     */
    async update_attendance() {
        // Debounce để tránh click nhiều lần
        if (this._attendanceDebounce) {
            return;
        }

        this._attendanceDebounce = setTimeout(() => {
            this._attendanceDebounce = null;
        }, 2000);

        const isGeolocationEnabled = await this.orm.call(
            'ir.config_parameter',
            'get_param',
            ['hdi_hr_attendance_geolocation.enabled', 'True']
        );

        if (isGeolocationEnabled === 'False') {
            return super.update_attendance();
        }

        if (!navigator.geolocation) {
            this.notification.add(
                this.env._t("Trình duyệt không hỗ trợ định vị GPS!"),
                { type: "warning" }
            );
            return super.update_attendance();
        }

        try {
            const position = await this._getCurrentPosition();
            await this._manual_attendance_kiosk(position);
        } catch (error) {
            console.error("Geolocation error in kiosk:", error);
            // Trong chế độ kiosk, vẫn cho phép chấm công nếu không có GPS
            await super.update_attendance();
        }
    },

    /**
     * Lấy vị trí GPS cho kiosk
     */
    _getCurrentPosition() {
        return new Promise((resolve, reject) => {
            navigator.geolocation.getCurrentPosition(resolve, reject, GEO_OPTIONS);
        });
    },

    /**
     * Chấm công kiosk với GPS
     */
    async _manual_attendance_kiosk(position) {
        const latitude = position.coords.latitude;
        const longitude = position.coords.longitude;

        try {
            const result = await this.orm.call(
                'hr.employee',
                'attendance_manual',
                [[this.employee_id]],
                {
                    context: {
                        latitude: latitude,
                        longitude: longitude,
                    }
                }
            );

            if (result.action) {
                this.action.doAction(result.action);
            } else if (result.warning) {
                this.notification.add(result.warning, { type: "warning" });
            }

            // Return to main screen
            this.do_return();
        } catch (error) {
            console.error("Error in kiosk attendance:", error);
            this.notification.add(
                this.env._t("Lỗi chấm công: ") + error.message,
                { type: "danger" }
            );
        }
    },
});
