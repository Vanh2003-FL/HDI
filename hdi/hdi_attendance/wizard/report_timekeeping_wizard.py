# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class ReportTimekeepingWizard(models.TransientModel):
    """Wizard tạo báo cáo chấm công"""
    _name = 'report.timekeeping.wizard'
    _description = 'Report Timekeeping Wizard'
    
    # Date range
    date_from = fields.Date(
        string='Từ ngày',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='Đến ngày',
        required=True,
        default=lambda self: fields.Date.today()
    )
    
    # Filters
    employee_ids = fields.Many2many(
        'hr.employee',
        string='Nhân viên',
        help='Để trống để lấy tất cả nhân viên'
    )
    
    department_ids = fields.Many2many(
        'hr.department',
        string='Phòng ban',
        help='Lọc theo phòng ban'
    )
    
    # Options
    include_explanations = fields.Boolean(
        string='Bao gồm giải trình',
        default=True
    )
    
    include_gps = fields.Boolean(
        string='Bao gồm GPS',
        default=False,
        help='Hiển thị tọa độ GPS check in/out'
    )
    
    group_by = fields.Selection([
        ('employee', 'Nhân viên'),
        ('department', 'Phòng ban'),
        ('date', 'Ngày'),
    ], string='Nhóm theo', default='employee')
    
    report_format = fields.Selection([
        ('pdf', 'PDF'),
        ('xlsx', 'Excel'),
        ('docx', 'Word'),
    ], string='Định dạng', required=True, default='xlsx')
    
    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        """Validate date range"""
        for rec in self:
            if rec.date_from > rec.date_to:
                raise UserError(_('Ngày bắt đầu phải nhỏ hơn ngày kết thúc'))
            
            # Max 3 months
            delta = (rec.date_to - rec.date_from).days
            if delta > 90:
                raise UserError(_('Khoảng thời gian tối đa là 90 ngày'))
    
    def action_generate_report(self):
        """Generate and download report"""
        self.ensure_one()
        
        # Build domain
        domain = [
            ('check_in', '>=', fields.Datetime.to_string(
                datetime.combine(self.date_from, datetime.min.time())
            )),
            ('check_in', '<=', fields.Datetime.to_string(
                datetime.combine(self.date_to, datetime.max.time())
            )),
        ]
        
        if self.employee_ids:
            domain.append(('employee_id', 'in', self.employee_ids.ids))
        elif self.department_ids:
            employees = self.env['hr.employee'].search([
                ('department_id', 'in', self.department_ids.ids)
            ])
            domain.append(('employee_id', 'in', employees.ids))
        
        # Get attendance records
        attendances = self.env['hr.attendance'].search(domain, order='check_in desc')
        
        if not attendances:
            raise UserError(_('Không tìm thấy dữ liệu chấm công trong khoảng thời gian này'))
        
        # Prepare data
        data = {
            'date_from': self.date_from,
            'date_to': self.date_to,
            'attendances': attendances,
            'include_explanations': self.include_explanations,
            'include_gps': self.include_gps,
            'group_by': self.group_by,
        }
        
        # Generate report based on format
        if self.report_format == 'pdf':
            return self._generate_pdf_report(data)
        elif self.report_format == 'xlsx':
            return self._generate_xlsx_report(data)
        elif self.report_format == 'docx':
            return self._generate_docx_report(data)
    
    def _generate_pdf_report(self, data):
        """Generate PDF report"""
        return self.env.ref('hdi_attendance.report_timekeeping_pdf').report_action(
            self, data=data
        )
    
    def _generate_xlsx_report(self, data):
        """Generate Excel report"""
        # Use xlsx report template
        return {
            'type': 'ir.actions.report',
            'report_type': 'xlsx',
            'report_name': 'hdi_attendance.report_timekeeping_xlsx',
            'report_file': 'hdi_attendance.report_timekeeping_xlsx',
            'data': data,
        }
    
    def _generate_docx_report(self, data):
        """Generate Word report"""
        return {
            'type': 'ir.actions.report',
            'report_type': 'docx',
            'report_name': 'hdi_attendance.report_timekeeping_docx',
            'report_file': 'hdi_attendance.report_timekeeping_docx',
            'data': data,
        }
