from collections import defaultdict
from odoo import fields, models, api, exceptions
from datetime import timedelta, datetime, time, date
from odoo.tools import config, date_utils, get_lang, html2plaintext
from dateutil.relativedelta import relativedelta
from pytz import timezone
import logging
from odoo.models import NewId

log = logging.getLogger(__name__)

READONLY_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
}
EDIT_DRAFT_STATES = {
    'to_approve': [('readonly', True)],
    'approved': [('readonly', True)],
    'refused': [('readonly', True)],
    'expire': [('readonly', True)],
}

org_chart_classes = {
    0: "level-0",
    1: "level-1",
    2: "level-2",
    3: "level-3",
    4: "level-4",
}

def daterange(start_date, end_date):
    for n in range(int(((end_date + timedelta(days=1)) - start_date).days)):
        yield start_date + timedelta(n)


class ResourcePlanning(models.Model):
    _name = 'en.resource.planning'
    _description = 'Kế hoạch nguồn lực'
    _order = 'seq_id asc'
    _inherit = 'ngsd.approval'
    _parent_store = True

    def name_get(self):
        names = []
        for record in self:
            name = record.name
            if record.version_number:
                name += f' ({record.version_number})'
            names.append((record.id, name))
        return names

    active = fields.Boolean(default=True)
    en_bmm = fields.Float(string='BMM', related='project_id.en_bmm')
    en_md = fields.Float(string='Tổng nguồn lực (MD)', compute_sudo=True, compute='_compute_en_m_uom', store=True)

    @api.depends('order_line.en_md', 'project_id.en_history_resource_ids', 'project_id.mm_rate')
    def _compute_en_m_uom(self):
        for rec in self:
            rec.en_md = sum(rec.order_line.mapped('en_md')) + sum(rec.project_id.en_history_resource_ids.mapped('plan')) * rec.project_id.mm_rate

    hours_total = fields.Float(string='Tổng nguồn lực (MH)', compute_sudo=True, compute='_compute_hours_total', store=True)

    @api.depends('order_line.en_mh')
    def _compute_hours_total(self):
        for rec in self:
            rec.hours_total = sum(rec.order_line.mapped('en_mh'))

    parent_path = fields.Char(index=True)
    seq_id = fields.Integer(string='💰', default=lambda self: int(self.env['ir.sequence'].next_by_code('seq.id')), copy=False)
    version_number = fields.Char(string='Số phiên bản', compute_sudo=True, compute='_compute_version_number', store=True, readonly=True, copy=False)

    @api.depends('project_id', 'project_id.en_resource_ids', 'parent_id', 'parent_id.child_ids', 'seq_id', 'version_type', 'state')
    def _compute_version_number(self):
        for parent in self.filtered(lambda x: x.parent_id).mapped("parent_id"):
            sequence = 1
            wbs = parent.child_ids.filtered(lambda x: x.parent_id)
            for line in sorted(wbs, key=lambda l: l.seq_id):
                line.version_number = f"{parent.technical_field_before}.{sequence}"
                sequence += 1
        for project in self.filtered(lambda x: not x.parent_id and x.version_type == 'plan').mapped("project_id"):
            sequence = 1
            wbs = project.en_resource_ids.filtered(lambda x: not x.parent_id and x.version_type == 'plan')
            for line in sorted(wbs, key=lambda l: l.seq_id):
                line.version_number = f"0.{sequence}"
                sequence += 1
        for project in self.filtered(lambda x: not x.parent_id and not x.version_type == 'plan').mapped("project_id"):
            sequence = 1
            wbs = project.en_resource_ids.filtered(lambda x: not x.parent_id and not x.version_type == 'plan')
            for line in sorted(wbs, key=lambda l: l.seq_id):
                line.version_number = f"{sequence}.0"
                sequence += 1

    parent_id = fields.Many2one(string='Thuộc về baseline', comodel_name='en.resource.planning', compute_sudo=True, compute='_compute_parent_id', store=True)

    @api.depends('version_type', 'project_id', 'state')
    def _compute_parent_id(self):
        for rec in self:
            parent_id = self.env['en.resource.planning']
            if rec.version_type == 'baseline': parent_id = False
            if rec.version_type == 'plan':
                parent_id = self.env['en.resource.planning'].search([('version_type', '=', 'baseline'), ('project_id', '=', rec.project_id.id), ('state', 'in', ['approved', 'expire']), ('id', '<', rec._origin.id)], limit=1, order='technical_field_before desc')
            rec.parent_id = parent_id

    child_ids = fields.One2many(string='Plan', comodel_name='en.resource.planning', inverse_name='parent_id')
    technical_field_before = fields.Integer(string='🪙', compute_sudo=True, compute='_compute_technical_field_beter', store=True)
    technical_field_after = fields.Integer(string='🪙', compute_sudo=True, compute='_compute_technical_field_beter', store=True)
    mm_rate = fields.Float(string='Đơn vị quy đổi MM', states={'to_approve': [('readonly', True)], 'approved': [('readonly', True)], 'refused': [('readonly', True)], 'expire': [('readonly', True)]}, required=False, related='project_id.mm_rate')

    # @api.constrains('mm_rate')
    # def check_mm_rate(self):
    #     for rec in self:
    #         if rec.mm_rate <= 0:
    #             raise UserError('Đơn vị quy đổi MM phải lớn hơn 0')

    mm_conversion = fields.Float(string='Tổng MM kế hoạch', compute='_get_mm_conversion')

    @api.depends('mm_rate', 'en_md')
    def _get_mm_conversion(self):
        for rec in self:
            rec.mm_conversion = rec.en_md / rec.mm_rate if rec.mm_rate > 0 else 0

    @api.depends('version_number')
    def _compute_technical_field_beter(self):
        for rec in self:
            try:
                version_part = rec.version_number.split('.')
                rec.technical_field_before = int(version_part[0])
                rec.technical_field_after = int(version_part[1])
            except:
                rec.technical_field_before = 0
                rec.technical_field_after = 0

    version_type = fields.Selection(string='Loại phiên bản', selection=[('baseline', 'Baseline'), ('plan', 'Plan')], store=True, compute_sudo=True, compute='_compute_version_type')

    @api.depends('state')
    def _compute_version_type(self):
        for rec in self:
            version_type = 'plan'
            if rec.state in ['approved', 'expire']:
                version_type = 'baseline'
            rec.version_type = version_type

    bmm_percent = fields.Float(
        string="MM/BMM (%)",
        compute="_compute_bmm_mm_conversion",
        store=True,
        help="Tỷ lệ phần trăm Tổng MM trên BMM"
    )


    @api.depends('en_bmm', 'mm_conversion')
    def _compute_bmm_mm_conversion(self):
        for rec in self:
            #BMM
            old_val = round(rec.bmm_percent,2)
            bmm = float(rec.en_bmm or 0.0)
            total_mm  = float(rec.mm_conversion or 0.0)

            # % BMM
            if bmm and total_mm:
                rec.bmm_percent = (total_mm / bmm) * 100
            else:
                rec.bmm_percent = 0.0

            new_val = round(rec.bmm_percent,2)
            # [TK3885] Hiển thị cảnh báo nếu vượt ngưỡng
            if rec.bmm_percent > 100 and rec.bmm_percent <= 105 and old_val != new_val:
                rec.env.user.notify_warning(
                    message="KHNL có nguồn lực dự kiến vượt quá 100% BMM, cần Giám đốc khối phê duyệt khi gửi",
                    title="Nhắc nhở",
                    sticky=False,
                )
            if rec.bmm_percent > 105 and old_val != new_val:
                rec.env.user.notify_warning(
                    message="KHNL có nguồn lực dự kiến vượt quá 105% BMM, không cho phép gửi duyệt",
                    title="Nhắc nhở",
                    sticky=False,
                )

    @api.constrains('project_id', 'state')
    def _constrains_no_more_than_one(self):
        if self._context.get('import_file') and any(rec.sudo().search_count([('project_id', '=', rec.project_id.id), ('state', 'in', ['draft', 'to_approve'])]) > 1 for rec in self):
            raise exceptions.ValidationError('Hiện tại đang có bản ghi KHNL chưa được duyệt, vui lòng duyệt để tạo bản ghi KHNL mới')

    @api.constrains('order_line')
    def _constrains_workload_gather_0(self):
        for line in self.order_line:
            if not line.workload > 0:
                raise exceptions.ValidationError(f'Nhân viên {line.employee_id.display_name} trong khoảng thời gian {line.date_start.strftime("%d/%m/%Y")} → {line.date_end.strftime("%d/%m/%Y")} không thể nhập workload nhỏ hơn hoặc bằng 0')

    @api.model
    def get_project_name(self):
        self = self.env['en.resource.planning'].browse(self._context.get('active_ids'))
        return f'Sơ đồ tổ chức dự án {self.project_id.name}'

    def to_org_chart(self):
        self = self.sudo()
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        report_action = 'ngsd_base.action_org_chart_overview'
        action = self.env.ref(report_action)
        record_url = f'{base_url}/web#active_id={self.id}&action={action.id}'
        client_action = {
            'type': 'ir.actions.act_url',
            'name': f'Sơ đồ tổ chức dự án {self.project_id.name}',
            'url': record_url,
        }
        return client_action

    def _get_employee_domain(self, parent_id):
        domain = []
        if not parent_id:
            domain.extend([("parent_id", "=", False)])
        else:
            domain.append(("parent_id", "=", parent_id))
        return domain

    def _get_employee_data(self, level=0, position=False):
        records = self.order_line.filtered(lambda x: x.job_position_id.id == position)
        record = self.env['en.job.position'].browse(position)
        a = []
        for r in records:
            if f'{r.employee_id.display_name} - {r.role_id.display_name}' not in a:
                a += [f'{r.employee_id.display_name} - {r.role_id.display_name}']
        return {
            "id": record.id,
            "name": record.name,
            "title": '<br/>'.join(a),
            "className": org_chart_classes[level],
        }

    @api.model
    def _get_children_data(self, child_ids, level):
        children = []
        # default_domain = [('id', 'in', self.mapped('order_line.job_position_id').ids)]
        default_domain = []
        for employee in child_ids:
            data = self._get_employee_data(level, employee.id)
            employee_child_ids = self.env['en.job.position'].search(default_domain + self._get_employee_domain(employee.id))
            if employee_child_ids:
                data.update({"children": self._get_children_data(employee_child_ids, (level + 1) % 5)})
            children.append(data)
        return children

    @api.model
    def get_organization_data(self):
        self = self.env['en.resource.planning'].browse(self._context.get('active_ids'))
        # First get employee with no manager
        data = {"id": None, "name": "", "title": "", "children": []}
        if not self: return data
        # default_domain = [('id', 'in', self.mapped('order_line.job_position_id').ids)]
        default_domain = []
        domain = default_domain + self._get_employee_domain(False)
        top_employees = self.env['en.job.position'].search(domain)
        for top_employee in top_employees:
            child_data = self._get_employee_data(position=top_employee.id)
            # If any child we fetch data recursively for childs of top employee
            top_employee_child_ids = self.env['en.job.position'].search(default_domain + self._get_employee_domain(top_employee.id))
            if top_employee_child_ids:
                child_data.update({"children": self._get_children_data(top_employee_child_ids, 1)})
            data.get("children").append(child_data)
        return data

    @api.constrains('project_id', 'state')
    def _constrains_project_id_state(self):
        if self._context.get('import_file') and any(self.env['en.resource.planning'].search_count([('project_id', '=', rec.project_id.id), ('state', '=', 'draft')]) > 1 for rec in self):
            raise exceptions.ValidationError(f'Bạn không thể tạo hai KHNL ở trạng thái dự kiến ')

    def action_open_new_tab(self):
        return self.open_form_or_tree_view('ngsd_base.resource_planning_act', False, self, {'default_project_id': self.id})

    en_state = fields.Selection(string='Trạng thái', related='project_id.en_state')
    # TODO TK3146 không sử dụng nữa chậm performance
    # def write(self, vals):
    #     before_state = {rec: rec.state for rec in self}
    #     res = super().write(vals)
    #     for rec in self:
    #         if rec.state == before_state.get(rec): continue
    #         newest_resource = self.env['en.resource.planning'].search([('project_id', '=', rec.project_id.id)], order='id desc', limit=1)
    #         # for wbs in self.env['en.wbs'].search([('resource_plan_id', '=', rec.id)], order='id desc', limit=1):
    #         # if rec.state == 'expire':
    #         #     for wbs in self.env['en.wbs'].search([('resource_plan_id', '=', rec.id)], order='technical_field_before desc,technical_field_after desc', limit=1):
    #         #         new_wbs = wbs.copy({'version_type': 'plan', 'resource_plan_id': newest_resource.id})
    #         #         for stage in wbs.project_stage_ids:
    #         #             stage.with_context(newest_resource=newest_resource.id).copy({'wbs_version': new_wbs.id})
    #         if rec.state == 'approved':
    #             for line in rec.order_line:
    #                 if not line.role_id or not line.en_user_id: continue
    #                 from_groups_with_love = line.role_id.sudo().should_we_make_group()
    #                 if not from_groups_with_love: continue
    #                 from_groups_with_love.sudo().write({'users': [(4, line.en_user_id.id)]})
    #         if rec.state != 'approved' and before_state.get(rec) == 'approved':
    #             for line in rec.order_line:
    #                 if not line.role_id or not line.en_user_id: continue
    #                 if not self.env['en.resource.detail'].search([('en_user_id', '=', line.en_user_id.id), ('order_id', '!=', line.order_id.id), ('order_id.state', '=', 'approved')]):
    #                     from_groups_with_love = line.role_id.sudo().should_we_make_group()
    #                     if not from_groups_with_love: continue
    #                     from_groups_with_love.sudo().write({'users': [(3, line.en_user_id.id)]})
    #     return res

    technical_field_27766 = fields.Boolean(string='🚑', compute='_compute_technical_field_27766')

    @api.depends('state', 'project_id')
    def _compute_technical_field_27766(self):
        for rec in self:
            technical_field_27766 = False
            if rec.state not in ['approved', 'refused'] or not rec.project_id:
                rec.technical_field_27766 = technical_field_27766
                continue
            if self.env['en.resource.planning'].search_count([('project_id', '=', rec.project_id.id), ('state', '=', 'draft')]) >= 1:
                rec.technical_field_27766 = technical_field_27766
                continue
            if rec._origin.id == self.env['en.resource.planning'].search([('project_id', '=', rec.project_id.id)], order='id desc', limit=1).id or rec._origin.id == self.env['en.resource.planning'].search([('project_id', '=', rec.project_id.id), ('state', '=', 'approved')], order='id desc', limit=1).id:
                technical_field_27766 = True
            rec.technical_field_27766 = technical_field_27766

    def new_resource(self):
        if not self.technical_field_27766: return
        order_line = []
        for line in self.order_line:
            if (line.employee_id.en_day_layoff_from
                and line.employee_id.en_day_layoff_to and line.employee_id.en_day_layoff_from <= line.date_start
                and line.employee_id.en_day_layoff_to >= line.date_end) or (
                    line.employee_id.departure_date and line.employee_id.departure_date <= line.date_start) or \
                    (line.employee_id.en_day_layoff_from and line.employee_id.en_day_layoff_to and line.employee_id.departure_date
                     and line.employee_id.en_day_layoff_from <= line.date_start and (line.employee_id.en_day_layoff_to == line.employee_id.departure_date or line.employee_id.en_day_layoff_to + relativedelta(days=1) == line.employee_id.departure_date)
                     and line.date_end >= line.employee_id.departure_date):
                continue
            value = {
                'type_id': line.type_id.id,
                'employee_id': line.employee_id.id,
                'role_id': line.role_id.id,
                'job_position_id': line.job_position_id.id,
                'workload': line.workload,
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
        resource_new = self.create(values)
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
        # return self.open_form_or_tree_view('ngsd_base.resource_planning_act', False, False, values, 'Tạo phiên bản mới', 'current')

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        # raise UserError('Bạn không được phép tạo KHNL tại thời điểm này')
        default = dict(default or {})
        order_line = []
        for line in self.order_line:
            # if line.date_end < fields.Date.today(): continue
            order_line += [(0, 0, {
                'type_id': line.type_id.id,
                'employee_id': line.employee_id.id,
                # 'en_replacement_staff': line.en_replacement_staff.id,
                'role_id': line.role_id.id,
                'job_position_id': line.job_position_id.id,
                'date_start': line.date_start,
                'date_end': line.date_end,
                'workload': line.workload,
                'old_line_id': line.id,
            })]
        default['order_line'] = order_line
        return super().copy(default)

    def button_resource_account_report_wizard_act(self):
        return self.open_form_or_tree_view('account_reports.resource_account_report_wizard_act', False, False, {'default_resource_planing_id': self.id}, 'Thông tin nguồn lực', 'new')

    def unlink(self):
        for rec in self:
            if rec.state in READONLY_STATES.keys():
                raise exceptions.UserError(f"Bản ghi đang ở trạng thái {dict(rec.fields_get(['state'])['state']['selection'])[rec.state]} . Không thể xóa bản ghi này !")
        return super().unlink()

    # @api.constrains('order_line', 'project_id')
    def _constrains_overload(self):
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        for rec in self:
            if rec.project_id.igone_overload:
                continue
            order_lines = rec.order_line.filtered(lambda l: l.employee_id.en_internal_ok)
            if not order_lines:
                continue
            employee_ids = order_lines.mapped('employee_id').ids
            date_min = min(order_lines.mapped('date_start'))
            date_max = max(order_lines.mapped('date_end'))
            resource_details = self.env['en.resource.detail'].search([
                ('employee_id', 'in', employee_ids),
                ('date_start', '<=', date_max),
                ('date_end', '>=', date_min),
                '|',
                ('order_id', '=', rec.id),
                '&',
                ('order_id.state', '=', 'approved'),
                ('order_id.project_id', '!=', rec.project_id.id),
            ])
            workload_by_date = defaultdict(float)
            for detail in resource_details:
                for d in date_utils.date_range(datetime.combine(detail.date_start, datetime.min.time()),
                        datetime.combine(detail.date_end, datetime.min.time()), step=relativedelta(days=1)):
                    workload_by_date[(detail.employee_id.id, d)] += detail.workload or 0.0
            groupby_overwork = defaultdict(list)
            for line in order_lines:
                emp_id = line.employee_id.id
                key = f"Nhân viên {line.employee_id.display_name} ở vị trí {line.job_position_id.display_name} đã bị quá workload vào ngày"
                for d in date_utils.date_range(
                        datetime.combine(line.date_start, datetime.min.time()),
                        datetime.combine(line.date_end, datetime.min.time()),
                        step=relativedelta(days=1)):
                    if round(workload_by_date[(emp_id, d)], 10) > 1.2:
                        groupby_overwork[key].append(d)

            def format_ranges(dates):
                dates = sorted(set(dates))
                ranges, start = [], dates[0]
                for i in range(1, len(dates)):
                    if dates[i] != dates[i - 1] + relativedelta(days=1):
                        ranges.append((start, dates[i - 1]))
                        start = dates[i]
                ranges.append((start, dates[-1]))
                return [
                    f"{s.strftime(lg.date_format)}" if s == e else f"{s.strftime(lg.date_format)} → {e.strftime(lg.date_format)}"
                    for s, e in ranges]
            expt_txt = [f"{msg} {' và '.join(format_ranges(dates))}" for msg, dates in groupby_overwork.items() if dates]
            if expt_txt:
                raise exceptions.ValidationError('\n'.join(expt_txt))

    def button_to_approve(self):
        rslt = self.button_sent()
        if not rslt: return
        self._constrains_overload()
        self.order_line.check_date_resource()
        self.order_line.check_date_resource_1()
        if self.approver_id: self.send_notify(f'Bạn có kế hoạch {self.display_name} cần được duyệt', self.approver_id)
        self.write({'state': 'to_approve'})

    def button_approved(self):
        self = self.sudo()

        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
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
        rslt = super(ResourcePlanning, self).button_approved()
        if rslt:
            self.write({'seq_id': int(self.env['ir.sequence'].next_by_code('seq.id'))})
            self.sudo().search([('project_id', '=', self.project_id.id), ('id', '<', self.id), ('state', '=', 'approved')]).sudo().write({'state': 'expire'})
        return rslt

    approver_id = fields.Many2one(string='Người phê duyệt', states=READONLY_STATES, comodel_name='res.users')
    reason = fields.Char(string='Lý do từ chối', states=READONLY_STATES, copy=False, readonly=True)
    state = fields.Selection(string='Trạng thái', selection=[('draft', 'Dự kiến'), ('to_approve', 'Chờ duyệt'), ('approved', 'Đã duyệt'), ('refused', 'Từ chối'), ('expire', 'Hết hiệu lực')], default='draft', readonly=True, required=True, copy=False, index=True)

    def draft_state(self):
        return 'draft'

    def sent_state(self):
        return 'to_approve'

    def approved_state(self):
        return 'approved'

    def refused_state(self):
        return 'refused'

    name = fields.Char(string='Tên', default=lambda self: f"[{self.version_number}] {dict(self.fields_get(['version_type'])['version_type']['selection'])[self.version_type] if self.version_type else ''}", states=EDIT_DRAFT_STATES, required=True)
    project_id = fields.Many2one(string='Dự án', states=READONLY_STATES, comodel_name='project.project', required=True)

    def get_flow_domain(self):
        return [('model_id.model', '=', self._name), '|', ('project_ids', '=', self.project_id.id), ('project_ids', '=', False)]

    project_code = fields.Char(related='project_id.en_code', string='Mã dự án')
    user_id = fields.Many2one(string='Người tạo', states=EDIT_DRAFT_STATES, comodel_name='res.users', default=lambda self: self.env.user, required=True)
    order_line = fields.One2many(string='Chi tiết nguồn lực', states=EDIT_DRAFT_STATES, comodel_name='en.resource.detail', inverse_name='order_id', copy=False)

    resource_total = fields.Float(string='Tổng nguồn lực (MM)', compute_sudo=True, compute='_compute_resource_total')
    resource_total_rate = fields.Float(default=1)
    increase_resource_total = fields.Boolean('Tăng nguồn lực với phiên bản cũ', compute='_compute_increase_resource_total', store=True)

    @api.depends('en_md', 'project_id.en_resource_id')
    def _compute_increase_resource_total(self):
        for rec in self:
            rec.increase_resource_total = False
            if (rec.project_id.en_resource_id and round(rec.project_id.en_resource_id.en_md, 2) < round(rec.en_md, 2)) or not rec.project_id.en_resource_id:
                rec.increase_resource_total = True


    @api.depends('order_line.mm', 'order_line.workload', 'order_line')
    def _compute_resource_total(self):
        for rec in self:
            rec.resource_total = sum(line.mm * line.workload for line in rec.order_line) * rec.resource_total_rate

    budget_over = fields.Float(string='% vượt mức budget', compute_sudo=True, compute='_compute_budget_over')

    @api.depends('resource_total', 'project_id.en_bmm')
    def _compute_budget_over(self):
        for rec in self:
            budget_over = 0
            if rec.project_id.en_bmm:
                budget_over = (rec.mm_conversion - rec.project_id.en_bmm) / rec.project_id.en_bmm
            rec.budget_over = max([budget_over, 0])

    baseline_over = fields.Float(string='% vượt mức baseline', compute_sudo=True, compute='_compute_baseline_over')

    @api.depends('mm_conversion', 'parent_id.mm_conversion', 'parent_id')
    def _compute_baseline_over(self):
        for rec in self:
            baseline_over = 0
            if rec.parent_id.mm_conversion:
                baseline_over = (rec.mm_conversion - rec.parent_id.mm_conversion) / rec.parent_id.mm_conversion
            rec.baseline_over = max([baseline_over, 0])

    confirm_user_approved = fields.Selection(string="Xác định người duyệt", selection=[
        ('v1', 'KHNL max > KHNL new'),
        ('v2', 'BMM > KHNL new > KHNL max'),
        ('v3', 'KHNL new > BMM > KHNL max'),
        ('v4', 'KHNL đầu tiên'),
        ], required=False, compute='_compute_confirm_user_approved', store=True, compute_sudo=True)

    @api.depends('mm_conversion', 'project_id.en_resource_ids.state', 'project_id.en_resource_ids')
    def _compute_confirm_user_approved(self):
        for rec in self:
            if not any(resource.state in ['approved', 'expire'] for resource in rec.project_id.en_resource_ids):
                rec.confirm_user_approved = 'v4'
            else:
                if any(round(resource.mm_conversion, 2) >= round(rec.mm_conversion, 2) for resource in rec.project_id.en_resource_ids.filtered(lambda x: x.state in ['approved', 'expire'])):
                    rec.confirm_user_approved = 'v1'
                else:
                    if round(rec.mm_conversion, 2) > rec.en_bmm:
                        rec.confirm_user_approved = 'v3'
                    else:
                        rec.confirm_user_approved = 'v2'


    def _compute_sent_ok(self):
        for rec in self:
            rec.sent_ok = True

    def read(self, fields=None, load='_classic_read'):
        # if not fields or 'order_line' in fields or 'en_md' in fields or 'hours_total' in fields:
        #     self.filtered(lambda d: d.state not in ['approved', 'expire']).order_line._compute_hours_indate()
        return super().read(fields, load)

    count_approver = fields.Integer(string='Số cấp duyệt', compute='_count_approver')

    def _count_approver(self):
        for rec in self:
            rec.count_approver = len(rec.en_approve_line_ids)

    def action_open_tree_for_export(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Kế hoạch nguồn lực',
            'res_model': 'en.resource.planning',
            'view_mode': 'tree,form',
            'target': 'current',
            'domain': [('id', 'in', self.ids)],
            'context': {
                'show_export_hint': True,
            },
        }


class ResourceDetail(models.Model):
    _name = 'en.resource.detail'
    _description = 'Chi tiết nguồn lực'

    en_used_hour = fields.Float(string='Số giờ đã sử dụng', compute='_compute_en_used_hour')
    old_line_id = fields.Many2one('en.resource.detail', string='Line cũ', readonly=True, copy=False)

    @api.depends('employee_id', 'order_id')
    def _compute_en_used_hour(self):
        for rec in self:
            en_used_hour = 0
            wbs_ids = rec.order_id.project_id.en_wbs_ids
            create_date = rec.order_id.create_date or fields.Datetime.now()
            create_date = timezone('UTC').localize(create_date).astimezone(timezone(self.env.user.tz or 'UTC')).replace(tzinfo=None)
            create_date = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(create_date.date(), time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
            if not self.env['en.resource.planning'].search([('project_id', '=', rec.order_id.project_id.id), ('state', '=', 'approved'), ('id', '<', rec.order_id._origin.id)]):
                rec.en_used_hour = en_used_hour
                continue
            wbs_id_lt = self.env['en.wbs'].search([('id', 'in', wbs_ids.ids), ('version_type', '=', 'baseline'), ('create_date', '<=', create_date)], limit=1, order='create_date desc')
            wbs_id_gt = self.env['en.wbs'].search([('id', 'in', wbs_ids.ids), ('version_type', '=', 'baseline'), ('create_date', '>=', create_date)], limit=1, order='create_date asc')
            wbs_id = self.env['en.wbs']
            if not wbs_id_lt:
                wbs_id = wbs_id_gt
            if not wbs_id_gt:
                wbs_id = wbs_id_lt
            if wbs_id_lt and wbs_id_gt:
                if (wbs_id_gt.create_date - create_date).total_seconds() < (create_date - wbs_id_lt.create_date).total_seconds():
                    wbs_id = wbs_id_gt
                else:
                    wbs_id = wbs_id_lt
            if not wbs_id:
                rec.en_used_hour = en_used_hour
                continue
            min_id = self.env['en.resource.detail'].search([('order_id.project_id', '=', rec.order_id.project_id.id), ('employee_id', '=', rec.employee_id.id), ('order_id', '=', rec.order_id._origin.id)], limit=1, order='id asc')
            if rec._origin.id != min_id.id:
                rec.en_used_hour = en_used_hour
                continue
            en_task_position = self.env['en.workpackage'].search([('id', 'child_of', wbs_id.workpackage_ids.ids)])
            tasks = self.env['project.task'].search([('en_handler', '=', rec.employee_id.user_id.id), ('en_task_position', 'in', en_task_position.ids)])
            effective_hours = sum(tasks.mapped('effective_hours'))
            a = 0
            plannings = self.env['en.resource.planning'].search([('project_id', '=', rec.order_id.project_id.id), ('order_line.employee_id', '=', rec.employee_id.id), ('id', '<', rec.order_id._origin.id), ('state', 'in', ['approved', 'expire'])], limit=1, order='create_date desc')
            for p in plannings:
                for l in p.order_line:
                    if l.employee_id != rec.employee_id: continue
                    effective_hours += l.en_used_hour
                    a += l.en_used_hour
            planning_id = self.env['en.resource.planning'].search([('project_id', '=', rec.order_id.project_id.id), ('id', '<', rec.order_id._origin.id), ('state', 'in', ['approved', 'expire'])], limit=1, order='create_date desc')
            for l in planning_id.order_line:
                if l.employee_id != rec.employee_id: continue
                ltime_start = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(l.date_start, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                ltime_end = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(l.date_end, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                if ltime_end <= create_date:
                    a += l.mh * l.workload
                    continue
                if ltime_start > create_date: continue

                datetime_from = ltime_start
                datetime_to = min([ltime_end, create_date])
                employee = rec.employee_id
                calendar = employee.resource_calendar_id
                datetime_start = datetime_from
                datetime_end = datetime_to
                workrange_hours = calendar.get_work_hours_count(datetime_start, datetime_end, compute_leaves=False)
                range_leave_intervals = employee.list_leaves(datetime_start, datetime_end)
                for day, hours, leave in range_leave_intervals:
                    workrange_hours -= hours

                a += workrange_hours * l.workload
            en_used_hour = max(a, effective_hours)
            rec.en_used_hour = en_used_hour

    en_user_id = fields.Many2one(string='User của nhân viên', related='employee_id.user_id')
    order_id = fields.Many2one(string='Kế hoạch nguồn lực', comodel_name='en.resource.planning', required=True, ondelete='cascade', index=True, auto_join=True)
    type_id = fields.Many2one(string='Loại', comodel_name='en.type', compute_sudo=True, compute='_compute_type_id', required=True, store=True, readonly=False)
    employee_id = fields.Many2one(string='Tên nhân sự', comodel_name='hr.employee', required=True, domain="[('en_type_id','=?',type_id), ('id', 'in', employee_ids)]", context={'active_test': False}, index=True)
    en_replacement_staff = fields.Many2one(string='Thay thế cho nhân viên', comodel_name='hr.employee', domain="[('en_type_id','=?',type_id)]", context={'active_test': False})
    employee_ids = fields.Many2many('hr.employee', compute='_compute_employee_domain', context={'active_test': False})

    @api.depends('order_id.project_id', 'order_id.project_id.en_resource_project_ids')
    def _compute_employee_domain(self):
        for rec in self:
            employee_ids = []
            for line in rec.order_id.project_id.en_resource_project_ids:
                    employee_ids.append(line.employee_id.id)
            rec.employee_ids = [(6, 0, employee_ids)]

    @api.onchange('type_id')
    def onchange_type_id(self):
        if self.employee_id and self.employee_id.en_type_id != self.type_id:
            self.employee_id = False
            # self.en_replacement_staff = False
            self.workload = 0

    @api.depends('employee_id')
    def _compute_type_id(self):
        for rec in self:
            type_id = rec.type_id
            if rec.employee_id and rec.employee_id.en_type_id != rec.type_id:
                type_id = rec.employee_id.en_type_id
            rec.type_id = type_id

    email = fields.Char(string='Email', related='employee_id.work_email')
    role_id = fields.Many2one(string='Vai trò', comodel_name='en.role', required=True, domain="[('id', 'in', role_ids)]")
    role_ids = fields.Many2many(string='Vai trò', comodel_name='en.role', compute='_compute_role')
    job_position_id = fields.Many2one(string='Vị trí', comodel_name='en.job.position', required=True, domain="[('id', 'in', job_position_ids)]")
    job_position_ids = fields.Many2many(string='Vị trí', comodel_name='en.job.position', compute='_compute_role')
    date_start = fields.Date(string='Thời gian bắt đầu', required=True, index=True)
    edit_date_start = fields.Boolean(compute='_get_readonly_date')
    edit_date_end = fields.Boolean(compute='_get_readonly_date')
    project_stage_id = fields.Many2one('en.project.stage', 'Giai đoạn', domain="[('id', 'in', project_stage_ids)]")
    project_stage_ids = fields.Many2many('en.project.stage', 'Giai đoạn', compute='_compute_project_stage')
    no_delete_line = fields.Boolean(compute='_compute_no_delete_line')

    @api.depends('date_start', 'date_end')
    def _compute_no_delete_line(self):
        today = date.today()
        month_check = today - relativedelta(months=1, day=1)
        if today.day > 5:
            month_check = today + relativedelta(day=1)
        for rec in self:
            no_delete_line = False
            if (rec.date_start and not rec.date_start >= month_check) or (rec.date_end and not rec.date_end >= month_check):
                no_delete_line = True
            rec.no_delete_line = no_delete_line

    @api.depends('order_id.project_id', 'order_id.project_id.en_current_version')
    def _compute_project_stage(self):
        for rec in self:
            rec.project_stage_ids = rec.order_id.project_id.en_current_version.project_stage_ids if rec.order_id.project_id.en_current_version else False

    @api.depends('employee_id')
    def _compute_role(self):
        for rec in self:
            resource_project = self.env['resource.project'].search([('project_id', '=', rec.order_id.project_id.id), ('employee_id', '=', rec.employee_id.id)])
            rec.role_ids = resource_project.role_ids if resource_project else False
            rec.job_position_ids = resource_project.en_job_position_ids if resource_project else False

    @api.onchange('employee_id')
    def _onchange_employee_data(self):
        for rec in self:
            if rec.employee_id:
                resource = rec.order_id.project_id.en_resource_project_ids.filtered(lambda x: x.employee_id == rec.employee_id and x.state == 'active')
                if not rec.old_line_id and not rec.order_id.parent_id:
                    rec.date_start = resource.date_start
                    rec.date_end = resource.date_end
                rec.role_id = resource.role_ids[0].id if resource.role_ids else False
                rec.job_position_id = resource.en_job_position_ids[0].id if resource.en_job_position_ids else False

    @api.depends('date_start', 'date_end')
    def _get_readonly_date(self):
        for rec in self:
            today_month = fields.Date.Date.context_today(rec)
            date_today = today_month.day
            month_pre = (today_month - relativedelta(months=1)).replace(day=1)
            month_current = today_month.replace(day=1)
            rec.edit_date_start = False
            rec.edit_date_end = False
            if not rec.old_line_id:
                rec.edit_date_start = True
                rec.edit_date_end = True
            else:
                if date_today <= 5:
                    if rec.date_start >= month_pre:
                        rec.edit_date_start = True
                    if rec.date_end >= month_pre:
                        rec.edit_date_end = True
                else:
                    if rec.date_start >= month_current:
                        rec.edit_date_start = True
                    if rec.date_end >= month_current:
                        rec.edit_date_end = True

            # rec.edit_date_start = not rec.date_start or rec.date_start >= fields.Date.Date.context_today(rec) or not rec.old_line_id or rec.employee_id.en_type_id.is_hidden
            # rec.edit_date_end = not rec.date_end or rec.date_end >= fields.Date.Date.context_today(rec) or not rec.old_line_id or rec.employee_id.en_type_id.is_hidden

    @api.onchange('date_start')
    def _onchange_check_date_start(self):
        for rec in self:
            today_month = fields.Date.Date.context_today(rec)
            date_today = today_month.day
            month_pre = (today_month - relativedelta(months=1)).replace(day=1)
            month_current = today_month.replace(day=1)
            if rec.old_line_id:
                if date_today <= 5:
                    if rec.date_start and rec.date_start < month_pre:
                        raise exceptions.ValidationError(f'Giá trị ngày bắt đầu phải lớn hơn hoặc bằng {month_pre.strftime("%d/%m/%Y")}')
                else:
                    if rec.date_start and rec.date_start < month_current:
                        raise exceptions.ValidationError(f'Giá trị ngày bắt đầu phải lớn hơn hoặc bằng {month_current.strftime("%d/%m/%Y")}')

    @api.onchange('date_end')
    def _onchange_check_date_end(self):
        for rec in self:
            today_month = fields.Date.Date.context_today(rec)
            date_today = today_month.day
            month_pre = (today_month - relativedelta(months=1)).replace(day=1)
            month_current = today_month.replace(day=1)
            if rec.old_line_id :
                if date_today <= 5:
                    if rec.date_end and rec.date_end < month_pre:
                        raise exceptions.ValidationError(f'Giá trị ngày kết thúc phải lớn hơn hoặc bằng {month_pre.strftime("%d/%m/%Y")}')
                else:
                    if rec.date_end and rec.date_end < month_current:
                        raise exceptions.ValidationError(f'Giá trị ngày kết thúc phải lớn hơn hoặc bằng {month_current.strftime("%d/%m/%Y")}')

    @api.onchange('date_start')
    def onchange_date_start(self):
        if not self.employee_id or not self.employee_id.en_date_start:
            self.date_start = False
        if self.employee_id and self.employee_id and self.employee_id.en_date_start and self.date_start and self.date_start < self.employee_id.en_date_start:
            self.date_start = False

    date_end = fields.Date(string='Thời gian kết thúc', required=True, index=True)
    workload = fields.Float(string='Workload', default=0, required=False, readonly=False, compute='_compute_en_md_workload', store=True)

    def check_date_resource(self):
        for rec in self:
            if rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.employee_id.en_day_layoff_from >= rec.date_start and rec.employee_id.en_day_layoff_from <= rec.date_end:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
                if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from and rec.date_start <= rec.employee_id.en_day_layoff_to:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
                if rec.date_end and rec.employee_id.en_day_layoff_from >= rec.date_end and rec.employee_id.en_day_layoff_to <= rec.date_end:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
                if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from and rec.date_end <= rec.employee_id.en_day_layoff_to:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
            elif rec.employee_id.en_day_layoff_from and not rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}')
                if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}')
            elif not rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.date_start <= rec.employee_id.en_day_layoff_to:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
                if rec.date_end and rec.date_end <= rec.employee_id.en_day_layoff_to:
                    raise exceptions.UserError(
                        f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}')
            elif rec.employee_id.departure_date and rec.date_start and rec.employee_id.departure_date <= rec.date_start:
                raise exceptions.UserError(
                    f'Nhân sự {rec.employee_id.name} có ngày dừng {rec.employee_id.departure_date.strftime("%d/%m/%Y")}')
            if rec.date_start and rec.order_id.project_id.date_start and rec.date_start < rec.order_id.project_id.date_start:
                raise exceptions.UserError('Thời gian bắt đầu sử dụng nguồn lực không được nhỏ hơn thời gian bắt đầu dự án!')
            # if rec.date_end and rec.order_id.project_id.date and rec.date_end > rec.order_id.project_id.date:
            #     raise exceptions.UserError('KHNL phải nằm trong thời gian bắt đầu và kết thúc dự án')
            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                raise exceptions.UserError(f'Thời gian kết thúc sử dụng nguồn lực {rec.employee_id.display_name} ở {rec.job_position_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {rec.date_start.strftime("%d/%m/%Y")}.')

    @api.onchange('date_start', 'date_end', 'employee_id')
    def _constrains_date_start(self):
        for rec in self:
            expt_txt = ''
            if rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.employee_id.en_day_layoff_from >= rec.date_start and rec.employee_id.en_day_layoff_from <= rec.date_end:
                    expt_txt = f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
                if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from and rec.date_start <= rec.employee_id.en_day_layoff_to:
                    expt_txt = f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
                if rec.date_end and rec.employee_id.en_day_layoff_from >= rec.date_end and rec.employee_id.en_day_layoff_to <= rec.date_end:
                    expt_txt = f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
                if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from and rec.date_end <= rec.employee_id.en_day_layoff_to:
                    expt_txt = f'Nhân sự {rec.employee_id.name} đang tạm dừng trong khoảng thời gian {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")} - {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
            elif rec.employee_id.en_day_layoff_from and not rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.date_start >= rec.employee_id.en_day_layoff_from:
                    expt_txt = f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}'
                if rec.date_end and rec.date_end >= rec.employee_id.en_day_layoff_from:
                    expt_txt = f'Nhân sự {rec.employee_id.name} có ngày bắt đầu tạm dừng {rec.employee_id.en_day_layoff_from.strftime("%d/%m/%Y")}'
            elif not rec.employee_id.en_day_layoff_from and rec.employee_id.en_day_layoff_to:
                if rec.date_start and rec.date_start <= rec.employee_id.en_day_layoff_to:
                    expt_txt = f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
                if rec.date_end and rec.date_end <= rec.employee_id.en_day_layoff_to:
                    expt_txt = f'Nhân sự {rec.employee_id.name} có ngày kết thúc tạm dừng {rec.employee_id.en_day_layoff_to.strftime("%d/%m/%Y")}'
            elif rec.employee_id.departure_date and rec.date_start and rec.employee_id.departure_date <= rec.date_start:
                expt_txt = f'Nhân sự {rec.employee_id.name} có ngày dừng {rec.employee_id.departure_date.strftime("%d/%m/%Y")}'
            if rec.date_start and rec.order_id.project_id.date_start and rec.date_start < rec.order_id.project_id.date_start:
                expt_txt = 'Thời gian bắt đầu sử dụng nguồn lực không được nhỏ hơn thời gian bắt đầu dự án!'

            if rec.date_start and rec.date_end and rec.date_start > rec.date_end:
                expt_txt = f'Thời gian kết thúc sử dụng nguồn lực {rec.employee_id.display_name} ở {rec.job_position_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {rec.date_start.strftime("%d/%m/%Y")}.'
            if expt_txt:
                self.env.user.notify_warning(expt_txt, 'Cảnh báo')

    def check_date_resource_1(self):
        for rec in self:
            resource_project = self.order_id.project_id.en_resource_project_ids.filtered(lambda x: x.employee_id == rec.employee_id and x.date_start and x.date_end)
            in_project = False
            expt_txt = ''
            for resource in resource_project:
                if rec.date_start and resource.date_start <= rec.date_start <= resource.date_end and rec.date_end and resource.date_start <= rec.date_end <= resource.date_end:
                    in_project = True
                    break
                else:
                    expt_txt = f'Thời gian sử dụng nguồn lực {rec.employee_id.display_name} không được nằm ngoài thời gian trong danh sách nhân sự'
            else:
                expt_txt = f'Thời gian sử dụng nguồn lực {rec.employee_id.display_name} không được nằm ngoài thời gian trong danh sách nhân sự'
            if not in_project:
                raise exceptions.UserError(expt_txt)

    @api.constrains('date_start', 'date_end', 'employee_id', 'workload')
    def check_workload_borrow(self):
        for rec in self:
            resource_project = self.order_id.project_id.en_resource_project_ids.filtered(lambda x: x.employee_id == rec.employee_id and x.is_borrow)
            if resource_project:
                department_resources = self.order_id.project_id.en_department_id.employee_borrow_ids.filtered(lambda x: x.employee_id == rec.employee_id and  x.date_start <= rec.date_start and rec.date_end <= x.date_end)
                for department_resource in department_resources:
                    if rec.workload > department_resource.workload:
                        expt_txt = f'KHNL nhân sự {rec.employee_id.display_name} thời gian từ {rec.date_start.strftime("%d/%m/%Y")} đến {rec.date_end.strftime("%d/%m/%Y")} có workload vượt quá workload đi mượn'
                        raise exceptions.UserError(expt_txt)

    @api.constrains('date_end', 'date_start', 'employee_id')
    def _constrain_date_employee_resource(self):
        for rec in self:
            resource_project = self.order_id.project_id.en_resource_project_ids.filtered(lambda x: x.employee_id == rec.employee_id)
            in_project = False
            expt_txt = ''
            for resource in resource_project:
                if rec.date_start and resource.date_start <= rec.date_start <= resource.date_end and rec.date_end and resource.date_start <= rec.date_end <= resource.date_end:
                    in_project = True
                    break
                else:
                    expt_txt = f'Thời gian sử dụng nguồn lực {rec.employee_id.display_name} không được nằm ngoài thời gian trong danh sách nhân sự'
            else:
                expt_txt = f'Thời gian sử dụng nguồn lực {rec.employee_id.display_name} không được nằm ngoài thời gian trong danh sách nhân sự'
            if not in_project:
                self.env.user.notify_warning(expt_txt, 'Cảnh báo')

    @api.onchange('date_start')
    def _onchange_date_start(self):
        if self.date_start and self.date_end and self.date_start > self.date_end:
            return {'warning': {
                'title': 'Cảnh báo',
                'message': f'Thời gian kết thúc sử dụng nguồn lực {self.employee_id.display_name} ở {self.job_position_id.display_name} không thể nhỏ hơn thời gian bắt đầu là {self.date_start.strftime("%d/%m/%Y")}.'
            }}

    # @api.onchange('date_end')
    # def _onchange_date_date_end(self):
    #     if self.order_id.version_number != '0.1' and not self._context.get('allow_date_end') and self.date_end and self.date_end < fields.Date.today():
    #         self.date_end = fields.Date.today()

    mh = fields.Float(string='🤣', compute_sudo=True, compute='_compute_m_uom', store=True)
    md = fields.Float(string='🤣', compute_sudo=True, compute='_compute_m_uom', store=True)
    mm = fields.Float(string='🤣', compute_sudo=True, compute='_compute_m_uom', store=True)

    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_m_uom(self):
        todate = fields.Date.today()

        for rec in self:
            mm = 0
            md = 0
            mh = 0
            if not rec.employee_id or not rec.date_start or not rec.date_end:
                rec.mm = mm
                rec.md = md
                rec.mh = mh
                continue
            min_date = min([rec.date_start, rec.date_end])
            max_date = max([rec.date_start, rec.date_end])
            date_from = min_date + relativedelta(day=1)
            date_to = max_date + relativedelta(day=1, months=1, days=-1)
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
            employee = rec.employee_id
            calendar = employee.resource_calendar_id
            for date_step in date_utils.date_range(datetime_from, datetime_to, relativedelta(months=1)):
                compared_from = max(date_step + relativedelta(day=1), datetime_from).date()
                compared_to = min(date_step + relativedelta(months=1, day=1, days=-1), datetime_to).date()
                comparedtime_from = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(compared_from, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                comparedtime_to = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(compared_to, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)

                workmonth_hours = rec.order_id.project_id.mm_rate * 8
                month_leave_intervals = employee.list_leaves(comparedtime_from, comparedtime_to)
                for day, hours, leave in month_leave_intervals:
                    workmonth_hours -= hours


                date_start = max(compared_from, min_date)
                date_end = min(compared_to, max_date)
                datetime_start = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(date_start, time.min)).astimezone(timezone('UTC')).replace(tzinfo=None)
                datetime_end = timezone(self.env.user.tz or 'UTC').localize(datetime.combine(date_end, time.max)).astimezone(timezone('UTC')).replace(tzinfo=None)
                workrange_hours = calendar.get_work_hours_count(datetime_start, datetime_end, compute_leaves=False)
                range_leave_intervals = employee.list_leaves(datetime_start, datetime_end)
                mm_ratio = workrange_hours / workmonth_hours if workmonth_hours else 0
                md_ratio = workrange_hours / (workmonth_hours/8) if workmonth_hours else 0
                mh_ratio = workmonth_hours
                for day, hours, leave in range_leave_intervals:
                    workrange_hours -= hours

                mm += mm_ratio
                md += md_ratio
                mh += mh_ratio
            rec.mm = mm
            rec.md = md
            rec.mh = mh

    hours_indate = fields.Float(string='Số giờ làm việc của nhân viên', compute_sudo=True, compute='_compute_hours_indate', store=True)

    @api.depends('employee_id', 'date_start', 'date_end')
    def _compute_hours_indate(self):
        for rec in self:
            if not rec.employee_id or not rec.date_start or not rec.date_end:
                rec.hours_indate = 0
                continue
            date_from = min([rec.date_start, rec.date_end])
            date_to = max([rec.date_start, rec.date_end])
            datetime_from = datetime.combine(date_from, time.min)
            datetime_to = datetime.combine(date_to, time.max)
            employee = rec.employee_id
            hours_indate = self.env['en.technical.model'].convert_daterange_to_hours(employee, datetime_from, datetime_to)
            rec.hours_indate = hours_indate

    en_mh = fields.Float(string='MH', compute_sudo=True, compute='_compute_en_mh', store=True)

    @api.depends('hours_indate', 'workload')
    def _compute_en_mh(self):
        for rec in self:
            rec.en_mh = rec.hours_indate * rec.workload

    en_md = fields.Float(string='MD', compute_sudo=True, readonly=False, compute='_compute_en_m_uom', store=True)
    en_md_migrate = fields.Float(string='MD', compute_sudo=True, compute=False, store=True, readonly=False)

    @api.depends('hours_indate', 'workload', 'employee_id')
    def _compute_en_m_uom(self):
        for rec in self:
            en_mh = 0
            if not rec.employee_id or not rec.date_start or not rec.date_end:
                rec.en_md = en_mh
                rec.en_mh = 0
                continue
            employee = rec.employee_id
            en_mh = rec.hours_indate
            rec.en_md = en_mh / employee.resource_calendar_id.hours_per_day * rec.workload
            rec.en_mh = en_mh * rec.workload

    @api.depends('hours_indate', 'en_md')
    def _compute_en_md_workload(self):
        for rec in self:
            if not rec.employee_id or not rec.date_start or not rec.date_end:
                rec.workload = 0
                continue
            employee = rec.employee_id
            en_md = rec.hours_indate
            rec.workload = (rec.en_md * employee.resource_calendar_id.hours_per_day) / en_md if en_md else 0

    en_state = fields.Selection(string='Trạng thái', related='employee_id.en_status')

    def convert_daterange_to_data(self, employee, start_date, end_date):
        query = f"""
        with rd as (
            select date_start, date_end, workload, state
            from en_resource_detail
            JOIN en_resource_planning on en_resource_detail.order_id = en_resource_planning.id
            where employee_id = {employee.id} and en_resource_planning.state = 'approved'
        )
        SELECT d.date as date, sum(workload) workload
        FROM en_technical_date d
        LEFT JOIN rd on d.date between rd.date_start and rd.date_end
        WHERE d.date >= '{start_date}' and d.date <= '{end_date}'
        group by d.date
        """
        self.env.cr.execute(query)
        result = {x.get('date'): x.get('workload') or 0 for x in self.env.cr.dictfetchall()}
        return result

    def read(self, fields=None, load='_classic_read'):
        # self.filtered(lambda d: d.order_id.state not in ['approved', 'expire'])._compute_hours_indate()
        return super().read(fields, load)

    @api.model
    def create(self, values):
        if self._context.get('import_file') and 'workload' not in values and values.get('en_md') and values.get('employee_id'):
            employee = self.env['hr.employee'].browse(values.get('employee_id'))
            date_from = min([fields.Date.from_string(values.get('date_start')), fields.Date.from_string(values.get('date_end'))])
            date_to = max([fields.Date.from_string(values.get('date_start')), fields.Date.from_string(values.get('date_end'))])
            en_md = self.env['en.technical.model'].convert_daterange_to_hours(employee, date_from, date_to)
            values['workload'] = (values.get('en_md') * employee.resource_calendar_id.hours_per_day) / en_md if en_md else 0
        return super(ResourceDetail, self).create(values)

    @api.onchange('employee_id', 'date_start', 'date_end', 'workload')
    def _change_date_overload(self):
        lg = self.env['res.lang']._lang_get(self.env.user.lang) or get_lang(self.env)
        for rec in self:
            employee = rec.employee_id
            if not employee or not employee.en_internal_ok or not rec.date_start or not rec.date_end or not rec.workload:
                continue
            datetime_start = datetime.combine(rec.date_start, time.min)
            datetime_end = datetime.combine(rec.date_end, time.max)
            if datetime_start > datetime_end:
                continue
            groupby_overwork = []
            for date_step in date_utils.date_range(datetime_start, datetime_end, relativedelta(days=1)):
                detail_domain = [('employee_id', '=', employee.id), ('date_start', '<=', date_step.date()), ('date_end', '>=', date_step.date())]
                if round(sum(rec.order_id.order_line.filtered(lambda x: x.employee_id == employee and (x._origin.id or type(x.id) == NewId and x.id.ref) and x.date_start <= date_step.date() and x.date_end >= date_step.date()).mapped('workload')) + sum(self.env['en.resource.detail'].search([('order_id.state', '=', 'approved'), ('order_id.project_id', '!=', rec.order_id.project_id.id)] + detail_domain).mapped('workload')), 10) <= 1.2:
                    continue
                groupby_overwork += [date_step.date()]
            if not groupby_overwork:
                continue
            employee_txt = f'Nhân viên {employee.display_name} ở vị trí {rec.job_position_id.display_name} đã bị quá workload vào ngày'
            dated = sorted(groupby_overwork)
            dated_txt = []
            min_dated = dated[0]
            max_dated = dated[0]
            for d in dated:
                if max_dated == d or max_dated + relativedelta(days=1) == d:
                    max_dated = d
                    continue
                if min_dated == max_dated:
                    dated_txt += [f'{max_dated.strftime(lg.date_format)}']
                else:
                    dated_txt += [f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
                min_dated = d
                max_dated = d
            else:
                if min_dated == max_dated:
                    dated_txt += [f'{max_dated.strftime(lg.date_format)}']
                else:
                    dated_txt += [f'{min_dated.strftime(lg.date_format)} → {max_dated.strftime(lg.date_format)}']
            expt_txt = f'{employee_txt} {" và ".join(dated_txt)}'
            self.env.user.notify_warning(expt_txt, 'Cảnh báo')