# -*- coding: utf-8 -*-
"""
HDI Contract & Payroll Management System
Advanced contract and payroll extensions with salary management, benefits tracking
Based on NGSD patterns with HDI enhancements
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class HdiContractType(models.Model):
    """Contract Type Management"""
    _name = 'hdi.contract.type'
    _description = 'HDI Contract Type'
    _order = 'sequence, name'
    
    name = fields.Char('Contract Type Name', required=True, translate=True)
    code = fields.Char('Code', required=True)
    sequence = fields.Integer('Sequence', default=10)
    
    description = fields.Text('Description')
    is_active = fields.Boolean('Active', default=True)
    
    # Contract Properties
    is_permanent = fields.Boolean('Permanent Contract', default=False)
    default_duration_months = fields.Integer('Default Duration (Months)', 
                                           help="Default contract duration for fixed-term contracts")
    probation_period_months = fields.Integer('Probation Period (Months)', default=2)
    notice_period_days = fields.Integer('Notice Period (Days)', default=30)
    
    # Benefits & Policies
    default_working_hours = fields.Float('Default Working Hours/Week', default=40.0)
    overtime_eligible = fields.Boolean('Overtime Eligible', default=True)
    bonus_eligible = fields.Boolean('Bonus Eligible', default=True)
    
    # Leave Entitlements
    annual_leave_days = fields.Integer('Annual Leave Days', default=15)
    sick_leave_days = fields.Integer('Sick Leave Days', default=30)
    maternity_leave_days = fields.Integer('Maternity Leave Days', default=90)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Contract type code must be unique!')
    ]


class HdiSalaryAdjustmentApproval(models.Model):
    """Approval record for salary adjustments"""
    _name = 'hdi.salary.adjustment.approval'
    _description = 'HDI Salary Adjustment Approval'

    adjustment_id = fields.Many2one('hdi.salary.adjustment', 'Salary Adjustment', required=True, ondelete='cascade')
    approver_user = fields.Many2one('res.users', 'Approver (User)', default=lambda self: self.env.user)
    approver_id = fields.Many2one('hr.employee', 'Approver (Employee)')
    approval_date = fields.Datetime('Approval Date', default=fields.Datetime.now)
    approval_level = fields.Integer('Approval Level', default=1)
    comment = fields.Text('Comment')


class HdiSalaryStructure(models.Model):
    """Salary Structure Management"""
    _name = 'hdi.salary.structure'
    _description = 'HDI Salary Structure'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'level_sequence, name'
    
    # Basic Information
    name = fields.Char('Structure Name', required=True, tracking=True)
    code = fields.Char('Code', required=True, tracking=True)
    level_sequence = fields.Integer('Level Sequence', default=1, tracking=True)
    
    # Structure Details
    grade = fields.Char('Grade/Band', tracking=True)
    level = fields.Char('Level', tracking=True)
    description = fields.Text('Description')
    
    # Salary Ranges
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                default=lambda self: self.env.company.currency_id, required=True)
    base_salary_min = fields.Monetary('Minimum Base Salary', currency_field='currency_id', tracking=True)
    base_salary_max = fields.Monetary('Maximum Base Salary', currency_field='currency_id', tracking=True)
    
    # Allowances & Benefits
    housing_allowance = fields.Monetary('Housing Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary('Transport Allowance', currency_field='currency_id')
    meal_allowance = fields.Monetary('Meal Allowance', currency_field='currency_id')
    phone_allowance = fields.Monetary('Phone Allowance', currency_field='currency_id')
    other_allowances = fields.Monetary('Other Allowances', currency_field='currency_id')
    
    # Performance & Bonuses
    performance_bonus_eligible = fields.Boolean('Performance Bonus Eligible', default=True)
    annual_bonus_percentage = fields.Float('Annual Bonus (%)', default=0.0, 
                                         help="Percentage of annual salary")
    kpi_bonus_eligible = fields.Boolean('KPI Bonus Eligible', default=True)
    
    # Benefits
    benefit_package_ids = fields.Many2many('hdi.benefit.package', 'salary_benefit_rel', 
                                         'salary_id', 'benefit_id', string='Benefit Packages')
    
    # Payroll Integration
    payroll_structure_id = fields.Many2one('hdi.payroll.structure', 'Payroll Structure',
                                         help="Payroll structure defines calculation rules for this salary structure")
    default_components_ids = fields.Many2many('hdi.payroll.component', 'salary_structure_component_rel',
                                           string='Default Payroll Components',
                                           help="Default components included in this salary structure")
    
    # Advanced Allowance Configuration
    include_housing_allowance = fields.Boolean('Housing Allowance', default=False)
    housing_allowance_rate = fields.Float('Housing Allowance Rate (%)', digits=(5, 2), default=15.0)
    housing_allowance_max = fields.Monetary('Max Housing Allowance', currency_field='currency_id')
    
    include_transport_allowance = fields.Boolean('Transport Allowance', default=False)
    transport_allowance_rate = fields.Float('Transport Allowance Rate (%)', digits=(5, 2), default=5.0)
    transport_allowance_max = fields.Monetary('Max Transport Allowance', currency_field='currency_id')
    
    include_meal_allowance = fields.Boolean('Meal Allowance', default=False)
    meal_allowance_rate = fields.Float('Meal Allowance Rate (%)', digits=(5, 2), default=10.0)
    meal_allowance_max = fields.Monetary('Max Meal Allowance', currency_field='currency_id')
    
    include_phone_allowance = fields.Boolean('Phone Allowance', default=False)
    phone_allowance_amount = fields.Monetary('Phone Allowance Amount', currency_field='currency_id')
    
    # Overtime Configuration
    overtime_eligible = fields.Boolean('Overtime Eligible', default=True)
    overtime_rate_weekday = fields.Float('Weekday Overtime Rate', digits=(5, 2), default=150.0)
    overtime_rate_weekend = fields.Float('Weekend Overtime Rate', digits=(5, 2), default=200.0)
    overtime_rate_holiday = fields.Float('Holiday Overtime Rate', digits=(5, 2), default=300.0)
    
    # Status
    is_active = fields.Boolean('Active', default=True, tracking=True)
    effective_date = fields.Date('Effective Date', default=fields.Date.today, tracking=True)
    
    # Related Records
    contract_ids = fields.One2many('hr.contract', 'hdi_salary_structure_id', string='Contracts')
    contracts_count = fields.Integer('Contracts Count', compute='_compute_contracts_count')
    
    @api.depends('contract_ids')
    def _compute_contracts_count(self):
        """Compute contracts count"""
        for record in self:
            record.contracts_count = len(record.contract_ids)
    
    @api.constrains('base_salary_min', 'base_salary_max')
    def _check_salary_range(self):
        """Validate salary range"""
        for record in self:
            if record.base_salary_min > record.base_salary_max:
                raise ValidationError("Minimum salary cannot be greater than maximum salary.")
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Salary structure code must be unique!')
    ]
    
    def calculate_total_compensation(self, base_salary):
        """Calculate total compensation package"""
        total = base_salary
        
        # Add allowances
        if self.include_housing_allowance:
            housing = min(base_salary * (self.housing_allowance_rate / 100), 
                         self.housing_allowance_max or float('inf'))
            total += housing
        
        if self.include_transport_allowance:
            transport = min(base_salary * (self.transport_allowance_rate / 100),
                           self.transport_allowance_max or float('inf'))
            total += transport
            
        if self.include_meal_allowance:
            meal = min(base_salary * (self.meal_allowance_rate / 100),
                      self.meal_allowance_max or float('inf'))
            total += meal
            
        if self.include_phone_allowance:
            total += self.phone_allowance_amount or 0
        
        return total
    
    def get_allowance_breakdown(self, base_salary):
        """Get detailed allowance breakdown"""
        breakdown = {
            'base_salary': base_salary,
            'housing_allowance': 0,
            'transport_allowance': 0,
            'meal_allowance': 0,
            'phone_allowance': 0,
            'total_allowances': 0,
            'total_compensation': base_salary
        }
        
        if self.include_housing_allowance:
            breakdown['housing_allowance'] = min(
                base_salary * (self.housing_allowance_rate / 100),
                self.housing_allowance_max or float('inf')
            )
        
        if self.include_transport_allowance:
            breakdown['transport_allowance'] = min(
                base_salary * (self.transport_allowance_rate / 100),
                self.transport_allowance_max or float('inf')
            )
        
        if self.include_meal_allowance:
            breakdown['meal_allowance'] = min(
                base_salary * (self.meal_allowance_rate / 100),
                self.meal_allowance_max or float('inf')
            )
        
        if self.include_phone_allowance:
            breakdown['phone_allowance'] = self.phone_allowance_amount or 0
        
        breakdown['total_allowances'] = (
            breakdown['housing_allowance'] + 
            breakdown['transport_allowance'] + 
            breakdown['meal_allowance'] + 
            breakdown['phone_allowance']
        )
        breakdown['total_compensation'] = base_salary + breakdown['total_allowances']
        
        return breakdown
    
    def calculate_overtime_pay(self, regular_hourly_rate, overtime_hours, overtime_type='weekday'):
        """Calculate overtime payment"""
        if not self.overtime_eligible:
            return 0.0
        
        if overtime_type == 'weekday':
            rate = self.overtime_rate_weekday
        elif overtime_type == 'weekend':
            rate = self.overtime_rate_weekend
        elif overtime_type == 'holiday':
            rate = self.overtime_rate_holiday
        else:
            rate = self.overtime_rate_weekday
        
        overtime_rate = regular_hourly_rate * (rate / 100)
        return overtime_hours * overtime_rate


class HdiBenefitPackage(models.Model):
    """Employee Benefit Package"""
    _name = 'hdi.benefit.package'
    _description = 'HDI Benefit Package'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Information
    name = fields.Char('Package Name', required=True, tracking=True)
    code = fields.Char('Code', required=True)
    description = fields.Html('Description')
    
    # Package Type
    package_type = fields.Selection([
        ('standard', 'Standard Package'),
        ('executive', 'Executive Package'),
        ('management', 'Management Package'),
        ('custom', 'Custom Package')
    ], string='Package Type', required=True, default='standard', tracking=True)
    
    # Health Benefits
    health_insurance = fields.Boolean('Health Insurance', default=True)
    health_insurance_coverage = fields.Selection([
        ('employee', 'Employee Only'),
        ('family', 'Employee + Family'),
        ('spouse', 'Employee + Spouse'),
        ('children', 'Employee + Children')
    ], string='Health Insurance Coverage', default='employee')
    health_insurance_amount = fields.Monetary('Health Insurance Amount', currency_field='currency_id')
    
    dental_insurance = fields.Boolean('Dental Insurance', default=False)
    dental_insurance_amount = fields.Monetary('Dental Insurance Amount', currency_field='currency_id')
    
    life_insurance = fields.Boolean('Life Insurance', default=True)
    life_insurance_coverage = fields.Monetary('Life Insurance Coverage', currency_field='currency_id')
    
    # Leave Benefits
    additional_leave_days = fields.Integer('Additional Leave Days', default=0)
    flexible_leave = fields.Boolean('Flexible Leave Policy', default=False)
    
    # Financial Benefits
    currency_id = fields.Many2one('res.currency', 'Currency', 
                                default=lambda self: self.env.company.currency_id, required=True)
    retirement_contribution = fields.Float('Retirement Contribution (%)', default=0.0)
    stock_options = fields.Boolean('Stock Options', default=False)
    stock_options_amount = fields.Integer('Stock Options (Shares)')
    
    # Perks & Additional Benefits
    gym_membership = fields.Boolean('Gym Membership', default=False)
    training_budget = fields.Monetary('Annual Training Budget', currency_field='currency_id')
    laptop_allowance = fields.Boolean('Laptop/Equipment Allowance', default=True)
    internet_allowance = fields.Monetary('Internet Allowance', currency_field='currency_id')
    
    # Travel & Transportation
    company_car = fields.Boolean('Company Car', default=False)
    fuel_allowance = fields.Monetary('Fuel Allowance', currency_field='currency_id')
    parking_allowance = fields.Monetary('Parking Allowance', currency_field='currency_id')
    
    # Flexible Benefits
    flexible_benefits_budget = fields.Monetary('Flexible Benefits Budget', currency_field='currency_id',
                                             help="Annual budget for flexible benefits selection")
    
    # Status
    is_active = fields.Boolean('Active', default=True, tracking=True)
    effective_date = fields.Date('Effective Date', default=fields.Date.today)
    
    # Eligibility
    eligible_contract_types = fields.Many2many('hdi.contract.type', 'benefit_contract_type_rel',
                                             'benefit_id', 'contract_type_id', 
                                             string='Eligible Contract Types')
    minimum_salary_level = fields.Monetary('Minimum Salary Level', currency_field='currency_id')
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Benefit package code must be unique!')
    ]


class HdiSalaryAdjustment(models.Model):
    """Salary Adjustment History"""
    _name = 'hdi.salary.adjustment'
    _description = 'HDI Salary Adjustment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'effective_date desc'
    
    # Basic Information
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, ondelete='cascade')
    contract_id = fields.Many2one('hr.contract', 'Contract', required=True, ondelete='cascade')
    
    # Adjustment Details
    adjustment_type = fields.Selection([
        ('promotion', 'Promotion'),
        ('annual_review', 'Annual Review'),
        ('performance', 'Performance Adjustment'),
        ('market_adjustment', 'Market Adjustment'),
        ('cost_of_living', 'Cost of Living'),
        ('merit_increase', 'Merit Increase'),
        ('correction', 'Correction'),
        ('other', 'Other')
    ], string='Adjustment Type', required=True, tracking=True)
    
    reason = fields.Text('Reason for Adjustment', required=True)
    
    # Salary Changes
    currency_id = fields.Many2one('res.currency', related='contract_id.currency_id', store=True)
    previous_salary = fields.Monetary('Previous Salary', currency_field='currency_id', required=True)
    new_salary = fields.Monetary('New Salary', currency_field='currency_id', required=True)
    adjustment_amount = fields.Monetary('Adjustment Amount', compute='_compute_adjustment', store=True)
    adjustment_percentage = fields.Float('Adjustment Percentage', compute='_compute_adjustment', store=True)
    
    # Structure Changes
    previous_structure_id = fields.Many2one('hdi.salary.structure', 'Previous Structure')
    new_structure_id = fields.Many2one('hdi.salary.structure', 'New Structure')
    
    # Timeline
    effective_date = fields.Date('Effective Date', required=True, tracking=True)
    review_date = fields.Date('Next Review Date')
    
    # Approval
    requested_by_id = fields.Many2one('hr.employee', 'Requested By', required=True, 
                                    default=lambda self: self.env.user.employee_id)
    approved_by_id = fields.Many2one('hr.employee', 'Approved By')
    approval_date = fields.Date('Approval Date')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted for Approval'),
        ('approved', 'Approved'),
        ('applied', 'Applied'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', required=True, tracking=True)

    # Multi-level approval
    required_approval_level = fields.Integer('Required Approval Level', default=1,
                                             help="Number of approvals required before applying")
    approval_count = fields.Integer('Approval Count', compute='_compute_approval_count', store=True)
    approval_ids = fields.One2many('hdi.salary.adjustment.approval', 'adjustment_id', string='Approvals')
    
    # Performance Data
    performance_rating = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory')
    ], string='Performance Rating')
    
    kpi_score = fields.Float('KPI Score')
    notes = fields.Html('Notes')
    
    @api.depends('previous_salary', 'new_salary')
    def _compute_adjustment(self):
        """Compute adjustment amount and percentage"""
        for record in self:
            record.adjustment_amount = record.new_salary - record.previous_salary
            if record.previous_salary > 0:
                record.adjustment_percentage = (record.adjustment_amount / record.previous_salary) * 100
            else:
                record.adjustment_percentage = 0.0
    
    def action_submit(self):
        """Submit for approval"""
        for record in self:
            if record.state == 'draft':
                record.state = 'submitted'

    @api.depends('approval_ids')
    def _compute_approval_count(self):
        for rec in self:
            rec.approval_count = len(rec.approval_ids)
    
    def action_approve(self):
        """Approve adjustment"""
        for record in self:
            if record.state == 'submitted' or record.state == 'under_review':
                # Prevent double approvals by same user
                exists = record.approval_ids.filtered(lambda a: a.approver_user and a.approver_user.id == self.env.uid)
                if exists:
                    raise UserError('You have already approved this adjustment.')

                # Only allow HR managers to approve
                if not self.env.user.has_group('hdi_hr.group_hdi_hr_manager'):
                    raise UserError('Only HR Managers may approve salary adjustments.')

                # Create an approval entry
                self.env['hdi.salary.adjustment.approval'].create({
                    'adjustment_id': record.id,
                    'approver_user': self.env.user.id,
                    'approver_id': self.env.user.employee_id.id if self.env.user.employee_id else False,
                    'comment': record.reason[:1024],
                })

                # If required approvals reached -> approved
                if record.approval_count >= (record.required_approval_level - 1):
                    record.state = 'approved'
                    record.approved_by_id = self.env.user.employee_id
                    record.approval_date = fields.Date.today()
                else:
                    record.state = 'under_review'
    
    def action_apply(self):
        """Apply the salary adjustment"""
        for record in self:
            if record.state == 'approved':
                # Update contract
                record.contract_id.write({
                    'wage': record.new_salary,
                    'hdi_salary_structure_id': record.new_structure_id.id if record.new_structure_id else record.contract_id.hdi_salary_structure_id.id,
                })
                record.state = 'applied'
                record.message_post(body=f"Salary adjustment applied. New salary: {record.new_salary}")

    def action_reject(self):
        for record in self:
            if record.state in ['submitted', 'under_review']:
                record.state = 'rejected'
                record.message_post(body=f"Salary adjustment rejected by {self.env.user.name}.")


# Extend HR Contract
class HrContract(models.Model):
    _inherit = 'hr.contract'
    
    # HDI Extensions
    hdi_contract_type_id = fields.Many2one('hdi.contract.type', 'HDI Contract Type')
    hdi_salary_structure_id = fields.Many2one('hdi.salary.structure', 'Salary Structure', tracking=True)
    
    # Contract Details
    contract_number = fields.Char('Contract Number', copy=False)
    probation_start_date = fields.Date('Probation Start Date')
    probation_end_date = fields.Date('Probation End Date')
    probation_passed = fields.Boolean('Probation Passed', default=False)
    
    # Salary Breakdown
    base_salary = fields.Monetary('Base Salary', currency_field='currency_id', tracking=True)
    housing_allowance = fields.Monetary('Housing Allowance', currency_field='currency_id')
    transport_allowance = fields.Monetary('Transport Allowance', currency_field='currency_id')
    meal_allowance = fields.Monetary('Meal Allowance', currency_field='currency_id')
    phone_allowance = fields.Monetary('Phone Allowance', currency_field='currency_id')
    other_allowances = fields.Monetary('Other Allowances', currency_field='currency_id')
    
    # Benefits
    benefit_package_ids = fields.Many2many('hdi.benefit.package', 'contract_benefit_rel', 
                                         'contract_id', 'benefit_id', string='Benefit Packages')
    
    # Performance & Reviews
    performance_bonus_eligible = fields.Boolean('Performance Bonus Eligible', default=True)
    kpi_bonus_eligible = fields.Boolean('KPI Bonus Eligible', default=True)
    last_review_date = fields.Date('Last Review Date')
    next_review_date = fields.Date('Next Review Date')
    
    # Adjustments History
    salary_adjustment_ids = fields.One2many('hdi.salary.adjustment', 'contract_id', 
                                          string='Salary Adjustments')
    
    # Computed Fields
    total_compensation = fields.Monetary('Total Compensation', compute='_compute_total_compensation', 
                                       store=True, currency_field='currency_id')
    
    @api.depends('base_salary', 'housing_allowance', 'transport_allowance', 'meal_allowance', 
                 'phone_allowance', 'other_allowances')
    def _compute_total_compensation(self):
        """Compute total compensation"""
        for record in self:
            record.total_compensation = (
                record.base_salary + record.housing_allowance + record.transport_allowance +
                record.meal_allowance + record.phone_allowance + record.other_allowances
            )
    
    @api.onchange('hdi_salary_structure_id')
    def _onchange_salary_structure(self):
        """Update salary and allowances based on structure"""
        if self.hdi_salary_structure_id:
            structure = self.hdi_salary_structure_id
            self.housing_allowance = structure.housing_allowance
            self.transport_allowance = structure.transport_allowance
            self.meal_allowance = structure.meal_allowance
            self.phone_allowance = structure.phone_allowance
            self.other_allowances = structure.other_allowances
            self.benefit_package_ids = [(6, 0, structure.benefit_package_ids.ids)]
    
    @api.onchange('hdi_contract_type_id')
    def _onchange_contract_type(self):
        """Update contract details based on type"""
        if self.hdi_contract_type_id:
            contract_type = self.hdi_contract_type_id
            if contract_type.probation_period_months and not self.probation_end_date:
                if self.date_start:
                    self.probation_end_date = self.date_start + relativedelta(months=contract_type.probation_period_months)
            
            if not contract_type.is_permanent and contract_type.default_duration_months:
                if self.date_start and not self.date_end:
                    self.date_end = self.date_start + relativedelta(months=contract_type.default_duration_months)
    
    def action_create_salary_adjustment(self):
        """Create salary adjustment"""
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Salary Adjustment',
            'res_model': 'hdi.salary.adjustment',
            'view_mode': 'form',
            'context': {
                'default_employee_id': self.employee_id.id,
                'default_contract_id': self.id,
                'default_previous_salary': self.wage,
                'default_previous_structure_id': self.hdi_salary_structure_id.id if self.hdi_salary_structure_id else False,
            },
            'target': 'new',
        }
    
    def action_complete_probation(self):
        """Complete probation period"""
        for record in self:
            if record.probation_end_date and fields.Date.today() >= record.probation_end_date:
                record.probation_passed = True
                record.message_post(body="Probation period completed successfully.")


# HdiPayrollComponent moved to hdi_payroll_components.py