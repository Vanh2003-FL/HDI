from odoo import *


class ReportTemplate(models.Model):
    _name = 'en.report.template'
    _description = 'Mẫu in'

    REPORT_WRITEABLE_FIELDS = ['name', 'model_id', 'report_type', 'report_name', 'report_type', 'groups_id', 'template', 'template_name']

    def _report_get_values(self):
        values = {}
        values['name'] = self.name
        values['model'] = self.model_id.model
        values['binding_model_id'] = self.model_id.id if self.active else False
        values['binding_type'] = 'report'
        values['multi'] = False
        values['report_type'] = self.report_type
        values['print_report_name'] = self.report_name
        values['docx_template' if self.report_type == 'docx' else 'xlsx_template' if self.report_type == 'xlsx' else 'pdf_template'] = self.template
        values['docx_template_name' if self.report_type == 'docx' else 'xlsx_template_name' if self.report_type == 'xlsx' else 'pdf_template_name'] = self.template_name
        values['report_name'] = f"{'report_docx.abstract' if self.report_type == 'docx' else '	report_xlsx.abstract' if self.report_type == 'xlsx' else 'report_docx2pdf.abstract'}.en_report_template_{self.id}"
        values['groups_id'] = [(6, 0, self.groups_id.ids)]
        return values

    @api.model_create_multi
    def create(self, vals_lst):
        res = super().create(vals_lst)
        for record in res:
            report_id = self.env['ir.actions.report'].sudo().create(record._report_get_values())
            record.write({'report_id': report_id.id})
        return res

    def write(self, vals):
        res = super().write(vals)
        if any(key in vals for key in self.REPORT_WRITEABLE_FIELDS):
            for record in self:
                record.report_id.sudo().write(record._report_get_values())
        return res

    def unlink(self):
        self.report_id.unlink()
        return super().unlink()

    def toggle_active(self):
        res = super().toggle_active()
        activated = self.filtered(lambda x: x.active)
        archived = self.filtered(lambda x: not x.active)
        if activated:
            activated.report_id.create_action()
        if archived:
            archived.report_id.unlink_action()
        return res

    report_id = fields.Many2one(string='Báo cáo', comodel_name='ir.actions.report', readonly=True, copy=False)

    def to_report(self):
        return self.open_form_or_tree_view(action='base.ir_action_report', records=self.report_id)

    model_id = fields.Many2one(string='Vị trí mẫu in', comodel_name='ir.model', domain="[('transient','=',False)]")
    name = fields.Char(string='Tên hành động', required=True)
    report_name = fields.Char(string='Tên file in', default="object.display_name")
    report_type = fields.Selection(string='Loại báo cáo', selection=[('qweb-pdf', 'PDF'), ('docx', 'Docx'), ('xlsx', 'Xlsx')], required=True)
    template = fields.Binary(string='Template', help="""Template cần đúng định dạng của loại báo cáo\n
                                                        Loại báo cáo pdf, docx cần file template là file docx\n
                                                        Loại báo cáo xlsx cần template là file xlxs""")
    template_name = fields.Char(string='Tên Template')
    active = fields.Boolean(string='Hoạt động', default=True)
    x_sms_params_ids = fields.One2many('x.sms.params', string='sms_params', inverse_name='en_report_template_id')
    groups_id = fields.Many2many(string='Nhóm', comodel_name='res.groups')

    field_type = fields.Selection(string='Loại trường', selection=[('user', 'Thông tin người đang đăng nhập'), ('company', 'Thông tin công ty'), ('object', 'Vị trí mẫu in'), ('datetime', 'Thời gian hiện tại')])
    ori_model = fields.Char(string='Model thông tin', compute='_compute_ori_field_model')

    @api.depends('field_type', 'model_id')
    def _compute_ori_field_model(self):
        for rec in self:
            ori_model = False
            if rec.field_type == 'user':
                ori_model = 'res.users'
            if rec.field_type == 'company':
                ori_model = 'res.company'
            if rec.field_type == 'object':
                ori_model = rec.model_id.model
            rec.ori_model = ori_model

    @api.onchange('ori_model')
    def _onchange_field_type_n_model(self):
        if self.ori_field_id.model != self.ori_model:
            self.ori_field_id = False
        if self.ori_model:
            self.datetime_value = False

    ori_field_id = fields.Many2one(string='Trường thông tin', comodel_name='ir.model.fields', domain="[('model','=',ori_model)]", invisible_domain="[('field_type','not in',['user','company','object'])]")
    ori_field_ttype = fields.Selection(string='Loại trường', related='ori_field_id.ttype')

    field1_model = fields.Char(string='Model trường phụ 1', compute='_compute_field1_model')

    @api.depends('ori_field_id')
    def _compute_field1_model(self):
        for rec in self:
            rec.field1_model = rec.ori_field_id.relation

    @api.onchange('field1_model')
    def _onchange_field1_model(self):
        if self.field1_id.model != self.field1_model:
            self.field1_id = False

    field1_id = fields.Many2one(string='Trường phụ 1', comodel_name='ir.model.fields', domain="[('model','=',field1_model)]", invisible_domain="[('ori_field_ttype','not in',['many2many','one2many','many2one'])]")
    field1_id_ttype = fields.Selection(string='Loại trường phụ 1', related='field1_id.ttype')

    field2_model = fields.Char(string='Model trường phụ 2', compute='_compute_field2_model')

    @api.depends('field1_id')
    def _compute_field2_model(self):
        for rec in self:
            rec.field2_model = rec.field1_id.relation

    @api.onchange('field2_model')
    def _onchange_field2_model(self):
        if self.field2_id.model != self.field2_model:
            self.field2_id = False

    field2_id = fields.Many2one(string='Trường phụ 2', comodel_name='ir.model.fields', domain="[('model','=',field2_model)]", invisible_domain="[('field1_id_ttype','not in',['many2many','one2many','many2one'])]")

    datetime_value = fields.Selection(string='Thời gian', selection=[('now', 'Thời điểm hiện tại'), ('today', 'Ngày hiện tại'), ('now_day', 'Ngày của ngày hiện tại'), ('now_month', 'Tháng của ngày hiện tại'), ('now_year', 'Năm của tháng hiện tại'), ('weekday', 'Thứ trong tuần của ngày hiện tại')], invisible_domain="[('field_type','not in',['datetime'])]")

    variable = fields.Char(string='Giá trị biến', compute="_compute_variable", store=True, readonly=False)

    @api.depends('field_type', 'ori_field_id', 'field1_id', 'field2_id', 'datetime_value')
    def _compute_variable(self):
        for rec in self:
            variables = []
            if rec.field_type:
                variables += [rec.field_type]
            last_field_type = 'many2one'
            first_field_type = ''
            should_be_sum = False
            if rec.field_type in ['user', 'company', 'object']:
                if rec.ori_field_id:
                    variables += [rec.ori_field_id.name]
                    if not first_field_type:
                        first_field_type = rec.ori_field_id.ttype
                    last_field_type = rec.ori_field_id.ttype
                if rec.field1_id:
                    variables += [rec.field1_id.name]
                    last_field_type = rec.field1_id.ttype
                if rec.field2_id:
                    variables += [rec.field2_id.name]
                    last_field_type = rec.field2_id.ttype
                if last_field_type in ['many2one']:
                    if first_field_type in ['one2many', 'many2many']:
                        variables += ['mapped("display_name")']
                    else:
                        variables += ['display_name']
                if last_field_type in ['char'] and first_field_type in ['one2many', 'many2many']:
                    var = variables.pop()
                    variables += [f'mapped("{var}")']
                if last_field_type in ['float', 'integer', 'monetary'] and first_field_type in ['one2many', 'many2many']:
                    var = variables.pop()
                    variables += [f'mapped("{var}")']
                    should_be_sum = True
                if last_field_type in ['many2many', 'one2many']:
                    variables += ['mapped("display_name")']
                if last_field_type in ['date']:
                    variables += ['strftime("%d/%m/%Y")']
                if last_field_type in ['datetime']:
                    variables += ['strftime("%d/%m/%Y %H:%M:%S")']
            if rec.field_type in ['datetime']:
                if rec.datetime_value == 'now':
                    variables += ['now()', 'strftime("%d/%m/%Y %H:%M:%S")']
                if rec.datetime_value == 'today':
                    variables += ['today()', 'strftime("%d/%m/%Y")']
                if rec.datetime_value == 'now_day':
                    variables += ['today()', 'strftime("%d")']
                if rec.datetime_value == 'now_month':
                    variables += ['today()', 'strftime("%m")']
                if rec.datetime_value == 'now_year':
                    variables += ['today()', 'strftime("%Y")']
                if rec.datetime_value == 'weekday':
                    variables += ['today()', 'strftime("%A")']
            if variables:
                if should_be_sum:
                    rec.variable = "{{sum(" + f"{'.'.join(variables)}" + ")}}"
                elif last_field_type in ['many2many', 'one2many'] or (last_field_type in ['char', 'many2one'] and first_field_type in ['one2many', 'many2many']):
                    rec.variable = "{{', '.join(" + f"{'.'.join(variables)}" + ")}}"
                else:
                    rec.variable = "{{" + f"{'.'.join(variables)}" + "}}"
            else:
                rec.variable = ''
