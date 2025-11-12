from odoo import fields, models, api
from odoo.exceptions import UserError


class HrOvertimeType(models.Model):
    _name = 'en.hr.overtime.type'
    _description = 'Loại tăng ca'

    name = fields.Char(string='Loại tăng ca', required=True)
    code = fields.Char(string='Mã', required=True)
    approve_type = fields.Selection(string='Phê duyệt', required=True, default='project_manager', selection=[('manager', 'Người quản lý'), ('project_manager', 'Quản lý dự án'), ('user', 'Người chỉ định')])
    approver_id = fields.Many2one(string='Người phụ trách', comodel_name='res.users')
    attendance_ids = fields.One2many('en.hr.overtime.attendance', 'type_id', string='Thời gian tăng ca')
    is_holiday = fields.Boolean(string='Tăng ca nghỉ lễ')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            approve_type = vals.get('approve_type')
            if approve_type != 'user':
                vals['approver_id'] = False
        return super().create(vals_list)

    def write(self, vals):
        if 'approve_type' in vals:
            approve_type = vals.get('approve_type')
            if approve_type != 'user':
                vals['approver_id'] = False
        return super().write(vals)

    def unlink(self):
        if self.env['en.hr.overtime'].sudo().search_count([('type_id', 'in', self.ids)]) > 0:
            raise UserError('Loại tăng ca này đã được sử dụng nên không xóa được.')
        return super().unlink()

    def copy(self, default=None):
        default = default or {}
        if not default.get('name'):
            default['name'] = "%s (sao chép)" % self.name
        if not default.get('attendance_ids'):
            default['attendance_ids'] = [(0, 0, {
                'name': l.name,
                'date': l.date,
                'time_start': l.time_start,
                'time_end': l.time_end,
            }) for l in self.attendance_ids]
        res = super(HrOvertimeType, self).copy(default)
        return res

    @api.constrains('is_holiday', 'attendance_ids')
    def _check_all_overtime(self):
        for rec in self:
            if not rec.attendance_ids:
                raise UserError('Loại tăng ca phải có thời gian tăng ca')
            if rec.is_holiday and self.sudo().search_count([('is_holiday', '=', True)]) > 1:
                raise UserError('Đã tồn tại bản ghi Loại tăng ca nghỉ lễ')


class HrOvertimeAttendance(models.Model):
    _name = "en.hr.overtime.attendance"
    _description = 'Thời gian Tăng ca'

    sequence = fields.Integer(string='Thứ tự', default=10)
    name = fields.Char(required=False, string="Tên")
    date = fields.Selection([
        ('0', 'Thứ hai'),
        ('1', 'Thứ ba'),
        ('2', 'Thứ tư'),
        ('3', 'Thứ năm'),
        ('4', 'Thứ sáu'),
        ('5', 'Thứ bảy'),
        ('6', 'Chủ nhật')
        ], 'Ngày trong tuần', required=True, default='0')
    day_period = fields.Selection([('morning', 'Sáng'), ('night', 'Tối')], string="Buổi", required=True, default='night')

    time_start = fields.Float(string='Thời gian bắt đầu', required=1)
    time_end = fields.Float(string='Thời gian kết thúc', required=1)
    type_id = fields.Many2one("en.hr.overtime.type", required=1, ondelete='cascade')
    rate = fields.Float(string='Hệ số', default=1)
    rate_cot = fields.Float(string='Hệ số đã có OT', default=1)

    @api.onchange('time_start', 'time_end')
    def _onchange_hours(self):
        # avoid negative or after midnight
        self.time_start = min(self.time_start, 23.99)
        self.time_start = max(self.time_start, 0.0)
        self.time_end = min(self.time_end, 24)
        self.time_end = max(self.time_end, 0.0)

        # avoid wrong order
        self.time_end = max(self.time_end, self.time_start)

    @api.constrains('time_start', 'time_end')
    def check_valid_hour(self):
        for rec in self:
            if not (0 <= rec.time_start <= 23.99):
                raise UserError('Thời điểm bắt đầu không hợp lệ (00:00-23:59)')
            if not (0 <= rec.time_end <= 24):
                raise UserError('Thời điểm kết thúc không hợp lệ (00:00-24)')
            if rec.time_start >= rec.time_end:
                raise UserError('Thời điểm bắt đầu phải nhỏ hơn Thời điểm kết thúc')

    @api.constrains('rate', 'rate_cot')
    def check_valid_rate(self):
        for rec in self:
            if rec.rate <= 0:
                raise UserError('Hệ số phải lớn hơn 0')
            if rec.rate_cot <= 0:
                raise UserError('Hệ số đã có OT phải lớn hơn 0')