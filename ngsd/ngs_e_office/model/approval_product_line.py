from odoo import fields, models, api
from odoo.exceptions import UserError
from odoo.addons.approvals.models.approval_category import CATEGORY_SELECTION


class ApprovalProductLine(models.Model):
    _inherit = 'approval.product.line'

    product_car_id = fields.Many2one(related='product_id', readonly=False)
    description = fields.Char(required=False)
    car_description = fields.Char(related='description', readonly=False)
    license_plate = fields.Char(related='product_id.license_plate')
    location_start = fields.Text(string='Điểm đón')
    location_end = fields.Text(string='Điểm đến')
    start_time = fields.Datetime(string='Thời gian đón')
    to_use = fields.Text(string='Mục đích sử dụng')
    desired_time = fields.Date(string='Thời gian mong muốn')

    @api.onchange('product_car_id')
    def change_product_car_id(self):
        self.product_id = self.product_car_id

    @api.onchange('car_description')
    def change_car_description(self):
        self.description = self.car_description

    def write(self, vals):
        vals_change_product = {}
        if 'product_id' in vals:
            vals_change_product = {r.id: r.product_id for r in self}
        vals_change_quantity = {}
        if 'quantity' in vals:
            vals_change_quantity = {r.id: r.quantity for r in self}
        res = super().write(vals)
        if vals_change_product:
            for rec in self:
                if rec.product_id != vals_change_product.get(rec.id, self.env['product.product']):
                    message = f'''Sản phẩm: {vals_change_product.get(rec.id).name} → {rec.product_id.name}'''
                    rec.approval_request_id.message_post(body=message)
        if vals_change_quantity:
            for rec in self:
                if rec.quantity != vals_change_quantity.get(rec.id, 0):
                    message = f'''Số lượng {rec.product_id.name}: {vals_change_quantity.get(rec.id)} → {rec.quantity}'''
                    rec.approval_request_id.message_post(body=message)
        return res

    @api.constrains('quantity', 'approval_request_id')
    def check_quantity(self):
        for rec in self:
            if rec.approval_request_id.approval_type == 'vpp' and rec.quantity <= 0:
                raise UserError('Số lượng sản phẩm phải lớn hơn 0!')
