odoo.define("hr_attendance_geolocation.attendances_geolocation", function (require) {
    "use strict";

    import { MyAttendances } from 'hr_attendance.my_attendances';
    import { KioskConfirm } from 'hr_attendance.kiosk_confirm';
    const session = require("web.session");

    import { core } from 'web.core';
    import { Dialog } from 'web.Dialog';
    var _t = core._t;

    MyAttendances.include({
        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.location = (null, null);
            this.errorCode = null;
        },
        update_attendance: function () {
            var button = $('.o_hr_attendance_sign_in_out_icon')
            if (button.hasClass('oe-processing')){
                return
            }
            $('.o_hr_attendance_sign_in_out_icon').addClass('oe-processing')
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 60000,
                maximumAge: 0,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    self._manual_attendance.bind(self),
                    self._getPositionError.bind(self),
                    options
                );
            }
        },

        _manual_attendance: function (position) {
            var self = this;
            const ctx = Object.assign(session.user_context, {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            });
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
            });
        },
        _getPositionError: function (error) {
            var message = "ERROR(" + error.code + "): " + error.message
            console.warn(message);
            this.showPositionError(message);
            // const position = {
            //     coords: {
            //         latitude: 0.0,
            //         longitude: 0.0,
            //     },
            // };
            // this._manual_attendance(position);
        },
        showPositionError: function (message) {
            var dialog = new Dialog(null, {
                title: 'Có lỗi xảy khi chấm công',
                size: 'medium',
                $content: `<p>${_.str.escapeHTML(message) || ''}</p>`,
                buttons: [{text: _t("Ok"), close: true}]
            }).open();
            dialog.on('closed', this, function () {
                var button = $('.o_hr_attendance_sign_in_out_icon')
                if (button.hasClass('oe-processing')){
                    button.removeClass('oe-processing')
                }
            });
            return dialog;
        }
    });

    KioskConfirm.include({
        events: _.extend(KioskConfirm.prototype.events, {
            "click .o_hr_attendance_sign_in_out_icon": _.debounce(
                function () {
                    this.update_attendance();
                },
                2000,
                true
            ),
            "click .o_hr_attendance_pin_pad_button_ok": _.debounce(
                function () {
                    this.pin_pad = true;
                    this.update_attendance();

                },
                2000,
                true
            ),
        }),
        // eslint-disable-next-line no-unused-vars
        init: function (parent, action) {
            this._super.apply(this, arguments);
            this.pin_pad = false;
        },
        update_attendance: function () {
            var self = this;
            var options = {
                enableHighAccuracy: true,
                timeout: 60000,
                maximumAge: 0,
            };
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    self._manual_attendance.bind(self),
                    self._getPositionError.bind(self),
                    options
                );
            }
        },
        _manual_attendance: function (position) {
            var self = this;
            var pinBoxVal = null;
            if (this.pin_pad) {
                this.$(".o_hr_attendance_pin_pad_button_ok").attr(
                    "disabled",
                    "disabled"
                );
                pinBoxVal = this.$(".o_hr_attendance_PINbox").val();
            }
            const ctx = Object.assign(session.user_context, {
                latitude: position.coords.latitude,
                longitude: position.coords.longitude,
            });
            this._rpc({
                model: "hr.employee",
                method: "attendance_manual",
                args: [[this.employee_id], this.next_action, pinBoxVal],
                context: ctx,
            }).then(function (result) {
                if (result.action) {
                    self.do_action(result.action);
                } else if (result.warning) {
                    if (self.pin_pad) {
                        self.$(".o_hr_attendance_PINbox").val("");
                        setTimeout(function () {
                            self.$(".o_hr_attendance_pin_pad_button_ok").removeAttr("disabled");
                        }, 500);
                    }
                    self.pin_pad = false;
                    self.showPositionError(result.warning);
                }
            });
        },
        _getPositionError: function (error) {
            var message = "ERROR(" + error.code + "): " + error.message
            console.warn(message);
            this.showPositionError(message);
            // const position = {
            //     coords: {
            //         latitude: 0.0,
            //         longitude: 0.0,
            //     },
            // };
            // this._manual_attendance(position);
        },
        showPositionError: function (message) {
            var dialog = new Dialog(null, {
                title: 'Có lỗi xảy khi chấm công',
                size: 'medium',
                $content: `<p>${_.str.escapeHTML(message) || ''}</p>`,
                buttons: [{text: _t("Ok"), close: true}]
            }).open();
            return dialog;
        }
    });
});
