from dateutil.relativedelta import relativedelta

from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError


class ProjectResourcePlanning(models.Model):
    _inherit = 'en.resource.planning'

    def get_default_en_wbs_latest(self):
        project_id = self._context.get('default_project_id', False)
        if not project_id:
            return self.env['en.wbs']
        en_wbs = self.env['en.wbs'].search([('project_id', '=', project_id),
             ('state', 'not in', ('draft', 'refused', 'inactive'))], order='id desc', limit=1)
        return en_wbs

    wbs_link_resource_planning = fields.Many2one(string='Phiên bản WBS', comodel_name='en.wbs',
                                                     compute_sudo=True, store=True, default=get_default_en_wbs_latest)

    def button_en_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})
            if rec.wbs_link_resource_planning and rec.wbs_link_resource_planning.state != 'approved':
                rec.wbs_link_resource_planning.write({'state': 'cancel'})
        return True

    state = fields.Selection(
        string='Trạng thái',
        selection=[
            ('draft', 'Nháp'),
            ('to_approve', 'Chờ duyệt'),
            ('to_wbs_approve', 'Chờ WBS duyệt'),
            ('approved', 'Đã duyệt'),
            ('refused', 'Bị từ chối'),
            ('expire', 'Hết hiệu lực'), ('cancel', 'Hủy')
        ],
        default='draft',
        readonly=True,
        required=True,
        copy=False,
        index=True
    )

    def button_to_approve(self):
        if self.wbs_link_resource_planning:
            project_stage_ids = self.wbs_link_resource_planning.wbs_task_ids.filtered(
                lambda x: x.category == 'phase' and x.stage_id.en_mark != 'b')
            stage_detail_map = {
                stage_id.code: False for stage_id in project_stage_ids
            }

            stage_code_id_map = {
                stage.code: stage for stage in project_stage_ids
            }

            for line in self.order_line:
                if line.project_task_stage_id and line.project_task_stage_id.code in stage_detail_map:
                    stage_detail_map[line.project_task_stage_id.code] = True

            missing_stages = [sid for sid, has_detail in stage_detail_map.items() if not has_detail]
            if missing_stages:
                data_error = ''
                for stage in missing_stages:
                    data_error += stage_code_id_map[stage].name + ', '
                data_error = data_error.rstrip(', ')
                raise exceptions.ValidationError(
                    f"Các giai đoạn sau chưa có bản ghi chi tiết nguồn lực: {data_error}"
                )
        rslt = self.button_sent()
        if not rslt: return
        self._constrains_overload()
        self.order_line.check_date_resource()
        self.order_line.check_date_resource_1()
        self.order_line._check_date_start_and_end()
        wbs = self.env['en.wbs'].search([('project_id', '=', self.project_id.id),
             ('state', 'not in', ('refused', 'inactive', 'draft'))], order='id desc', limit=1)
        if wbs and wbs.state == 'waiting_create_resource_plan': # trạng thái "Chờ tạo kế hoạch nguồn lực" là 'waiting_create_resource_plan'
            wbs.button_sent_from_resource_planing()  # Cập nhật trạng thái của WBS thành 'awaiting'
        self.write({'state': 'to_approve'})

    def button_approved(self):
        self = self.sudo()
        self.order_line._check_date_start_and_end()
        for rec in self:
            try:
                rec._constrains_overload()
            except Exception as e:
                self.env['en.refuse.reason.wizard'].with_context(active_model=rec._name, active_ids=rec.ids).create({'name': str(e)}).do()
                view = self.env.ref('ngsd_base.message_wizard')
                context = dict(self._context or {})
                context['message'] = str(e)
                return {
                    'name': 'Lỗi xác nhận',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'message.wizard',
                    'views': [(view.id, 'form')],
                    'view_id': view.id,
                    'target': 'new',
                    'context': context,
                }
        result = super(ProjectResourcePlanning, self).button_approved()
        if result:
            flag_approve = True
            wbs = self.env['en.wbs'].search([('project_id', '=', self.project_id.id),
                                             ('state', 'not in', ('refused', 'inactive', 'draft'))], order='id desc',
                                            limit=1)
            if wbs:
                if wbs.state == 'awaiting':
                    flag_approve = False
                if wbs.state == 'waiting_resource_plan_approve':
                    flag_approve = True
            if flag_approve:
                self.write({'seq_id': int(self.env['ir.sequence'].next_by_code('seq.id'))})
                self.sudo().search([('project_id', '=', self.project_id.id), ('id', '<', self.id),
                                    ('state', '=', 'approved')]).sudo().write({'state': 'expire'})
                self.sudo().wbs_link_resource_planning.write({"state": "approved"})
            else:
                self.sudo().write({'state': 'to_wbs_approve'})
        return result

    def _update_resource_plan_state(self):
        if self.resource_plan_id:
            all_approved = all(wbs.state == 'approved' for wbs in self.resource_plan_id.wbs_ids)
            new_state = 'approved' if all_approved else 'to_wbs_approve'
            self.resource_plan_id.write({'state': new_state})

    def _callback_after_refused(self):
        wbs = self.env['en.wbs'].search(
            [('project_id', '=', self.project_id.id),
             ('state', 'not in', ('refused', 'inactive', 'draft')),
             ],
            order='id desc',
            limit=1
        )
        if wbs:
            if wbs.state == 'waiting_resource_plan_approve' or wbs.state == 'awaiting':
                wbs.sudo().write({'state': 'refused'})

    def new_resource(self):
        if not self.technical_field_27766: return
        if not self.project_id.project_decision_ids.filtered(lambda d: d.state == 'approved'):
            raise UserError("Dự án chưa có QĐ Thành lập dự án, vui lòng tạo quyết định trước.")
        order_line = []
        wbs = self.env['en.wbs'].search(
            [('project_id', '=', self.project_id.id),
             ('state', 'not in', ('refused', 'inactive', 'draft')),
             ],
            order='id desc',
            limit=1
        )
        for line in self.order_line:
            if (line.employee_id.en_day_layoff_from
                and line.employee_id.en_day_layoff_to and line.employee_id.en_day_layoff_from <= line.date_start
                and line.employee_id.en_day_layoff_to >= line.date_end) or (
                    line.employee_id.departure_date and line.employee_id.departure_date <= line.date_start) or \
                    (line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_to and line.employee_id.departure_date
                     and line.employee_id.en_day_layoff_from <= line.date_start and (line.employee_id.en_day_layoff_to == line.employee_id.departure_date or line.employee_id.en_day_layoff_to + relativedelta(days=1) == line.employee_id.departure_date)
                     and line.date_end >= line.employee_id.departure_date):
                continue

            if wbs and (wbs.state == 'waiting_create_resource_plan' or wbs.state == 'approved'):
                project_stage_ids = wbs.wbs_task_ids.filtered(lambda x: x.category == 'phase' and x.id == line.project_task_stage_id.id)
                value = {
                    'type_id': line.type_id.id,
                    'employee_id': line.employee_id.id,
                    'role_id': line.role_id.id,
                    'project_task_stage_id': project_stage_ids[0].id if project_stage_ids else line.project_task_stage_id.id,
                    'job_position_id': line.job_position_id.id,
                    'workload': line.workload,
                    'en_md': line.en_md,
                    'old_line_id': line.id,
                }
            else:
                value = {
                    'type_id': line.type_id.id,
                    'employee_id': line.employee_id.id,
                    'role_id': line.role_id.id,
                    'job_position_id': line.job_position_id.id,
                    'workload': line.workload,
                    'en_md': line.en_md,
                    'old_line_id': line.id,
                }
            if line.employee_id.en_day_layoff_from \
                    and line.employee_id.en_day_layoff_to and line.employee_id.en_day_layoff_from <= line.date_start \
                    and line.employee_id.en_day_layoff_to < line.date_end and line.employee_id.en_day_layoff_to >= line.date_start and not line.employee_id.departure_date:
                value.update({
                    'date_start': line.employee_id.en_day_layoff_to + relativedelta(days=1),
                    'date_end': line.date_end,
                })
            elif line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_from == line.date_start and line.employee_id.departure_date \
                    and line.employee_id.departure_date > line.employee_id.en_day_layoff_to  and line.employee_id.departure_date <= line.date_end:
                value.update({
                    'date_start': line.employee_id.en_day_layoff_to + relativedelta(days=1),
                    'date_end': line.employee_id.departure_date - relativedelta(days=1),
                })
            elif line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_from >= line.date_start and ((line.employee_id.en_day_layoff_to \
                    and line.employee_id.en_day_layoff_to <= line.date_end and not line.employee_id.departure_date) or (line.employee_id.departure_date \
                    and line.employee_id.departure_date > line.employee_id.en_day_layoff_from)):
                value.update({
                    'date_start': line.date_start,
                    'date_end': line.employee_id.en_day_layoff_from - relativedelta(days=1),
                })
            elif line.date_end and line.date_start and line.employee_id.departure_date and line.employee_id.departure_date > line.date_start and line.employee_id.departure_date <= line.date_end:
                value.update({
                    'date_start': line.date_start,
                    'date_end': line.employee_id.departure_date - relativedelta(days=1)
                })
            else:
                value.update({
                    'date_start': line.date_start,
                    'date_end': line.date_end
                })
            order_line += [(0, 0, value)]
        values = {'order_line': order_line}
        f_lst = self.fields_get()
        for f in f_lst:
            if f_lst.get(f).get('type') == 'one2many':continue
            if not f_lst.get(f).get('store'):continue
            if f_lst.get(f).get('readonly'):continue
            if f_lst.get(f).get('type') == 'many2one':
                values[f'{f}'] = self[f].id
                continue
            if f_lst.get(f).get('type') == 'many2many':
                values[f'{f}'] = [(6,0,self[f].ids)]
                continue
            values[f'{f}'] = self[f]
        values['wbs_link_resource_planning'] = wbs.id
        resource_new = self.with_context(no_constrains=True).create(values)
        view = self.env.ref('ngsd_base.resource_planning_form')
        return {
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'en.resource.planning',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'res_id': resource_new.id,
            'target': 'current',
        }

    @api.model
    def create(self, values):
        if self._context.get('import_file') and 'workload' not in values and values.get('en_md') and values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values.get('employee_id'))
            date_from = min([fields.Date.from_string(values.get('date_start')), fields.Date.from_string(values.get('date_end'))])
            date_to = max([fields.Date.from_string(values.get('date_start')), fields.Date.from_string(values.get('date_end'))])
            en_md = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_from, date_to)
            values['workload'] = (values.get('en_md') * employee.resource_calendar_id.hours_per_day) / en_md if en_md else 0
        resource_new = super(ProjectResourcePlanning, self).create(values)
        return resource_new