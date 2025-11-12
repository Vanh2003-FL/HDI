import json
import ast
from lxml import etree
from lxml import html
from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError, AccessError

readonly_fields = [
"name", "is_internal", "en_level_project", "en_area_id", "en_block_id", "en_department_id", "en_project_type_id",
"en_list_project_id", "en_project_model_id", "date_start", "date", "en_warranty_time", "en_project_implementation_id",
"en_project_block_id", "en_project_manager_id", "user_id", "en_project_vicepm_ids", "en_project_qa_id",
"en_project_sale_id", "en_project_accountant_id", "en_contracting_entity", "en_customer_type_id", "partner_id",
"en_contract_type_id", "en_contract_number", "en_branch_id", "currency_id", "customer_resource_calendar_id",
"en_no_contract", "mm_rate", "en_link_system", "show_import_button"]


class ProjectProject(models.Model):
    _inherit = 'project.project'

    show_create_resource_plan = fields.Boolean(compute='_compute_show_create_resource_plan', store=False)

    version_link_resource_planning = fields.Many2one(string='Phiên bản WBS hiện tại', comodel_name='en.wbs', compute_sudo=True,
                                         compute='_compute_version_link_resource_planning', store=True)

    @api.depends('en_wbs_ids', 'en_wbs_ids.state')
    def _compute_version_link_resource_planning(self):
        for rec in self:
            version_link_resource_planning = self.env['en.wbs']
            if rec.en_wbs_ids.filtered(lambda x: x.state == 'waiting_create_resource_plan'):
                version_link_resource_planning = rec.en_wbs_ids.filtered(lambda x: x.state == 'waiting_create_resource_plan')[-1]
            elif rec.en_wbs_ids.filtered(lambda x: x.state == 'approved'):
                version_link_resource_planning = rec.en_wbs_ids.filtered(lambda x: x.state == 'approved')[-1]
            rec.version_link_resource_planning = version_link_resource_planning

    @api.model
    def get_project_stage_ids(self, id, project_model):
        project_id = id
        if project_model == 'en.resource.detail':
            resource_plan = self.env['en.resource.planning'].search([
                ('id', '=', id),
            ], order='id desc', limit=1)
            if resource_plan and resource_plan.state not in ('refused', 'expire'):
                project_id = resource_plan.project_id.id
        wbs = self.env['en.wbs'].search(
            [('project_id', '=', project_id),
             ('state', 'not in', ('refused', 'expire', 'draft')),
             ],
            order='id desc',
            limit=1
        )
        project_stage_ids = wbs.project_stage_ids
        if project_stage_ids:
            return project_stage_ids.mapped(lambda s: {
                'id': s.id,
                'name': s.name,
                'stage_code': s.stage_code
            })
        return []

    @api.depends('en_wbs_ids.state', 'en_resource_ids')
    def _compute_show_create_resource_plan(self):
        for record in self:
            if not record.sudo().en_wbs_ids:
                record.show_create_resource_plan = False
            else:
                if record.sudo().en_wbs_ids.filtered(lambda x: x.state not in ['refused', 'expire']):
                    record.show_create_resource_plan = True
                else:
                    record.show_create_resource_plan = False

    def check_wbs_resource_planning(self):
        project_id = self.id
        en_wbs = self.env['en.wbs'].search([
            ('project_id', '=', project_id),
            ('state', '=', 'draft')
        ])

        en_resource_planning = self.env['en.resource.planning'].search([
            ('project_id', '=', project_id),
            ('state', '=', 'draft')
        ])
        if en_wbs or en_resource_planning:
            return True

    def button_create_project_decision(self):
        if self.check_wbs_resource_planning():
            raise UserError("Tồn tại KHNL/WBS đang ở trong trạng thái nháp; "
                            "yêu cầu Xóa/Hủy các bản này trước khi tạo QĐTLDA mới")
        action = self.open_form_or_tree_view('ngsc_project.project_decision_act', False, False, {'default_project_id': self.id, 'default_user_id': self.user_id.id},
                                             'Tạo QĐ TL Dự án')
        action['views'] = [(False, 'form')]
        action['context'] = {'create': 0, 'default_project_id': self.id, 'default_user_id': self.user_id.id, 'default_en_bmm': self.en_bmm}
        return action

    def import_project_decision(self):
        return

    en_level_project = fields.Many2one('en.project.level', 'Cấp độ dự án')
    en_warranty_time = fields.Char('Thời gian bảo hành')
    en_no_contract = fields.Boolean(string='Chưa có hợp đồng')
    en_contract_start_date = fields.Date(string="Ngày bắt đầu dự kiến theo hợp đồng")
    en_contract_end_date = fields.Date(string="Ngày kết thúc dự kiến theo hợp đồng")
    en_contracting_entity = fields.Many2one('en.project.legal.entity', string='Pháp nhân ký HĐ')

    en_project_goal = fields.Text(string="Mục tiêu dự án")
    en_business_scope = fields.Text(string="Phạm vi nghiệp vụ")
    en_implementation_scope = fields.Text(string="Phạm vi triển khai")
    en_other_scope = fields.Text(string="Phạm vi khác")

    project_decision_ids = fields.One2many(string='Phiên bản', comodel_name='project.decision', inverse_name='project_id')

    show_create_project_decision = fields.Boolean(compute='_compute_project_decision', store=False)
    show_create_wbs = fields.Boolean(compute='_compute_is_valid_project_decision', store=False)
    is_readonly_fields = fields.Boolean(string="Không được phép sửa thông tin dự án",
                                           compute="_compute_is_readonly_fields", default=False)

    @api.constrains('en_no_contract', 'is_internal', 'en_contract_start_date', 'en_contract_end_date')
    def _check_contract_dates(self):
        """Vô hiệu hóa constraint gốc để không chặn khi chỉ xem."""
        return
    @api.model
    def create(self, vals):
        record = super().create(vals)
        if not self.env.context.get('bypass_contract_check'):
            record._validate_contract_dates()
        return record

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('bypass_contract_check'):
            self._validate_contract_dates()
        return res
    def _validate_contract_dates(self):
        for record in self:
            if not record.en_no_contract:
                if not record.en_contract_start_date or not record.en_contract_end_date:
                    raise ValidationError(
                        "Vui lòng nhập ngày bắt đầu và ngày kết thúc dự kiến theo hợp đồng.")

                if record.en_contract_end_date < record.en_contract_start_date:
                    raise ValidationError(
                        "Ngày kết thúc dự kiến theo hợp đồng phải sau ngày bắt đầu.")

    @api.depends("project_decision_ids")
    def _compute_project_decision(self):
        self.show_create_project_decision = True
        for record in self:
            # Nếu trạng thái là draft(dự kiến) ẩn tạo QĐTLDA
            if record.en_state == 'draft':
                record.show_create_project_decision = True
                continue
            if not record.project_decision_ids:
                self.show_create_project_decision = False
            else:
                all_refused = all(project_decision.state == 'refused' for project_decision in record.project_decision_ids)
                if all_refused:
                    self.show_create_project_decision = False

    @api.depends("en_wbs_ids")
    def _compute_is_valid_project_decision(self):
        for record in self:
            if not record.sudo().project_decision_ids or record.sudo().en_wbs_ids:
                record.show_create_wbs = True
            else:
                all_approved = any(project_decision.state == 'approved' for project_decision in record.sudo().project_decision_ids)
                if all_approved:
                    record.show_create_wbs = False
                else:
                    record.show_create_wbs = True

    @api.depends('project_decision_ids.en_bmm', 'project_decision_ids.state')
    def _compute_en_bmm(self):
        for rec in self:
            approved_decisions = rec.project_decision_ids.filtered(lambda d: d.state == 'approved')
            rec.en_bmm = approved_decisions[0].en_bmm if approved_decisions else 0.0

    @api.constrains("stage_id")
    def _constrains_project_state(self):
        for rec in self:
            if rec.stage_id.en_state != "doing":
                continue
            if not rec.project_decision_ids.filtered(lambda x: x.state == "approved"):
                raise UserError("Quyết định thành lập dự án chưa được tạo, vui lòng tạo trước khi chuyển trạng thái Dự án.")

    @api.depends_context('uid')
    @api.depends('user_id', 'en_project_vicepm_ids',
        'en_project_implementation_id', 'en_project_block_id',
        'en_project_manager_id', 'en_project_qa_id')
    def _compute_is_readonly_fields(self):
        uid = self._uid
        for rec in self:
            if self.env.user.has_group("base.group_system"):
                rec.is_readonly_fields = False
                continue
            access_ids = [rec.en_project_implementation_id.id, rec.en_project_block_id.id, rec.en_project_manager_id.id, rec.en_project_qa_id.id]
            rec.is_readonly_fields = ((uid == rec.user_id.id or uid in rec.en_project_vicepm_ids.ids) and uid not in access_ids)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type != 'form':
            return res
        doc = etree.XML(res['arch'])
        readonly_condition = ["is_readonly_fields", "=", True]
        for field_name in readonly_fields:
            for node in doc.xpath(f"//field[@name='{field_name}']"):
                modifiers = json.loads(node.get('modifiers', '{}'))
                old_readonly = modifiers.get('readonly')
                if 'readonly' in modifiers:
                    if isinstance(old_readonly, str):
                        try:
                            old_readonly = ast.literal_eval(old_readonly)
                        except Exception as e:
                            print("Exception", e)
                            old_readonly = []
                    modifiers['readonly'] = ['|', readonly_condition] + old_readonly
                else:
                    modifiers['readonly'] = [readonly_condition]
                node.set('modifiers', json.dumps(modifiers))
        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def button_en_doing(self):
        for rec in self:
            if rec.en_state == 'wait_for_execution':
                rec.stage_id = self.env['project.project.stage'].search([('en_state', '=', 'doing')], limit=1)

    def button_en_finish(self):
        for rec in self:
            if rec.en_state != 'doing':
                continue
            if not rec.en_real_end_date:
                rec.en_real_end_date = fields.Datetime.now()
            rec.stage_id = self.env['project.project.stage'].search([('en_state', '=', 'finish')], limit=1)

    def button_en_complete(self):
        for rec in self:
            if rec.en_state == 'finish':
                # rec.en_real_end_date = fields.Datetime.now()
                rec.stage_id = self.env['project.project.stage'].search([('en_state', '=', 'complete')], limit=1)

    # Update logic mới mm_rate
    @api.depends('task_ids.timesheet_ids.en_total_amount')
    def _compute_technical_field_28187(self):
        analytic_line_obj = self.env['account.analytic.line'].sudo()
        technical_obj = self.env["en.technical.model"].sudo()
        for rec in self:
            analytic_lines = analytic_line_obj.search([('project_id', '=', rec.id), ('en_state', '=', 'approved')])
            range_date = analytic_lines.mapped("date")
            if not range_date:
                rec.technical_field_28187 = 0
                continue
            date_from = min(range_date)
            date_to = max(range_date)
            net_working_day_months = technical_obj.count_net_working_days_by_months(date_from, date_to)
            group_by_months = analytic_line_obj.read_group(
                domain=[('project_id', '=', rec.id), ('en_state', '=', 'approved')],
                fields=['en_total_amount', 'date'],
                groupby=['date:month'], lazy=False)
            technical_field_28187 = sum(rec.en_history_resource_ids.mapped('actual'))
            for data_month in group_by_months:
                month = fields.Date.from_string(data_month.get('__range', {}).get('date', {}).get('from'))
                total_amount = data_month['en_total_amount'] or 0.0
                working_days = net_working_day_months.get(str(month), 22)
                technical_field_28187 += total_amount / 8 / working_days
            rec.technical_field_28187 = str(round(technical_field_28187, 2))


    def export_data(self, fields_to_export, *args, **kwargs):
        """
        Override export_data để loại bỏ HTML khi export các trường text/html
        """
        res = super(ProjectProject, self).export_data(fields_to_export, *args, **kwargs)

        def html_to_text(value):
            """Chuyển HTML sang text, an toàn với None hoặc lỗi parser"""
            if not value or value in ['False', False, None]:
                return ''
            try:
                # Trường hợp có thẻ HTML
                return html.fromstring(value).text_content().strip()
            except Exception:
                # Nếu không phải HTML thì giữ nguyên
                return str(value).strip()

        # Danh sách các trường cần làm sạch HTML
        html_fields = {
            'en_project_goal',
            'en_business_scope',
            'en_implementation_scope',
            'en_other_scope',
        }

        # Chỉ xử lý nếu có dữ liệu
        if res and res.get('datas'):
            for row in res['datas']:
                for i, field_name in enumerate(fields_to_export):
                    if field_name in html_fields and i < len(row):
                        row[i] = html_to_text(row[i])

        return res