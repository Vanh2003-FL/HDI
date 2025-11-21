from odoo import models, fields, api, _
from dateutil.relativedelta import relativedelta
from datetime import datetime, time, timedelta, date
from pytz import timezone


class ReportTimekeepingWizard(models.TransientModel):
    _name = 'report.timekeeping.wizard'
    _description = 'Xuất bảng chấm công'

    employee_ids = fields.Many2many('hr.employee', string='Nhân viên', required=False)
    department_ids = fields.Many2many('hr.department', string='Trung tâm', required=False)
    en_department_ids = fields.Many2many('en.department', string='Phòng', required=False, domain="[('id', 'in', en_department_domain)]")
    month = fields.Selection(selection=[('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12')], string='Dữ liệu của tháng', required=True)
    year = fields.Char('Dữ liệu của năm', required=True)
    en_department_domain = fields.Many2many(string='Trung tâm', comodel_name='en.department', compute='_get_en_department_domain')
    export_option = fields.Selection(string="Xuất theo", required=True,
                                     selection=[('month', 'Theo tháng'), ('custom', 'Tùy chọn')],
                                     default='month')
    date_from = fields.Date(string="Từ ngày")
    date_to = fields.Date(string="Đến ngày")

    @api.depends('department_ids')
    def _get_en_department_domain(self):
        for rec in self:
            if rec.department_ids:
                rec.en_department_domain = rec.env['en.department'].search([('department_id', 'in', rec.department_ids.ids)])
            else:
                rec.en_department_domain = rec.env['en.department'].search([])

    @api.onchange('start_year', 'end_year', 'start_month', 'end_month')
    def onchange_year(self):
        self.check_year()

    @api.constrains('start_year', 'end_year', 'start_month', 'end_month', 'line_ids')
    def constrain_year(self):
        self.check_year()
        self.validate_selection_date()

    def check_year(self):
        check = True
        try:
            int(self.year)
        except:
            check = False
        if not check:
            raise UserError('Trường năm không hợp lệ!')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        year = fields.Date.today().year
        selection = []
        for i in range(-5, 5):
            selection.append((str(year +i), str(year + i)))
        res = super(ReportTimekeepingWizard, self).fields_get(allfields, attributes=attributes)
        if res.get('year'):
            res['year']['type'] = 'selection'
            res['year']['selection'] = selection
        return res

    def action_view(self):
        report = self.env.ref('ngs_attendance.ngs_action_report_timekeeping')
        return report.report_action(self)

    def get_view_action(self):
        date_f = (fields.Date.Date.Date.context_today(self) - relativedelta(months=1))
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'report.timekeeping.wizard',
            'name': 'Xuất bảng chấm công',
            'target': 'new',
            'views': [(self.env.ref('ngs_attendance.report_timekeeping_wizard_form').id, 'form')],
            'context': {
                'default_year': str(date_f.year),
                'default_month': str(date_f.month)
            }
        }

    def get_emps_info(self):
        self.ensure_one()
        emps_info = []
        for idx, emp in enumerate(self.employee_ids, start=1):

            date_from = date(int(self.year), int(self.month), 1)
            date_to = date_from + relativedelta(months=1, days=-1)
            vals = {
                'idx': idx,
                'code': str(emp.en_employee_code or ''),
                'name': emp.name,
                'total_day': 0,
                'normal_day': 0,
                'holiday': self.env['en.calendar.holiday.line'].search_count([('en_date', '>=', date_from), ('en_date', '<=', date_to)]),
                'an_ca': 0,
            }

            tz = emp.tz
            tz_date_from = timezone(tz).localize(datetime.combine(date_from, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
            tz_date_to = timezone(tz).localize(datetime.combine(date_to, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
            attendances = self.env['hr.attendance'].search([('employee_id', '=', emp.id), ('check_in', '>=', tz_date_from), ('check_in', '<=', tz_date_to)])
            for att in attendances:
                day = timezone('UTC').localize(att.check_in).astimezone(timezone(tz)).day
                if ('day_' + str(day)) not in vals:
                    vals['day_' + str(day)] = 0
                vals['day_' + str(day)] += att.worked_hours / 24

            clause_1 = ['&', ('date_end', '<=', date_to), ('date_end', '>=', date_from)]
            clause_2 = ['&', ('date_start', '<=', date_to), ('date_start', '>=', date_from)]
            clause_3 = ['&', ('date_start', '<=', date_from), '|', ('date_end', '=', False), ('date_end', '>=', date_to)]
            clause_final = [('employee_id', '=', emp.id), '|', '|'] + clause_1 + clause_2 + clause_3
            overtime_data = []
            leave_data = []
            payslip_data = self.env['hr.payslip'].with_context(report_timekeeping=True).get_worked_day_lines(self.env['hr.contract'].search(clause_final, limit=1), date_from, date_to)
            for p in payslip_data:
                if p.get('code') == 'WORK100':
                    vals['total_day'] = p.get('number_of_days')
                if p.get('code') == 'WORKDAY':
                    vals['normal_day'] += p.get('number_of_days')
                if p.get('code') == 'PROBATION':
                    vals['normal_day'] += p.get('number_of_days')
                if p.get('code') == 'MEALDAY':
                    vals['an_ca'] = p.get('number_of_days')
                if p.get('overtime_id'):
                    overtime_data.append(p)
                if p.get('leave_id'):
                    leave_data.append(p)
            vals['overtime_data'] = overtime_data
            vals['leave_data'] = leave_data
            emps_info.append(vals)
        return emps_info

    def _get_report_filename(self):
        if self.export_option == 'month':
            return f"Bảng chấm công tháng {self.month}-{self.year}.xlsx"
        else:
            return f"Bảng chấm công từ {self.date_from.strftime('%d/%m/%Y')} đến ngày {self.date_to.strftime('%d/%m/%Y')}.xlsx"
