# -*- coding: utf-8 -*-
"""
HDI Payroll Components
Advanced payroll component management with earning/deduction structures
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from dateutil.relativedelta import relativedelta


class HdiPayrollComponent(models.Model):
    """Payroll Component Base Model"""
    _name = 'hdi.payroll.component'
    _description = 'HDI Payroll Component'
    _order = 'sequence, name'
    
    name = fields.Char('Component Name', required=True, translate=True)
    code = fields.Char('Component Code', required=True, size=20)
    sequence = fields.Integer('Sequence', default=10)
    
    component_type = fields.Selection([
        ('earning', 'Earning'),
        ('deduction', 'Deduction'),
        ('benefit', 'Benefit'),
        ('tax', 'Tax'),
        ('contribution', 'Contribution')
    ], string='Component Type', required=True, default='earning')
    
    category = fields.Selection([
        ('basic', 'Basic Salary'),
        ('allowance', 'Allowance'),
        ('overtime', 'Overtime'),
        ('bonus', 'Bonus'),
        ('commission', 'Commission'),
        ('reimbursement', 'Reimbursement'),
        ('social_insurance', 'Social Insurance'),
        ('tax_deduction', 'Tax Deduction'),
        ('loan_deduction', 'Loan Deduction'),
        ('advance_deduction', 'Advance Deduction'),
        ('disciplinary', 'Disciplinary Deduction'),
        ('other', 'Other')
    ], string='Category', required=True)
    
    # Calculation
    calculation_method = fields.Selection([
        ('fixed', 'Fixed Amount'),
        ('percentage', 'Percentage of Base'),
        ('hourly_rate', 'Hourly Rate'),
        ('formula', 'Custom Formula'),
        ('tiered', 'Tiered Calculation'),
        ('attendance_based', 'Attendance Based')
    ], string='Calculation Method', required=True, default='fixed')
    
    base_amount = fields.Monetary('Base Amount/Rate', currency_field='currency_id')
    percentage = fields.Float('Percentage (%)', digits=(5, 2))
    formula = fields.Text('Calculation Formula')
    
    # Base for Percentage Calculation
    percentage_base = fields.Selection([
        ('basic_salary', 'Basic Salary'),
        ('gross_salary', 'Gross Salary'),
        ('net_salary', 'Net Salary'),
        ('taxable_income', 'Taxable Income'),
        ('working_days', 'Working Days'),
        ('overtime_hours', 'Overtime Hours')
    ], string='Percentage Base')
    
    # Conditions
    is_mandatory = fields.Boolean('Mandatory', default=False, 
                                help="If checked, this component will be automatically included")
    is_taxable = fields.Boolean('Taxable', default=True,
                              help="Include in taxable income calculation")
    is_social_insurance_base = fields.Boolean('Social Insurance Base', default=True,
                                            help="Include in social insurance calculation")
    
    # Limits
    has_minimum_limit = fields.Boolean('Has Minimum Limit')
    minimum_amount = fields.Monetary('Minimum Amount', currency_field='currency_id')
    has_maximum_limit = fields.Boolean('Has Maximum Limit')
    maximum_amount = fields.Monetary('Maximum Amount', currency_field='currency_id')
    
    # Eligibility
    eligibility_criteria = fields.Text('Eligibility Criteria')
    department_ids = fields.Many2many('hr.department', string='Applicable Departments')
    job_ids = fields.Many2many('hr.job', string='Applicable Job Positions')
    
    # Accounting
    account_debit = fields.Many2one('account.account', 'Debit Account')
    account_credit = fields.Many2one('account.account', 'Credit Account')
    
    # Configuration
    is_active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', store=True)
    
    # Reporting
    appears_on_payslip = fields.Boolean('Appears on Payslip', default=True)
    payslip_group = fields.Selection([
        ('earnings', 'Earnings'),
        ('deductions', 'Deductions'),
        ('taxes', 'Taxes'),
        ('net_pay', 'Net Pay Information'),
        ('employer_costs', 'Employer Costs')
    ], string='Payslip Group')
    
    # Advanced Features
    proration_method = fields.Selection([
        ('none', 'No Proration'),
        ('daily', 'Daily Proration'),
        ('monthly', 'Monthly Proration'),
        ('attendance', 'Attendance Based')
    ], string='Proration Method', default='none')
    
    frequency = fields.Selection([
        ('monthly', 'Monthly'),
        ('quarterly', 'Quarterly'),
        ('annually', 'Annually'),
        ('one_time', 'One Time'),
        ('variable', 'Variable')
    ], string='Payment Frequency', default='monthly')
    
    # Tiered Calculation Lines
    tier_line_ids = fields.One2many('hdi.payroll.component.tier', 'component_id', 
                                   string='Tier Lines')
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure component code is unique"""
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Component code '{record.code}' already exists.")
    
    @api.constrains('percentage')
    def _check_percentage_range(self):
        """Validate percentage range"""
        for record in self:
            if record.calculation_method == 'percentage' and not (0 <= record.percentage <= 100):
                raise ValidationError("Percentage must be between 0 and 100.")
    
    def calculate_amount(self, contract, payroll_period=None, attendance_data=None):
        """Calculate component amount for given contract and period"""
        if self.calculation_method == 'fixed':
            return self._calculate_fixed_amount(contract, payroll_period)
        elif self.calculation_method == 'percentage':
            return self._calculate_percentage_amount(contract, payroll_period)
        elif self.calculation_method == 'hourly_rate':
            return self._calculate_hourly_amount(contract, attendance_data)
        elif self.calculation_method == 'formula':
            return self._calculate_formula_amount(contract, payroll_period)
        elif self.calculation_method == 'tiered':
            return self._calculate_tiered_amount(contract, payroll_period)
        elif self.calculation_method == 'attendance_based':
            return self._calculate_attendance_amount(contract, attendance_data)
        return 0.0
    
    def _calculate_fixed_amount(self, contract, payroll_period):
        """Calculate fixed amount with proration if applicable"""
        amount = self.base_amount
        if self.proration_method != 'none' and payroll_period:
            # Apply proration logic here
            pass
        return self._apply_limits(amount)
    
    def _calculate_percentage_amount(self, contract, payroll_period):
        """Calculate percentage-based amount"""
        base_value = self._get_percentage_base_value(contract, payroll_period)
        amount = base_value * (self.percentage / 100)
        return self._apply_limits(amount)
    
    def _calculate_tiered_amount(self, contract, payroll_period):
        """Calculate tiered amount based on tier lines"""
        base_value = self._get_percentage_base_value(contract, payroll_period)
        total_amount = 0.0
        
        for tier in self.tier_line_ids.sorted('sequence'):
            if base_value > tier.threshold_from:
                applicable_amount = min(base_value, tier.threshold_to or float('inf')) - tier.threshold_from
                if applicable_amount > 0:
                    if tier.calculation_type == 'percentage':
                        total_amount += applicable_amount * (tier.rate / 100)
                    else:  # fixed
                        total_amount += tier.rate
        
        return self._apply_limits(total_amount)
    
    def _get_percentage_base_value(self, contract, payroll_period):
        """Get base value for percentage calculation"""
        if self.percentage_base == 'basic_salary':
            return contract.wage
        elif self.percentage_base == 'gross_salary':
            # Calculate gross salary including allowances
            gross = contract.wage
            if hasattr(contract, 'housing_allowance'):
                gross += contract.housing_allowance or 0
            # Add other allowances...
            return gross
        # Add other base calculations...
        return contract.wage
    
    def _apply_limits(self, amount):
        """Apply minimum and maximum limits"""
        if self.has_minimum_limit and amount < self.minimum_amount:
            amount = self.minimum_amount
        if self.has_maximum_limit and amount > self.maximum_amount:
            amount = self.maximum_amount
        return amount
    
    def _calculate_hourly_amount(self, contract, attendance_data):
        """Calculate hourly-based amount"""
        if not attendance_data:
            return 0.0
        hours = attendance_data.get('total_hours', 0)
        return hours * self.base_amount
    
    def _calculate_attendance_amount(self, contract, attendance_data):
        """Calculate attendance-based amount"""
        if not attendance_data:
            return 0.0
        
        attendance_rate = attendance_data.get('attendance_percentage', 100) / 100
        base_amount = self.base_amount or contract.wage
        return base_amount * attendance_rate


class HdiPayrollComponentTier(models.Model):
    """Payroll Component Tier for Tiered Calculations"""
    _name = 'hdi.payroll.component.tier'
    _description = 'HDI Payroll Component Tier'
    _order = 'component_id, sequence'
    
    component_id = fields.Many2one('hdi.payroll.component', 'Component', ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    name = fields.Char('Tier Name', required=True)
    threshold_from = fields.Monetary('From Amount', currency_field='currency_id', required=True)
    threshold_to = fields.Monetary('To Amount', currency_field='currency_id')
    
    calculation_type = fields.Selection([
        ('percentage', 'Percentage'),
        ('fixed', 'Fixed Amount')
    ], string='Calculation Type', required=True, default='percentage')
    
    rate = fields.Float('Rate', required=True, digits=(12, 4))
    
    currency_id = fields.Many2one('res.currency', related='component_id.currency_id')
    
    @api.constrains('threshold_from', 'threshold_to')
    def _check_thresholds(self):
        """Validate threshold values"""
        for record in self:
            if record.threshold_to and record.threshold_from >= record.threshold_to:
                raise ValidationError("'From Amount' must be less than 'To Amount'.")


class HdiPayrollRule(models.Model):
    """Payroll Rule - Groups components and defines calculation order"""
    _name = 'hdi.payroll.rule'
    _description = 'HDI Payroll Rule'
    _order = 'sequence, name'
    
    name = fields.Char('Rule Name', required=True, translate=True)
    code = fields.Char('Rule Code', required=True, size=20)
    sequence = fields.Integer('Sequence', default=10)
    
    rule_type = fields.Selection([
        ('basic', 'Basic Earnings'),
        ('allowance', 'Allowances'),
        ('overtime', 'Overtime'),
        ('bonus', 'Bonuses'),
        ('gross_calculation', 'Gross Calculation'),
        ('deduction', 'Deductions'),
        ('tax_calculation', 'Tax Calculation'),
        ('net_calculation', 'Net Calculation')
    ], string='Rule Type', required=True)
    
    component_ids = fields.Many2many('hdi.payroll.component', string='Components')
    
    # Conditions
    condition = fields.Text('Condition (Python Expression)',
                          help="Python expression that must be True for rule to apply")
    
    # Calculation
    calculation_formula = fields.Text('Calculation Formula',
                                    help="Python formula for calculation")
    
    # Configuration
    is_active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    
    appears_on_payslip = fields.Boolean('Appears on Payslip', default=True)
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure rule code is unique"""
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Rule code '{record.code}' already exists.")


class HdiPayrollStructure(models.Model):
    """Payroll Structure - Defines complete payroll calculation"""
    _name = 'hdi.payroll.structure'
    _description = 'HDI Payroll Structure'
    
    name = fields.Char('Structure Name', required=True, translate=True)
    code = fields.Char('Structure Code', required=True, size=20)
    
    # Rules
    rule_ids = fields.Many2many('hdi.payroll.rule', string='Payroll Rules',
                               help="Rules will be applied in sequence order")
    
    # Default Components
    default_component_ids = fields.Many2many('hdi.payroll.component', 
                                           'structure_component_rel',
                                           string='Default Components')
    
    # Configuration
    is_active = fields.Boolean('Active', default=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    
    # Salary Structures using this payroll structure
    salary_structure_ids = fields.One2many('hdi.salary.structure', 'payroll_structure_id',
                                         string='Salary Structures')
    
    @api.constrains('code')
    def _check_code_unique(self):
        """Ensure structure code is unique"""
        for record in self:
            if self.search_count([('code', '=', record.code), ('id', '!=', record.id)]) > 0:
                raise ValidationError(f"Structure code '{record.code}' already exists.")


class HdiEmployeePayrollComponent(models.Model):
    """Employee-specific Payroll Components"""
    _name = 'hdi.employee.payroll.component'
    _description = 'HDI Employee Payroll Component'
    _rec_name = 'component_id'
    
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, ondelete='cascade')
    component_id = fields.Many2one('hdi.payroll.component', 'Component', required=True)
    
    # Override Values
    custom_amount = fields.Monetary('Custom Amount', currency_field='currency_id',
                                  help="Override default component amount")
    custom_percentage = fields.Float('Custom Percentage (%)', digits=(5, 2),
                                   help="Override default percentage")
    
    # Validity Period
    date_from = fields.Date('Valid From', required=True, default=fields.Date.today)
    date_to = fields.Date('Valid To')
    
    # Status
    is_active = fields.Boolean('Active', default=True)
    is_temporary = fields.Boolean('Temporary Component', default=False,
                                help="Component will be automatically removed after date_to")
    
    # Reason
    reason = fields.Text('Reason for Override')
    approved_by_id = fields.Many2one('hr.employee', 'Approved By')
    
    currency_id = fields.Many2one('res.currency', related='employee_id.company_id.currency_id')
    
    @api.constrains('date_from', 'date_to')
    def _check_date_validity(self):
        """Validate date range"""
        for record in self:
            if record.date_to and record.date_from > record.date_to:
                raise ValidationError("'Valid From' date must be before 'Valid To' date.")
    
    def calculate_amount(self, contract, payroll_period=None, attendance_data=None):
        """Calculate component amount with employee-specific overrides"""
        if self.custom_amount:
            return self.custom_amount
        elif self.custom_percentage:
            # Use custom percentage with component's base calculation
            component = self.component_id
            original_percentage = component.percentage
            component.percentage = self.custom_percentage
            amount = component.calculate_amount(contract, payroll_period, attendance_data)
            component.percentage = original_percentage  # Restore original
            return amount
        else:
            return self.component_id.calculate_amount(contract, payroll_period, attendance_data)