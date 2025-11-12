odoo.define('hr_attendance_custom.my_attendances', function (require) {
    "use strict";

    const MyAttendances = require('hr_attendance.my_attendances');
    const session = require('web.session');
    const rpc = require('web.rpc');
    const core = require('web.core');
    const Dialog = require('web.Dialog');
    const _t = core._t;

    let pendingClick = false;

    function preventDoubleClick() {
        if (pendingClick) {
            Dialog.alert(null, _t("Bạn đã bấm rồi, vui lòng chờ xử lý xong."));
            return true;
        }
        pendingClick = true;
        setTimeout(() => {
            pendingClick = false;
        }, 3000);
        return false;
    }

    function formatOdooDatetimeUTC(date) {
        function pad(n) {
            return n < 10 ? '0' + n : n;
        }

        return date.getUTCFullYear() + '-' +
            pad(date.getUTCMonth() + 1) + '-' +
            pad(date.getUTCDate()) + ' ' +
            pad(date.getUTCHours()) + ':' +
            pad(date.getUTCMinutes()) + ':' +
            pad(date.getUTCSeconds());
    }

    // 🔹 Offline queue utils
    function saveToOfflineQueue(payload) {
        let queue = JSON.parse(localStorage.getItem("attendance_offline_queue") || "[]");
        queue.push(payload);
        localStorage.setItem("attendance_offline_queue", JSON.stringify(queue));
        console.warn("📥 [OFFLINE] Log đã lưu offline:", payload);
        Dialog.alert(null, _t("Không có kết nối. Thao tác đã được lưu tạm và sẽ gửi khi online."));
    }

    function flushOfflineQueue() {
        let queue = JSON.parse(localStorage.getItem("attendance_offline_queue") || "[]");
        if (!queue.length) return;

        console.log("🔄 [OFFLINE] Bắt đầu gửi lại", queue.length, "log offline...");
        const newQueue = [];

        queue.forEach(payload => {
            rpc.query({
                route: '/hr_attendance_async/log',
                params: payload,
            }).then(res => {
                console.log("✅ [OFFLINE] Gửi thành công:", res);
            }).catch(err => {
                console.error("❌ [OFFLINE] Gửi thất bại, giữ lại:", err);
                newQueue.push(payload);
            });
        });

        localStorage.setItem("attendance_offline_queue", JSON.stringify(newQueue));
    }

    // Lắng nghe khi mạng online trở lại
    window.addEventListener("online", flushOfflineQueue);

    MyAttendances.include({

        _sendAttendanceLog(values) {
            console.log("📤 [LOG] Payload gửi tới controller:", values);
            rpc.query({
                route: '/hr_attendance_async/log',
                params: values,
            }).then(res => {
                console.log("📥 [LOG] Kết quả trả về từ controller:", res);
            }).catch(err => {
                console.error("❌ [LOG] Lỗi RPC log:", err);
                saveToOfflineQueue(values);
            });
        },

        update_attendance() {
            const self = this;
            const $btn = this.$('.o_hr_attendance_sign_in_out_icon');

            if ($btn.prop('disabled')) return;
            if (preventDoubleClick()) return;

            $btn.prop('disabled', true).addClass('o_disabled');

            const employee_id = (self.employee && self.employee.id) || session.employee_id;
            if (!employee_id) {
                Dialog.alert(this, _t("Không tìm thấy nhân viên hiện tại"));
                $btn.prop('disabled', false).removeClass('o_disabled');
                return;
            }

            let actionToLog = self.employee && self.employee.attendance_state === "checked_in"
                ? "check_out" : "check_in";

            const ts = formatOdooDatetimeUTC(new Date());
            const result = this._super.apply(this, arguments);

            const afterCore = () => {
                const payload = {
                    employee_id: employee_id,
                    action: actionToLog,
                    timestamp: ts,
                };
                console.log("📦 [DEBUG] Payload final gửi log:", payload);
                self._sendAttendanceLog(payload);
            };

            if (result && typeof result.then === "function") {
                result.then(afterCore).finally(() => {
                    setTimeout(() => $btn.prop('disabled', false).removeClass('o_disabled'), 1500);
                });
                return result;
            } else {
                afterCore();
                setTimeout(() => $btn.prop('disabled', false).removeClass('o_disabled'), 1500);
                return result;
            }
        },

    });

    return MyAttendances;
});
