/** @odoo-module **/

import ListRenderer from 'web.ListRenderer';

const columnTooltips = {
    quality_evaluation_display: "Chất lượng công việc:\n" +
        "1 - Trung bình: Hoàn thành công việc dưới mức yêu cầu, thường xuyên mắc lỗi nghiêm trọng.\n" +
        "2 - Khá: Hoàn thành công việc chưa đáp ứng đầy đủ yêu cầu, còn xảy ra lỗi cần sửa chữa.\n" +
        "3 - Tốt (Đạt chuẩn): Luôn hoàn thành công việc đúng hạn, đạt yêu cầu về chất lượng và không cần giám sát chặt chẽ.\n" +
        "4 - Xuất sắc: Hoàn thành công việc vượt mức mong đợi, chất lượng cao, có thể hỗ trợ đồng nghiệp.\n" +
        "5 - Rất xuất sắc: Luôn hoàn thành xuất sắc mọi nhiệm vụ, góp phần cải tiến và nâng cao chất lượng công việc cho công ty.\n",
    attitude_evaluation: "Thái độ công việc:\n" +
        "1 - Trung bình: Thường xuyên trì hoãn, thiếu trách nhiệm, có thái độ tiêu cực, vi phạm kỉ luật công ty thường xuyên.\n" +
        "2 - Khá: Chưa chủ động trong công việc, đôi khi còn thiếu hợp tác, vi phạm kỷ luật công ty.\n" +
        "3 - Tốt (Đạt chuẩn): Có trách nhiệm, nghiêm túc và phối hợp tốt với đồng nghiệp, tuân thủ quy định & văn hóa doanh nghiệp.\n" +
        "4 - Xuất sắc: Luôn chủ động, nhiệt tình, có tinh thần xây dựng và cầu tiến.\n" +
        "5 - Rất Xuất sắc: Luôn thể hiện sự tận tâm, là tấm gương về thái độ làm việc chuyên nghiệp, truyền cảm hứng cho mọi người.\n",
    evaluation: "Chất lượng công việc:\n" +
        "1 - Trung bình: Hoàn thành công việc dưới mức yêu cầu, thường xuyên mắc lỗi nghiêm trọng.\n" +
        "2 - Khá: Hoàn thành công việc chưa đáp ứng đầy đủ yêu cầu, còn xảy ra lỗi cần sửa chữa.\n" +
        "3 - Tốt (Đạt chuẩn): Luôn hoàn thành công việc đúng hạn, đạt yêu cầu về chất lượng và không cần giám sát chặt chẽ.\n" +
        "4 - Xuất sắc: Hoàn thành công việc vượt mức mong đợi, chất lượng cao, có thể hỗ trợ đồng nghiệp.\n" +
        "5 - Rất xuất sắc: Luôn hoàn thành xuất sắc mọi nhiệm vụ, góp phần cải tiến và nâng cao chất lượng công việc cho công ty.\n",
};

const modelTooltips = ["ngsc.hr.performance.evaluation", "task.evaluation"]

ListRenderer.include({
    _renderHeaderCell(node) {
        const $th = this._super.apply(this, arguments);
        if (modelTooltips.includes(this.state.model)) {
            const help_field = columnTooltips[node.attrs.name];
            if (help_field) {
                const $icon = $('<i/>', {
                    class: 'fa fa-info-circle text-muted ms-1',
                    style: 'margin-right: 2px; color: blue !important;',
                    title: help_field,
                });
                $th.prepend($icon);
            }
        }
        return $th;
    },
});
