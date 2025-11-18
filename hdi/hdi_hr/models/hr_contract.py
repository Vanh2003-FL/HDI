# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class HrContract(models.Model):
    _inherit = 'hr.contract'

    # HDI Contract Extensions
    hdi_contract_code = fields.Char(
        string='Mã hợp đồng HDI',
        help='Mã hợp đồng theo quy định HDI'
    )
    
    hdi_salary_grade = fields.Selection([
        ('1', 'Bậc 1'),
        ('2', 'Bậc 2'),
        ('3', 'Bậc 3'),
        ('4', 'Bậc 4'),
        ('5', 'Bậc 5'),
        ('6', 'Bậc 6'),
        ('7', 'Bậc 7'),
        ('8', 'Bậc 8'),
    ], string='Bậc lương HDI')
    
    hdi_probation_period = fields.Integer(
        string='Thời gian thử việc (tháng)',
        default=2,
        help='Số tháng thử việc theo quy định HDI'
    )
    
    hdi_bonus_kpi = fields.Monetary(
        string='Thưởng KPI tối đa',
        help='Mức thưởng KPI tối đa theo hợp đồng'
    )
    
    hdi_allowances = fields.One2many(
        'hdi.contract.allowance',
        'contract_id',
        string='Phụ cấp HDI'
    )
    
    # Override để bổ sung logic HDI
    @api.model
    def create(self, vals):
        # Auto generate HDI contract code
        if not vals.get('hdi_contract_code'):
            vals['hdi_contract_code'] = self.env['ir.sequence'].next_by_code('hdi.contract') or 'HDI/CT/0001'
        return super().create(vals)


class HdiContractAllowance(models.Model):
    _name = 'hdi.contract.allowance'
    _description = 'HDI Contract Allowances'
    
    contract_id = fields.Many2one('hr.contract', string='Hợp đồng', required=True, ondelete='cascade')
    name = fields.Char(string='Tên phụ cấp', required=True)
    allowance_type = fields.Selection([
        ('transport', 'Phụ cấp đi lại'),
        ('phone', 'Phụ cấp điện thoại'),
        ('meal', 'Phụ cấp ăn trưa'),
        ('housing', 'Phụ cấp nhà ở'),
        ('other', 'Phụ cấp khác'),
    ], string='Loại phụ cấp', required=True)
    amount = fields.Monetary(string='Số tiền', currency_field='currency_id', required=True)
    currency_id = fields.Many2one(related='contract_id.currency_id', store=True)
    note = fields.Text(string='Ghi chú')