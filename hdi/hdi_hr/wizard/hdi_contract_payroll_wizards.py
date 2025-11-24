# -*- coding: utf-8 -*-
"""
HDI Contract & Payroll Wizards
Advanced wizards for salary adjustments, contract management, and payroll processing
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class HdiSalaryAdjustmentWizard(models.TransientModel):
    """Salary Adjustment Wizard"""
    _name = 'hdi.salary.adjustment.wizard'
    _description = 'HDI Salary Adjustment Wizard'
    
    # Selection Mode
    selection_mode = fields.Selection([
        ('single', 'Single Employee'),
        ('multiple', 'Multiple Employees'),
        ('department', 'By Department'),
        ('job_position', 'By Job Position')
    ], string='Selection Mode', default='single', required=True)
    
    # Single Employee
    employee_id = fields.Many2one('hr.employee', 'Employee')
    contract_id = fields.Many2one('hr.contract', 'Contract')
    
    # Multiple Selection
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_ids = fields.Many2many('hr.department', string='Departments')
    job_ids = fields.Many2many('hr.job', string='Job Positions')
    
    # Adjustment Details
    adjustment_type = fields.Selection([
        ('promotion', 'Promotion'),
        ('annual_review', 'Annual Review'),
        ('performance', 'Performance Adjustment'),
        ('market_adjustment', 'Market Adjustment'),
        ('cost_of_living', 'Cost of Living'),
        ('merit_increase', 'Merit Increase'),
        ('correction', 'Correction'),
        ('mass_adjustment', 'Mass Adjustment')
    ], string='Adjustment Type', required=True, default='annual_review')
    
    adjustment_method = fields.Selection([
        ('percentage', 'Percentage Increase'),
        ('fixed_amount', 'Fixed Amount'),
        ('new_salary', 'New Salary Amount'),
        ('structure_change', 'Salary Structure Change')
    ], string='Adjustment Method', required=True, default='percentage')
    
    # Adjustment Values
    percentage_increase = fields.Float('Percentage Increase (%)', default=0.0)
    fixed_amount = fields.Monetary('Fixed Amount Increase', currency_field='currency_id')
    new_structure_id = fields.Many2one('hdi.salary.structure', 'New Salary Structure')
    
    # Common Fields
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    effective_date = fields.Date('Effective Date', required=True, default=fields.Date.today)
    reason = fields.Text('Reason for Adjustment', required=True)
    
    # Performance Data
    performance_rating = fields.Selection([
        ('outstanding', 'Outstanding'),
        ('exceeds', 'Exceeds Expectations'),
        ('meets', 'Meets Expectations'),
        ('below', 'Below Expectations'),
        ('unsatisfactory', 'Unsatisfactory')
    ], string='Performance Rating')
    
    # Preview
    preview_lines = fields.One2many('hdi.salary.adjustment.wizard.line', 'wizard_id', 
                                   string='Preview Adjustments')
    
    @api.onchange('selection_mode')
    def _onchange_selection_mode(self):
        """Clear fields when selection mode changes"""
        self.employee_id = False
        self.employee_ids = [(5, 0, 0)]
        self.department_ids = [(5, 0, 0)]
        self.job_ids = [(5, 0, 0)]
        self.preview_lines = [(5, 0, 0)]
    
    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """Update contract when employee changes"""
        if self.employee_id:
            contract = self.env['hr.contract'].search([
                ('employee_id', '=', self.employee_id.id),
                ('state', '=', 'open')
            ], limit=1)
            self.contract_id = contract.id if contract else False
    
    def action_preview_adjustments(self):
        """Preview salary adjustments before creating"""
        self.preview_lines = [(5, 0, 0)]  # Clear existing lines
        employees = self._get_selected_employees()
        
        preview_vals = []
        for employee in employees:
            contract = self._get_employee_contract(employee)
            if not contract:
                continue
                
            current_salary = contract.wage
            new_salary = self._calculate_new_salary(current_salary)
            
            preview_vals.append({
                'wizard_id': self.id,
                'employee_id': employee.id,
                'contract_id': contract.id,
                'current_salary': current_salary,
                'new_salary': new_salary,
                'adjustment_amount': new_salary - current_salary,
                'adjustment_percentage': ((new_salary - current_salary) / current_salary * 100) if current_salary > 0 else 0,
            })
        
        self.preview_lines = [(0, 0, vals) for vals in preview_vals]
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Adjustment Preview',
            'res_model': 'hdi.salary.adjustment.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def action_create_adjustments(self):
        """Create salary adjustments"""
        if not self.preview_lines:
            raise UserError("Please preview adjustments first.")
        
        adjustments_created = []
        for line in self.preview_lines:
            if line.selected:
                adjustment_vals = {
                    'employee_id': line.employee_id.id,
                    'contract_id': line.contract_id.id,
                    'adjustment_type': self.adjustment_type,
                    'reason': self.reason,
                    'previous_salary': line.current_salary,
                    'new_salary': line.new_salary,
                    'effective_date': self.effective_date,
                    'performance_rating': self.performance_rating,
                    'requested_by_id': self.env.user.employee_id.id,
                }
                
                if self.new_structure_id:
                    adjustment_vals.update({
                        'previous_structure_id': line.contract_id.hdi_salary_structure_id.id,
                        'new_structure_id': self.new_structure_id.id,
                    })
                
                adjustment = self.env['hdi.salary.adjustment'].create(adjustment_vals)
                adjustments_created.append(adjustment.id)
        
        if not adjustments_created:
            raise UserError("No adjustments were selected for creation.")
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Created Salary Adjustments',
            'res_model': 'hdi.salary.adjustment',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', adjustments_created)],
        }
    
    def _get_selected_employees(self):
        """Get employees based on selection mode"""
        if self.selection_mode == 'single':
            return self.employee_id
        elif self.selection_mode == 'multiple':
            return self.employee_ids
        elif self.selection_mode == 'department':
            return self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)])
        elif self.selection_mode == 'job_position':
            return self.env['hr.employee'].search([('job_id', 'in', self.job_ids.ids)])
        return self.env['hr.employee']
    
    def _get_employee_contract(self, employee):
        """Get active contract for employee"""
        return self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open')
        ], limit=1)
    
    def _calculate_new_salary(self, current_salary):
        """Calculate new salary based on adjustment method"""
        if self.adjustment_method == 'percentage':
            return current_salary * (1 + self.percentage_increase / 100)
        elif self.adjustment_method == 'fixed_amount':
            return current_salary + self.fixed_amount
        elif self.adjustment_method == 'new_salary':
            return self.fixed_amount  # Using fixed_amount field for new salary
        elif self.adjustment_method == 'structure_change':
            if self.new_structure_id:
                # Use minimum of new structure range or keep current if within range
                min_sal = self.new_structure_id.base_salary_min
                max_sal = self.new_structure_id.base_salary_max
                if min_sal <= current_salary <= max_sal:
                    return current_salary
                else:
                    return min_sal
            return current_salary
        return current_salary


class HdiSalaryAdjustmentWizardLine(models.TransientModel):
    """Salary Adjustment Wizard Line"""
    _name = 'hdi.salary.adjustment.wizard.line'
    _description = 'HDI Salary Adjustment Wizard Line'
    
    wizard_id = fields.Many2one('hdi.salary.adjustment.wizard', 'Wizard', ondelete='cascade')
    selected = fields.Boolean('Select', default=True)
    
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True)
    
    current_salary = fields.Monetary('Current Salary', currency_field='currency_id', readonly=True)
    new_salary = fields.Monetary('New Salary', currency_field='currency_id')
    adjustment_amount = fields.Monetary('Adjustment Amount', currency_field='currency_id', readonly=True)
    adjustment_percentage = fields.Float('Adjustment %', readonly=True, digits=(5, 2))
    
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')
    
    @api.onchange('new_salary')
    def _onchange_new_salary(self):
        """Recalculate adjustment when new salary changes"""
        if self.current_salary and self.new_salary:
            self.adjustment_amount = self.new_salary - self.current_salary
            if self.current_salary > 0:
                self.adjustment_percentage = (self.adjustment_amount / self.current_salary) * 100


class HdiContractRenewalWizard(models.TransientModel):
    """Contract Renewal Wizard"""
    _name = 'hdi.contract.renewal.wizard'
    _description = 'HDI Contract Renewal Wizard'
    
    contract_id = fields.Many2one('hr.contract', 'Current Contract', required=True)
    employee_id = fields.Many2one('hr.employee', related='contract_id.employee_id', readonly=True)
    
    # New Contract Details
    new_start_date = fields.Date('New Start Date', required=True)
    new_end_date = fields.Date('New End Date')
    contract_type_id = fields.Many2one('hdi.contract.type', 'Contract Type', required=True)
    
    # Salary Details
    keep_salary = fields.Boolean('Keep Current Salary', default=True)
    new_wage = fields.Monetary('New Salary', currency_field='currency_id')
    salary_structure_id = fields.Many2one('hdi.salary.structure', 'Salary Structure')
    
    # Benefits
    keep_benefits = fields.Boolean('Keep Current Benefits', default=True)
    benefit_package_ids = fields.Many2many('hdi.benefit.package', string='Benefit Packages')
    
    currency_id = fields.Many2one('res.currency', related='contract_id.currency_id')
    
    @api.onchange('keep_salary')
    def _onchange_keep_salary(self):
        """Update salary fields"""
        if self.keep_salary and self.contract_id:
            self.new_wage = self.contract_id.wage
            self.salary_structure_id = self.contract_id.hdi_salary_structure_id
    
    @api.onchange('keep_benefits')
    def _onchange_keep_benefits(self):
        """Update benefit fields"""
        if self.keep_benefits and self.contract_id:
            self.benefit_package_ids = [(6, 0, self.contract_id.benefit_package_ids.ids)]
    
    def action_renew_contract(self):
        """Create new contract and close current one"""
        if not self.contract_id:
            raise UserError("No contract selected for renewal.")
        
        # Close current contract
        self.contract_id.write({
            'date_end': self.new_start_date - timedelta(days=1),
            'state': 'close'
        })
        
        # Create new contract
        new_contract_vals = {
            'name': f"{self.employee_id.name} - Renewed Contract",
            'employee_id': self.employee_id.id,
            'date_start': self.new_start_date,
            'date_end': self.new_end_date,
            'hdi_contract_type_id': self.contract_type_id.id,
            'wage': self.new_wage,
            'hdi_salary_structure_id': self.salary_structure_id.id,
            'benefit_package_ids': [(6, 0, self.benefit_package_ids.ids)],
            'state': 'draft',
        }
        
        # Copy relevant fields from old contract
        fields_to_copy = ['job_id', 'department_id', 'resource_calendar_id', 'working_hours']
        for field in fields_to_copy:
            if hasattr(self.contract_id, field):
                new_contract_vals[field] = self.contract_id[field].id if hasattr(self.contract_id[field], 'id') else self.contract_id[field]
        
        new_contract = self.env['hr.contract'].create(new_contract_vals)
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Renewed Contract',
            'res_model': 'hr.contract',
            'res_id': new_contract.id,
            'view_mode': 'form',
            'target': 'current',
        }


class HdiBenefitEnrollmentWizard(models.TransientModel):
    """Benefit Enrollment Wizard"""
    _name = 'hdi.benefit.enrollment.wizard'
    _description = 'HDI Benefit Enrollment Wizard'
    
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', required=True)
    
    enrollment_type = fields.Selection([
        ('new_hire', 'New Hire Enrollment'),
        ('annual_enrollment', 'Annual Open Enrollment'), 
        ('life_event', 'Life Event Change'),
        ('promotion', 'Promotion/Role Change')
    ], string='Enrollment Type', required=True, default='new_hire')
    
    effective_date = fields.Date('Effective Date', required=True, default=fields.Date.today)
    
    # Available Benefits
    available_package_ids = fields.Many2many('hdi.benefit.package', 
                                          compute='_compute_available_packages',
                                          string='Available Packages')
    
    # Selected Benefits
    selected_package_ids = fields.Many2many('hdi.benefit.package', 
                                         'wizard_benefit_rel', 
                                         'wizard_id', 'package_id',
                                         string='Selected Packages')
    
    # Health Insurance Details
    health_coverage = fields.Selection([
        ('employee', 'Employee Only'),
        ('family', 'Employee + Family'),
        ('spouse', 'Employee + Spouse'),
        ('children', 'Employee + Children')
    ], string='Health Insurance Coverage')
    
    # Dependents
    dependent_count = fields.Integer('Number of Dependents', default=0)
    spouse_coverage = fields.Boolean('Include Spouse')
    children_coverage = fields.Boolean('Include Children')
    
    # Flexible Benefits
    flexible_budget = fields.Monetary('Flexible Benefits Budget', currency_field='currency_id')
    flexible_selections = fields.One2many('hdi.benefit.enrollment.line', 'wizard_id', 
                                        string='Flexible Benefit Selections')
    
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    @api.depends('contract_id')
    def _compute_available_packages(self):
        """Compute available benefit packages"""
        for wizard in self:
            if wizard.contract_id and wizard.contract_id.hdi_salary_structure_id:
                structure = wizard.contract_id.hdi_salary_structure_id
                wizard.available_package_ids = structure.benefit_package_ids
            else:
                # Get all active packages
                wizard.available_package_ids = self.env['hdi.benefit.package'].search([('is_active', '=', True)])
    
    def action_enroll_benefits(self):
        """Process benefit enrollment"""
        if not self.contract_id:
            raise UserError("Contract is required for benefit enrollment.")
        
        # Update contract with selected benefits
        self.contract_id.write({
            'benefit_package_ids': [(6, 0, self.selected_package_ids.ids)]
        })
        
        # Create enrollment record
        enrollment_vals = {
            'employee_id': self.employee_id.id,
            'contract_id': self.contract_id.id,
            'enrollment_type': self.enrollment_type,
            'effective_date': self.effective_date,
            'health_coverage': self.health_coverage,
            'dependent_count': self.dependent_count,
            'selected_packages': [(6, 0, self.selected_package_ids.ids)],
        }
        
        # Note: You might want to create a separate model for enrollment history
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Contract Updated',
            'res_model': 'hr.contract',
            'res_id': self.contract_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


class HdiBenefitEnrollmentLine(models.TransientModel):
    """Benefit Enrollment Line for Flexible Benefits"""
    _name = 'hdi.benefit.enrollment.line'
    _description = 'HDI Benefit Enrollment Line'
    
    wizard_id = fields.Many2one('hdi.benefit.enrollment.wizard', 'Wizard', ondelete='cascade')
    
    benefit_type = fields.Selection([
        ('gym', 'Gym Membership'),
        ('transport', 'Transport Allowance'),
        ('meal', 'Meal Vouchers'),
        ('training', 'Training Courses'),
        ('childcare', 'Childcare Support'),
        ('other', 'Other')
    ], string='Benefit Type', required=True)
    
    description = fields.Char('Description')
    amount = fields.Monetary('Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')


class HdiPayrollSimulationWizard(models.TransientModel):
    """Payroll Simulation Wizard"""
    _name = 'hdi.payroll.simulation.wizard'
    _description = 'HDI Payroll Simulation Wizard'
    
    # Selection
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    department_ids = fields.Many2many('hr.department', string='Departments')
    
    # Period
    date_from = fields.Date('From Date', required=True, default=lambda self: fields.Date.today().replace(day=1))
    date_to = fields.Date('To Date', required=True, 
                         default=lambda self: (fields.Date.today().replace(day=1) + relativedelta(months=1) - timedelta(days=1)))
    
    # Simulation Parameters
    include_overtime = fields.Boolean('Include Overtime', default=True)
    include_bonuses = fields.Boolean('Include Bonuses', default=True)
    tax_simulation = fields.Boolean('Apply Tax Calculation', default=True)
    
    # Results
    simulation_lines = fields.One2many('hdi.payroll.simulation.line', 'wizard_id', 
                                     string='Simulation Results', readonly=True)
    
    total_gross = fields.Monetary('Total Gross Salary', compute='_compute_totals', 
                                currency_field='currency_id', store=True)
    total_deductions = fields.Monetary('Total Deductions', compute='_compute_totals', 
                                     currency_field='currency_id', store=True)
    total_net = fields.Monetary('Total Net Salary', compute='_compute_totals', 
                              currency_field='currency_id', store=True)
    
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    @api.depends('simulation_lines.gross_salary', 'simulation_lines.total_deductions', 'simulation_lines.net_salary')
    def _compute_totals(self):
        """Compute total amounts"""
        for wizard in self:
            wizard.total_gross = sum(line.gross_salary for line in wizard.simulation_lines)
            wizard.total_deductions = sum(line.total_deductions for line in wizard.simulation_lines)
            wizard.total_net = sum(line.net_salary for line in wizard.simulation_lines)
    
    def action_run_simulation(self):
        """Run payroll simulation"""
        # Clear existing results
        self.simulation_lines = [(5, 0, 0)]
        
        employees = self._get_employees_for_simulation()
        simulation_vals = []
        
        for employee in employees:
            contract = self._get_employee_contract(employee)
            if not contract:
                continue
            
            # Calculate gross salary
            gross_salary = self._calculate_gross_salary(contract)
            
            # Calculate deductions
            deductions = self._calculate_deductions(contract, gross_salary)
            
            # Calculate net salary
            net_salary = gross_salary - deductions
            
            simulation_vals.append({
                'wizard_id': self.id,
                'employee_id': employee.id,
                'contract_id': contract.id,
                'gross_salary': gross_salary,
                'total_deductions': deductions,
                'net_salary': net_salary,
            })
        
        self.simulation_lines = [(0, 0, vals) for vals in simulation_vals]
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Payroll Simulation Results',
            'res_model': 'hdi.payroll.simulation.wizard',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }
    
    def _get_employees_for_simulation(self):
        """Get employees for simulation"""
        if self.employee_ids:
            return self.employee_ids
        elif self.department_ids:
            return self.env['hr.employee'].search([('department_id', 'in', self.department_ids.ids)])
        else:
            return self.env['hr.employee'].search([])
    
    def _get_employee_contract(self, employee):
        """Get active contract for employee"""
        return self.env['hr.contract'].search([
            ('employee_id', '=', employee.id),
            ('state', '=', 'open'),
            ('date_start', '<=', self.date_to),
            '|', ('date_end', '=', False), ('date_end', '>=', self.date_from)
        ], limit=1)
    
    def _calculate_gross_salary(self, contract):
        """Calculate gross salary including allowances"""
        gross = contract.wage
        if hasattr(contract, 'housing_allowance'):
            gross += contract.housing_allowance or 0
        if hasattr(contract, 'transport_allowance'):
            gross += contract.transport_allowance or 0
        if hasattr(contract, 'meal_allowance'):
            gross += contract.meal_allowance or 0
        if hasattr(contract, 'phone_allowance'):
            gross += contract.phone_allowance or 0
        if hasattr(contract, 'other_allowances'):
            gross += contract.other_allowances or 0
        return gross
    
    def _calculate_deductions(self, contract, gross_salary):
        """Calculate total deductions"""
        deductions = 0.0
        
        # Social Insurance (8%)
        deductions += gross_salary * 0.08
        
        # Health Insurance (1.5%)
        deductions += gross_salary * 0.015
        
        # Unemployment Insurance (1%)
        deductions += gross_salary * 0.01
        
        # Personal Income Tax (simplified calculation)
        if self.tax_simulation:
            taxable_income = gross_salary - (gross_salary * 0.105)  # After social insurance
            if taxable_income > 11000000:  # Tax threshold
                deductions += (taxable_income - 11000000) * 0.05  # 5% tax rate (simplified)
        
        return deductions


class HdiPayrollSimulationLine(models.TransientModel):
    """Payroll Simulation Line"""
    _name = 'hdi.payroll.simulation.line'
    _description = 'HDI Payroll Simulation Line'
    
    wizard_id = fields.Many2one('hdi.payroll.simulation.wizard', 'Wizard', ondelete='cascade')
    
    employee_id = fields.Many2one('hr.employee', 'Employee', readonly=True)
    contract_id = fields.Many2one('hr.contract', 'Contract', readonly=True)
    
    gross_salary = fields.Monetary('Gross Salary', currency_field='currency_id', readonly=True)
    total_deductions = fields.Monetary('Total Deductions', currency_field='currency_id', readonly=True)
    net_salary = fields.Monetary('Net Salary', currency_field='currency_id', readonly=True)
    
    currency_id = fields.Many2one('res.currency', related='wizard_id.currency_id')