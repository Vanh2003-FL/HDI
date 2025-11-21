from dateutil.relativedelta import relativedelta
from odoo import models, fields, api, _, exceptions
from odoo.exceptions import ValidationError, UserError, AccessError


class ResourcePlaning(models.Model):
    _inherit = "en.resource.planning"

    order_line = fields.One2many(context={'ctx_resource_stage_display': True})

    # Ghi đè lại logic tạo phiên bản mới KHNL
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
                project_stage_id = self.env["project.task"].sudo().search(
                    [("related_task_id", "=", line.project_task_stage_id.id)], limit=1).id
                if not project_stage_id:
                    project_stage_ids = wbs.wbs_task_ids.filtered(lambda x: x.category == 'phase')
                    stage_ids = project_stage_ids.filtered(
                        lambda x: x.name == line.project_task_stage_id.name)
                    project_stage_id = stage_ids[0].id if stage_ids else False
                value = {
                    'type_id': line.type_id.id,
                    'employee_id': line.employee_id.id,
                    'role_id': line.role_id.id,
                    'project_task_stage_id': project_stage_id,
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