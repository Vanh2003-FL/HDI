# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import calendar
from dateutil.relativedelta import relativedelta
from math import copysign

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero, float_round


class ResSupplier(models.Model):
    _name = 'res.supplier'
    _description = 'Nhà cung cấp'

    name = fields.Char('Tên nhà cung cấp', required=1)


class RepairDetail(models.Model):
    _name = 'repair.detail'
    _description = 'Nâng cấp/Sửa chữa'

    sequence = fields.Integer('STT', required=1)
    name = fields.Char('Chi tiết', required=1)
    date = fields.Date('Ngày', required=1)
    amount = fields.Monetary('Chi phí', required=1)
    currency_id = fields.Many2one(related='asset_id.currency_id', string='Tỷ giá')
    asset_id = fields.Many2one('account.asset', required=1, ondelete='cascade', string='Tài sản')

    @api.onchange('sequence')
    def get_sequence(self):
        self.sequence = max(self.asset_id.repair_ids.mapped('sequence') or 0) + 1


class AccountAsset(models.Model):
    _inherit = 'account.asset'
    _rec_name = 'code'

    code = fields.Char('Mã tài sản')
    category = fields.Selection(selection=[('pc', 'Máy tính'), ('chair', 'Bàn ghế'), ('screen', 'Màn hình'), ('cabinet', 'Tủ'), ('phone', 'Điện thoại'), ('other', 'Khác')], string='Danh mục')
    category_other = fields.Char('Danh mục khác')
    partner_id = fields.Many2one('res.supplier', string='Nhà cung cấp')
    quality = fields.Char('Chất lượng')
    current_amount = fields.Monetary('Giá trị hiện tại', compute='_get_current_amount')

    @api.depends('original_value', 'repair_total_amount')
    def _get_current_amount(self):
        for rec in self:
            rec.current_amount = rec.original_value + rec.repair_total_amount

    invoice_number = fields.Char('Số hợp đồng/hoá đơn')

    employee_id = fields.Many2one('hr.employee', string='Tên người dùng', tracking=True)
    employee_barcode = fields.Char(related='employee_id.barcode', string='Mã nhân sự', store=True)
    current_location = fields.Char('Địa điểm hiện tại')
    project_id = fields.Many2one('project.project', string='Dự án phục vụ', context={'view_all_project': True})
    delivery_date = fields.Datetime('Ngày bàn giao')
    retrieve_date = fields.Datetime('Dự kiến thu hồi')

    repair_number = fields.Integer('Số lần nâng cấp/sửa chữa')
    repair_total_amount = fields.Monetary('Tổng chi phí nâng cấp/sửa chữa', compute='_get_repair_total_amount', store=True)
    state = fields.Selection(selection_add=[('dispensing', 'Đã thanh lý'), ('paused',), ('transfer_to_warehouse', 'Kho'), ('close',)])
    liquidation_date = fields.Date(string='Ngày thanh lý')

    @api.depends('repair_ids')
    def _get_repair_total_amount(self):
        for rec in self:
            rec.repair_total_amount = sum(rec.repair_ids.mapped('amount'))

    repair_ids = fields.One2many('repair.detail', 'asset_id', string='Nâng cấp/Sửa chữa')

    def validate(self):
        fields = [
            'method',
            'method_number',
            'method_period',
            'method_progress_factor',
            'salvage_value',
            'original_move_line_ids',
        ]
        ref_tracked_fields = self.env['account.asset'].fields_get(fields)
        self.write({'state': 'open'})
        for asset in self:
            tracked_fields = ref_tracked_fields.copy()
            if asset.method == 'linear':
                del (tracked_fields['method_progress_factor'])
            dummy, tracking_value_ids = asset._mail_track(tracked_fields, dict.fromkeys(fields))
            asset_name = {
                'purchase': (_('Asset created'), _('An asset has been created for this move:')),
                'sale': (_('Deferred revenue created'), _('A deferred revenue has been created for this move:')),
                'expense': (_('Deferred expense created'), _('A deferred expense has been created for this move:')),
            }[asset.asset_type]
            msg = asset_name[1] + ' <a href=# data-oe-model=account.asset data-oe-id=%d>%s</a>' % (asset.id, asset.name)
            asset.message_post(body=asset_name[0], tracking_value_ids=tracking_value_ids)

    def destroy_assets(self):
        for rec in self:
            rec.write({
                'state': 'close',
            })

    def transfer_to_warehouse(self):
        for rec in self:
            rec.write({
                'state': 'transfer_to_warehouse',
            })

    def button_liquidation(self):
        self.write({
            'state': 'dispensing',
            'liquidation_date': fields.Date.Date.context_today(self)
        })

    def write(self, vals):
        if vals.get('state') == 'transfer_to_warehouse':
            vals['current_location'] = 'Kho'
        return super(AccountAsset, self).write(vals)
