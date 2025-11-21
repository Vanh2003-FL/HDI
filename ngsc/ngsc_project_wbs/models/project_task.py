import logging
from datetime import datetime, time, timedelta, date

from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.fields import Datetime
from odoo.tools import config
from odoo.tools import float_round

_logger = logging.getLogger(__name__)
from odoo import models, fields, api, _, exceptions


class ProjectTask(models.Model):
    _inherit = "project.task"

    @api.model
    def default_get(self, fields):
        vals = super().default_get(fields)
        display_project_id = self.env.context.get('default_display_project_id') or self.env.context.get(
            'default_project_id')
        if display_project_id:
            vals["stage_id"] = self.stage_find(display_project_id, [('fold', '=', False), ('is_closed', '=', False)])
        return vals

    code = fields.Char(string="Mã", compute="_compute_code", store=True)
    project_wbs_id = fields.Many2one("en.wbs", string="Phiên bản")
    project_id = fields.Many2one(index=True)
    project_wbs_state = fields.Selection(string="Trạng thái WBS", related="project_wbs_id.state", store=True)
    stage_type_id = fields.Many2one("en.stage.type", string="Giai đoạn dự án", tracking=True)
    parent_id = fields.Many2one("project.task", string="Thuộc", ondelete='set null', tracking=True, index=True)
    child_ids = fields.One2many("project.task", "parent_id", string="Danh sách công việc con")
    count_subtask = fields.Integer(string="Số lượng Subtask", compute="_compute_count_subtask", store=False)
    category = fields.Selection(string="Loại", index=True,
                                default='task',
                                selection=[('phase', 'Giai đoạn'),
                                           ('package', 'Gói việc'),
                                           ('child_package', 'Gói việc con'),
                                           ('task', 'Công việc')], tracking=True)
    actual_start_date = fields.Date(string="Ngày bắt đầu thực tế", tracking=True)
    actual_end_date = fields.Date(string="Ngày kết thúc thực tế", tracking=True)
    is_project_milestone = fields.Boolean(string="Mốc dự án", default=False, tracking=True)
    is_project_payment = fields.Boolean(string="Mốc thanh toán", default=False, tracking=True)
    is_hand_over_document = fields.Boolean(string="Sản phẩm bàn giao", default=False, tracking=True)
    plan_percent_completed = fields.Float(string="% Hoàn thành kế hoạch",store=True)
    actual_percent_completed = fields.Float(string="% Hoàn thành thực tế", compute="_compute_actual_percent_completed",
                                            store=True, recursive=True)
    has_child_package = fields.Boolean(string="Có gói việc con", compute="_compute_has_child_package", store=True)
    planned_hours = fields.Float(recursive=True)
    is_start_date_past = fields.Boolean(string="Ngày bắt đầu là quá khứ", default=False, compute="_compute_is_past")
    is_end_date_past = fields.Boolean(string="Ngày kết thúc là quá khứ", default=False, compute="_compute_is_past")
    is_invisible_btn = fields.Boolean(string="Ẩn nút", default=False, compute="_compute_invisible_btn")
    resource_state = fields.Char(string="Trạng thái nguồn lực trong dự án", search="_search_resource_state",
                                 store=False)
    task_old_related_id = fields.Many2one("project.task", string="Công việc liên quan")

    full_code = fields.Char(string="Mã đầy đủ", compute="_compute_full_code", store=False)

    @api.model
    def _cron_update_daily_progress(self):
        """Cron job - TỐI ƯU CAO: SQL thuần + Chỉ task đang chạy"""
        _logger.info("🔄 Bắt đầu cập nhật % hoàn thành Công việc (TỐI ƯU CAO)...")

        try:
            today = fields.Date.Date.context_today(self)
            _logger.info(f"📅 Ngày cập nhật: {today}")

            # SQL THUẦN - CỰC NHANH
            query = """
                    SELECT id \
                    FROM project_task
                    WHERE active = TRUE
                      AND en_start_date <= %s
                      AND date_deadline >= %s
                      AND stage_id NOT IN (SELECT id \
                                           FROM project_task_type \
                                           WHERE LOWER(name) LIKE \
                        ANY (ARRAY['%%cancel%%' \
                        , '%%huy%%' \
                        , '%%hủy%%' \
                        , '%%huỷ%%'])
                        ) \
                    """
            self.env.cr.execute(query, (today, today))
            running_task_ids = [row[0] for row in self.env.cr.fetchall()]

            if not running_task_ids:
                _logger.info("✅ Không có công việc đang chạy nào cần cập nhật")
                return

            _logger.info(f"📊 Số công việc đang chạy: {len(running_task_ids)}")

            # Xử lý tất cả trong 1 lần
            batch_records = self.browse(running_task_ids)
            batch_records.with_context(
                report_date=today,
                force_recompute=True
            )._compute_plan_percent_completed()

            self.env.cr.commit()
            _logger.info("✅ Cập nhật % hoàn thành Công việc hoàn tất (TỐI ƯU)")

        except Exception as e:
            _logger.error(f"❌ Lỗi: {e}")
            self.env.cr.commit()

    @api.model
    def update_module_migration(self):
        """
        Method này sẽ được gọi tự động sau khi update module
        Chỉ cần gọi 1 lần duy nhất từ UI hoặc script
        """
        migration_done = self.env['ir.config_parameter'].sudo().get_param(
            'ngsc_project_wbs.task_migration_v2_done', 'False'
        )

        if migration_done == 'True':
            _logger.info("Task migration v2 already done.")
            return True

        _logger.info("Starting Task migration v2 (bottom-up calculation)...")

        try:
            # Chạy migration bằng hàm run_migration_once hiện có
            success = self.run_migration_once()

            if success:
                # Đánh dấu đã hoàn thành
                self.env['ir.config_parameter'].sudo().set_param(
                    'ngsc_project_wbs.task_migration_v2_done', 'True'
                )
                _logger.info("Task migration v2 completed successfully.")
            else:
                _logger.error("Task migration v2 failed.")

            return success

        except Exception as e:
            _logger.error(f"Task migration v2 failed: {e}")
            return False

    # Giữ nguyên hàm run_migration_once của bạn ở đây
    @api.model
    def run_migration_once(self):
        """Chạy migrate % hoàn thành một lần duy nhất (SQL thuần, batch). Gọi thủ công sau upgrade."""
        # Check flag
        self.env['ir.config_parameter'].sudo().set_param('ngsc_project_wbs.migrated_percent_v1', 'running')
        if self.env['ir.config_parameter'].sudo().get_param('ngsc_project_wbs.migrated_percent_v1') == 'done':
            _logger.info("Migration already done for project.task.")
            return True

        cr = self.env.cr
        report_date = '2025-10-14'
        chunk_size = 1000

        # Lấy tất cả parent ids (category != 'task'), batch theo id
        cr.execute("SELECT id FROM project_task WHERE category != 'task' ORDER BY id LIMIT %s", (chunk_size,))
        chunks = []
        while True:
            rows = cr.fetchall()
            if not rows:
                break
            chunk_ids = [r[0] for r in rows]
            chunks.append(chunk_ids)
            cr.execute("SELECT id FROM project_task WHERE category != 'task' AND id > %s ORDER BY id LIMIT %s",
                       (chunk_ids[-1], chunk_size))

        total_updated = 0
        for chunk in chunks:
            # SQL cho plan_percent_completed (từ leaves)
            sql_plan = """
                       WITH RECURSIVE \
                           task_tree AS (SELECT id, \
                                                parent_id, \
                                                category, \
                                                en_start_date, \
                                                date_deadline, \
                                                planned_hours, \
                                                plan_percent_completed, \
                                                en_progress, \
                                                stage_id, \
                                                active \
                                         FROM project_task \
                                         WHERE id = ANY (%(chunk)s) \
                                         UNION ALL \
                                         SELECT t.id, \
                                                t.parent_id, \
                                                t.category, \
                                                t.en_start_date, \
                                                t.date_deadline, \
                                                t.planned_hours, \
                                                t.plan_percent_completed, \
                                                t.en_progress, \
                                                t.stage_id, \
                                                t.active \
                                         FROM project_task t \
                                                  JOIN task_tree tt ON t.parent_id = tt.id \
                                         WHERE t.active = TRUE), \
                           leaves AS (SELECT tt.root_id as parent_id, \
                                             l.en_start_date, \
                                             l.date_deadline, \
                                             l.planned_hours, \
                                             l.plan_percent_completed \
                                      FROM task_tree tt \
                                               JOIN project_task l ON l.id = tt.id \
                                               LEFT JOIN project_task_type st ON st.id = l.stage_id \
                                      WHERE l.category = 'task' \
                                        AND l.active = TRUE \
                                        AND (st.id IS NULL OR \
                                             LOWER(st.name) NOT LIKE ANY (ARRAY['%%huy%%','%%cancel%%','%%hủy%%','%%huỷ%%'])) \
                                        AND tt.id != tt.root_id -- Chỉ con
                           ), durations AS (
                       SELECT parent_id, COALESCE (
                           GREATEST(0, (EXTRACT (epoch FROM (LEAST(%(report)s:: date, date_deadline) - GREATEST( \
                                                                   %(report)s:: date, en_start_date)) / 86400) * 5 / 7), -- Approx workdays
                           planned_hours / 8.0
                           ) as duration, plan_percent_completed
                           FROM leaves
                           WHERE en_start_date IS NOT NULL AND date_deadline IS NOT NULL
                           ), weights AS (
                           SELECT parent_id, SUM (duration) as total_weight, SUM (plan_percent_completed * duration) as weighted_sum
                           FROM durations
                           GROUP BY parent_id
                           )
                       UPDATE project_task p
                       SET plan_percent_completed = ROUND(CASE WHEN w.total_weight > 0 THEN w.weighted_sum / w.total_weight ELSE 0 END, 2)
                       FROM weights w
                       WHERE p.id = w.parent_id AND p.id = ANY (%(chunk)s) \
                       """
            cr.execute(sql_plan, {'chunk': tuple(chunk), 'report': report_date})
            updated_plan = cr.rowcount
            total_updated += updated_plan

            # SQL cho actual_percent_completed (từ leaves en_progress)
            sql_actual = """
                         WITH RECURSIVE \
                             task_tree AS (SELECT id, \
                                                  parent_id, \
                                                  category, \
                                                  en_start_date, \
                                                  date_deadline, \
                                                  planned_hours, \
                                                  actual_percent_completed, \
                                                  en_progress, \
                                                  stage_id, \
                                                  active \
                                           FROM project_task \
                                           WHERE id = ANY (%(chunk)s) \
                                           UNION ALL \
                                           SELECT t.id, \
                                                  t.parent_id, \
                                                  t.category, \
                                                  t.en_start_date, \
                                                  t.date_deadline, \
                                                  t.planned_hours, \
                                                  t.actual_percent_completed, \
                                                  t.en_progress, \
                                                  t.stage_id, \
                                                  t.active \
                                           FROM project_task t \
                                                    JOIN task_tree tt ON t.parent_id = tt.id \
                                           WHERE t.active = TRUE), \
                             leaves AS (SELECT tt.root_id    as parent_id, \
                                               l.en_start_date, \
                                               l.date_deadline, \
                                               l.planned_hours, \
                                               l.en_progress as percent \
                                        FROM task_tree tt \
                                                 JOIN project_task l ON l.id = tt.id \
                                                 LEFT JOIN project_task_type st ON st.id = l.stage_id \
                                        WHERE l.category = 'task' \
                                          AND l.active = TRUE \
                                          AND (st.id IS NULL OR \
                                               LOWER(st.name) NOT LIKE ANY (ARRAY['%%huy%%','%%cancel%%','%%hủy%%','%%huỷ%%'])) \
                                          AND tt.id != tt.root_id
                             ), durations AS (
                         SELECT parent_id, COALESCE (
                             GREATEST(0, (EXTRACT (epoch FROM (date_deadline - en_start_date) / 86400) * 5 / 7), planned_hours / 8.0
                             ) as duration, percent
                             FROM leaves
                             WHERE en_start_date IS NOT NULL AND date_deadline IS NOT NULL
                             ), weights AS (
                             SELECT parent_id, SUM (duration) as total_weight, SUM (percent * duration) as weighted_sum
                             FROM durations
                             GROUP BY parent_id
                             )
                         UPDATE project_task p
                         SET actual_percent_completed = ROUND(CASE WHEN w.total_weight > 0 THEN w.weighted_sum / w.total_weight ELSE 0 END, 2)
                         FROM weights w
                         WHERE p.id = w.parent_id AND p.id = ANY (%(chunk)s) \
                         """
            cr.execute(sql_actual, {'chunk': tuple(chunk), 'report': report_date})
            updated_actual = cr.rowcount
            total_updated += updated_actual

            _logger.info(
                f"Batch chunk {chunk[0]}-{chunk[-1]}: Updated {updated_plan} plan + {updated_actual} actual in project.task.")

        # Set flag done
        self.env['ir.config_parameter'].sudo().set_param('ngsc_project_wbs.migrated_percent_v1', 'done')
        _logger.info(f"Migration done for project.task: {total_updated} total updates.")
        return True

    @api.depends('code', 'parent_id')
    def _compute_full_code(self):
        if not self:
            return

        # 1️⃣ Lấy tất cả record hiện tại + toàn bộ parent chain
        all_ids = set()
        for rec in self:
            current = rec
            while current:
                all_ids.add(current.id)
                current = current.parent_id

        if not all_ids:
            return

        # 2️⃣ SQL CTE tính full_code theo format cha/con/... đúng thứ tự
        query = """
                WITH RECURSIVE task_path AS (SELECT id, parent_id, code, code::text AS full_code
                                             FROM project_task
                                             WHERE parent_id IS NULL

                                             UNION ALL

                                             SELECT c.id,
                                                    c.parent_id,
                                                    c.code,
                                                    (p.full_code || '/' || c.code) ::text AS full_code
                                             FROM project_task c
                                                      JOIN task_path p ON p.id = c.parent_id)
                SELECT id, full_code
                FROM task_path
                WHERE id IN %s
                """
        self.env.cr.execute(query, (tuple(all_ids),))
        data = dict(self.env.cr.fetchall())

        # 3️⃣ Gán kết quả vào field full_code
        for rec in self:
            rec.full_code = data.get(rec.id, '') or ''

    # 🔹 Tự động cập nhật full_code khi tạo mới
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._compute_full_code()  # tính cả parent chain
        return records

    # 🔹 Tự động cập nhật full_code khi sửa code hoặc parent
    def write(self, vals):
        res = super().write(vals)
        if any(k in vals for k in ['code', 'parent_id']):
            self._compute_full_code()  # tính cả parent chain
        return res

    @api.depends('parent_id', 'project_wbs_id')
    def _compute_code(self):
        """Sinh mã thứ tự (P.1, W.2, T.3,...) ổn định theo từng cấp theo code"""
        if not self:
            return

        ids = tuple(self.ids)
        if not ids:
            return

        query = """
                WITH ordered AS (SELECT id, \
                                        category, \
                                        ROW_NUMBER() OVER (
                        PARTITION BY COALESCE(parent_id, project_wbs_id)
                        ORDER BY code ASC
                    ) AS seq \
                                 FROM project_task \
                                 WHERE id IN %s)
                SELECT id, category, seq
                FROM ordered; \
                """
        self.env.cr.execute(query, (ids,))
        results = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall()}

        prefix_map = {
            'phase': 'P',
            'package': 'W',
            'child_package': 'Z',
            'task': 'T'
        }

        for rec in self:
            cat, seq = results.get(rec.id, (rec.category, 0))
            prefix = prefix_map.get(cat, '')
            rec.code = f"{prefix}.{seq}"  # cập nhật trực tiếp record

    @api.model
    def _search_resource_state(self, operator, value):
        default_res_id = self._context.get("default_res_id", False)
        if not default_res_id:
            return []
        project = self.env["project.task"].sudo().browse(default_res_id).project_id
        en_resource_project_ids = project.en_resource_project_ids
        if value == "active":
            employee_actives = en_resource_project_ids.filtered(lambda x: x.state == "active").mapped(
                'employee_id.user_id')
            return [('en_handler', 'in', employee_actives.ids)]
        elif value == "inactive":
            employee_actives = en_resource_project_ids.filtered(lambda x: x.state == "active").mapped(
                'employee_id.user_id')
            employee_inactives = en_resource_project_ids.filtered(lambda x: x.state == "inactive").mapped(
                'employee_id.user_id')
            return [('en_handler', 'in', (employee_inactives - employee_actives).ids)]
        return []

    # TODO TK3665 Bỏ depends tối ưu performance, update qua cron job hàng ngày refresh dữ liệu
    effective_hours = fields.Float(depends=[])

    def _compute_invisible_btn(self):
        for rec in self:
            rec.is_invisible_btn = self.env.context.get('x2many_search', False)

    def _compute_is_past(self):
        today = fields.Date.Date.context_today(self)
        for rec in self:
            if rec.category != "phase" or not rec.project_wbs_id.created_by_wbs_id:
                rec.is_start_date_past = False
                rec.is_end_date_past = False
            else:
                wbs_baseline = rec.sudo().project_wbs_id.project_id.en_wbs_ids.filtered(
                    lambda x: x.version_type == "baseline")
                rec.is_start_date_past = bool(rec.en_start_date and rec.en_start_date < today and wbs_baseline)
                rec.is_end_date_past = bool(rec.date_deadline and rec.date_deadline < today and wbs_baseline)

    @api.model
    def create(self, values):
        if self._context.get('ctx_task_wbs', False):
            values["category"] = "task"

        if self.env.context.get('is_import_task'):
            if 'en_start_date' not in values or not values.get('en_start_date'):
                raise ValidationError("Ngày bắt đầu là trường bắt buộc và không được để trống!")
            if 'date_deadline' not in values or not values.get('date_deadline'):
                raise ValidationError("Hạn hoàn thành là trường bắt buộc và không được để trống!")
            # Lấy giá trị từ context nếu không có trong vals
            if 'display_project_id' not in values:
                values['display_project_id'] = self.env.context.get('default_display_project_id')
            if 'parent_id' not in values:
                values['parent_id'] = self.env.context.get('default_parent_id')
            if 'project_wbs_id' not in values:
                values['project_wbs_id'] = self.env.context.get('default_wbs_id')
            if 'project_wbs_state' not in values:
                values['project_wbs_state'] = self.env.context.get('default_wbs_state')
            values['category'] = 'task'

        res = super().create(values)
        if res.category == "task" and not res.project_wbs_id and res.parent_id:
            res.project_wbs_id = res.parent_id.project_wbs_id.id
        if res.category == "task" and not self._context.get("copy_wbs", False):
            wbs_draft = self.env["en.wbs"].sudo().search([("project_id", "=", res.project_id.id),
                                                          ("state", "in",
                                                           ['draft', 'waiting_create_resource_plan', 'awaiting',
                                                            'waiting_resource_plan_approve'])])
            if wbs_draft:
                raise ValidationError("Chỉ có thể tạo Công việc khi WBS ở trạng thái Đã duyệt")

        if self.env.context.get('is_import_task'):
            if (res.parent_id and
                res.parent_id.en_handler != self.env.user) and (
                    res.project_id.user_id != self.env.user and
                    self.env.user not in res.project_id.en_project_vicepm_ids):
                raise ValidationError(
                    'Bạn không thể tạo công việc cho gói việc mà bạn không phải là người chịu trách nhiệm')

        return res

    @api.depends('child_ids.category')
    def _compute_has_child_package(self):
        for rec in self:
            rec.has_child_package = any(child.category == 'child_package' for child in rec.child_ids)

    @api.depends("project_wbs_id", "parent_id", "child_ids", "parent_id.child_ids", "project_wbs_id.wbs_task_ids")
    def _compute_code(self):
        for rec in self:
            if rec.category == "phase":
                rec._update_phase_code()
            elif rec.category == "package":
                rec._update_phase_package()
            elif rec.category == "child_package":
                rec._update_phase_child_package()
            elif rec.category == "task":
                rec._update_phase_task()
            else:
                rec.code = False

    def _update_phase_code(self):
        phase_ids = self.project_wbs_id.wbs_task_ids.filtered(lambda x: x.category == "phase").sorted(key="id")
        sequence = 1
        if not self._origin:
            phase_ids += self
        for phase in phase_ids:
            phase.code = f"P.{sequence}"
            sequence += 1

    def _update_phase_package(self):
        package_ids = self.parent_id.child_ids.sorted(key="id")
        sequence = 1
        if not self._origin:
            package_ids += self
        for package in package_ids:
            package.code = f"W.{sequence}"
            sequence += 1

    def _update_phase_child_package(self):
        package_ids = self.parent_id.child_ids.sorted(key="id")
        sequence = 1
        if not self._origin:
            package_ids += self
        for package in package_ids:
            package.code = f"Z.{sequence}"
            sequence += 1

    def _update_phase_task(self):
        task_ids = self.parent_id.child_ids.sorted(key="id")
        sequence = 1
        if not self._origin:
            task_ids += self
        for task in task_ids:
            task.code = f"T.{sequence}"
            sequence += 1

    def _compute_count_subtask(self):
        for rec in self:
            rec.count_subtask = len(rec.child_ids)

    def action_unlink(self):
        self.unlink()

    @staticmethod
    def _get_display_name_form_create(category=False):
        name = "Thêm mới"
        if category == "phase":
            name = "Thêm mới giai đoạn"
        elif category == "package":
            name = "Thêm mới gói việc"
        elif category == "child_package":
            name = "Thêm mới gói việc con"
        elif category == "task":
            name = "Thêm mới công việc"
        return name

    def _get_display_name_form_edit(self):
        name = "Cập nhật"
        if self.category == "phase":
            name = "Cập nhật giai đoạn"
        elif self.category == "package":
            name = "Cập nhật gói việc"
        elif self.category == "child_package":
            name = "Cập nhật gói việc con"
        elif self.category == "task":
            name = "Cập nhật công việc"
        return name

    def _get_display_name_form_view(self):
        name = "Xem"
        if self.category == "phase":
            name = "Xem giai đoạn"
        elif self.category == "package":
            name = "Xem gói việc"
        elif self.category == "child_package":
            name = "Xem gói việc con"
        elif self.category == "task":
            name = "Xem công việc"
        return name

    def action_open_wizard_create_task(self, project_wbs_id=False, parent_id=False, category=False):
        form_view_create_id = self.env.ref('ngsc_project_wbs.ngsc_project_task_view_form_create').id
        context = {
            'default_project_wbs_id': project_wbs_id,
            'default_parent_id': parent_id,
            'default_category': category,
            'default_display_project_id': self.display_project_id.id or self._context.get('project_id', False),
            'default_project_id': self.project_id.id or self._context.get('project_id', False),
            'default_stage_type_id': self.stage_type_id.id,
            'ctx_new_record': True
        }
        if category in ["phase", "package"] or self.category == "child_package":
            context["readonly"] = True
        if self.category == "package":
            context["category"] = "package"
            if not context.get("default_category"):
                context["default_category"] = "child_package"
        return {
            'name': self._get_display_name_form_create(category),
            'view_mode': 'form',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'view_id': form_view_create_id,
            'views': [(form_view_create_id, 'form')],
            'context': context,
            'target': 'new',
        }

    def action_create(self):
        category = False
        if self.category == "phase":
            category = "package"
        elif self.category == "child_package":
            category = "task"
        return self.action_open_wizard_create_task(project_wbs_id=self.project_wbs_id.id, parent_id=self.id,
                                                   category=category)

    def action_open_wizard_update_task(self):
        form_view_edit = self.env.ref('ngsc_project_wbs.ngsc_project_task_view_form_edit').id
        return {
            'name': self._get_display_name_form_edit(),
            'view_mode': 'form',
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'view_id': form_view_edit,
            'views': [(form_view_edit, 'form')],
            'res_id': self.id,
            'target': 'new',
        }

    def action_update(self):
        return self.action_open_wizard_update_task()

    def action_save(self):
        if not self._context.get("ctx_new_record", False):
            self.env.user.refresh_form_view()

    def action_save_and_create(self):
        self.env.user.refresh_form_view()
        return self.action_open_wizard_create_task(project_wbs_id=self.project_wbs_id.id, parent_id=self.parent_id.id,
                                                   category=self.category)

    def action_unlink(self):
        self.unlink()

    def _is_cancelled_record(self, record):
        """Kiểm tra record bị hủy/ẩn - CHỈ KIỂM TRA CÁC TRƯỜNG TỒN TẠI THỰC SỰ."""
        if not record or not record.exists():
            return False

        # 1. Kiểm tra active = False
        if hasattr(record, "active") and record.active is False:
            return True

        # 2. Kiểm tra state (nếu có)
        if hasattr(record, "state"):
            state = getattr(record, "state", None)
            if state and str(state).strip().lower() in (
                    "cancel", "cancelled", "huy", "hủy", "huỷ", "huy_bo", "hủy_bỏ"
            ):
                return True

        # 3. Kiểm tra stage_id.name
        if hasattr(record, "stage_id") and record.stage_id:
            stage_name = record.stage_id.name or ""
            stage_lower = stage_name.strip().lower()
            # Kiểm tra các từ khóa hủy bỏ
            cancel_keywords = ['cancel', 'cancelled', 'huy', 'hủy', 'huỷ', 'hủy bỏ', 'huy bo', 'đã hủy', 'da huy']
            if any(keyword in stage_lower for keyword in cancel_keywords):
                return True

        return False

    def _get_holidays_set(self):
        ctx = self.env.context or {}
        holidays = ctx.get("holidays")  # expected list of date strings or date objects
        result = set()
        if not holidays:
            return result
        for h in holidays:
            if isinstance(h, str):
                try:
                    d = datetime.strptime(h, "%Y-%m-%d").date()
                except Exception:
                    continue
            elif isinstance(h, datetime):
                d = h.date()
            elif isinstance(h, date):
                d = h
            else:
                continue
            result.add(d)
        return result

    def _get_workdays(self, start_date, end_date, holidays_set=None):
        if not start_date or not end_date:
            return 0
        if isinstance(start_date, datetime):
            start_date = start_date.date()
        if isinstance(end_date, datetime):
            end_date = end_date.date()
        if start_date > end_date:
            return 0
        if holidays_set is None:
            holidays_set = set()
        delta_days = (end_date - start_date).days + 1
        workdays = 0
        for i in range(delta_days):
            d = start_date + timedelta(days=i)
            # weekday(): 0=Mon ... 6=Sun
            if d.weekday() >= 5:
                # skip Sat(5), Sun(6)
                continue
            if d in holidays_set:
                continue
            workdays += 1
        return workdays

    @api.depends("en_start_date", "date_deadline", "en_handler", "child_ids", "child_ids.planned_hours")
    def _compute_planned_hours(self):
        if not self._context.get("migration_wbs", False):
            super()._compute_planned_hours()
        for rec in self:
            if rec.category == "task":
                continue
            rec.planned_hours = 0.0
            children = rec.child_ids.filtered(lambda c: not self._is_cancelled_record(c))
            total = sum(child.planned_hours or 0.0 for child in children)
            rec.planned_hours = round(total, 2)

    # @api.depends("child_ids", "child_ids.effective_hours", "timesheet_ids.unit_amount")
    # TODO TK3665 Bỏ depends tối ưu performance, update qua cron job hàng ngày refresh dữ liệu
    def _compute_effective_hours(self):
        if not self._context.get("migration_wbs", False) and not self._context.get("ir_cron_update", False):
            super()._compute_effective_hours()
        for rec in self:
            if rec.category == "task":
                continue
            children = rec.child_ids.filtered(lambda c: not self._is_cancelled_record(c))
            total = sum(child.effective_hours or 0.0 for child in children)
            rec.effective_hours = round(total, 2)

    def _get_valid_children_ids_sql(self, rec_id):
        """Trả về danh sách id các con (mọi cấp) của rec_id, đã loại bỏ các task bị hủy/inactive."""
        if not rec_id:
            return []
        mapping = self._get_valid_children_ids_sql_for_roots([rec_id])
        return mapping.get(rec_id, [])

    def _get_valid_children_ids_sql_for_roots(self, root_ids):
        """
        Trả về dict: {root_id: [child_id, ...]}.
        Lấy toàn bộ con hợp lệ (mọi cấp) bằng 1 truy vấn SQL duy nhất.
        Loại bỏ task inactive hoặc bất kỳ cha nào bị hủy.
        """
        if not root_ids:
            return {}

        roots = list(root_ids)
        result = {rid: [] for rid in roots}

        # Query không dùng unaccent (fallback)
        sql_no_unaccent = """
                          WITH RECURSIVE task_tree AS (SELECT id, \
                                                              parent_id, \
                                                              stage_id, \
                                                              active, \
                                                              id    AS root_id, \
                                                              FALSE AS parent_cancelled \
                                                       FROM project_task \
                                                       WHERE id = ANY (%s) \
 \
                                                       UNION ALL \
 \
                                                       SELECT t.id, \
                                                              t.parent_id, \
                                                              t.stage_id, \
                                                              t.active, \
                                                              tt.root_id, \
                                                              ( \
                                                                  tt.parent_cancelled \
                                                                      OR COALESCE(t.active, TRUE) = FALSE \
                                                                      OR LOWER(COALESCE(st.name, '')) LIKE '%%huy%%' \
                                                                      OR LOWER(COALESCE(st.name, '')) LIKE '%%cancel%%' \
                                                                      OR LOWER(COALESCE(st.name, '')) LIKE '%%hủy%%' \
                                                                      OR LOWER(COALESCE(st.name, '')) LIKE '%%huỷ%%' \
                                                                  ) AS parent_cancelled \
                                                       FROM project_task t \
                                                                JOIN task_tree tt ON t.parent_id = tt.id \
                                                                LEFT JOIN project_task_type st ON st.id = t.stage_id)
                          SELECT t.id, t.root_id
                          FROM task_tree t
                                   LEFT JOIN project_task_type st2 ON st2.id = t.stage_id
                          WHERE t.id != t.root_id
              AND t.parent_cancelled = FALSE
              AND COALESCE(t.active, TRUE) = TRUE
              AND LOWER(COALESCE(st2.name, '')) NOT LIKE '%%huy%%'
              AND LOWER(COALESCE(st2.name, '')) NOT LIKE '%%cancel%%'
              AND LOWER(COALESCE(st2.name, '')) NOT LIKE '%%hủy%%'
              AND LOWER(COALESCE(st2.name, '')) NOT LIKE '%%huỷ%%' \
                          """

        cr = self.env.cr

        # Kiểm tra extension unaccent
        try:
            cr.execute("SELECT 1 FROM pg_proc WHERE proname='unaccent'")
            has_unaccent = bool(cr.fetchone())
        except Exception:
            has_unaccent = False

        if has_unaccent:
            sql_unaccent = sql_no_unaccent.replace(
                "LOWER(COALESCE(st.name, ''))",
                "LOWER(unaccent(COALESCE(st.name, '')))"
            ).replace(
                "LOWER(COALESCE(st2.name, ''))",
                "LOWER(unaccent(COALESCE(st2.name, '')))"
            )
            try:
                cr.execute(sql_unaccent, (roots,))
            except Exception:
                cr.execute(sql_no_unaccent, (roots,))
        else:
            cr.execute(sql_no_unaccent, (roots,))

        rows = cr.fetchall()
        for task_id, root_id in rows:
            result.setdefault(root_id, []).append(task_id)

        return result

    @api.depends("category", "child_ids.plan_percent_completed", "en_start_date", "date_deadline", "stage_id")
    def _compute_plan_percent_completed(self):
        """Tính % hoàn thành kế hoạch - bottom-up, không cần task, tính cả package/phase."""

        ctx = self.env.context or {}
        if not self:
            return

        holidays_set = self._get_holidays_set()

        # Xác định report_date
        report_date_ctx = ctx.get("report_date")
        if isinstance(report_date_ctx, str):
            try:
                report_date = datetime.strptime(report_date_ctx, "%Y-%m-%d").date()
            except Exception:
                report_date = fields.Date.Date.context_today(self)
        elif isinstance(report_date_ctx, datetime):
            report_date = report_date_ctx.date()
        elif isinstance(report_date_ctx, date):
            report_date = report_date_ctx
        else:
            report_date = fields.Date.Date.context_today(self)

        # Lấy toàn bộ record + con cháu
        all_ids = set()
        for rec in self:
            all_ids.add(rec.id)
            all_ids.update(self._get_valid_children_ids_sql(rec.id))

        if not all_ids:
            return

        # Đọc dữ liệu
        all_tasks = self.env['project.task'].browse(list(all_ids)).read([
            'id', 'parent_id', 'category', 'en_start_date', 'date_deadline',
            'planned_hours', 'stage_id', 'active'
        ])
        task_dict = {t['id']: t for t in all_tasks}

        # Map cha -> con
        children_map = {}
        for t in all_tasks:
            pid = t['parent_id'] and t['parent_id'][0]
            if pid:
                children_map.setdefault(pid, []).append(t['id'])

        # Hàm phụ
        def compute_self_percent(task_data):
            """Tính % theo thời gian của chính node (dù là task, package hay phase)."""
            if not task_data or self._is_cancelled_record(self.env['project.task'].browse(task_data['id'])):
                return 0.0

            start = task_data.get('en_start_date')
            end = task_data.get('date_deadline')
            if not (start and end):
                return 0.0

            if isinstance(start, datetime):
                start = start.date()
            if isinstance(end, datetime):
                end = end.date()

            duration_days = self._get_workdays(start, end, holidays_set)
            if duration_days <= 0:
                return 0.0

            if report_date < start:
                return 0.0
            elif report_date >= end:
                return 1.0
            else:
                plan_to = min(report_date, end)
                plan_duration_days = self._get_workdays(start, plan_to, holidays_set)
                val = plan_duration_days / duration_days if duration_days else 0.0
                return max(0.0, min(1.0, val))

        def get_duration(task_data):
            """Tính số ngày kế hoạch (hoặc planned_hours nếu không có ngày)."""
            s = task_data.get('en_start_date')
            e = task_data.get('date_deadline')
            planned_hours = task_data.get('planned_hours') or 0.0

            if not (s and e):
                return (planned_hours / 8.0) if planned_hours > 0 else 0.0

            if isinstance(s, datetime):
                s = s.date()
            if isinstance(e, datetime):
                e = e.date()

            duration = self._get_workdays(s, e, holidays_set)
            if duration <= 0:
                duration = (planned_hours / 8.0) if planned_hours > 0 else 0.0
            return duration

        # ==== Bắt đầu tính bottom-up ====
        percent_map = {}

        # B1: node lá (không có con)
        all_task_ids = set(task_dict.keys())
        non_leaf_ids = set(children_map.keys())
        leaf_ids = list(all_task_ids - non_leaf_ids)

        for tid in leaf_ids:
            percent_map[tid] = compute_self_percent(task_dict[tid])

        # B2: duyệt lên
        remaining = set(all_task_ids) - set(leaf_ids)
        max_loops = len(all_task_ids) + 5

        while remaining and max_loops > 0:
            computed_now = set()
            for tid in list(remaining):
                children = children_map.get(tid, [])
                # Lọc chỉ con hợp lệ
                valid_children = [
                    cid for cid in children
                    if cid in task_dict and not self._is_cancelled_record(self.env['project.task'].browse(cid))
                ]

                if not valid_children:
                    # Không có con -> tự tính theo chính nó
                    percent_map[tid] = compute_self_percent(task_dict[tid])
                    computed_now.add(tid)
                    continue

                # Nếu tất cả con đã tính
                if all(cid in percent_map for cid in valid_children):
                    total_weight = 0.0
                    weighted_sum = 0.0
                    for cid in valid_children:
                        c_data = task_dict[cid]
                        duration = get_duration(c_data)
                        if duration <= 0:
                            continue
                        weighted_sum += percent_map[cid] * duration
                        total_weight += duration
                    percent_map[tid] = (weighted_sum / total_weight) if total_weight else compute_self_percent(
                        task_dict[tid])
                    computed_now.add(tid)

            remaining -= computed_now
            max_loops -= 1

        # B3: gán kết quả cho các record đầu vào
        for rec in self:
            if self._is_cancelled_record(rec):
                rec.plan_percent_completed = 0.0
            else:
                val = percent_map.get(rec.id, compute_self_percent(task_dict.get(rec.id)))
                rec.plan_percent_completed = float_round(val, precision_digits=2)

    def _get_planned_hours_by_range_date(self, start_date, end_date):
        if not start_date or not end_date or start_date > end_date:
            return 0.0
        employee = self.sudo().en_handler.employee_id
        if not employee:
            return 0.0
        datetime_start = datetime.combine(start_date, time.min)
        datetime_end = datetime.combine(end_date, time.max)
        return self.env['en.technical.model'].convert_daterange_to_hours(employee, datetime_start, datetime_end) or 0.0

    @api.depends("category", "child_ids.actual_percent_completed", "effective_hours", "stage_id", "en_progress")
    def _compute_actual_percent_completed(self):
        """Tính % hoàn thành thực tế - TÍNH TỪ CẤP THẤP NHẤT ĐI LÊN."""
        # Lấy tất cả record cần tính toán
        all_ids = set()
        for rec in self:
            all_ids.add(rec.id)
            child_ids = self._get_valid_children_ids_sql(rec.id)
            all_ids.update(child_ids)

        if not all_ids:
            return

        # Đọc tất cả dữ liệu một lần
        all_tasks = self.env['project.task'].browse(list(all_ids)).read([
            'id', 'parent_id', 'category', 'en_start_date', 'date_deadline',
            'planned_hours', 'en_progress', 'stage_id', 'active'
        ])

        task_dict = {task['id']: task for task in all_tasks}
        children_map = {}
        for task in all_tasks:
            parent_id = task['parent_id'] and task['parent_id'][0]
            if parent_id:
                children_map.setdefault(parent_id, []).append(task['id'])

        # Hàm tính % đệ quy từ dưới lên
        def calculate_actual_percent(task_id):
            task_data = task_dict.get(task_id)
            if not task_data or self._is_cancelled_record(self.env['project.task'].browse(task_id)):
                return 0.0

            # Nếu là task lá (category='task')
            if task_data.get('category') == 'task':
                return task_data.get('en_progress') or 0.0

            # Nếu là task cha - tính từ các CON TRỰC TIẾP (đệ quy)
            children_ids = children_map.get(task_id, [])
            if not children_ids:
                return 0.0

            total_weight = 0.0
            weighted_sum = 0.0
            holidays_set = self._get_holidays_set()

            for child_id in children_ids:
                child_data = task_dict.get(child_id)
                if not child_data or self._is_cancelled_record(self.env['project.task'].browse(child_id)):
                    continue

                # GỌI ĐỆ QUY để tính % cho con
                child_percent = calculate_actual_percent(child_id)

                # Tính trọng số cho con
                s = child_data.get('en_start_date')
                e = child_data.get('date_deadline')
                planned_hours = child_data.get('planned_hours') or 0.0

                if not (s and e):
                    duration = (planned_hours / 8.0) if planned_hours > 0 else 0.0
                else:
                    if isinstance(s, datetime):
                        s = s.date()
                    if isinstance(e, datetime):
                        e = e.date()
                    duration = self._get_workdays(s, e, holidays_set)
                    if duration <= 0:
                        duration = (planned_hours / 8.0) if planned_hours > 0 else 0.0

                if duration <= 0:
                    continue

                total_weight += duration
                weighted_sum += child_percent * duration

            return (weighted_sum / total_weight) if total_weight else 0.0

        # Tính toán và gán kết quả
        for rec in self:
            if self._is_cancelled_record(rec):
                rec.actual_percent_completed = 0.0
            else:
                raw_value = calculate_actual_percent(rec.id)
                # ✅ CHỈ LÀM TRÒN KHI GÁN KẾT QUẢ CUỐI
                rec.actual_percent_completed = float_round(raw_value, precision_digits=2)

    @api.model
    def get_project_task_phase_ids(self, wbs_id):
        wbs = self.env['en.wbs'].sudo().browse(wbs_id)
        task_phase_ids = wbs.wbs_task_ids.filtered(lambda x: x.category == "phase").mapped(
            lambda s: {'id': s.id, 'name': s.name, 'code': s.code})
        return task_phase_ids

    @api.model
    def get_ref_form_view_id(self):
        return self.env.ref('ngsc_project_wbs.ngsc_project_task_view_form_edit').id

    def _copy_task_tree(self, new_wbs):
        self.ensure_one()
        tasks_to_copy = []
        task_queue = [(self, None)]
        while task_queue:
            current, new_parent_id = task_queue.pop(0)
            tasks_to_copy.append((current, new_parent_id))
            for child in current.child_ids.filtered(lambda x: x.stage_id.en_mark != 'b'):
                task_queue.append((child, current.id))
        old_to_new = {}
        task_vals = []
        for task, _ in tasks_to_copy:
            task_vals.append({
                "name": task.name,
                "related_task_id": task.id,
                "project_wbs_id": new_wbs.id,
                "stage_id": task.stage_id.id or False,
                "code": task.code,
                "display_project_id": task.display_project_id.id,
                "project_id": task.project_id.id,
                "en_requester": task.en_requester.id or False,
                "en_supervisor": task.en_supervisor.id or False,
                "en_handler": task.en_handler.id or False,
                "en_approver_id": task.en_approver_id.id or False,
                "is_project_milestone": task.is_project_milestone,
                "is_project_payment": task.is_project_payment,
                "is_hand_over_document": task.is_hand_over_document,
                "category": task.category,
                "stage_type_id": task.stage_type_id.id or False,
                "en_start_date": task.en_start_date or False,
                "date_deadline": task.date_deadline or False,
                "actual_start_date": task.actual_start_date or False,
                "actual_end_date": task.actual_end_date or False,
                "planned_hours": task.planned_hours,
                "en_progress": task.en_progress,
                "company_id": task.company_id.id or False,
                "description": task.description,
            })
        new_tasks = self.env["project.task"].with_context(copy_wbs=True).create(task_vals)
        for (task, _), new_task in zip(tasks_to_copy, new_tasks):
            old_to_new[task.id] = new_task
        for (task, parent_old_id), new_task in zip(tasks_to_copy, new_tasks):
            if parent_old_id:
                new_task.parent_id = old_to_new[parent_old_id].id
        return old_to_new[self.id]

    @api.constrains('en_start_date', 'date_deadline', 'en_task_position', 'en_handler', 'planned_hours')
    def _en_constrains_start_deadline_date(self):
        pass

    # TODO
    @api.constrains("stage_id")
    def _constrains_stage_id(self):
        for r in self:
            continue

    @api.constrains("en_start_date", "date_deadline")
    def _constrains_date(self):
        if self._context.get("copy_wbs", False):
            return
        for rec in self.filtered(lambda x: x.category and x.stage_id.en_mark != 'b'):
            if not rec.en_start_date or not rec.date_deadline:
                continue
            if rec.en_start_date > rec.date_deadline:
                raise ValidationError("Ngày bắt đầu phải nhỏ hơn hoặc bằng ngày kết thúc.")
            if rec.parent_id and rec.parent_id.stage_id.en_mark != 'b' and rec.parent_id.en_start_date and rec.parent_id.date_deadline:
                start_date = datetime.strftime(rec.parent_id.en_start_date, '%d/%m/%Y')
                end_date = datetime.strftime(rec.parent_id.date_deadline, '%d/%m/%Y')
                category = dict(self._fields['category'].selection).get(rec.parent_id.category).lower()
                name = rec.parent_id.name or ""
                if rec.en_start_date < rec.parent_id.en_start_date or rec.en_start_date > rec.parent_id.date_deadline:
                    raise ValidationError(
                        f"Ngày bắt đầu phải nằm trong khoảng thời gian của {category} {name}({start_date}-{end_date})")
                if rec.date_deadline < rec.parent_id.en_start_date or rec.date_deadline > rec.parent_id.date_deadline:
                    raise ValidationError(
                        f"Ngày kết thúc phải nằm trong khoảng thời gian của {category} {name}({start_date}-{end_date})")
            if rec.child_ids:
                category = dict(self._fields['category'].selection).get(rec.category).lower()
                child_ids_start_date = rec.child_ids.filtered(lambda
                                                                  x: x.parent_id.stage_id.en_mark != 'b' and x.en_start_date < rec.en_start_date or x.en_start_date > rec.date_deadline)
                if child_ids_start_date:
                    start_date = datetime.strftime(child_ids_start_date[0].en_start_date, '%d/%m/%Y')
                    end_date = datetime.strftime(child_ids_start_date[0].date_deadline, '%d/%m/%Y')
                    category_child = dict(self._fields['category'].selection).get(
                        child_ids_start_date[0].category).lower()
                    name = child_ids_start_date[0].name or ""
                    raise ValidationError(
                        f"Ngày bắt đầu của {category} phải bao gồm thời gian của {category_child} {name}({start_date}-{end_date})")
                child_ids_end_date = rec.child_ids.filtered(lambda
                                                                x: x.parent_id.stage_id.en_mark != 'b' and x.date_deadline < rec.en_start_date or x.date_deadline > rec.date_deadline)
                if child_ids_end_date:
                    start_date = datetime.strftime(child_ids_end_date[0].en_start_date, '%d/%m/%Y')
                    end_date = datetime.strftime(child_ids_end_date[0].date_deadline, '%d/%m/%Y')
                    category_child = dict(self._fields['category'].selection).get(child_ids_end_date[0].category)
                    name = child_ids_end_date[0].name or ""
                    raise ValidationError(
                        f"Ngày kết thúc của {category} phải bao gồm thời gian của {category_child} {name}({start_date}-{end_date})")

    @api.constrains("stage_id")
    def _constrains_stage_in_progress(self):
        if self._context.get("copy_wbs", False):
            return
        for rec in self.filtered(lambda x: x.category == "task"):
            if rec.stage_id.en_mark == 'c' and rec.parent_id and rec.parent_id.stage_id.en_mark == 'a':
                category = dict(self._fields['category'].selection).get(rec.parent_id.category)
                name = rec.parent_id.name or ""
                raise UserError(
                    f'{category} "{name}" chưa bật trạng thái "Đang thực hiện", người dùng cần liên hệ Người chịu trách nhiệm của {category} để cập nhật.')

    @api.constrains("stage_id")
    def _constrains_stage_task_complete(self):
        if self._context.get("copy_wbs", False): return
        for rec in self.filtered(lambda x: x.category == "task" and x.stage_id.en_mark != 'b'):
            if rec.project_wbs_id.state != 'approved': continue
            tasks_not_done = rec.parent_id.child_ids.filtered(lambda x: x.stage_id.en_mark != 'g')
            if not tasks_not_done:
                rec.parent_id._sent_email_task_complete()

        for rec in self.filtered(lambda x: x.category == "package" and x.stage_id.en_mark != 'b'):
            if rec.project_wbs_id.state != 'approved': continue
            tasks_not_done = rec.parent_id.child_ids.filtered(lambda x: x.stage_id.en_mark != 'g')
            if not tasks_not_done:
                rec.parent_id._sent_email_package_complete()

    def _sent_email_task_complete(self):
        self.env.ref('ngsc_project.email_template_project_task_complete').send_mail(self.id, force_send=True)

    def _sent_email_package_complete(self):
        self.env.ref('ngsc_project.email_template_en_workpackage_complete').send_mail(self.id, force_send=True)

    # @api.model
    # def action_refresh_task_percent_plan(self, date_refresh=False):
    #     if not date_refresh:
    #         date_refresh = fields.Date.Date.context_today(self)
    #     _domain = [('project_wbs_state', '=', 'approved'),
    #                ('category', '=', 'task'),
    #                ('en_start_date', '<=', date_refresh),
    #                ('date_deadline', '>=', date_refresh)]
    #     self.sudo().search(_domain)._compute_plan_percent_completed()

    @api.model
    def action_refresh_task_percent_plan(self, date_refresh=False):
        if not date_refresh:
            date_refresh = fields.Date.Date.context_today(self)

        project_ids = self.env.context.get('project_ids', None)

        Task = self.env['project.task']

        # 1️⃣ Lấy tất cả task lá (category='task')
        _domain_task = [
            ('project_wbs_state', '=', 'approved'),
            ('category', '=', 'task'),
            ('en_start_date', '<=', date_refresh),
            ('date_deadline', '>=', date_refresh),
        ]

        # 2️⃣ Lấy tất cả các cấp cha (package, child_package, phase)
        _domain_parent = [
            ('project_wbs_state', '=', 'approved'),
            ('category', 'in', ['package','child_package', 'phase']),  # phase có thể là cấp cao nhất
        ]

        if project_ids:
            _domain_task.append(('project_wbs_id', 'in', project_ids))
            _domain_parent.append(('project_wbs_id', 'in', project_ids))

        tasks = Task.sudo().search(_domain_task)
        parents = Task.sudo().search(_domain_parent)

        # 3️⃣ Bắt đầu tính từ cấp thấp nhất trước (task)
        tasks.with_context(force_recompute=True)._compute_plan_percent_completed()

        # 4️⃣ Sau đó, tính dồn lên cho các cấp cha (package, child_package, phase)
        #    => Lặp nhiều lần đến khi không còn cấp cha nào nữa
        parent_tasks = parents
        while parent_tasks:
            parent_tasks.with_context(force_recompute=True)._compute_plan_percent_completed()
            # Lấy tất cả cha của nhóm vừa tính (để tính tiếp lên trên)
            parent_tasks = parent_tasks.mapped('parent_id')

    @api.model
    def action_refresh_wbs_effective_hours(self, date_refresh=False):
        if not date_refresh:
            date_refresh = fields.Date.Date.context_today(self)
        _domain = ["|",
                   "&", ("en_state", "in", ['approved', 'waiting']), ("approved_timesheet_date", "=", date_refresh),
                   "&", ("ot_state", "=", 'approved'), ("approved_overtime_date", "=", date_refresh)]
        analytic_obj = self.env["account.analytic.line"].sudo()
        task_obj = self.env["project.task"].sudo()
        tasks = analytic_obj.search(_domain).mapped("task_id")
        if not tasks:
            return
        all_tasks = task_obj.search(
            [("id", "parent_of", tasks.ids), ("category", "in", ['child_package', 'package', 'phase'])])
        child_packages = all_tasks.filtered(lambda x: x.category == "child_package")
        packages = all_tasks.filtered(lambda x: x.category == "package")
        phases = all_tasks.filtered(lambda x: x.category == "phase")
        tasks._compute_effective_hours()
        if child_packages:
            child_packages.with_context(ir_cron_update=True)._compute_effective_hours()
        if packages:
            packages.with_context(ir_cron_update=True)._compute_effective_hours()
        if phases:
            phases.with_context(ir_cron_update=True)._compute_effective_hours()

    @api.constrains("stage_id")
    def _constrains_stage_auto(self):
        task_type = self.env["project.task.type"]
        for rec in self.filtered(lambda x: x.category not in ["task"]):
            if rec.stage_id.en_mark == 'c' and rec.parent_id.stage_id.en_mark == 'a':
                stage_id = task_type.search([("project_ids", "=", rec.project_id.id), ("en_mark", "=", "c")], limit=1)
                rec.parent_id.stage_id = stage_id.id
                if rec.parent_id.parent_id.stage_id.en_mark == 'a':
                    rec.parent_id.parent_id.stage_id = stage_id.id

    @api.constrains('en_progress')
    def _constrains_en_progress(self):
        for rec in self.filtered(lambda x: x.category == "task"):
            if rec.en_progress < 0 or rec.en_progress > 1:
                raise ValidationError('% Hoàn thành chỉ được nhập trong khoảng 0 -> 100')

    @api.onchange('parent_id')
    def _onchange_parent_id_package(self):
        for rec in self:
            if rec.category != "task": continue
            if rec.project_id.user_id == self.env.user or self.env.user in rec.project_id.en_project_vicepm_ids: continue
            if rec.parent_id and rec.parent_id.en_handler != self.env.user:
                raise ValidationError(
                    'Bạn không thể tạo công việc cho gói việc mà bạn không phải là người chịu trách nhiệm')

    def unlink(self):
        for rec in self:
            rec.child_ids.unlink()
        return super().unlink()

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        domain = domain or []
        if self._context.get("x2many_search", False):
            records = self.search(domain)
            if records:
                domain = ['|', ('id', 'in', records.ids), ('id', 'parent_of', records.ids)]
        return super().search_read(domain, fields, offset, limit, order)

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields=allfields, attributes=attributes)
        if self._context.get("x2many_search", False):
            fields_options = ["name", "category", "code", "en_start_date", "date_deadline", "en_handler", "stage_id"]
            for field_name, field_info in res.items():
                if field_name not in fields_options:
                    field_info["selectable"] = False
                    field_info["exportable"] = False
                    field_info["searchable"] = False
                    field_info["sortable"] = False
        return res

    def name_get(self):
        result = []
        if not self._context.get('ctx_resource_stage_display', False):
            return super().name_get()
        for rec in self:
            start = rec.en_start_date.strftime('%d/%m/%Y') if rec.en_start_date else ''
            end = rec.date_deadline.strftime('%d/%m/%Y') if rec.date_deadline else ''
            name = f"{rec.name} ({start}-{end})"
            result.append((rec.id, name))
        return result

    def _raise_if_not_completed(self, records, message, name):
        not_approved = records.filtered(lambda r: r.stage_id.en_mark not in ('g', 'b'))
        if not_approved:
            items = "\n- " + "\n- ".join(not_approved.mapped("name"))
            raise ValidationError(message % (name, items))

    def _is_cancel_stage(self, stage):
        """Trả về True nếu stage có tên chứa từ khóa chỉ 'hủy'."""
        if not stage or not stage.name:
            return False
        name = str(stage.name).strip().lower()
        cancel_keywords = ("cancel", "cancelled", "huy", "hủy", "huỷ")
        return any(k in name for k in cancel_keywords)

    def _cascade_cancel_sql(self, cancel_stage):
        """Hủy toàn bộ task con các cấp bằng SQL (an toàn, không đệ quy ORM)."""
        if not self.ids:
            return

        # 🔹 Lấy toàn bộ ID con nhiều cấp bằng CTE đệ quy SQL
        self.env.cr.execute("""
                            WITH RECURSIVE all_children AS (SELECT id
                                                            FROM project_task
                                                            WHERE parent_id = ANY (%s)
                                                            UNION ALL
                                                            SELECT t.id
                                                            FROM project_task t
                                                                     JOIN all_children c ON t.parent_id = c.id)
                            SELECT id
                            FROM all_children
                            """, (self.ids,))
        child_task_ids = [r[0] for r in self.env.cr.fetchall()]

        if not child_task_ids:
            return

        # 🔹 Kiểm tra các task con có timesheet chưa bị hủy
        self.env.cr.execute("""
                            SELECT DISTINCT t.id, t.name
                            FROM project_task t
                                     JOIN account_analytic_line aal ON aal.task_id = t.id
                            WHERE t.id = ANY (%s)
                            """, (child_task_ids,))
        bad_tasks = self.env.cr.fetchall()

        if bad_tasks:
            msg = "\n".join(f"- {name}" for _, name in bad_tasks)
            raise UserError(_("Không thể hủy vì các công việc con sau có timesheet:\n%s") % msg)

        # 🔹 Cập nhật tất cả stage_id sang stage "Hủy"
        all_ids = self.ids + child_task_ids
        self.env.cr.execute("""
                            UPDATE project_task
                            SET stage_id = %s
                            WHERE id = ANY (%s)
                            """, (cancel_stage.id, all_ids))

    def write(self, values):
        res = super().write(values)
        if "stage_id" in values:
            for rec in self.filtered(lambda x: x.category == "task" and x.stage_id.en_mark == 'g'):
                if not rec.timesheet_ids.filtered(lambda x: x.en_state == "approved"):
                    raise ValidationError("Bạn không thể hoàn thành công việc khi chưa khai timesheet.")
            for task in self:
                if task.stage_id.en_mark == 'g':
                    if task.category == 'phase':
                        packages = self.env['project.task'].search(
                            [('parent_id', '=', task.id), ('category', '=', 'package')])
                        self._raise_if_not_completed(packages,
                                                     "Không thể hoàn thành %s vì vẫn còn gói việc dưới đây chưa hoàn thành:\n%s",
                                                     task.name)

                    elif task.category == 'package':
                        children = self.env['project.task'].search(
                            [('parent_id', '=', task.id), ('category', 'in', ('child_package', 'task'))])
                        self._raise_if_not_completed(children,
                                                     "Không thể hoàn thành %s vì vẫn còn gói việc con hoặc công việc dưới đây chưa hoàn thành:\n%s",
                                                     task.name)

                    elif task.category == 'child_package':
                        child_tasks = self.env['project.task'].search(
                            [('parent_id', '=', task.id), ('category', '=', 'task')])
                        self._raise_if_not_completed(child_tasks,
                                                     "Không thể hoàn thành %s vì vẫn còn công việc dưới đây chưa hoàn thành:\n%s",
                                                     task.name)

            # 🔹 Xử lý khi đổi stage sang "Hủy"
            for task in self:
                new_stage = task.stage_id
                if self._is_cancel_stage(new_stage):
                    # Gọi phiên bản SQL tối ưu
                    task._cascade_cancel_sql(new_stage)

        return res


class ProjectTaskImportWizard(models.TransientModel):
    _name = 'project.task.import.wizard'
    _description = 'Import Project and WBS Wizard'

    project_id = fields.Many2one('project.project', string='Dự án', required=True)
    package_id = fields.Many2one('project.task',
                                 string='Gói công việc',
                                 required=True,
                                 domain="[('display_project_id', '=', project_id), ('category', 'in', ['package', 'child_package']),('project_wbs_state', '=', 'approved')]")

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.package_id = False
        if not self.project_id:
            return {'domain': {'package_id': []}}
        return {'domain': {
            'package_id': [
                ('project_id', '=', self.project_id.id),
                ('category', 'in', ['package', 'child_package']),
                ('project_wbs_state', '=', 'approved')
            ]
        }}

    def action_confirm(self):
        self.ensure_one()
        # Trả về client action với type 'import' và truyền ID của project và WBS
        return {
            'type': 'ir.actions.client',
            'tag': 'import',
            'params': {
                'model': 'project.task',
                'context': {
                    'default_display_project_id': self.project_id.id,
                    'default_parent_id': self.package_id.id,
                    'default_wbs_id': self.package_id.project_wbs_id.id,
                    'default_wbs_state': self.package_id.project_wbs_state,
                    'is_import_task': True
                }
            },

        }

    class IrCron(models.Model):
        _inherit = 'ir.cron'

        show_wbs_button = fields.Boolean(string="Hiển thị nút WBS", default=False)

    class WizardManualWbsRun(models.TransientModel):
        _name = 'wizard.manual.wbs.run'
        _description = 'Chạy thủ công cập nhật WBS theo ngày'

        date_run = fields.Date(string="Ngày cần chạy", required=True, default=fields.Date.context_today)

        def action_run_manual(self):
            """Gọi hàm cập nhật WBS theo ngày được chọn"""
            self.env['project.task'].action_refresh_wbs_effective_hours(self.date_run)
