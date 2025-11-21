from odoo import models, fields, api, _, exceptions
from datetime import date, datetime, time
from dateutil.relativedelta import relativedelta


class ProjectResourceDetail(models.Model):
    _inherit = 'en.resource.detail'

    #TODO Cần cron job quét lại dữ liệu cột này
    def _auto_init(self):
        self._cr.execute("""alter table en_resource_detail add column if not exists en_mm numeric;""")
        return super()._auto_init()

    can_copy = fields.Boolean(string='Có thể Copy', compute='_compute_can_copy', store=False)
    project_stage_code = fields.Char('Mã giai đoạn', compute='_compute_project_stage_code', readonly=False, store=False)
    work_email = fields.Char(string="Email nhân sự")

    @api.depends('project_stage_id')
    def _compute_project_stage_code(self):
        for rec in self:
            if rec.project_stage_id:
                rec.project_stage_code = rec.project_stage_id.stage_code

    @api.depends('order_id.project_id', 'order_id.project_id.version_link_resource_planning')
    def _compute_project_stage(self):
        for rec in self:
            rec.project_stage_ids = rec.order_id.project_id.version_link_resource_planning.project_stage_ids if rec.order_id.project_id.version_link_resource_planning else False

    @api.depends('date_end', 'date_start')
    def _compute_can_copy(self):
        today = date.today()
        for rec in self:
            rec.can_copy = False
            if rec.date_end and rec.date_start:
                if (rec.date_start < date(today.year, today.month, 1) <= rec.date_end and today <= date(today.year,
                                                                                                        today.month,
                                                                                                        5)) or (
                        rec.date_end >= today and rec.date_start < today):
                    rec.can_copy = True

    def open_split_confirm_popup(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Xác nhận tách dòng',
            'res_model': 'split.line.confirm.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_detail_id': self.id,
            }
        }

    @api.depends('date_end', 'date_start', 'hours_indate', 'en_md')
    def action_split_line(self, split_date=None):
        self = self.with_context(no_constrains=True)
        for record in self:
            # 1. Xác định tháng hiện tại
            today = fields.Date.today()
            original_end_date = record.date_end
            md_original = record.en_md

            if record.date_end and record.date_end < split_date:
                raise exceptions.UserError("Không thể tách ngày kết thúc nhỏ hơn ngày tách dòng được.")
            if record.date_start and record.date_start >= split_date:
                raise exceptions.UserError("Không thể tách ngày bắt đầu nhỏ hơn ngày tách dòng được.")

            prev_split_date = split_date - relativedelta(days=1)

            # 3. Update dòng cũ
            record.date_end = prev_split_date

            # 4. Tính lại MD dòng cũ
            work_days = record._get_workdays(record.date_start, prev_split_date, record.employee_id)
            record.en_md = record.workload * work_days

            # 5. Tạo dòng mới
            record.copy(default={
                'date_start': split_date,
                'date_end': max(original_end_date, today),
                'en_md': md_original - record.en_md,  # MD còn lại
            })

    def _get_workdays(self, date_start, date_end, employee_id):
        # Gọi phương thức convert_daterange_to_data để lấy dữ liệu về các ngày của nhân viên
        tech_data = self.env['en.technical.model'].convert_daterange_to_data(employee_id, date_start, date_end)

        # Kiểm tra nếu tech_data không phải là None hoặc rỗng
        if not tech_data:
            return 0
        work_date = 0
        for item, info in tech_data.items():
            if info.get('tech_type') not in ['off', 'not_work', 'layoff', 'holiday']:
                work_date += 1

        return work_date

    @api.constrains('project_stage_id', 'date_start', 'date_end')
    def _check_date_start_and_end(self):
        for rec in self:
            if self._context.get('no_constrains', False):continue
            if not rec.project_stage_id or not rec.date_start or not rec.date_end:
                continue

            # lấy tất cả các dòng cùng đơn & cùng giai đoạn
            overlaps = self.search([
                ('id', '!=', rec.id),
                ('order_id', '=', rec.order_id.id),
                ('date_start', '<=', rec.date_end),
                ('date_end', '>=', rec.date_start),
                ('employee_id', '=', rec.employee_id.id),

            ])
            overlaps = overlaps.filtered(lambda s: s.project_stage_id.stage_code == rec.project_stage_id.stage_code)
            if overlaps:
                raise exceptions.ValidationError(
                    f'Nhân sự {rec.employee_id.name} đang bị trùng thời gian trong cùng 1 giai đoạn. Vui lòng kiểm tra lại.'
                )

            stage = rec.project_stage_id
            if not stage.start_date or not stage.end_date:
                continue  # Nếu giai đoạn chưa có ngày, bỏ qua

            if rec.date_start < stage.start_date or rec.date_end > stage.end_date:
                raise exceptions.ValidationError(
                    f'Ngày bắt đầu – kết thúc của nhân sự {rec.employee_id.name} phải nằm trong thời gian của  giai đoạn tương ứng'
                )

    @api.depends('date_start', 'date_end')
    def _get_readonly_date(self):
        for rec in self:
            today = fields.Date.Date.context_today(rec)
            first_day_of_month = today.replace(day=1)
            rec.edit_date_start = False
            rec.edit_date_end = False
            if not rec.old_line_id:
                rec.edit_date_start = True
                rec.edit_date_end = True
            else:
                if 1 <= today.day <= 5:
                    if rec.date_start and rec.date_start > first_day_of_month:
                        rec.edit_date_start = True
                        rec.edit_date_end = True
                elif rec.date_start and rec.date_start >= today:
                    rec.edit_date_start = True
                    rec.edit_date_end = True

    @api.onchange('date_start')
    def _onchange_check_date_start(self):
        for rec in self:
            today = fields.Date.Date.context_today(rec)
            first_month = date(today.year, today.month, 1)
            if rec.old_line_id:
                if today > date(today.year, today.month, 5):
                    if rec.date_start and rec.date_start < today:
                        raise exceptions.ValidationError(
                            f'Giá trị ngày bắt đầu phải lớn hơn hoặc bằng {today.strftime("%d/%m/%Y")}')
                else:
                    if rec.date_start and rec.date_start < first_month:
                        raise exceptions.ValidationError(
                            f'Giá trị ngày bắt đầu phải lớn hơn hoặc bằng {first_month.strftime("%d/%m/%Y")}')

    @api.onchange('date_end')
    def _onchange_check_date_end(self):
        for rec in self:
            today = fields.Date.Date.context_today(rec)
            first_month = date(today.year, today.month, 1)
            if rec.old_line_id:
                if today > date(today.year, today.month, 5):
                    if rec.date_end and rec.date_end < today:
                        raise exceptions.ValidationError(
                            f'Giá trị ngày kết thúc phải lớn hơn hoặc bằng {today.strftime("%d/%m/%Y")}')
                else:
                    if rec.date_end and rec.date_end < first_month:
                        raise exceptions.ValidationError(
                            f'Giá trị ngày kết thúc phải lớn hơn hoặc bằng {first_month.strftime("%d/%m/%Y")}')

    @api.depends('date_start', 'date_end')
    def _compute_no_delete_line(self):
        for rec in self:
            today = fields.Date.Date.context_today(rec)
            first_day_of_month = today.replace(day=1)
            no_delete_line = True
            if not rec.old_line_id:
                no_delete_line = False
            else:
                if 1 <= today.day <= 5:
                    if rec.date_start and rec.date_start > first_day_of_month:
                        no_delete_line = False
                elif rec.date_start and rec.date_start >= today:
                    no_delete_line = False
            rec.no_delete_line = no_delete_line

    @api.model
    def create(self, vals):
        if self._context.get("import_file", False):
            if 'employee_id' in vals:
                vals.pop('employee_id', None)
            if 'work_email' in vals:
                work_email = vals.get('work_email')
                employee = self.env['hr.employee'].with_context(active_test=False).sudo().search(
                    [('work_email', '=', work_email)], limit=1)
                if employee:
                    vals['employee_id'] = employee.id
        res = super().create(vals)
        if not res.employee_id and self._context.get("import_file", False):
            raise ValueError("Không tìm thấy nhân sự với email: {}".format(work_email))
        return res
