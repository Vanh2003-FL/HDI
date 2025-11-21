odoo.define('ngsd_base.geolocation', function (require) {
"use strict";

import { FormController } from 'web.FormController';
import { Dialog } from 'web.Dialog';

FormController.include({

    _loactionCallback: function (position) {
        var self = this;
        this.renderer._rpc({
            model: self.modelName,
            method: self.location_calback,
            args: [self.renderer.state.data.id || self.renderer.state.data, position.coords.latitude, position.coords.longitude],
        }).then (function (datas) {
            self.trigger_up('reload');
            if (!datas) return;
            var type = datas[0];
            var data = datas[1];
            if (type === 'show_effect') {
                self.trigger_up('show_effect', {
                    type: 'rainbow_man',
                    fadeout: 'slow',
                    message: data,
                    messageIsHtml: true,
                });
            } else if (type === 'action') {
                self.do_action(data)
            }
        });
    },

    _onButtonClicked: function (ev) {
        var self = this;
        var attrs = ev.data.attrs;
        if (attrs.type === 'location' && attrs.confirm) {
            if (!self.renderer.state.data.id) {
                return new Promise(function (resolve, reject) {
                    Dialog.confirm(this, "Vui lòng Lưu bản ghi trước!", {
                        buttons: [{
                                text: 'Xác nhận',
                                close: true,
                                click: reject,
                            }
                        ],
                    });
                });
            }
            new Promise(function (resolve, reject) {
                Dialog.confirm(self, attrs.confirm, {
                    confirm_callback: function () {
                                var options = {
                                    enableHighAccuracy: true,
                                    timeout: 60000,
                                    maximumAge: 0
                                };
                                self.location_calback = attrs.name
                                if (navigator.geolocation) {
                                    navigator.geolocation.getCurrentPosition(
                                        self._loactionCallback.bind(self),
                                        function () {
                                            alert('Vui lòng cấp quyền truy cập vị trí!');
                                        },
                                        options
                                    );
                                } else {
                                    alert('Thiết bị không hỗ trợ lấy vị trí!');
                                }
                    },
                }).on("closed", null, resolve);
            }).then(function () {
            self._enableButtons();
                if (attrs.close) {
                    self.trigger_up('close_dialog');
                }
            }).guardedCatch(this._enableButtons.bind(this));
        }
        else if (attrs.type === 'location'){
            if (!self.renderer.state.data.id) {
                return new Promise(function (resolve, reject) {
                    Dialog.confirm(this, "Vui lòng Lưu bản ghi trước!", {
                        buttons: [{
                                text: 'Xác nhận',
                                close: true,
                                click: reject,
                            }
                        ],
                    });
                });
            }
            var options = {
                enableHighAccuracy: true,
                timeout: 60000,
                maximumAge: 0
            };
            self.location_calback = attrs.name
            if (navigator.geolocation) {
                navigator.geolocation.getCurrentPosition(
                    self._loactionCallback.bind(self),
                    function () {
                        alert('Vui lòng cấp quyền truy cập vị trí!');
                    },
                    options
                );
            } else {
                alert('Thiết bị không hỗ trợ lấy vị trí!');
            }
        }else {
            this._super.apply(this, arguments);
        }
    },

});

});
