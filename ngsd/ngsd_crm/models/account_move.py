from odoo import *
import json
from lxml import etree


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def _create_payment_vals_from_wizard(self):
        payment_vals = super()._create_payment_vals_from_wizard()
        if self._context.get('active_model') == 'account.move':
            payment_vals['x_contract_id'] = self.env[self._context.get('active_model')].browse(self._context.get('active_id')).contract_id.id
        return payment_vals


class AccountMove(models.Model):
    _inherit = 'account.move'

    newoice_date_due = fields.Date(related='invoice_date_due', string='Đến hạn')

    # @api.model
    # def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
    #     res = super().fields_view_get(view_id, view_type, toolbar, submenu)
    #     if view_type != 'tree':
    #         return res
    #     doc = etree.XML(res['arch'])
    #     for node in doc.xpath("//field[@name='activity_ids']"):
    #         modifiers = json.loads(node.get("modifiers", "{}"))
    #         modifiers['invisible'] = True
    #         modifiers['column_invisible'] = True
    #         node.set("modifiers", json.dumps(modifiers))
    #     for node in doc.xpath("//field[@name='invoice_date_due']"):
    #         modifiers = json.loads(node.get("modifiers", "{}"))
    #         modifiers['invisible'] = True
    #         modifiers['column_invisible'] = True
    #         node.set("modifiers", json.dumps(modifiers))
    #     for node in doc.xpath("//tree"):
    #         filter = etree.Element('field', {'name': 'invoice_date_due', 'widget': 'remaining_days', 'string': 'Đến hạn'})
    #         node.append(filter)
    #     res['arch'] = etree.tostring(doc, encoding='unicode')
    #     return res

    # x_contract_id = fields.Many2one(string='Hợp đồng', copy=False, readonly=True, comodel_name='x.sale.contract')
