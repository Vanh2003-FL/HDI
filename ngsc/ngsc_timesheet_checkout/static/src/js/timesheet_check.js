// Định nghĩa module JavaScript mở rộng hành vi checkin/checkout trong Odoo
odoo.define("ngsc_timesheet_checkout.timesheet_check", function (require) {
    "use strict";

    // Import các module cần thiết
    const rpc = require("web.rpc");                         // Dùng để gọi RPC tới server Python
    const MyAttendances = require("hr_attendance.my_attendances");  // Widget giao diện chấm công mặc định

    // Ghi lại phương thức gốc để gọi lại sau nếu không can thiệp
    const original_manual_attendance = MyAttendances.prototype._manual_attendance;

    // Ghi đè phương thức _manual_attendance (khi bấm nút Check In / Check Out)
    MyAttendances.include({
        _manual_attendance: function (position) {
            const self = this;

            // Gọi RPC tới server để lấy cấu hình bật/tắt popup khai Timesheet
            return rpc.query({
                route: '/timesheet_checkout/config',  // Route trả về enable_timesheet_popup
            }).then(function (result) {

                // Nếu nhân viên đang "checked_in" và bật cấu hình khai timesheet trước khi checkout
                if (
                    self.employee.attendance_state === "checked_in" &&
                    result.enable_timesheet_popup
                ) {
                    // Hiển thị form wizard popup cho phép khai timesheet trước khi checkout
                    return self.do_action({
                        type: 'ir.actions.act_window',
                        name: 'Khai Timesheet trước khi Checkout',
                        res_model: 'timesheet.checkout.wizard',
                        view_mode: 'form',
                        views: [[false, 'form']],
                        target: 'new',  // Hiển thị ở dạng popup (modal)
                    });
                }

                // Ngược lại: không can thiệp, gọi lại hàm gốc check in / check out
                return original_manual_attendance.call(self, position);
            });
        },
    });
});
