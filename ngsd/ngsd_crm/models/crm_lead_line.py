from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CrmLeadLine(models.Model):
    _name = 'crm.lead.line'
    _description = 'Thông tin sản phẩm'

    x_expected_ratio = fields.Float(string='Tỷ suất lợi nhuận', compute='_compute_x_expected_ratio', store=True)

    @api.depends('ngsd_revenue_taxed', 'ngsd_revenue')
    def _compute_x_expected_ratio(self):
        for rec in self:
            rec.x_expected_ratio = rec.ngsd_revenue_taxed / rec.ngsd_revenue if rec.ngsd_revenue else 0

    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        required=True,
        ondelete='cascade',
    )
    product_name = fields.Char(
        string='Sản phẩm',
    )
    type_id = fields.Many2one(
        comodel_name='crm.product.type',
        string='Loại',
    )
    categ_id = fields.Many2one(
        comodel_name='product.category',
        string='Danh mục',
        domain="[('product_type_id', '!=', False), ('product_type_id', '=', type_id)]"
    )
    supplier_id = fields.Many2one(
        comodel_name='res.partner',
        string='Đơn vị bán',
        domain="[('is_supplier', '=', True)]"
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Hãng',
        domain="[('is_manufacturer', '=', True)]"
    )
    estimated_value = fields.Float(string="Tổng giá trị dự án (Bao gồm cả VAT)", default=0)
    note = fields.Text(
    )
    description = fields.Text('Miêu tả')
    ngsd_revenue = fields.Float(
        string='Giá trị hợp đồng NGSC (Bao gồm cả VAT)', default=0
    )

    ngsd_revenue_taxed = fields.Float(
        string='Lợi nhuận dự kiến NGSC', default=0
    )

    @api.onchange('estimated_value')
    def onchange_estimated_value(self):
        if not self.ngsd_revenue:
            self.ngsd_revenue = self.estimated_value

    company_type = fields.Char(string='Loại Công ty', related='lead_id.company_id.company_type')
    currency_id = fields.Many2one('res.currency', related='lead_id.company_id.currency_id', string="Tiền tệ")
    total_revenue = fields.Float(
        string='Doanh thu', default=0
    )

    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     if not self.partner_id and len(self.move_id.line_ids) == 1:
    #         self.partner_id = self.move_id.main_partner_id
    #
