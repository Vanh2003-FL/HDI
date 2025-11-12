from odoo import fields, models, api
from odoo.exceptions import UserError


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    en_service_type = fields.Selection(selection=[('car', 'Xe'), ('vpp', 'VPP'), ('other', 'Khác')], required=1, string='Loại dịch vụ', default='other')
    license_plate = fields.Char('Biển kiểm soát')
    vetc_payment_date = fields.Date('Thời gian nạp tiền VETC')
    vetc_payment_amount = fields.Float('Số tiền VETC cần nạp')
    body_contract_date = fields.Date('Thời hạn hợp đồng thân vỏ xe')
    tnds_insurance_date = fields.Date('Thời hạn bảo hiểm TNNS')
    registration_date = fields.Date('Thời hạn đăng kiểm')
    list_price = fields.Monetary()

