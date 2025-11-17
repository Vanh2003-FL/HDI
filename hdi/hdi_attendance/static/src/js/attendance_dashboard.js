odoo.define('hdi_attendance.dashboard', function (require) {
    'use strict';

    var AbstractAction = require('web.AbstractAction');
    var core = require('web.core');
    var rpc = require('web.rpc');

    var QWeb = core.qweb;
    var _t = core._t;

    var AttendanceDashboard = AbstractAction.extend({
        template: 'hdi_attendance.Dashboard',
        
        events: {
            'click .hdi_checkin_btn': '_onCheckinClick',
            'click .hdi_checkout_btn': '_onCheckoutClick',
            'click .hdi_get_location_btn': '_onGetLocationClick',
        },

        init: function(parent, context) {
            this._super(parent, context);
            this.dashboardData = {};
        },

        start: function() {
            var self = this;
            return this._super().then(function() {
                return self._loadDashboardData();
            });
        },

        _loadDashboardData: function() {
            var self = this;
            return rpc.query({
                model: 'hr.employee',
                method: 'get_attendance_dashboard_data',
                args: [this.getSession().uid],
            }).then(function(data) {
                self.dashboardData = data;
                self._renderDashboard();
            });
        },

        _renderDashboard: function() {
            var self = this;
            this.$('.hdi_dashboard_content').html(QWeb.render('hdi_attendance.DashboardContent', {
                widget: self,
                data: self.dashboardData,
            }));
        },

        _onCheckinClick: function(ev) {
            ev.preventDefault();
            this._openCheckinWizard('check_in');
        },

        _onCheckoutClick: function(ev) {
            ev.preventDefault();
            this._openCheckinWizard('check_out');
        },

        _openCheckinWizard: function(mode) {
            var self = this;
            return this.do_action({
                name: _t('Chấm công'),
                type: 'ir.actions.act_window',
                res_model: 'attendance.checkin.wizard',
                view_mode: 'form',
                view_type: 'form',
                views: [[false, 'form']],
                target: 'new',
                context: {
                    default_attendance_mode: mode,
                },
            });
        },

        _onGetLocationClick: function(ev) {
            var self = this;
            ev.preventDefault();
            
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    function(position) {
                        var lat = position.coords.latitude;
                        var lng = position.coords.longitude;
                        self._updateLocationDisplay(lat, lng);
                    },
                    function(error) {
                        self._showLocationError(error);
                    }
                );
            } else {
                self.displayNotification({
                    type: 'warning',
                    title: _t('GPS không hỗ trợ'),
                    message: _t('Trình duyệt của bạn không hỗ trợ GPS'),
                });
            }
        },

        _updateLocationDisplay: function(lat, lng) {
            this.$('.hdi_current_location').text(
                _t('Vị trí hiện tại: ') + lat.toFixed(6) + ', ' + lng.toFixed(6)
            );
        },

        _showLocationError: function(error) {
            var message;
            switch(error.code) {
                case error.PERMISSION_DENIED:
                    message = _t("Quyền truy cập vị trí bị từ chối");
                    break;
                case error.POSITION_UNAVAILABLE:
                    message = _t("Thông tin vị trí không khả dụng");
                    break;
                case error.TIMEOUT:
                    message = _t("Yêu cầu lấy vị trí bị timeout");
                    break;
                default:
                    message = _t("Lỗi không xác định khi lấy vị trí");
                    break;
            }
            
            this.displayNotification({
                type: 'warning',
                title: _t('Lỗi GPS'),
                message: message,
            });
        },

        destroy: function() {
            this._super.apply(this, arguments);
        }
    });

    core.action_registry.add('hdi_attendance_dashboard', AttendanceDashboard);
    
    return AttendanceDashboard;
});