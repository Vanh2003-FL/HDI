# -*- coding: utf-8 -*-
"""
HDI Leave Management Advanced System
Enhanced leave management with approval workflows, accrual rules, calendar integration
Based on NGSD leave patterns with HDI enhancements
"""

from odoo import models, fields, api
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import calendar


class HdiLeaveType(models.Model):
    """Advanced Leave Type Management"""
    _inherit = 'hr.leave.type'
    
    # HDI Extensions
    hdi_code = fields.Char('HDI Code', help="Internal HDI leave type code")
    category = fields.Selection([
        ('annual', 'Annual Leave'),
        ('sick', 'Sick Leave'), 
        ('maternity', 'Maternity Leave'),
        ('paternity', 'Paternity Leave'),
        ('compassionate', 'Compassionate Leave'),
        ('study', 'Study Leave'),
        ('unpaid', 'Unpaid Leave'),
        ('compensatory', 'Compensatory Leave'),
        ('emergency', 'Emergency Leave'),
        ('other', 'Other')
    ], string='Leave Category', required=True, default='annual')
    
    # Accrual Settings
    accrual_method = fields.Selection([
        ('manual', 'Manual Allocation'),
        ('monthly', 'Monthly Accrual'),
        ('yearly', 'Yearly Allocation'),
        ('service_based', 'Service Length Based')
    ], string='Accrual Method', default='yearly')
    
    monthly_accrual_rate = fields.Float('Monthly Accrual Rate', digits=(8, 2), default=0.0)
    yearly_allocation = fields.Float('Yearly Allocation', digits=(8, 2), default=15.0)
    max_accumulation = fields.Float('Maximum Accumulation', digits=(8, 2), default=30.0)
    
    # Carry Forward Rules
    carry_forward_allowed = fields.Boolean('Allow Carry Forward', default=True)
    carry_forward_limit = fields.Float('Carry Forward Limit', digits=(8, 2), default=5.0)
    carry_forward_expiry_months = fields.Integer('Carry Forward Expiry (Months)', default=6)
    
    # Approval Workflow
    requires_approval = fields.Boolean('Requires Approval', default=True)
    auto_approve_threshold = fields.Float('Auto-approve Threshold (Days)', default=0.0,
                                        help="Auto-approve leaves below this threshold")
    
    approval_levels = fields.Selection([
        ('single', 'Single Level'),
        ('dual', 'Dual Level'), 
        ('multiple', 'Multiple Levels')
    ], string='Approval Levels', default='single')
    
    # Restrictions
    min_days_advance = fields.Integer('Minimum Days in Advance', default=0)
    max_days_advance = fields.Integer('Maximum Days in Advance', default=365)
    min_leave_duration = fields.Float('Minimum Leave Duration (Hours)', default=0.5)
    max_leave_duration = fields.Float('Maximum Leave Duration (Days)', default=30.0)
    
    # Medical Certificate
    requires_medical_certificate = fields.Boolean('Requires Medical Certificate', default=False)
    medical_certificate_threshold = fields.Float('Medical Certificate Threshold (Days)', default=3.0)
    
    # Weekends & Holidays
    exclude_weekends = fields.Boolean('Exclude Weekends', default=True)
    exclude_public_holidays = fields.Boolean('Exclude Public Holidays', default=True)
    
    # Encashment
    encashment_allowed = fields.Boolean('Allow Encashment', default=False)
    encashment_rate = fields.Float('Encashment Rate (%)', default=100.0)
    min_balance_for_encashment = fields.Float('Minimum Balance for Encashment', default=5.0)


class HdiLeaveAccrual(models.Model):
    """Leave Accrual Management"""
    _name = 'hdi.leave.accrual'
    _description = 'HDI Leave Accrual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'display_name'
    _order = 'accrual_date desc'
    
    # Basic Information
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, ondelete='cascade')
    leave_type_id = fields.Many2one('hr.leave.type', 'Leave Type', required=True, ondelete='cascade')
    
    # Accrual Details
    accrual_date = fields.Date('Accrual Date', required=True, default=fields.Date.today)
    accrued_days = fields.Float('Accrued Days', digits=(8, 2), required=True)
    accrual_reason = fields.Selection([
        ('monthly', 'Monthly Accrual'),
        ('yearly', 'Yearly Allocation'),
        ('adjustment', 'Manual Adjustment'),
        ('carry_forward', 'Carry Forward'),
        ('service_milestone', 'Service Milestone'),
        ('correction', 'Correction')
    ], string='Accrual Reason', required=True, default='monthly')
    
    # Balance Information
    previous_balance = fields.Float('Previous Balance', digits=(8, 2), default=0.0)
    new_balance = fields.Float('New Balance', digits=(8, 2), compute='_compute_new_balance', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True)
    
    # References
    allocation_id = fields.Many2one('hr.leave.allocation', 'Related Allocation')
    notes = fields.Text('Notes')
    
    display_name = fields.Char('Display Name', compute='_compute_display_name', store=True)
    
    @api.depends('previous_balance', 'accrued_days')
    def _compute_new_balance(self):
        """Compute new balance"""
        for record in self:
            record.new_balance = record.previous_balance + record.accrued_days
    
    @api.depends('employee_id', 'leave_type_id', 'accrual_date', 'accrued_days')
    def _compute_display_name(self):
        """Compute display name"""
        for record in self:
            if record.employee_id and record.leave_type_id:
                record.display_name = f"{record.employee_id.name} - {record.leave_type_id.name} ({record.accrual_date})"
            else:
                record.display_name = "New Accrual"
    
    def action_confirm(self):
        """Confirm accrual"""
        for record in self:
            if record.state == 'draft':
                record.state = 'confirmed'
                record._create_allocation()
    
    def _create_allocation(self):
        """Create leave allocation from accrual"""
        for record in self:
            if record.accrued_days > 0:
                allocation_vals = {
                    'name': f"Accrual - {record.leave_type_id.name}",
                    'employee_id': record.employee_id.id,
                    'holiday_status_id': record.leave_type_id.id,
                    'number_of_days': record.accrued_days,
                    'allocation_type': 'regular',
                    'state': 'validate',
                    'date_from': record.accrual_date,
                    'date_to': record.accrual_date + relativedelta(years=1),
                }
                allocation = self.env['hr.leave.allocation'].create(allocation_vals)
                record.allocation_id = allocation.id


class HdiLeavePolicy(models.Model):
    """Leave Policy Management"""
    _name = 'hdi.leave.policy'
    _description = 'HDI Leave Policy'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Information
    name = fields.Char('Policy Name', required=True, tracking=True)
    code = fields.Char('Policy Code', required=True)
    description = fields.Html('Policy Description')
    
    # Applicability
    department_ids = fields.Many2many('hr.department', 'policy_department_rel', 
                                    'policy_id', 'department_id', string='Applicable Departments')
    job_ids = fields.Many2many('hr.job', 'policy_job_rel', 
                             'policy_id', 'job_id', string='Applicable Jobs')
    employee_category_ids = fields.Many2many('hr.employee.category', 'policy_category_rel',
                                           'policy_id', 'category_id', string='Employee Categories')
    
    # Policy Rules
    leave_type_rules = fields.One2many('hdi.leave.policy.rule', 'policy_id', string='Leave Type Rules')
    
    # Approval Rules
    default_approval_levels = fields.Selection([
        ('single', 'Single Level'),
        ('dual', 'Dual Level'),
        ('multiple', 'Multiple Levels')
    ], string='Default Approval Levels', default='single')
    
    # Status
    is_active = fields.Boolean('Active', default=True, tracking=True)
    effective_date = fields.Date('Effective Date', default=fields.Date.today, tracking=True)
    
    _sql_constraints = [
        ('code_unique', 'UNIQUE(code)', 'Leave policy code must be unique!')
    ]


class HdiLeavePolicyRule(models.Model):
    """Leave Policy Rules"""
    _name = 'hdi.leave.policy.rule'
    _description = 'HDI Leave Policy Rule'
    _order = 'sequence, leave_type_id'
    
    policy_id = fields.Many2one('hdi.leave.policy', 'Leave Policy', required=True, ondelete='cascade')
    sequence = fields.Integer('Sequence', default=10)
    
    leave_type_id = fields.Many2one('hr.leave.type', 'Leave Type', required=True)
    
    # Entitlement Rules
    entitlement_days = fields.Float('Annual Entitlement (Days)', digits=(8, 2), default=0.0)
    accrual_start_month = fields.Selection([
        ('1', 'January'), ('2', 'February'), ('3', 'March'), ('4', 'April'),
        ('5', 'May'), ('6', 'June'), ('7', 'July'), ('8', 'August'),
        ('9', 'September'), ('10', 'October'), ('11', 'November'), ('12', 'December')
    ], string='Accrual Start Month', default='1')
    
    # Service-based Rules
    min_service_months = fields.Integer('Minimum Service (Months)', default=0)
    service_increments = fields.One2many('hdi.leave.service.increment', 'rule_id', 
                                       string='Service-based Increments')


class HdiLeaveServiceIncrement(models.Model):
    """Service-based Leave Increments"""
    _name = 'hdi.leave.service.increment'
    _description = 'HDI Leave Service Increment'
    _order = 'service_months'
    
    rule_id = fields.Many2one('hdi.leave.policy.rule', 'Policy Rule', required=True, ondelete='cascade')
    
    service_months = fields.Integer('Service Months', required=True)
    additional_days = fields.Float('Additional Days', digits=(8, 2), required=True)
    description = fields.Char('Description')


class HdiLeaveCalendar(models.Model):
    """Leave Calendar Integration"""
    _name = 'hdi.leave.calendar'
    _description = 'HDI Leave Calendar'
    
    name = fields.Char('Calendar Name', required=True)
    department_id = fields.Many2one('hr.department', 'Department')
    
    # Calendar Rules
    working_days = fields.Selection([
        ('mon_fri', 'Monday to Friday'),
        ('sun_thu', 'Sunday to Thursday'),
        ('custom', 'Custom Schedule')
    ], string='Working Days', default='mon_fri', required=True)
    
    # Public Holidays
    holiday_ids = fields.One2many('hdi.public.holiday', 'calendar_id', string='Public Holidays')
    
    # Blackout Periods
    blackout_period_ids = fields.One2many('hdi.leave.blackout', 'calendar_id', string='Blackout Periods')


class HdiPublicHoliday(models.Model):
    """Public Holiday Management"""
    _name = 'hdi.public.holiday'
    _description = 'HDI Public Holiday'
    _order = 'date'
    
    name = fields.Char('Holiday Name', required=True, translate=True)
    date = fields.Date('Date', required=True)
    calendar_id = fields.Many2one('hdi.leave.calendar', 'Calendar', ondelete='cascade')
    
    is_fixed = fields.Boolean('Fixed Date', default=True, help="Same date every year")
    is_active = fields.Boolean('Active', default=True)
    
    _sql_constraints = [
        ('date_calendar_unique', 'UNIQUE(date, calendar_id)', 'Holiday date must be unique per calendar!')
    ]


class HdiLeaveBlackout(models.Model):
    """Leave Blackout Periods"""
    _name = 'hdi.leave.blackout'
    _description = 'HDI Leave Blackout Period'
    
    name = fields.Char('Blackout Period Name', required=True)
    calendar_id = fields.Many2one('hdi.leave.calendar', 'Calendar', ondelete='cascade')
    
    date_from = fields.Date('From Date', required=True)
    date_to = fields.Date('To Date', required=True)
    
    leave_type_ids = fields.Many2many('hr.leave.type', 'blackout_leave_type_rel',
                                    'blackout_id', 'leave_type_id', 
                                    string='Restricted Leave Types')
    
    reason = fields.Text('Reason')
    is_active = fields.Boolean('Active', default=True)
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate blackout dates"""
        for record in self:
            if record.date_from > record.date_to:
                raise ValidationError("From date cannot be after To date.")


# Extend HR Leave
class HrLeave(models.Model):
    _inherit = 'hr.leave'
    
    # HDI Extensions
    leave_category = fields.Selection(related='holiday_status_id.category', store=True)
    approval_level = fields.Integer('Approval Level', default=1)
    current_approver_id = fields.Many2one('hr.employee', 'Current Approver')
    
    # Enhanced Approval Workflow
    approval_history_ids = fields.One2many('hdi.leave.approval', 'leave_id', string='Approval History')
    
    # Medical Certificate
    medical_certificate = fields.Binary('Medical Certificate', attachment=True)
    medical_certificate_filename = fields.Char('Certificate Filename')
    medical_certificate_required = fields.Boolean(related='holiday_status_id.requires_medical_certificate')
    
    # Enhanced Information
    emergency_contact = fields.Char('Emergency Contact')
    emergency_phone = fields.Char('Emergency Phone')
    coverage_employee_id = fields.Many2one('hr.employee', 'Coverage Employee')
    
    # Financial Impact
    is_paid = fields.Boolean('Paid Leave', default=True)
    encashment_request = fields.Boolean('Encashment Request', default=False)
    encashment_amount = fields.Monetary('Encashment Amount', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    @api.constrains('request_date_from', 'request_date_to')
    def _check_blackout_periods(self):
        """Check for blackout periods"""
        for leave in self:
            if leave.request_date_from and leave.request_date_to:
                # Get employee's calendar
                calendar = self._get_employee_calendar(leave.employee_id)
                if calendar:
                    blackouts = calendar.blackout_period_ids.filtered(
                        lambda b: b.is_active and 
                        leave.holiday_status_id in b.leave_type_ids and
                        b.date_from <= leave.request_date_to and
                        b.date_to >= leave.request_date_from
                    )
                    if blackouts:
                        raise ValidationError(f"Leave request conflicts with blackout period: {blackouts[0].name}")
    
    def _get_employee_calendar(self, employee):
        """Get employee's leave calendar"""
        calendar = self.env['hdi.leave.calendar'].search([
            ('department_id', '=', employee.department_id.id)
        ], limit=1)
        if not calendar:
            calendar = self.env['hdi.leave.calendar'].search([], limit=1)
        return calendar
    
    def action_approve(self):
        """Enhanced approval with multi-level support"""
        for leave in self:
            # Create approval record
            approval_vals = {
                'leave_id': leave.id,
                'approver_id': self.env.user.employee_id.id,
                'approval_level': leave.approval_level,
                'action': 'approved',
                'approval_date': fields.Datetime.now(),
                'comments': f"Approved at level {leave.approval_level}"
            }
            self.env['hdi.leave.approval'].create(approval_vals)
            
            # Check if more approvals needed
            max_levels = self._get_required_approval_levels(leave)
            if leave.approval_level < max_levels:
                leave.approval_level += 1
                leave.current_approver_id = self._get_next_approver(leave)
                leave.message_post(body=f"Approved at level {leave.approval_level - 1}. Waiting for level {leave.approval_level} approval.")
            else:
                # Final approval
                super().action_approve()
                leave.message_post(body="Leave request fully approved.")
    
    def _get_required_approval_levels(self, leave):
        """Get required approval levels for leave"""
        if leave.holiday_status_id.approval_levels == 'single':
            return 1
        elif leave.holiday_status_id.approval_levels == 'dual':
            return 2
        else:
            return 3  # Multiple levels
    
    def _get_next_approver(self, leave):
        """Get next approver based on hierarchy"""
        if leave.approval_level == 1:
            return leave.employee_id.parent_id
        elif leave.approval_level == 2:
            return leave.employee_id.parent_id.parent_id if leave.employee_id.parent_id else leave.employee_id.parent_id
        else:
            # HR approval
            hr_dept = self.env['hr.department'].search([('name', 'ilike', 'hr')], limit=1)
            if hr_dept and hr_dept.manager_id:
                return hr_dept.manager_id
        return False


class HdiLeaveApproval(models.Model):
    """Leave Approval History"""
    _name = 'hdi.leave.approval'
    _description = 'HDI Leave Approval'
    _order = 'approval_date desc'
    
    leave_id = fields.Many2one('hr.leave', 'Leave Request', required=True, ondelete='cascade')
    approver_id = fields.Many2one('hr.employee', 'Approver', required=True)
    approval_level = fields.Integer('Approval Level', required=True)
    
    action = fields.Selection([
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
        ('delegated', 'Delegated')
    ], string='Action', required=True)
    
    approval_date = fields.Datetime('Approval Date', required=True)
    comments = fields.Text('Comments')
    
    delegated_to_id = fields.Many2one('hr.employee', 'Delegated To')


class HdiLeaveEncashment(models.Model):
    """Leave Encashment Management"""
    _name = 'hdi.leave.encashment'
    _description = 'HDI Leave Encashment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    # Basic Information
    employee_id = fields.Many2one('hr.employee', 'Employee', required=True, ondelete='cascade')
    leave_type_id = fields.Many2one('hr.leave.type', 'Leave Type', required=True)
    
    # Encashment Details
    encashment_date = fields.Date('Encashment Date', default=fields.Date.today, required=True)
    days_to_encash = fields.Float('Days to Encash', digits=(8, 2), required=True)
    daily_rate = fields.Monetary('Daily Rate', currency_field='currency_id', required=True)
    total_amount = fields.Monetary('Total Amount', compute='_compute_total_amount', store=True)
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)
    
    # Balance Information
    available_balance = fields.Float('Available Balance', digits=(8, 2))
    remaining_balance = fields.Float('Remaining Balance', compute='_compute_remaining_balance', store=True)
    
    # Status
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('approved', 'Approved'),
        ('paid', 'Paid'),
        ('rejected', 'Rejected')
    ], string='Status', default='draft', tracking=True)
    
    # Approval
    approved_by_id = fields.Many2one('hr.employee', 'Approved By')
    approval_date = fields.Date('Approval Date')
    rejection_reason = fields.Text('Rejection Reason')
    
    notes = fields.Text('Notes')
    
    @api.depends('days_to_encash', 'daily_rate')
    def _compute_total_amount(self):
        """Compute total encashment amount"""
        for record in self:
            record.total_amount = record.days_to_encash * record.daily_rate
    
    @api.depends('available_balance', 'days_to_encash')
    def _compute_remaining_balance(self):
        """Compute remaining balance after encashment"""
        for record in self:
            record.remaining_balance = record.available_balance - record.days_to_encash
    
    @api.constrains('days_to_encash', 'available_balance')
    def _check_encashment_limit(self):
        """Validate encashment limits"""
        for record in self:
            if record.days_to_encash > record.available_balance:
                raise ValidationError("Cannot encash more days than available balance.")
            
            min_balance = record.leave_type_id.min_balance_for_encashment
            if record.remaining_balance < min_balance:
                raise ValidationError(f"Minimum balance of {min_balance} days must be maintained.")
    
    def action_submit(self):
        """Submit for approval"""
        for record in self:
            if record.state == 'draft':
                record.state = 'submitted'
    
    def action_approve(self):
        """Approve encashment"""
        for record in self:
            if record.state == 'submitted':
                record.state = 'approved'
                record.approved_by_id = self.env.user.employee_id
                record.approval_date = fields.Date.today()
                record._create_leave_deduction()
    
    def action_reject(self):
        """Reject encashment"""
        for record in self:
            record.state = 'rejected'
    
    def _create_leave_deduction(self):
        """Create leave allocation deduction"""
        for record in self:
            # Create negative allocation to deduct encashed days
            allocation_vals = {
                'name': f"Encashment - {record.leave_type_id.name}",
                'employee_id': record.employee_id.id,
                'holiday_status_id': record.leave_type_id.id,
                'number_of_days': -record.days_to_encash,
                'allocation_type': 'regular',
                'state': 'validate',
            }
            self.env['hr.leave.allocation'].create(allocation_vals)