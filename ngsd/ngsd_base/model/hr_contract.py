from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields, models, api, exceptions
from odoo.exceptions import UserError
from odoo.fields import Domain


class HrContract(models.Model):
    _inherit = 'hr.contract'

    working_hour = fields.Float(string='Thời giờ làm việc')
    basic_salary = fields.Integer(string='Mức lương cơ bản')
    remuneration = fields.Float(string='Thù lao')
    payment_batch_ids = fields.One2many(comodel_name='payment.batch', inverse_name='hr_contract_id', string='Đợt thanh toán')
    training_location = fields.Char(string='Địa điểm đào tạo')
    training_cost_ids = fields.One2many(comodel_name='training.cost', inverse_name='hr_contract_id', string='Chi phí đào tạo')
    monthly_performance_bonus = fields.Integer(string='Thưởng hiệu quả hàng tháng tạm tính tối đa')
    lunch_allowance = fields.Integer(string='Phụ cấp ăn trưa')
    phone_allowance = fields.Integer(string='Phụ cấp điện thoại')
    travel_allowance = fields.Integer(string='Phụ cấp đi lại')
    contract_type = fields.Selection(related='contract_type_id.contract_type', string='Loại hợp đồng', store=True)
    employee_barcode = fields.Char(string='Mã nhân viên', related='employee_id.barcode', store=True)
    contract_date_id = fields.Many2one(comodel_name='contract.date', string='Thời hạn hợp đồng')
    extension_status = fields.Selection([('extend', 'Gia hạn'), ('not_extend', 'Không gia hạn')], string='Tình trạng gia hạn')
    representative = fields.Many2one('hr.employee', string='Người đại diện', default=lambda self: self.env['hr.employee'].search([('check_representative', '=', True)]).id)
    position = fields.Many2one('hr.job', string='Chức vụ', default=lambda self: self.env['hr.employee'].search([('check_representative', '=', True)]).job_id)
    phone = fields.Char(string='Số điện thoại', default=lambda self: self.env['hr.employee'].search([('check_representative', '=', True)]).work_phone)
    name = fields.Char(required=0)
    sequence = fields.Integer()
    date_end = fields.Date(compute='compute_date_end', store=True)
    kanban_state = fields.Selection(default='done')
    search_contract_type = fields.Text(string='Tìm kiếm loại hợp đồng', compute='compute_search_contract_type', store=True)
    wage = fields.Monetary(required=False)

    def compute_search_contract_type(self):
        for rec in self:
            rec.search_contract_type = dict(rec.fields_get(['contract_type'])['contract_type']['selection']).get(rec.contract_type, '')

    @api.depends('contract_date_id', 'date_start')
    def compute_date_end(self):
        for rec in self:
            rec.date_end = False
            if rec.contract_date_id.unit == 'year':
                rec.date_end = rec.date_start + relativedelta(years=rec.contract_date_id.period)
            elif rec.contract_date_id.unit == 'month':
                rec.date_end = rec.date_start + relativedelta(months=rec.contract_date_id.period)
            elif rec.contract_date_id.unit == 'day':
                rec.date_end = rec.date_start + relativedelta(days=rec.contract_date_id.period)

    def action_send_warning_contract(self):
        for rec in self:
            if not rec.date_end or rec.state != 'open':
                continue
            expiration_date = (rec.date_end - fields.Date.Date.Date.context_today(self)).days
            contract_warning = self.env['contract.warning'].search([('contract_type_ids', '=', rec.contract_type_id.id), ('advance_waring_period', '>=', expiration_date)])
            if contract_warning and expiration_date >= 0 and not rec.extension_status:
                rec.send_notify(f'Hợp đồng {rec.name} sắp hết hạn sau {expiration_date} ngày nữa. Vui lòng bấm vào đây để kiểm tra chi tiết', rec.hr_responsible_id, 'Cảnh báo hết hạn hợp đồng')
            elif expiration_date < 0:
                rec.state = 'close'

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for fname in res:
            if res.get(fname).get('readonly'):
                continue
            states = {
                'draft': [('readonly', False)],
                'open': [('readonly', True)],
                'close': [('readonly', True)],
                'cancel': [('readonly', True)],
            }
            res[fname].update({'states': states})
        return res

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise exceptions.ValidationError('Bạn không thể xoá hợp đồng đang ở trạng thái Đang hoạt động, Đã hết hạn và Huỷ')
        return super().unlink()

    def action_cancel(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Chuyển trạng thái hợp đồng',
            'res_model': 'confirm.cancel.hr.contract.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_contract_id': self.id},
        }
        return action

    def button_show_history(self):
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Lịch sử hợp đồng',
            'res_model': 'hr.contract',
            'view_mode': 'form',
            'views': [(self.env.ref('ngsd_base.form_history_hr_contract').id, 'form')],
            'res_id': self.id,
            'target': 'new',
            'context': {'default_message_follower_ids': self.message_follower_ids.ids,
                        'default_activity_ids': self.activity_ids.ids,
                        'default_message_ids': self.message_ids.ids},
        }
        return action

    def action_change_state_contract(self):
        hr_contracts = self.env['hr.contract'].search([('date_start', '<=', fields.Date.Date.Date.context_today(self)), ('state', '=', 'draft')])
        for contract in hr_contracts:
            domain = [
                ('id', '!=', contract.id),
                ('employee_id', '=', contract.employee_id.id),
                ('company_id', '=', contract.company_id.id),
                '|',
                ('state', 'in', ['open', 'close']),
                '&',
                ('state', '=', 'draft'),
                ('kanban_state', '=', 'done')  # replaces incoming
            ]
            if not contract.date_end:
                start_domain = []
                end_domain = ['|', ('date_end', '>=', contract.date_start), ('date_end', '=', False)]
            else:
                start_domain = [('date_start', '<=', contract.date_end)]
                end_domain = ['|', ('date_end', '>', contract.date_start), ('date_end', '=', False)]
            domain = Domain.AND([domain, start_domain, end_domain])
            if not self.search_count(domain):
                contract.write({'state': 'open'})



    def create_name(self, contract_type_id):
        if contract_type_id:
            contract_type = self.sudo().env['hr.contract.type'].browse(contract_type_id).contract_type
            contract = self.sudo().search([('contract_type_id.contract_type', '=', contract_type), ('sequence', '!=', False)], order='sequence desc', limit=1)
            sequence = contract.sequence + 1 if contract else 1
            suffix = ''
            if contract_type == 'hdld':
                suffix = '/HĐLĐ/NGSC'
            elif contract_type == 'hdtv':
                suffix = '/HĐTV/NGSC'
            elif contract_type == 'hdi':
                suffix = '/HĐTTS/NGSC'
            elif contract_type == 'hdctv':
                suffix = '/HĐCTV/NGSC'
            elif contract_type == 'hddtf':
                suffix = '/HĐĐT/NGSC'
            elif contract_type in ['hdtldtv', 'hdtldktv']:
                suffix = '/HDLD/NGS'
            elif contract_type == 'hdkv':
                suffix = '/HĐKV/NGSC'
            elif contract_type == 'plhdld':
                suffix = '/PLHĐLĐ/NGSC'
            elif contract_type == 'plhdtv':
                suffix = '/PLHĐTV/NGSC'
            name = str(fields.Date.Date.Date.context_today(self).year) + '_' + str(sequence).zfill(4) + suffix
            return name, sequence
        return '', 1


    @api.constrains('employee_id', 'date_start', 'date_end')
    def check_has_hr_contract(self):
        for rec in self:
            if self.search([
                ('employee_id', '=', rec.employee_id.id),
                ('employee_id', '!=', False),
                ('state', 'in', ['open', 'draft', 'close']),
                ('date_end', '=', rec.date_start),
                ('id', '!=', rec.id)]):
                raise UserError(f'Một nhân viên chỉ có thể có một hợp đồng cùng lúc. (Không tính hợp đồng nháp và hợp đồng đã hủy).\n\nNhân viên: {rec.employee_id.name}',)

    @api.model
    def create(self, vals):
        name, sequence = self.create_name(vals.get('contract_type_id', ''))
        vals.update({
            'name': name,
            'sequence': sequence,
        })
        res = super().create(vals)
        return res

    def write(self, vals):
        res = super().write(vals)
        for rec in self:
            if rec.state != 'draft' and self._context.get('import_file', ''):
                raise UserError('Chỉ được phép import update hợp đồng ở trạng thái mới')
            if rec.state == 'draft' and vals.get('contract_type_id'):
                name, sequence = rec.create_name(rec.contract_type_id.id)
                rec.write({
                    'name': name,
                    'sequence': sequence,
                })
        return res


class HrContractType(models.Model):
    _inherit = 'hr.contract.type'

    contract_type = fields.Selection([('hdkv', 'Hợp đồng khoán việc'),
                                      ('hddtf', 'Hợp đồng đào tạo Fresher'),
                                      ('plhdld', 'Phụ lục hợp đồng lao động'),
                                      ('hdld', 'Hợp đồng lao động'),
                                      ('hdctv', 'Hợp đồng CTV'),
                                      ('hdi', 'Hợp đồng Intern'),
                                      ('plhdtv', 'Phụ lục hợp đồng thử việc'),
                                      ('hdtldtv', 'VTB - HĐ thuê LĐ có thử việc'),
                                      ('hdtldktv', 'VTB - HĐ thuê LĐ không có thử việc'),
                                      ('hdtv', 'Hợp đồng Thử việc')], string='Loại hợp đồng', required=True)


class ConfirmCancelHrContractWizrad(models.TransientModel):
    _name = 'confirm.cancel.hr.contract.wizard'
    _description = 'popup chuyển thái hủy hợp đồng'


    contract_id = fields.Many2one('hr.contract', string='Hợp đồng', required=True)

    def action_confirm(self):
        self.contract_id.write({
            'state': 'cancel'
        })
        return {'type': 'ir.actions.act_window_close'}

    def action_cancel(self):
        return {'type': 'ir.actions.act_window_close'}

class PaymentBatch(models.Model):
    _name = 'payment.batch'
    _description = 'Đợt thanh toán'

    name = fields.Char(string='Đợt thanh toán')
    money = fields.Float(string='Số tiền')
    note = fields.Text(string='Ghi chú')
    hr_contract_id = fields.Many2one(comodel_name='hr.contract', string='Hợp đồng', ondelete='cascade', required=True)

class TrainingCost(models.Model):
    _name = 'training.cost'
    _description = 'Chi phí đào tạo'

    name = fields.Char(string='Tên chi phí đào tạo')
    sequence = fields.Integer(string='Thứ tự')
    content = fields.Char(string='Nội dung')
    unit_price = fields.Float(string='Đơn giá(VNĐ/3 tháng)')
    training_time = fields.Float(string='Thời gian đào tạo/học nghề(tháng)')
    amount = fields.Float(string='Tổng tiền(VNĐ)', related='unit_price')
    hr_contract_id = fields.Many2one(comodel_name='hr.contract', string='Hợp đồng', ondelete='cascade', required=True)


class ContractDate(models.Model):
    _name = 'contract.date'
    _description = 'Thời hạn hợp đồng'

    name = fields.Char(string='Tên', compute='_get_name', store=True)
    period = fields.Integer(string='Thời hạn', required=True)
    unit = fields.Selection([('day', 'Ngày'), ('month', 'Tháng'), ('year', 'Năm')], string='Đơn vị', required=True)

    @api.depends('period', 'unit')
    def _get_name(self):
        unit_selection = dict(self.fields_get(['unit'])['unit']['selection'])
        for rec in self:
            if rec.period and rec.unit:
                rec.name = f"{rec.period} {unit_selection.get(rec.unit, '')}"
            else:
                rec.name = 'Chưa thiết lập'


class ContractWarning(models.Model):
    _name = 'contract.warning'
    _description = 'Cảnh báo hợp đồng'

    name = fields.Char(string='Tên cảnh báo', required=True)
    contract_type_ids = fields.Many2many('hr.contract.type', string='Loại hợp đồng', required=True)
    advance_waring_period = fields.Integer('Thời hạn cảnh báo trước', required=True)