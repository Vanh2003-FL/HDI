odoo.define("mbank_attendance.attendances_work_location", function (require) {
    "use strict";

    import { MyAttendances } from 'hr_attendance.my_attendances';
    const session = require("web.session");

    MyAttendances.include({
        willStart: async function () {
            var def = await this._super.apply(this, arguments)
            var self = this;
//            if (self.employee.attendance_state != 'checked_in'){
            var def2 = this._rpc({
                model: 'hr.employee',
                method: 'get_working_locations',
                args: [self.employee.id],
            }).then(function (result) {
                self.locations = result
            })
            var def3 = this._rpc({
                model: 'hr.employee',
                method: 'get_en_checked_diff_ok',
                args: [self.employee.id],
            }).then(function (result) {
                self.en_checked_diff_ok = result
            })
            return Promise.all([def3,def2, def]);
//            }else {
//                return def
//            }
        },
        _manual_attendance: function (position) {
            var self = this;
            var locations = document.getElementById('en_location_id');
            var ctx = Object.assign(session.user_context, {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            });
            if (locations){
                ctx = Object.assign(session.user_context, {
                    latitude: position.coords.latitude,
                    longitude: position.coords.longitude,
                    en_location_id: document.getElementById('en_location_id').selectedOptions[0].value,
                });
            }
            this._rpc({
                model: "hr.employee",
                method: "attendance_manual",
                args: [
                    [self.employee.id],
                    "hr_attendance.hr_attendance_action_my_attendances",
                ],
                context: ctx,
            }).then(function (result) {
                var button = $('.o_hr_attendance_sign_in_out_icon')
                if (button.hasClass('oe-processing')){
                    button.removeClass('oe-processing')
                }
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    self.showPositionError(result.warning);
                }
            }).guardedCatch((reason) => {
                var button = $('.o_hr_attendance_sign_in_out_icon')
                if (button.hasClass('oe-processing')){
                    button.removeClass('oe-processing')
                }
            });
        },
    });
});
