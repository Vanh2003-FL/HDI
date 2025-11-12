import base64
import html
import logging
from io import BytesIO

import xlsxwriter
from bs4 import BeautifulSoup

from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class NgscInnovation(models.Model):
    _name = 'ngsc.innovation.idea'
    _description = 'Ý tưởng sáng tạo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'idea_name'
    idea_name = fields.Char(string='Tên ý tưởng', required=True, tracking=True)
    sender_id = fields.Many2one('res.users', string='Người gửi',
                                default=lambda self: self.env.user, required=True)
    sender_email = fields.Char(
        string='Email',
        related='sender_id.work_email',
        readonly=True
    )
    sender_phone = fields.Char(
        string='SĐT',
        related='sender_id.mobile_phone',
        readonly=True
    )
    sender_block_id = fields.Many2one('en.name.block', string='Khối', required=True,
                                      related='sender_id.employee_id.en_block_id', tracking=True, readonly=True)
    sender_department_id = fields.Many2one('hr.department', string='Trung tâm', required=True,
                                           related='sender_id.department_id', tracking=True, readonly=True)
    sender_en_department_id = fields.Many2one('en.department', string='Phòng ban', tracking=True,
                                              related='sender_id.employee_id.en_department_id', readonly=True)
    send_type = fields.Selection([
        ('individual', 'Cá nhân'),
        ('team', 'Theo đội/nhóm')
    ], string='Hình thức gửi', required=True, default='individual', tracking=True)
    impact_type_ids = fields.Many2many(
        'ngsc.innovation.config',
        'ngsc_innovation_idea_impact_rel',
        'idea_id', 'impact_id',
        string='Phân loại theo tác động',
        tracking=True,
        domain="[('type', '=', 'impact'), ('status', '=', True)]",
        required=True
    )

    field_type_id = fields.Many2one(
        'ngsc.innovation.config',
        string='Phân loại theo lĩnh vực',
        required=True,
        tracking=True,
        domain="[('type', '=', 'field'), ('status', '=', True)]"
    )

    current_status_id = fields.Many2one(
        'ngsc.innovation.config',
        string='Tình trạng hiện tại',
        required=True,
        tracking=True,
        domain="[('type', '=', 'status'), ('status', '=', True)]"
    )
    other = fields.Text(string='Vui lòng ghi rõ', tracking=True)
    description = fields.Html(string='Mô tả sáng kiến', sanitize=False, tracking=True)
    state = fields.Selection([
        ('new', 'Mới'),
        ('submitted', 'Đã gửi duyệt'),
        ('approved', 'Đã duyệt vòng 1'),
        ('check_point', 'Đã đánh giá'),
        ('accepted', 'Được duyệt'),
        ('rejected', 'Chưa phù hợp')
    ], string='Trạng thái', required=True, default='new', tracking=True)
    submit_date = fields.Datetime(string='Ngày gửi', tracking=True)
    member_ids = fields.Many2many('hr.employee', string='Thông tin thành viên (nếu có)')
    is_editable = fields.Boolean(string='Có thể chỉnh sửa', compute='_compute_is_editable', store=False)
    is_submit_user = fields.Boolean(string='Is Submit User', compute='_compute_is_submit_user', store=False)
    reject_reason = fields.Text(string='Lý do từ chối', tracking=True, readonly=True)
    attachment_ids = fields.One2many(
        'ngsc.innovation.attachment',
        'idea_id',
        string='Tệp đính kèm',
    )

    version_id = fields.Many2one(
        'ngsc.innovation.version',
        string='Phiên bản áp dụng',
        tracking=True
    )

    scoring_ids = fields.One2many(
        'ngsc.innovation.scoring',
        'idea_id',
        string='Tổng hợp điểm theo tiêu chí',
        help='Danh sách điểm trung bình theo từng tiêu chí'
    )

    latest_scoring_ids = fields.One2many(
        'ngsc.innovation.summary',
        'idea_id',
        string='Điểm chấm mới nhất',
        compute='_compute_latest_scoring_ids',
        store=False
    )

    @api.depends('scoring_ids.detail_ids.is_latest')
    def _compute_latest_scoring_ids(self):
        for record in self:
            record.latest_scoring_ids = self.env[
                'ngsc.innovation.summary'].search([
                ('idea_id', '=', record.id),
                ('evaluator_id', '=', self.env.uid),
                ('is_latest', '=', True)
            ])

    scoring_status = fields.Selection([
        ('not_scored', 'Chưa chấm điểm'),
        ('scoring', 'Đang chấm điểm'),
        ('all_locked', 'Đã chốt điểm')
    ], string='Trạng thái chấm điểm',
        compute='_compute_scoring_status',
        store=True)

    required_evaluators = fields.Integer(
        string='Số người cần chấm',
        compute='_compute_evaluators_count'
    )
    locked_evaluators = fields.Integer(
        string='Số người đã chốt điểm',
        compute='_compute_evaluators_count'
    )

    scoring_status = fields.Selection([
        ('not_scored', 'Chưa chấm điểm'),
        ('scoring', 'Đang chấm điểm'),
        ('all_locked', 'Đã chốt điểm')
    ], string='Trạng thái chấm điểm',
        compute='_compute_scoring_status',
        store=True)

    has_locked_scores = fields.Boolean(
        string='Đã chốt điểm',
        compute='_compute_has_locked_scores',
        store=False
    )

    rejection_stage = fields.Selection([
        ('initial', 'Từ chối vòng 1'),
        ('after_evaluation', 'Từ chối sau đánh giá')
    ], string='Giai đoạn từ chối', tracking=True)

    member_names_csv = fields.Char(
        string="Thông tin thành viên (nếu có)",
        compute="_compute_member_names_csv",
        inverse="_inverse_member_names_csv",
        store=False
    )

    description_text = fields.Text(
        string="Mô tả sáng kiến",
        compute="_compute_description_text",
        inverse="_inverse_description_text",
        store=False
    )

    impact_names_csv = fields.Char(
        string="Phân loại tác động (CSV)",
        compute="_compute_impact_names_csv",
        inverse="_inverse_impact_names_csv",
        store=False
    )

    @api.depends("impact_type_ids")
    def _compute_impact_names_csv(self):
        for rec in self:
            rec.impact_names_csv = ",".join(rec.impact_type_ids.mapped("name"))

    def _inverse_impact_names_csv(self):
        for rec in self:
            if rec.impact_names_csv:
                names = [n.strip() for n in rec.impact_names_csv.split(",") if n.strip()]
                impacts = self.env["ngsc.innovation.config"].search([("name", "in", names),
                                                                     ("type", "=", "impact")])
                rec.impact_type_ids = [(6, 0, impacts.ids)]
            else:
                rec.impact_type_ids = [(5, 0, 0)]

    @api.depends("description")
    def _compute_description_text(self):
        for rec in self:
            if rec.description:
                # Parse HTML bằng BeautifulSoup
                soup = BeautifulSoup(rec.description, "html.parser")

                # Lấy text sạch, giữ xuống dòng khi có <br>
                for br in soup.find_all("br"):
                    br.replace_with("\n")

                clean = soup.get_text(separator="\n")

                # Decode entity (vd: &nbsp; -> space, &amp; -> &)
                clean = html.unescape(clean)

                rec.description_text = clean.strip()
            else:
                rec.description_text = False

    def _inverse_description_text(self):
        for rec in self:
            if rec.description_text:
                rec.description = "<p>%s</p>" % rec.description_text.replace("\n", "<br/>")
            else:
                rec.description = False

    @api.depends("member_ids")
    def _compute_member_names_csv(self):
        for rec in self:
            rec.member_names_csv = ",".join(rec.member_ids.mapped("name"))

    def _inverse_member_names_csv(self):
        for rec in self:
            if rec.member_names_csv:
                names = [n.strip() for n in rec.member_names_csv.split(",") if n.strip()]
                employees = self.env["hr.employee"].search([("name", "in", names)])
                rec.member_ids = [(6, 0, employees.ids)]
            else:
                rec.member_ids = [(5, 0, 0)]

    @api.depends('latest_scoring_ids.status', 'state')
    def _compute_evaluators_count(self):
        for record in self:
            evaluation_group = self.env.ref(
                'ngsc_innovation.group_evaluation_board')
            all_evaluators = evaluation_group.users
            record.required_evaluators = len(all_evaluators)

            if record.state == 'approved':
                locked_scores = self.env['ngsc.innovation.summary'].search([
                    ('idea_id', '=', record.id),
                    ('is_latest', '=', True),
                    ('status', '=', True)
                ])

                locked_evaluators = locked_scores.mapped('evaluator_id')
                record.locked_evaluators = len(set(locked_evaluators.ids))
            else:
                record.locked_evaluators = 0

    @api.depends('required_evaluators', 'locked_evaluators', 'state')
    def _compute_scoring_status(self):
        for record in self:
            if record.state != 'approved':
                record.scoring_status = 'not_scored'
            elif record.locked_evaluators == 0:
                record.scoring_status = 'not_scored'
            elif record.locked_evaluators < record.required_evaluators:
                record.scoring_status = 'scoring'
            else:
                record.scoring_status = 'all_locked'
                if record.state == 'approved':
                    record.state = 'check_point'

    @api.depends('latest_scoring_ids.status')
    def _compute_has_locked_scores(self):
        for record in self:
            current_user_scores = record.latest_scoring_ids.filtered(
                lambda r: r.evaluator_id.id == self.env.user.id and r.status
            )
            record.has_locked_scores = bool(current_user_scores)

    def action_open_ttnb_scoring_management(self):
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError(_('Bạn không có quyền chấm điểm thay.'))

        if self.state not in ['approved', 'check_point']:
            raise UserError(
                _('Chỉ có thể chấm điểm cho ý tưởng đã duyệt hoặc đã đánh giá.'))

        return {
            'name': _('Quản lý chấm điểm - Hội đồng đánh giá'),
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.evaluators.management.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_idea_id': self.id,
            }
        }

    def action_score_idea(self):
        self.ensure_one()

        if not self.env.user.has_group('ngsc_innovation.group_evaluation_board'):
            raise UserError(_('Bạn không có quyền chấm điểm.'))

        if self.state != 'approved':
            raise UserError(_('Chỉ được chấm điểm cho ý tưởng đã duyệt.'))

        if self.has_locked_scores:
            raise UserError(_('Bạn đã chốt điểm, không thể chấm lại.'))

        evaluation_period = self.env['ngsc.innovation.evaluation.period']
        if not evaluation_period.is_evaluation_period():
            raise UserError(_('Hiện không trong thời gian chấm điểm.'))

        return {
            'name': _('Chấm điểm'),
            'type': 'ir.actions.act_window',
            'res_model': 'ngsc.innovation.scoring.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_idea_id': self.id,
                'default_version_id': self.version_id.id,
                'parent_model': 'ngsc.innovation.idea',
                'parent_id': self.id,
            }
        }

    def action_lock_scores(self):
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_evaluation_board'):
            raise UserError(_('Bạn không có quyền chốt điểm.'))

        current_user_scores = self.latest_scoring_ids.filtered(
            lambda r: r.evaluator_id.id == self.env.user.id
        )

        if not current_user_scores:
            raise UserError(_('Bạn chưa chấm điểm, không thể chốt.'))

        if current_user_scores.filtered(lambda r: r.status):
            raise UserError(_('Bạn đã chốt điểm rồi.'))

        current_user_scores.write({'status': True})

        ScoringModel = self.env['ngsc.innovation.scoring'].sudo()
        for score_record in current_user_scores:
            if score_record.criteria_id.type == 'point':
                self._update_scoring_summary(score_record.criteria_id.id,
                                             ScoringModel)

        self.message_post(
            body=_('Người dùng %s đã chốt điểm.') % self.env.user.name
        )

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _('Đã chốt điểm thành công!'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def _update_scoring_summary(self, criteria_id, ScoringModel):
        criteria = self.env['ngsc.scoring.criteria'].browse(criteria_id)
        if criteria.type != 'point':
            return False

        locked_summaries = self.env['ngsc.innovation.summary'].search([
            ('idea_id', '=', self.id),
            ('version_id', '=', self.version_id.id),
            ('criteria_id', '=', criteria_id),
            ('is_latest', '=', True),
            ('status', '=', True)
        ])

        scoring = ScoringModel.search([
            ('idea_id', '=', self.id),
            ('version_id', '=', self.version_id.id),
            ('criteria_id', '=', criteria_id)
        ], limit=1)

        if locked_summaries:
            total_score = sum(locked_summaries.mapped('score'))
            number_of_evaluators = len(locked_summaries)
            average_score = total_score / number_of_evaluators if number_of_evaluators > 0 else 0

            values = {
                'total_score': total_score,
                'number_of_evaluators': number_of_evaluators,
                'average_score': average_score,
            }

            if scoring:
                scoring.write(values)
            else:
                values.update({
                    'idea_id': self.id,
                    'version_id': self.version_id.id,
                    'criteria_id': criteria_id,
                })
                ScoringModel.create(values)
        else:
            if scoring:
                scoring.write({
                    'total_score': 0,
                    'number_of_evaluators': 0,
                    'average_score': 0,
                })

        return True

    @api.model
    def create(self, vals):
        version = self.env['ngsc.innovation.version'].search(
            [('status', '=', True)], limit=1, order='start_date desc')
        if version:
            vals['version_id'] = version.id
        record = super(NgscInnovation, self).create(vals)
        return record

    def _send_status_email(self):
        template = self.env.ref('ngsc_innovation.email_template_innovation_status',
                                raise_if_not_found=False)
        for rec in self:
            # Lấy email thực sự để gửi
            recipient_email = rec.sender_id.email
            if recipient_email and rec.state in ('approved', 'rejected'):
                # Gọi send_mail, truyền email_to
                template.send_mail(
                    rec.id, force_send=True, raise_exception=False
                )

    def get_backend_url(self):
        self.ensure_one()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        return f"{base_url}/web#id={self.id}&model=ngsc.innovation.idea&view_type=form"

    @api.depends('sender_id')
    def _compute_is_submit_user(self):
        current_user_id = self.env.user.id
        for record in self:
            record.is_submit_user = record.sender_id and record.sender_id.id == current_user_id

    @api.depends('sender_id', 'state')
    def _compute_is_editable(self):
        user = self.env.user
        for rec in self:
            rec.is_editable = (
                    rec.state == 'new' and
                    (rec.sender_id and rec.sender_id.id == user.id)
            )

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        user = self.env.user
        group_ttnb = self.env.ref(
            'ngsc_innovation.group_internal_communication')
        group_hd = self.env.ref('ngsc_innovation.group_evaluation_board')

        if group_ttnb in user.groups_id:
            # Truyền thông nội bộ: thấy tất cả
            domain = []
        elif group_hd in user.groups_id:
            domain = []
        else:
            # Người khác: chỉ thấy record của mình
            domain = [('sender_id', '=', user.id)]

        args = domain + list(args)
        return super().search(args, offset=offset, limit=limit, order=order,
                              count=count)

    def _change_state(self, new_state, message):
        for rec in self:
            rec.write({'state': new_state})
            rec.message_post(body=message)

    def action_submit(self):
        if self.state != 'new':
            raise UserError(_('Chỉ ý tưởng trạng thái Mới mới được gửi duyệt.'))
        self.write({
            'state': 'submitted',
            'submit_date': fields.Datetime.now(),
        })
        self.message_post(body=_('Ý tưởng đã được gửi duyệt.'))

    def action_approve(self):
        if self.state != 'submitted':
            raise UserError(_('Chỉ ý tưởng trạng thái Đã gửi duyệt mới được duyệt.'))
        self._change_state('approved', _('Ý tưởng đã được duyệt.'))
        self._send_status_email()

    def action_reject(self, reason=None):
        if self.state != 'submitted':
            raise UserError(_('Chỉ ý tưởng trạng thái Đã gửi duyệt mới được từ chối.'))
        self.write({
            'state': 'rejected',
            'reject_reason': reason,
            'rejection_stage': 'initial',
        })
        self.message_post(body=_('Ý tưởng bị từ chối.' + (f" Lý do: {reason}" if reason else "")))
        self._send_status_email()

    def action_final_approve(self):
        if self.state != 'check_point':
            raise UserError(
                _('Chỉ ý tưởng trạng thái Đã đánh giá mới được duyệt cuối cùng.'))

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError(_('Bạn không có quyền duyệt ý tưởng.'))

        self._change_state('accepted', _('Ý tưởng đã được duyệt cuối cùng.'))
        self._send_status_email()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Thành công'),
                'message': _(
                    'Ý tưởng đã được duyệt thành công!'),
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    def action_final_reject(self):
        if self.state != 'check_point':
            raise UserError(
                _('Chỉ ý tưởng trạng thái Đã đánh giá mới được từ chối.'))

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError(_('Bạn không có quyền từ chối ý tưởng.'))

        self.write({
            'state': 'rejected',
            'rejection_stage': 'after_evaluation',
        })
        self.message_post(body=_('Ý tưởng đã bị từ chối sau đánh giá.'))
        self._send_status_email()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã xử lý'),
                'message': _('Ý tưởng đã bị từ chối.'),
                'type': 'warning',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                }
            }
        }

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        res = super(NgscInnovation, self).fields_view_get(view_id, view_type,
                                                          toolbar, submenu)
        context = self._context or {}
        if view_type == 'form' and context.get('form_view_ref'):
            try:
                view = self.env.ref(context['form_view_ref'])
                if view:
                    res['arch'] = view.arch
                    res['view_id'] = view.id
            except ValueError as e:
                _logger.warning(
                    f"Không tìm thấy view với XML ID: {context['form_view_ref']}")
        return res

    def action_export_evaluation_excel(self):
        self.ensure_one()

        if not self.env.user.has_group(
                'ngsc_innovation.group_internal_communication'):
            raise UserError(_('Bạn không có quyền xuất báo cáo này.'))

        if not self.version_id:
            raise UserError(
                _('Ý tưởng chưa được thiết lập quy tắc chấm điểm. Không thể xuất báo cáo.'))

        try:
            # Tạo file Excel
            output = BytesIO()
            workbook = xlsxwriter.Workbook(output, {'in_memory': True})
            worksheet = workbook.add_worksheet('Bảng điểm đánh giá')

            # --- Định nghĩa format ---
            header_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1
            })

            cell_text_format = workbook.add_format({
                'align': 'left',
                'valign': 'vcenter',
                'border': 1
            })

            cell_number_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'num_format': '0'
            })

            total_format = workbook.add_format({
                'bold': True,
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'num_format': '0'
            })

            # --- Lấy dữ liệu ---
            criteria_records = self.env['ngsc.scoring.criteria'].search([
                ('type', '=', 'point'),
                ('version_id', '=', self.version_id.id)
            ], order='name')

            if not criteria_records:
                raise UserError(
                    _('Không tìm thấy tiêu chí điểm nào cho phiên bản này.'))

            evaluation_group = self.env.ref(
                'ngsc_innovation.group_evaluation_board')
            evaluators = evaluation_group.users

            # --- Header ---
            row = 0
            col = 0
            worksheet.write(row, col, 'Người đánh giá', header_format)
            col += 1

            criteria_cols = {}
            for criteria in criteria_records:
                worksheet.write(row, col, criteria.name, header_format)
                criteria_cols[criteria.id] = col
                col += 1

            total_col = col
            worksheet.write(row, col, 'Tổng điểm', header_format)

            # --- Dữ liệu ---
            row += 1
            evaluator_totals = []

            for evaluator in evaluators:
                worksheet.write(row, 0, evaluator.name, cell_text_format)

                evaluator_total = 0
                has_scores = False

                for criteria in criteria_records:
                    score_record = self.env['ngsc.innovation.summary'].search([
                        ('idea_id', '=', self.id),
                        ('criteria_id', '=', criteria.id),
                        ('evaluator_id', '=', evaluator.id),
                        ('version_id', '=', self.version_id.id),
                        ('is_latest', '=', True),
                        ('status', '=', True)
                    ], limit=1)

                    if score_record:
                        score = score_record.score
                        worksheet.write(row, criteria_cols[criteria.id], score,
                                        cell_number_format)
                        evaluator_total += score
                        has_scores = True
                    else:
                        worksheet.write(row, criteria_cols[criteria.id], '-',
                                        cell_number_format)

                if has_scores:
                    worksheet.write(row, total_col, evaluator_total,
                                    cell_number_format)
                    evaluator_totals.append(evaluator_total)
                else:
                    worksheet.write(row, total_col, '-', cell_number_format)

                row += 1

            # --- Trung bình ---
            worksheet.write(row, 0, 'Trung bình', total_format)

            for criteria in criteria_records:
                criteria_scores = self.env['ngsc.innovation.summary'].search([
                    ('idea_id', '=', self.id),
                    ('criteria_id', '=', criteria.id),
                    ('version_id', '=', self.version_id.id),
                    ('is_latest', '=', True),
                    ('status', '=', True)
                ])
                if criteria_scores:
                    avg_score = sum(criteria_scores.mapped('score')) / len(
                        criteria_scores)
                    worksheet.write(row, criteria_cols[criteria.id], avg_score,
                                    total_format)
                else:
                    worksheet.write(row, criteria_cols[criteria.id], 0,
                                    total_format)

            if evaluator_totals:
                avg_total = sum(evaluator_totals) / len(evaluator_totals)
                worksheet.write(row, total_col, avg_total, total_format)
            else:
                worksheet.write(row, total_col, 0, total_format)

            # --- Căn chỉnh độ rộng cột ---
            worksheet.set_column(0, 0, 30)  # Người đánh giá
            for i in range(1, len(criteria_records) + 2):
                worksheet.set_column(i, i, 18)

            # Đóng workbook
            workbook.close()
            output.seek(0)

            # Tạo attachment
            filename = f"Bang_diem_danh_gia_{self.idea_name}_{fields.Date.today().strftime('%Y%m%d')}.xlsx"
            filename = "".join(c for c in filename if
                               c.isalnum() or c in (' ', '-', '_',
                                                    '.')).rstrip()

            attachment = self.env['ir.attachment'].create({
                'name': filename,
                'type': 'binary',
                'datas': base64.b64encode(output.read()),
                'res_model': self._name,
                'res_id': self.id,
                'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            })

            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Thành công'),
                    'message': _(
                        'File Excel đã được tạo và tải xuống thành công!'),
                    'type': 'success',
                    'sticky': False,
                    'next': {
                        'type': 'ir.actions.act_url',
                        'url': f'/web/content/{attachment.id}?download=true',
                        'target': 'new',
                    }
                }
            }

        except Exception as e:
            _logger.error(f"Lỗi khi xuất Excel: {str(e)}")
            raise UserError(_('Có lỗi xảy ra khi xuất file Excel: %s') % str(e))
