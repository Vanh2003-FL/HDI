odoo.define('ngsc_recruitment.copy_url_link', function (require) {
    "use strict";

    const KanbanRenderer = require('web.KanbanRenderer');
    const core = require('web.core');
    const _t = core._t;

    KanbanRenderer.include({
        async _renderView() {
            const res = await this._super(...arguments);
            this._attachCopyUrlLink();
            return res;
        },

        _attachCopyUrlLink() {
            const self = this;
            this.$el.find(".o_copy_url_link").off("click").on("click", function () {
                const link = this.dataset.link;

                if (!link) {
                    self.call('notification', 'notify', {
                        title: _t("Không có link tin tuyển dụng"),
                        message: _t("Không tìm thấy URL để copy."),
                        type: 'warning',
                    });
                    return;
                }

                if (navigator.clipboard && navigator.clipboard.writeText) {
                    navigator.clipboard.writeText(link)
                        .then(() => {
                            self.call('notification', 'notify', {
                                title: _t("Đã copy link tin tuyển dụng"),
                                message: link,
                                type: 'success',
                            });
                        })
                        .catch(err => {
                            self.call('notification', 'notify', {
                                title: _t("Lỗi khi copy link tin tuyển dụng"),
                                message: err.toString(),
                                type: 'danger',
                            });
                        });
                } else {
                    // Fallback: dùng execCommand
                    const textarea = document.createElement("textarea");
                    textarea.value = link;
                    textarea.setAttribute("readonly", "");
                    textarea.style.position = "absolute";
                    textarea.style.left = "-9999px";
                    document.body.appendChild(textarea);
                    textarea.select();
                    try {
                        const successful = document.execCommand("copy");
                        if (successful) {
                            self.call('notification', 'notify', {
                                title: _t("Đã copy link tin tuyển dụng"),
                                message: link,
                                type: 'success',
                            });
                        } else {
                            throw new Error("execCommand thất bại");
                        }
                    } catch (err) {
                        self.call('notification', 'notify', {
                            title: _t("Lỗi khi copy link tin tuyển dụng"),
                            message: err.toString(),
                            type: 'danger',
                        });
                    }
                    document.body.removeChild(textarea);
                }
            });
        },
    });
});
