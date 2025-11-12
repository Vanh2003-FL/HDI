from odoo import api, fields, models
from odoo.exceptions import ValidationError, UserError


class ProjectDecision(models.Model):
    _inherit = "project.decision"

    bmm_os = fields.Float(string="BMM OS")
    expense_os = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency")
    bmm_stage_ids = fields.One2many("project.decision.bmm.stage", "project_decision_id", string="BMM theo giai đoạn")
    bmm_ids = fields.One2many("project.decision.bmm", "project_decision_id", string="BMM theo tháng")

    @api.onchange('project_id')
    def _onchange_project_bmm_expense(self):
        if not self.project_id: return
        bmm_stage_ids, bmm_ids = [], []
        for line in self.project_id.en_bmm_stage_ids:
            vals = (0, 0,
                    {'bmm_stage_id': line.bmm_stage_id.id,
                     'number_of_week': line.number_of_week,
                     'date_start': line.date_start,
                     'date_end': line.date_end,
                     'bmm': line.bmm,
                     'expense': line.expense,
                     'company_currency': line.company_currency.id}
                    )
            bmm_stage_ids.append(vals)
        for line in self.project_id.en_bmm_ids:
            vals = (0, 0,
                    {'date': line.date,
                     'month_txt': line.month_txt,
                     'bmm': line.bmm,
                     'expense': line.expense,
                     'company_currency': line.company_currency.id}
                    )
            bmm_ids.append(vals)
        self.bmm_stage_ids = bmm_stage_ids
        self.bmm_ids = bmm_ids

    def check_wbs_resource_planning(self):
        project_id = self.project_id.id
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



    def button_duplicate_project_decision(self):
        if not self.technical_field_27768:
            raise ValidationError('QĐ TL Dự án này không được phép Tạo phiên bản mới')

        if self.check_need_vice_ceo() or self.check_wbs_resource_planning():
                # self.env.user.notify_warning(
                #     message='Tồn tại KHNL/WBS đang ở trong trạng thái nháp; yêu cầu Xóa/Hủy các bản này trước khi tạo QĐTLDA mới',
                #     title='Cảnh báo',
                #     sticky=True
                # )
                # return
                raise UserError("Tồn tại KHNL/WBS đang ở trong trạng thái nháp; "
                                "yêu cầu Xóa/Hủy các bản này trước khi tạo QĐTLDA mới")
        self.ensure_one()
        if not self.project_id:
            raise ValidationError('Bản ghi này không có project cha.')
        fields_to_copy = [
            'is_internal',
            'en_level_project',
            'en_area_id',
            'en_block_id',
            'en_department_id',
            'en_project_type_id',
            'en_list_project_id',
            'en_project_model_id',
            'date_start',
            'date_end',
            'date',
            'en_real_start_date',
            'en_real_end_date',
            'en_warranty_time',
            'en_project_implementation_id',
            'en_project_manager_id',
            'en_project_block_id',
            'user_id',
            'en_project_vicepm_ids',
            'en_project_qa_id',
            'en_project_sale_id',
            'en_project_accountant_id',
            'en_contracting_entity',
            'en_customer_type_id',
            'name_partner',
            'en_contract_type_id',
            'en_contract_number',
            'en_branch_id',
            'currency_id',
            'customer_resource_calendar_id',
            'en_no_contract',
            'en_md_resource',
            'technical_field_28187',
            'en_resource_id',
            'mm_rate',
            'mm_conversion',
            'en_current_version',
            'en_link_system',
            'show_import_button',
            'en_project_goal',
            'en_business_scope',
            'en_implementation_scope',
            'en_other_scope',
            'bmm_os',
            'expense_os',
        ]
        vals = {'project_id': self.project_id.id}
        project = self.project_id
        for field in fields_to_copy:
            if hasattr(project, field):
                val = getattr(project, field)
                field_obj = self.env['project.decision']._fields.get(field)
                if field_obj is not None:
                    if field_obj.type == 'many2one':
                        vals[field] = val.id if val else False
                    elif field_obj.type == 'many2many':
                        vals[field] = [(6, 0, val.ids)] if val else [(6, 0, [])]
                    else:
                        vals[field] = val
        vals['version_type'] = 'plan'
        vals['company_currency'] = project.company_currency.id
        vals['state'] = 'draft'
        vals['en_bmm'] = round(sum(project.en_bmm_ids.mapped("bmm")), 3) + project.bmm_os
        # BMM
        bmm_stage_ids, bmm_ids = [], []
        for line in project.en_bmm_stage_ids:
            val = (0, 0,
                   {'bmm_stage_id': line.bmm_stage_id.id,
                    'number_of_week': line.number_of_week,
                    'date_start': line.date_start,
                    'date_end': line.date_end,
                    'bmm': line.bmm,
                    'expense': line.expense,
                    'company_currency': line.company_currency.id}
                   )
            bmm_stage_ids.append(val)
        for line in project.en_bmm_ids:
            val = (0, 0,
                   {'date': line.date,
                    'month_txt': line.month_txt,
                    'bmm': line.bmm,
                    'expense': line.expense,
                    'company_currency': line.company_currency.id}
                   )
            bmm_ids.append(val)
        vals['bmm_stage_ids'] = bmm_stage_ids
        vals['bmm_ids'] = bmm_ids
        # Tạo mới quyết định
        new_decision = self.env['project.decision'].create(vals)
        # snapshot
        new_decision._create_resource_snapshots()
        new_decision._create_processing_rate_snapshots()
        new_decision._create_response_rate_snapshots()
        return self.open_create_project_decision_popup(new_decision)


class ProjectDecisionStage(models.Model):
    _name = "project.decision.bmm.stage"
    _description = "BMM theo giai đoan quyết định thành lập dự án"

    project_decision_id = fields.Many2one("project.decision", string="QĐ thành lập Dự án")
    bmm_stage_id = fields.Many2one("en.stage.type", string="Giai đoạn")
    number_of_week = fields.Integer(string="Số tuần")
    date_start = fields.Date(string="Ngày bắt đầu")
    date_end = fields.Date(string="Ngày kết thúc")
    bmm = fields.Float(string="BMM")
    expense = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency")


class ProjectDecisionBmm(models.Model):
    _name = "project.decision.bmm"
    _description = "BMM theo tháng quyết định thành lập dự án"

    project_decision_id = fields.Many2one("project.decision", string="QĐ thành lập Dự án")
    date = fields.Date(string='Ngày')
    month_txt = fields.Char(string='Tháng')
    bmm = fields.Float(string="BMM")
    expense = fields.Monetary(string="Chi phí", currency_field="company_currency")
    company_currency = fields.Many2one("res.currency", string="Currency")
