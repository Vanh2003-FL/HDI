# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command, _
from odoo.exceptions import UserError, ValidationError


class ExplanationTaskTimesheetWizard(models.TransientModel):
    """Wizard tạo timesheet cho giải trình TSDA/TSNDA"""
    _name = 'explanation.task.timesheet'
    _description = 'Explanation Task Timesheet Wizard'
    
    explanation_id = fields.Many2one(
        'hr.attendance.explanation',
        string='Giải trình',
        required=True,
        ondelete='cascade'
    )
    
    type = fields.Selection([
        ('TSDA', 'Timesheet đã duyệt'),
        ('TSNDA', 'Timesheet chưa duyệt'),
    ], string='Loại', required=True)
    
    line_ids = fields.One2many(
        'explanation.task.timesheet.line',
        'wizard_id',
        string='Timesheet Lines'
    )
    
    @api.model
    def default_get(self, fields_list):
        """Pre-fill with existing timesheets if any"""
        res = super().default_get(fields_list)
        
        if self.env.context.get('default_explanation_id'):
            explanation = self.env['hr.attendance.explanation'].browse(
                self.env.context['default_explanation_id']
            )
            
            # Get timesheets for the date
            timesheets = self.env['account.analytic.line'].search([
                ('employee_id', '=', explanation.employee_id.id),
                ('date', '=', explanation.explanation_date),
            ])
            
            if timesheets:
                lines = []
                for ts in timesheets:
                    lines.append(Command.create({
                        'project_id': ts.project_id.id,
                        'task_id': ts.task_id.id,
                        'name': ts.name,
                        'unit_amount': ts.unit_amount,
                    }))
                res['line_ids'] = lines
        
        return res
    
    def action_create_timesheet(self):
        """Tạo/cập nhật timesheets và gửi phê duyệt"""
        self.ensure_one()
        
        if not self.line_ids:
            raise ValidationError(_('Vui lòng thêm ít nhất một dòng timesheet'))
        
        # Create/Update timesheets
        Timesheet = self.env['account.analytic.line']
        created_ts = self.env['account.analytic.line']
        
        for line in self.line_ids:
            ts_vals = {
                'employee_id': self.explanation_id.employee_id.id,
                'date': self.explanation_id.explanation_date,
                'project_id': line.project_id.id,
                'task_id': line.task_id.id,
                'name': line.name,
                'unit_amount': line.unit_amount,
                'explanation_id': self.explanation_id.id,
                'en_state': 'pending',  # Will be approved after explanation approved
            }
            
            # Check if exists
            existing = Timesheet.search([
                ('employee_id', '=', ts_vals['employee_id']),
                ('date', '=', ts_vals['date']),
                ('project_id', '=', ts_vals['project_id']),
                ('task_id', '=', ts_vals['task_id']),
            ], limit=1)
            
            if existing:
                existing.write(ts_vals)
                created_ts |= existing
            else:
                created_ts |= Timesheet.create(ts_vals)
        
        # Link timesheets to explanation
        self.explanation_id.write({'ts_ids': [(6, 0, created_ts.ids)]})
        
        # Auto-send for approval
        self.explanation_id.send_approve()
        
        return {'type': 'ir.actions.act_window_close'}


class ExplanationTaskTimesheetLine(models.TransientModel):
    """Line items for timesheet wizard"""
    _name = 'explanation.task.timesheet.line'
    _description = 'Explanation Timesheet Line'
    
    wizard_id = fields.Many2one(
        'explanation.task.timesheet',
        string='Wizard',
        required=True,
        ondelete='cascade'
    )
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )
    
    task_id = fields.Many2one(
        'project.task',
        string='Task',
        domain="[('project_id', '=', project_id)]"
    )
    
    name = fields.Char(
        string='Description',
        required=True
    )
    
    unit_amount = fields.Float(
        string='Hours',
        required=True,
        default=8.0
    )
    
    @api.onchange('task_id')
    def _onchange_task_id(self):
        """Auto-fill description from task"""
        if self.task_id:
            self.name = self.task_id.name
