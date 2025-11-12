from odoo import fields, Command, models, api, _
from odoo.exceptions import UserError
from odoo.tools.safe_eval import safe_eval


class ApprovalRequest(models.Model):
    _inherit = 'approval.request'

    job_id = fields.Many2one('hr.job', string='Chức vụ', compute='_get_job_id', store=True, readonly=False, tracking=True)
    en_department_id = fields.Many2one('en.department', string='Phòng', compute='_get_en_department_id', store=True, readonly=False, tracking=True)
    mobile_phone = fields.Char(string='SĐT', compute='_get_mobile_phone', store=True, readonly=False, tracking=True)
    department_id = fields.Many2one('hr.department', string='Trung tâm/Ban', compute='_get_department_id', store=True, readonly=True, tracking=True)
    hr_user_ids = fields.Many2many('res.users', string='HCNS phụ trách', compute='_get_hr_user_ids', store=True, readonly=False, tracking=True, domain="[('employee_ids.en_department_id.code', 'like', '%HCNS%')]")
    has_job = fields.Selection(related="category_id.has_job")
    has_department = fields.Selection(related="category_id.has_department")
    has_phone = fields.Selection(related="category_id.has_phone")
    has_hr_department = fields.Selection(related="category_id.has_hr_department")
    has_hr_user = fields.Selection(related="category_id.has_hr_user")
    date = fields.Date(default=lambda self: fields.Datetime.now(), tracking=True)

    product_type_domain = fields.Char(compute='_get_product_type_domain')
    request_owner_id = fields.Many2one(tracking=True, default=lambda self: self.env.user)
    active = fields.Boolean(default=True)

    business_plan = fields.Many2one("business.plan", string='Kế hoạch công tác', domain="[('id', 'in', business_domain)]")
    business_domain = fields.Many2many("business.plan", compute='_get_business_domain')

    @api.depends('request_owner_id')
    def _get_business_domain(self):
        for rec in self:
            employee_id = rec.sudo().mapped('request_owner_id.employee_ids.id')
            if not employee_id:
                rec.business_domain = False
                continue
            plan = rec.env['business.plan.partner'].search([('plan_id.state', '=', 'approved'), ('employee_id', '=', employee_id[0])]).plan_id
            plan += rec.env['business.plan'].search([('state', '=', 'approved'), ('responsible_id', '=', employee_id[0])])
            rec.business_domain = plan

    business_description = fields.Text('Nội dung đi công tác')
    support_ids = fields.Many2many('approval.request.support', string='Yêu cầu hỗ trợ')
    personnel_list_ids = fields.One2many('approval.request.personnel.list', 'request_id', string='Danh sách nhân sự')
    plane_list_ids = fields.One2many('approval.request.plane.list', 'request_id', string='Máy bay')
    hotel_list_ids = fields.One2many('approval.request.hotel.list', 'request_id', string='Khách sạn')
    car_list_ids = fields.One2many('approval.request.car.list', 'request_id', string='Xe')

    has_plane_support = fields.Boolean(compute='_get_support_option')
    has_hotel_support = fields.Boolean(compute='_get_support_option')
    has_car_support = fields.Boolean(compute='_get_support_option')

    email = fields.Char(string='Email', compute='_get_hr_info', store=True)
    hr_barcode = fields.Char('Mã nhân sự', compute='_get_hr_info', store=True)
    en_block_id = fields.Many2one('en.name.block', string='Khối', compute='_get_hr_info', store=True)
    request_status = fields.Selection(tracking=False)

    @api.depends('request_owner_id')
    def _get_hr_info(self):
        for rec in self:
            rec.hr_barcode = rec.request_owner_id.employee_id.barcode
            rec.email = rec.request_owner_id.employee_id.work_email
            rec.en_block_id = rec.request_owner_id.employee_id.en_block_id

    expected_date = fields.Date('Thời gian mong muốn')
    delivery_date = fields.Date('Ngày bàn giao', readonly=True)
    repair_ids = fields.One2many('repair.request.detail', 'request_id', string='Sửa chữa/Nâng cấp TSCĐ')
    asset_ids = fields.One2many('asset.request.detail', 'request_id', string='Sửa chữa/Nâng cấp TSCĐ')
    person_asset_ids = fields.One2many('person.asset.request.detail', 'request_id', string='Tài sản cá nhân')

    show_button_delivery = fields.Boolean(compute='_get_show_button_delivery')

    approver_ids = fields.One2many(compute=False, readonly=True)

    origin_location = fields.Char("Địa điểm xuất phát")
    destination_location = fields.Char("Địa điểm đến")
    start_time = fields.Date("Thời gian đi")
    end_time = fields.Date("Thời gian về")

    @api.depends('approver_ids.status', 'approver_ids.required')
    def _compute_request_status(self):
        for request in self:
            status_lst = request.mapped('approver_ids.status')
            required_approved = all(rec == 'approved' for rec in status_lst)
            if status_lst:
                if status_lst.count('cancel'):
                    status = 'cancel'
                elif status_lst.count('refused'):
                    status = 'refused'
                elif status_lst.count('new'):
                    status = 'new'
                elif status_lst.count('approved') and required_approved:
                    status = 'approved'
                else:
                    status = 'pending'
            else:
                status = 'new'
            request.request_status = status

    @api.depends('approver_ids.status')
    def _compute_user_status(self):
        for approval in self:
            status = approval.approver_ids.filtered(lambda approver: approver.user_id == self.env.user).mapped('status')
            if len(set(status)) == 1:
                user_status = status[0]
            elif 'cancel' in status:
                user_status = 'cancel'
            elif 'refused' in status:
                user_status = 'refused'
            elif 'pending' in status:
                user_status = 'pending'
            elif 'new' in status:
                user_status = 'new'
            elif 'approved' in status:
                user_status = 'approved'
            else:
                user_status = False

            if user_status == 'pending' and self.env['office.approve.flow']._get_next_possible_approver(approval.approver_ids).user_id != self.env.user:
                user_status = False
            approval.user_status = user_status

    @api.depends('approval_type', 'request_status')
    def _get_show_button_delivery(self):
        for rec in self:
            show_button_delivery = False
            if rec.approval_type == 'old_asset' and rec.request_status == 'done':
                show_button_delivery = True
            if rec.approval_type == 'new_asset' and rec.request_status == 'approved':
                show_button_delivery = True
            rec.show_button_delivery = show_button_delivery

    @api.depends('support_ids')
    def _get_support_option(self):
        for rec in self:
            all_key = rec.support_ids.mapped('key')
            rec.has_plane_support = 'plane' in all_key
            rec.has_car_support = 'car' in all_key
            rec.has_hotel_support = 'hotel' in all_key

    @api.depends('category_id')
    def _get_product_type_domain(self):
        for rec in self:
            rec.product_type_domain = rec.category_id.approval_type if rec.category_id.approval_type in ['car', 'vpp'] else 'other'

    @api.depends('request_owner_id', 'has_job')
    def _get_job_id(self):
        for rec in self:
            if rec.request_owner_id and rec.has_job != 'no':
                rec.job_id = rec.request_owner_id.employee_id.job_id
            else:
                rec.job_id = False

    @api.depends('request_owner_id', 'has_department')
    def _get_en_department_id(self):
        for rec in self:
            if rec.request_owner_id and rec.has_department != 'no':
                rec.en_department_id = rec.request_owner_id.employee_id.en_department_id
            else:
                rec.en_department_id = False

    @api.depends('request_owner_id', 'has_phone')
    def _get_mobile_phone(self):
        for rec in self:
            if rec.request_owner_id and rec.has_phone != 'no':
                rec.mobile_phone = rec.request_owner_id.employee_id.phone
            else:
                rec.mobile_phone = False

    @api.depends('request_owner_id', 'has_hr_department')
    def _get_department_id(self):
        for rec in self:
            if rec.request_owner_id and rec.has_hr_department != 'no':
                rec.department_id = rec.request_owner_id.employee_ids[0].department_id if rec.request_owner_id.employee_ids else False
            else:
                rec.department_id = False

    @api.depends('has_hr_user')
    def _get_hr_user_ids(self):
        for rec in self:
            if rec.has_hr_department != 'no':
                rec.hr_user_ids = rec.hr_user_ids
            else:
                rec.hr_user_ids = False

    def action_draft(self):
        if any(r.status == 'approved' for r in self.approver_ids):
            raise UserError('Yêu cầu đã được phê duyệt không thể chuyển về Để trình')
        self.sudo().write({'approver_ids': False, 'date_confirmed': False})

    def action_confirm(self):
        self.ensure_one()
        self._new_compute_approver_ids()
        if self.request_owner_id.employee_id.department_id.bod:
            self.approver_ids.write({'status': 'approved'})
            self.action_approve()
            return True
        else:
            lines = self.env['office.approve.flow']._get_next_possible_approver(self.approver_ids)
            users = lines.user_id
            mes = self.get_message('action_confirm')
            action = self.get_action_view_from_id()
            access_link = f'/web#id={self.id}&action={action.id}&model=approval.request&view_type=form'
            self.send_notify(mes, users, access_link=access_link)
        if self.requirer_document == 'required' and not self.attachment_number:
            raise UserError('Bạn phải đính kèm ít nhất một tài liệu.')
        approvers = self.mapped('approver_ids').filtered(lambda approver: approver.status == 'new')
        approvers.write({'status': 'pending'})
        self.write({'date_confirmed': fields.Datetime.now()})

    def get_action_view_from_id(self):
        self.ensure_one()
        if self.category_id.approval_type in ['old_asset', 'new_asset', 'person_asset']:
            return self.env.ref('ngs_e_office.account_asset_request_action_all')
        return self.env.ref('approvals.approval_request_action_all')

    @api.onchange('category_id', 'request_owner_id')
    def default_value(self):
        if self.category_id.approval_type == 'business' and not self.personnel_list_ids and self.request_owner_id:
            self.personnel_list_ids = [(0, 0, {
                'sequence': 1,
                'employee_id': self.request_owner_id.employee_id.id,
                'phone': self.request_owner_id.employee_id.mobile_phone,
                'dob': self.request_owner_id.employee_id.birthday,
                'cccd': self.request_owner_id.employee_id.identification_id,
                'passport': self.request_owner_id.employee_id.passport_id
            })]


    def action_approve(self, approver=None):
        if not isinstance(approver, models.BaseModel):
            approver = self.env['office.approve.flow']._get_next_possible_approver(self.approver_ids)
        approver.write({'status': 'approved'})
        action = self.get_action_view_from_id()
        access_link = f'/web#id={self.id}&action={action.id}&model=approval.request&view_type=form'
        if self.request_status == 'approved':
            users = self.request_owner_id | self.hr_user_ids
            self.send_notify(self.get_message('action_approve'), users, access_link=access_link)
        else:
            next_approver = self.env['office.approve.flow']._get_next_possible_approver(self.approver_ids)
            self.send_notify(self.get_message('action_confirm'), next_approver.user_id, access_link=access_link)


    def action_refuse(self):
        res = super().action_refuse()
        for rec in self:
            users = self.request_owner_id
            mes = rec.get_message('action_refuse')
            rec.send_notify(mes, users)
        return res

    def button_delivery(self):
        if any(rec.approval_type not in ['new_asset', 'old_asset'] for rec in self):
            raise UserError('Không được phép bàn giao với loại yêu cầu này')
        self.write({
            'request_status': 'delivery',
            'delivery_date': fields.Datetime.now()
        })

    def get_message(self, state):
        self.ensure_one()
        data = {
            'other': {
                'action_confirm': 'Bạn có yêu cầu mới cần phê duyệt. Bấm tại đây để xem chi tiết.',
                'action_approve': 'Yêu cầu của bạn đã được phê duyệt. Bấm tại đây để xem chi tiết.',
                'action_refuse': 'Yêu cầu của bạn đã bị từ chối. Bấm tại đây để xem chi tiết.',
            },
            'business': {
                'action_confirm': 'Bạn có yêu cầu công tác mới cần duyệt. Bấm tại đây để xem chi tiết.',
                'action_approve': 'Yêu cầu công tác đã được phê duyệt. Bấm tại đây để xem chi tiết.',
                'action_refuse': 'Yêu cầu công tác đã bị từ chối. Bấm tại đây để xem chi tiết.',
            },
            'new_asset': {
                'action_confirm': 'Bạn có yêu cầu cấp tài sản cần duyệt. Bấm tại đây để xem chi tiết.',
                'action_approve': 'Yêu cầu cấp tài sản vừa được duyệt. Bấm tại đây để xem chi tiết.',
                'action_refuse': 'Yêu cầu cấp tài sản đã bị từ chối. Bấm tại đây để xem chi tiết.',
            },
            'old_asset': {
                'action_confirm': 'Bạn có yêu cầu sửa chữa tài sản cần duyệt. Bấm tại đây để xem chi tiết.',
                'action_approve': 'Yêu cầu sửa chữa tài sản vừa được duyệt. Bấm tại đây để xem chi tiết.',
                'action_refuse': 'Yêu cầu sửa chữa tài sản đã bị từ chối. Bấm tại đây để xem chi tiết.',
            },
        }
        default = data.get('other', {})
        return data.get(self.approval_type, default).get(state, '')


    def create_name(self):
        for rec in self:
            approval_type = rec.category_id.approval_type
            if approval_type == 'new_asset':
                rec.name = self.env['ir.sequence'].next_by_code('seq.new.asset')
            elif approval_type == 'old_asset':
                rec.name = self.env['ir.sequence'].next_by_code('seq.old.asset')
            elif approval_type == 'person_asset':
                rec.name = self.env['ir.sequence'].next_by_code('seq.person.asset')
            elif approval_type == 'business':
                rec.name = self.env['ir.sequence'].next_by_code('seq.approval.business')            
            elif approval_type == 'vpp':
                rec.name = self.env['ir.sequence'].next_by_code('seq.approval.vpp')
            elif approval_type == 'car':
                rec.name = self.env['ir.sequence'].next_by_code('seq.approval.car')

    @api.constrains('product_line_ids', 'category_id', 'repair_ids', 'asset_ids', 'personnel_list_ids')
    def check_product_line_ids(self):
        for rec in self:
            if not rec.product_line_ids and rec.category_id.approval_type == 'vpp':
                raise UserError('Vui lòng nhập thông tin sản phẩm!')
            elif not rec.product_line_ids and rec.category_id.approval_type == 'car':
                raise UserError('Vui lòng nhập thông tin xe!')
            elif rec.category_id.approval_type == 'business' and not rec.personnel_list_ids:
                raise UserError('Vui lòng nhập Danh sách nhân sự!')
            elif not rec.repair_ids and rec.category_id.approval_type == 'old_asset':
                raise UserError('Vui lòng nhập thông tin Sửa chữa/Nâng cấp TSCĐ!')
            elif not rec.asset_ids and rec.category_id.approval_type == 'new_asset':
                raise UserError('Vui lòng nhập thông tin TSCD/CCDC!')

    @api.constrains('plane_list_ids', 'hotel_list_ids', 'car_list_ids', 'category_id')
    def check_contrains_approval_type_business(self):
        for rec in self:
            error = []
            if rec.category_id.approval_type == 'business' and not self._context.get('create_value'):
                if not rec.plane_list_ids and rec.has_plane_support:
                    error.append('máy bay')
                if not rec.hotel_list_ids and rec.has_hotel_support:
                    error.append('khách sạn')
                if not rec.car_list_ids and rec.has_car_support:
                    error.append('xe')
            if error:
                raise UserError('Vui lòng nhập thông tin ' + ', '.join(error) + '!')


    @api.model
    def create(self, vals):
        res = super(ApprovalRequest, self.with_context(create_value=True)).create(vals)
        res.create_name()
        value_refresh = {
            'plane_list_ids': res.refresh_plane_list_line(),
            'hotel_list_ids': res.refresh_hotel_list_line(),
            'car_list_ids': res.refresh_car_list_line(),
        }
        res.write(value_refresh)
        if res.category_id.approval_type == 'old_asset':
            res.send_evalute_to_handler()
        return res

    def write(self, vals):
        res = super().write(vals)
        if 'support_ids' in vals or 'personnel_list_ids' in vals:
            for rec in self:
                value_refresh = {
                    'plane_list_ids': rec.refresh_plane_list_line(),
                    'hotel_list_ids': rec.refresh_hotel_list_line(),
                    'car_list_ids': rec.refresh_car_list_line(),
                }
                rec.write(value_refresh)
        for rec in self:
            if rec.category_id.approval_type == 'old_asset' and not self._context.get('create_value'):
                rec.send_evalute_to_handler()
        return res

    def send_evalute_to_handler(self):
        for rec in self:
            it_ids = rec.repair_ids.filtered(lambda x: x.it_id and not x.it_result).mapped('it_id')
            for it_id in it_ids.sudo():
                action = self.env.ref('ngs_e_office.account_asset_request_approval_action_all')
                access_link = f'/web#id={self.id}&action={action.id}&model=approval.request&view_type=form'
                rec.send_notify('Bạn đang có phiếu Sửa chữa cần đánh giá. Vui lòng bấm tại đây để xem chi tiết.', it_id.user_id, 'Điền thông tin đánh giá', access_link=access_link)

    def refresh_plane_list_line(self):
        self.ensure_one()
        need_create = self.personnel_list_ids - self.plane_list_ids.line_id
        vals = []
        if not self.has_plane_support:
            vals = [(5, 0, 0)]
        else:
            for rec in need_create:
                vals.append((0, 0, {
                    'line_id': rec.id,
                    'sequence': rec.sequence,
                    'employee_id': rec.employee_id.id,
                    'level': rec.level,
                    'phone': rec.phone,
                    'dob': rec.dob,
                    'cccd': rec.cccd,
                    'passport': rec.passport,
                }))
        return vals


    def refresh_hotel_list_line(self):
        self.ensure_one()
        need_create = self.personnel_list_ids - self.hotel_list_ids.line_id
        vals = []
        if not self.has_hotel_support:
            vals = [(5, 0, 0)]
        else:
            for rec in need_create:
                vals.append((0, 0, {
                    'line_id': rec.id,
                    'sequence': rec.sequence,
                    'employee_id': rec.employee_id.id,
                    'level': rec.level,
                    'phone': rec.phone,
                }))
        return vals

    def refresh_car_list_line(self):
        self.ensure_one()
        need_create = self.personnel_list_ids - self.car_list_ids.line_id
        vals = []
        if not self.has_car_support:
            vals = [(5, 0, 0)]
        else:
            for rec in need_create:
                vals.append((0, 0, {
                    'line_id': rec.id,
                    'sequence': rec.sequence,
                    'employee_id': rec.employee_id.id,
                    'level': rec.level,
                    'phone': rec.phone
                }))
        return vals

    def get_flow_domain(self):
        return [('model', '=', self._name), '|', ('block_ids', '=', False), ('block_ids', '=', self.request_owner_id.employee_id.en_block_id.id), '|',
                ('department_ids', '=', False), ('department_ids', '=', self.request_owner_id.employee_id.department_id.id), '|',
                ('en_department_ids', '=', False), ('en_department_ids', '=', self.request_owner_id.employee_id.en_department_id.id)]

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if attributes and not 'readonly' in attributes:
            return res
        for fname in res:
            if res[fname]['readonly']:
                continue
            if fname in ['hr_user_ids']:
                continue
            res[fname].update({
                'readonly_domain': "[('request_status', '!=', 'new')]"
            })
        return res

    def _new_compute_approver_ids(self):
        self.ensure_one()
        request = self.sudo()
        processes = self.env['office.approve.flow'].sudo().search(request.get_flow_domain(), order='id desc')
        approver_id_vals = []
        for process in processes:
            if not request.filtered_domain(safe_eval(process.domain or '[]')):
                continue
            for rule in process.rule_ids.sorted(lambda x: x.visible_sequence):
                approver_user_id = self.env['res.users']
                role_selection = False
                if rule.type == 'person':
                    approver_user_id = rule.user_id
                    role_selection = rule.en_role_detail
                if rule.type == 'role' and rule.role_selection:
                    employee = request.request_owner_id.employee_id
                    role_selection_selection = dict(rule.fields_get(['role_selection'])['role_selection']['selection'])
                    if rule.role_selection == 'block':
                        approver_user_id = employee.en_block_id.en_project_implementation_id
                    if rule.role_selection == 'department':
                        approver_user_id = employee.department_id.manager_id.user_id
                    if rule.role_selection == 'en_department':
                        approver_user_id = employee.en_department_id.manager_id.user_id
                    if rule.role_selection == 'manager':
                        approver_user_id = employee.parent_id.user_id
                    if rule.role_selection == 'pm_project':
                        approver_user_id = request.business_plan.project_id.user_id
                    role_selection = role_selection_selection.get(rule.role_selection)
                if not approver_user_id:
                    continue
                approver_id_vals.append(Command.create({
                    'user_id': approver_user_id.id,
                    'status': 'new',
                    'required': rule.required,
                    'role_selection': role_selection,
                    'sequence': rule.sequence
                }))
            break
        if not approver_id_vals:
            raise UserError('Không tìm thấy quy trình duyệt hoặc người duyệt tương ứng')
        approver_id_vals = [(5, 0, 0)] + approver_id_vals
        request.update({'approver_ids': approver_id_vals})

    def action_done(self):
        self.write({'request_status': 'done'})

    expected_return_date = fields.Date("Hạn trả dự kiến")
    actual_return_date = fields.Date("Ngày trả thực tế")
    has_expected_return_date = fields.Selection(related="category_id.has_expected_return_date")
    has_actual_return_date = fields.Selection(related="category_id.has_actual_return_date")

    plan_date_used = fields.Date("Thời gian dự kiến sử dụng")
    plan_date_end_used = fields.Date("Thời gian dự kiến kết thúc sử dụng")
    actual_date_used = fields.Date("Thời gian thực tế sử dụng")
    actual_date_end_used = fields.Date("Thời gian thực tế kết thúc sử dụng")


class ApprovalRequestSupport(models.Model):
    _name = 'approval.request.support'
    _description = 'Yêu cầu hỗ trợ công tác'

    name = fields.Char()
    key = fields.Char()


class ApprovalRequestPersonnelList(models.Model):
    _name = 'approval.request.personnel.list'
    _description = 'Danh sách nhân sự'

    sequence = fields.Integer('STT')
    employee_id = fields.Many2one('hr.employee', string='Họ và tên', required=1, ondelete='cascade')
    level = fields.Char('Level', required=1)
    phone = fields.Char('Số điện thoại', required=1)
    dob = fields.Date('Ngày sinh', required=1)
    cccd = fields.Char('CCCD', required=1)
    passport = fields.Char('Hộ chiếu')
    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')

    @api.onchange('sequence')
    def get_sequence(self):
        self.sequence = max(self.sudo().request_id.personnel_list_ids.mapped('sequence') or 0) + 1

    @api.onchange('employee_id')
    def get_value_employee_id(self):
        if self.employee_id:
            self.phone = self.sudo().employee_id.mobile_phone
            self.dob = self.sudo().employee_id.birthday
            self.cccd = self.sudo().employee_id.identification_id
            self.passport = self.sudo().employee_id.passport_id


class ApprovalRequestPlaneList(models.Model):
    _name = 'approval.request.plane.list'
    _description = 'Danh sách Máy bay'

    sequence = fields.Integer('STT')
    employee_id = fields.Many2one('hr.employee', string='Họ và tên', required=1, ondelete='cascade')
    level = fields.Char('Level', required=1)
    phone = fields.Char('Số điện thoại', required=1)
    dob = fields.Date('Ngày sinh', required=1)
    cccd = fields.Char('CCCD', required=1)
    passport = fields.Char('Hộ chiếu')
    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    line_id = fields.Many2one('approval.request.personnel.list', string='Danh sách nhân sự', required=1, ondelete='cascade')


class ApprovalRequestHotelList(models.Model):
    _name = 'approval.request.hotel.list'
    _description = 'Danh sách Khách sạn'

    sequence = fields.Integer('STT')
    employee_id = fields.Many2one('hr.employee', string='Họ và tên', required=1, ondelete='cascade')
    level = fields.Char('Level', required=1)
    phone = fields.Char('Số điện thoại', required=1)
    location = fields.Char('Điểm đến công tác')
    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    line_id = fields.Many2one('approval.request.personnel.list', string='Danh sách nhân sự', required=1, ondelete='cascade')


class ApprovalRequestcarList(models.Model):
    _name = 'approval.request.car.list'
    _description = 'Danh sách Xe'

    sequence = fields.Integer('STT')
    employee_id = fields.Many2one('hr.employee', string='Họ và tên', required=1, ondelete='cascade')
    level = fields.Char('Level', required=1)
    phone = fields.Char('Số điện thoại', required=1)
    location_start = fields.Char('Điểm đón')
    location_end = fields.Char('Điểm đến')
    start_time = fields.Datetime('Thời gian đón')
    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    line_id = fields.Many2one('approval.request.personnel.list', string='Danh sách nhân sự', required=1, ondelete='cascade')


class RepairRequestDetail(models.Model):
    _name = 'repair.request.detail'
    _description = 'Sửa chữa/Nâng cấp TSCĐ'

    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    asset_id = fields.Many2one('account.asset', required=1, ondelete='cascade', string='Mã tài sản')
    code = fields.Char(related='asset_id.name', string='Tài sản')
    quality = fields.Selection(selection=[('repair', 'Cần sửa chữa'), ('upgrade', 'Cần nâng cấp')], string='Tình trạng', required=1, default='repair')
    quantity = fields.Integer('Số lượng', required=1)
    description = fields.Text('Mô tả')
    it_id = fields.Many2one('hr.employee', string='Người xử lý', domain="['|', ('department_id.code', '=', 'CN'), ('en_department_id.code', 'like', '%HCNS%')]", context={'view_all_hr_employee': True})
    it_result = fields.Selection([('fixable', 'Sửa được'), ('unfixable', 'Không sửa được')], string='Đánh giá')
    reason_norepair = fields.Char(string='Tình trạng máy sau đánh giá')
    state = fields.Selection(selection=[('draft', 'Chưa xử lý'), ('progress', 'Đang xử lý'), ('done', 'Đã xử lý')], string='Trạng thái sửa chữa', required=1, default='draft')

    hr_edit = fields.Boolean(compute='_get_hr_edit')

    @api.depends('request_id')
    def _get_hr_edit(self):
        for rec in self:
            hr_edit = False
            # if rec.request_id.request_status == 'new':
            #     hr_edit = True
            if rec.request_id.request_status in ['approved', 'progress'] and self.env.user in rec.request_id.hr_user_ids:
                hr_edit = True
            rec.hr_edit = hr_edit

    it_edit = fields.Boolean(compute='_get_it_edit')

    @api.depends('it_id')
    def _get_it_edit(self):
        for rec in self:
            it_edit = False
            # if rec.request_id.request_status == 'new':
            #     it_edit = True
            if rec.request_id.request_status in ['approved', 'progress'] and self.env.user.employee_id == rec.it_id:
                it_edit = True
            rec.it_edit = it_edit

    def write(self, vals):
        res = super(RepairRequestDetail, self).write(vals)
        if vals.get('state') == 'progress':
            for rec in self:
                if rec.request_id.request_status == 'approved':
                    rec.request_id.request_status = 'progress'
        if vals.get('state') == 'done':
            for rec in self:
                if rec.request_id.request_status in ['approved', 'progress'] and all(repair.state == 'done' for repair in rec.request_id.repair_ids):
                    rec.request_id.request_status = 'done'
        return res


class AssetRequestDetail(models.Model):
    _name = 'asset.request.detail'
    _description = 'TSCD/CCDC'

    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    asset_id = fields.Many2one('account.asset', ondelete='cascade', string='Tài sản')
    code = fields.Char(related='asset_id.code', readonly=False)
    category = fields.Selection(selection=[('pc', 'Máy tính'), ('chair', 'Bàn ghế'), ('screen', 'Màn hình'), ('cabinet', 'Tủ'), ('phone', 'Điện thoại'), ('other', 'Khác')], string='Danh mục', required=1)
    configuration = fields.Text('Cấu hình mong muốn')
    model = fields.Text('Dòng máy')
    quantity = fields.Integer('Số lượng')
    reason = fields.Text('Lý do cấp')

class PersonAssetRequestDetail(models.Model):
    _name = 'person.asset.request.detail'
    _description = 'TSCN'

    request_id = fields.Many2one('approval.request', string='Yêu cầu', required=1, ondelete='cascade')
    asset_type = fields.Selection(selection=[('person', 'Tài sản cá nhân'), ('customer', 'Tài sản mượn của KH/Dự án'), ('other', 'Khác')], string='Loại tài sản', required=1)
    asset_name = fields.Text('Tên tài sản')
    quantity = fields.Integer('Số lượng')
    description = fields.Text('Mô tả')
    commitmentBinding = fields.Text('Cam kết ràng buộc')
