import logging
from datetime import datetime, timedelta, date

from lxml import etree
from odoo.exceptions import ValidationError, UserError, AccessError
from odoo.fields import Datetime
from odoo.tools import config
from odoo.tools import float_round

_logger = logging.getLogger(__name__)
from odoo import fields, models, api, SUPERUSER_ID


class EnWbs(models.Model):
    _inherit = "en.wbs"

    wbs_task_ids = fields.One2many("project.task", "project_wbs_id", string="Danh sách công việc")
    plan_percent_completed = fields.Float(string="% hoàn thành kế hoạch",
                                          compute="_compute_plan_percent_completed", store=True)
    actual_percent_completed = fields.Float(string="% hoàn thành thực tế",
                                            compute="_compute_actual_percent_completed", store=True)
    planned_hours = fields.Float(string="Tổng giờ kế hoạch",
                                 compute="_compute_planned_hours", store=True)
    effective_hours = fields.Float(string="Tổng gờ thực tế",
                                   compute="_compute_effective_hours", store=True)

    end_le_contract = fields.Boolean(
        string="Kết thúc ≤ Hợp đồng",
        compute="_compute_contract_conditions",
        store=True,
        help="Ngày kết thúc nhỏ hơn hoặc bằng ngày kết thúc dự kiến theo hợp đồng."
    )

    end_gt_contract = fields.Boolean(
        string="Kết thúc > Hợp đồng",
        compute="_compute_contract_conditions",
        store=True,
        help="Ngày kết thúc lớn hơn ngày kết thúc dự kiến theo hợp đồng."
    )

    def action_refresh_task_percent_plan(self):
        # Gọi hàm cập nhật % hoàn thành
        self.env['project.task'].action_refresh_task_percent_plan()

    @api.model
    def _cron_update_daily_progress(self):
        """Cron job - TỐI ƯU CAO: SQL thuần + Chỉ update thay đổi"""
        _logger.info("🔄 Bắt đầu cập nhật % hoàn thành dự kiến WBS (TỐI ƯU CAO)...")

        try:
            today = fields.Date.Date.context_today(self)
            _logger.info(f"📅 Ngày cập nhật: {today}")

            # SỬ DỤNG SQL THUẦN để lọc nhanh nhất
            query = """
                    SELECT id \
                    FROM en_wbs
                    WHERE active = TRUE
                      AND state NOT IN ('cancel', 'cancelled', 'huy', 'hủy', 'huỷ', 'huy_bo', 'hủy_bỏ')
                      AND id IN (SELECT DISTINCT project_wbs_id \
                                 FROM project_task \
                                 WHERE active = TRUE \
                                   AND en_start_date <= %s \
                                   AND date_deadline >= %s) \
                    """
            self.env.cr.execute(query, (today, today))
            valid_wbs_ids = [row[0] for row in self.env.cr.fetchall()]

            if not valid_wbs_ids:
                _logger.info("✅ Không có WBS nào cần cập nhật")
                return

            _logger.info(f"📊 Số WBS cần cập nhật: {len(valid_wbs_ids)}")

            # CHỈ tính toán cho các WBS thực sự có task đang chạy
            batch_records = self.browse(valid_wbs_ids)
            batch_records.with_context(
                report_date=today,
                force_recompute=True
            )._compute_plan_percent_completed()

            self.env.cr.commit()
            _logger.info("✅ Cập nhật % hoàn thành WBS hoàn tất (TỐI ƯU)")

        except Exception as e:
            _logger.error(f"❌ Lỗi: {e}")
            self.env.cr.commit()

    @api.depends("end_date", "project_id.en_contract_end_date")
    def _compute_contract_conditions(self):
        for rec in self:
            contract_end = rec.project_id.en_contract_end_date
            wbs_end = rec.end_date

            if wbs_end and isinstance(wbs_end, datetime):
                wbs_end = wbs_end.date()
            if contract_end and isinstance(contract_end, datetime):
                contract_end = contract_end.date()

            # reset mặc định
            rec.end_le_contract = False
            rec.end_gt_contract = False

            # AC2: Ngày kết thúc <= contract_end hoặc contract_end rỗng
            if not contract_end or (wbs_end and wbs_end <= contract_end):
                rec.end_le_contract = True
            # AC3: Ngày kết thúc > contract_end và contract_end có dữ liệu
            elif contract_end and wbs_end and wbs_end > contract_end:
                rec.end_gt_contract = True

    @api.model
    def update_module_migration(self):
        """
        Method này sẽ được gọi tự động sau khi update module
        Chỉ cần gọi 1 lần duy nhất từ UI hoặc script
        """
        migration_done = self.env['ir.config_parameter'].sudo().get_param(
            'ngsc_project_wbs.wbs_migration_v2_done', 'False'
        )

        if migration_done == 'True':
            _logger.info("WBS migration v2 already done.")
            return True

        _logger.info("Starting WBS migration v2 (bottom-up calculation)...")

        try:
            # Chạy migration bằng hàm run_migration_once hiện có
            success = self.run_migration_once()

            if success:
                # Đánh dấu đã hoàn thành
                self.env['ir.config_parameter'].sudo().set_param(
                    'ngsc_project_wbs.wbs_migration_v2_done', 'True'
                )
                _logger.info("WBS migration v2 completed successfully.")
            else:
                _logger.error("WBS migration v2 failed.")

            return success

        except Exception as e:
            _logger.error(f"WBS migration v2 failed: {e}")
            return False

    # Giữ nguyên hàm run_migration_once của bạn ở đây
    @api.model
    def run_migration_once(self):
        """Chạy migrate % hoàn thành một lần duy nhất cho WBS (SQL thuần, batch). Gọi thủ công sau upgrade."""
        # Check flag (riêng cho WBS)
        self.env['ir.config_parameter'].sudo().set_param('ngsc_project_wbs.migrated_wbs_percent_v1', 'running')
        if self.env['ir.config_parameter'].sudo().get_param('ngsc_project_wbs.migrated_wbs_percent_v1') == 'done':
            _logger.info("Migration already done for en_wbs.")
            return True

        cr = self.env.cr
        report_date = '2025-10-14'
        chunk_size = 1000

        # Lấy tất cả WBS ids, batch
        cr.execute("SELECT id FROM project_wbs ORDER BY id LIMIT %s", (chunk_size,))
        chunks = []
        while True:
            rows = cr.fetchall()
            if not rows:
                break
            chunk_ids = [r[0] for r in rows]
            chunks.append(chunk_ids)
            cr.execute("SELECT id FROM project_wbs WHERE id > %s ORDER BY id LIMIT %s", (chunk_ids[-1], chunk_size))

        total_updated = 0
        for chunk in chunks:
            # SQL cho plan_percent_completed (từ leaves task của wbs_task_ids)
            sql_plan = """
                       WITH RECURSIVE task_tree AS (SELECT t.id, \
                                                           t.parent_id, \
                                                           t.category, \
                                                           t.en_start_date, \
                                                           t.date_deadline, \
                                                           t.planned_hours, \
                                                           t.plan_percent_completed, \
                                                           t.stage_id, \
                                                           t.active, \
                                                           w.id as wbs_id \
                                                    FROM project_task t \
                                                             JOIN project_wbs w ON w.id = ANY (%(chunk)s) AND t.project_wbs_id = w.id \
                                                    WHERE t.category != 'task' -- Start từ intermediate
                       UNION ALL
                       SELECT tt.id, \
                              tt.parent_id, \
                              tt.category, \
                              tt.en_start_date, \
                              tt.date_deadline, \
                              tt.planned_hours, \
                              tt.plan_percent_completed, \
                              tt.stage_id, \
                              tt.active, \
                              tt.wbs_id
                       FROM project_task tt
                                JOIN task_tree t ON tt.parent_id = t.id
                       WHERE tt.active = TRUE ),
                leaves AS (
                    SELECT wbs_id, l.en_start_date, l.date_deadline, l.planned_hours, l.plan_percent_completed
                    FROM task_tree tt
                    JOIN project_task l ON l.id = tt.id
                    LEFT JOIN project_task_type st ON st.id = l.stage_id
                    WHERE l.category = 'task'
                      AND l.active = TRUE
                      AND (st.id IS NULL OR LOWER(st.name) NOT LIKE ANY (ARRAY['%%huy%%','%%cancel%%','%%hủy%%','%%huỷ%%']))
                ),
                durations AS (
                    SELECT wbs_id,
                           COALESCE(
                               GREATEST(0, (EXTRACT(epoch FROM (LEAST(%(report)s:: date \
                           , date_deadline) - GREATEST(%(report)s:: date \
                           , en_start_date)) / 86400) * 5 / 7) \
                           , planned_hours / 8.0
                           ) as duration \
                           , plan_percent_completed
                           FROM leaves
                           WHERE en_start_date IS NOT NULL \
                         AND date_deadline IS NOT NULL
                           ) \
                           , weights AS (
                           SELECT wbs_id \
                           , SUM (duration) as total_weight \
                           , SUM (plan_percent_completed * duration) as weighted_sum
                           FROM durations
                           GROUP BY wbs_id
                           )
                           UPDATE project_wbs w
                           SET plan_percent_completed = ROUND(CASE WHEN wgt.total_weight \
                           > 0 THEN wgt.weighted_sum / wgt.total_weight ELSE 0 END \
                           , 2)
                           FROM weights wgt
                           WHERE w.id = wgt.wbs_id \
                         AND w.id = ANY (%(chunk)s) \
                       """
            cr.execute(sql_plan, {'chunk': tuple(chunk), 'report': report_date})
            updated_plan = cr.rowcount
            total_updated += updated_plan

            # SQL cho actual_percent_completed (tương tự, dùng en_progress)
            sql_actual = """
                         WITH RECURSIVE task_tree AS (SELECT t.id, \
                                                             t.parent_id, \
                                                             t.category, \
                                                             t.en_start_date, \
                                                             t.date_deadline, \
                                                             t.planned_hours, \
                                                             t.actual_percent_completed, \
                                                             t.en_progress, \
                                                             t.stage_id, \
                                                             t.active, \
                                                             w.id as wbs_id \
                                                      FROM project_task t \
                                                               JOIN project_wbs w ON w.id = ANY (%(chunk)s) AND t.project_wbs_id = w.id \
                                                      WHERE t.category != 'task'
                         UNION ALL
                         SELECT tt.id, \
                                tt.parent_id, \
                                tt.category, \
                                tt.en_start_date, \
                                tt.date_deadline, \
                                tt.planned_hours, \
                                tt.actual_percent_completed, \
                                tt.en_progress, \
                                tt.stage_id, \
                                tt.active, \
                                tt.wbs_id
                         FROM project_task tt
                                  JOIN task_tree t ON tt.parent_id = t.id
                         WHERE tt.active = TRUE ),
                leaves AS (
                    SELECT wbs_id, l.en_start_date, l.date_deadline, l.planned_hours, l.en_progress as percent
                    FROM task_tree tt
                    JOIN project_task l ON l.id = tt.id
                    LEFT JOIN project_task_type st ON st.id = l.stage_id
                    WHERE l.category = 'task'
                      AND l.active = TRUE
                      AND (st.id IS NULL OR LOWER(st.name) NOT LIKE ANY (ARRAY['%%huy%%','%%cancel%%','%%hủy%%','%%huỷ%%']))
                ),
                durations AS (
                    SELECT wbs_id,
                           COALESCE(
                               GREATEST(0, (EXTRACT(epoch FROM (date_deadline - en_start_date) / 86400) * 5 / 7),
                               planned_hours / 8.0
                           ) as duration,
                           percent
                    FROM leaves
                    WHERE en_start_date IS NOT NULL AND date_deadline IS NOT NULL
                ),
                weights AS (
                    SELECT wbs_id, SUM(duration) as total_weight, SUM(percent * duration) as weighted_sum
                    FROM durations
                    GROUP BY wbs_id
                )
                UPDATE project_wbs w
                SET actual_percent_completed = ROUND(CASE WHEN wgt.total_weight > 0 THEN wgt.weighted_sum / wgt.total_weight ELSE 0 END, 2)
                FROM weights wgt
                WHERE w.id = wgt.wbs_id AND w.id = ANY(%(chunk)s) \
                         """
            cr.execute(sql_actual, {'chunk': tuple(chunk), 'report': report_date})
            updated_actual = cr.rowcount
            total_updated += updated_actual

            # Update hours (tương tự, sum từ leaves)
            sql_hours_plan = """
                             UPDATE project_wbs w
                             SET planned_hours = ROUND(COALESCE(SUM(l.planned_hours), 0), 2) FROM project_task l
                LEFT JOIN project_task_type st \
                             ON st.id = l.stage_id
                             WHERE l.project_wbs_id = w.id
                               AND l.category = 'task'
                               AND l.active = TRUE
                               AND (st.id IS NULL \
                                OR LOWER (st.name) NOT LIKE ANY (ARRAY['%%huy%%' \
                                 , '%%cancel%%' \
                                 , '%%hủy%%' \
                                 , '%%huỷ%%']))
                               AND w.id = ANY (%(chunk)s)
                             GROUP BY w.id \
                             """
            cr.execute(sql_hours_plan, {'chunk': tuple(chunk)})
            updated_ph = cr.rowcount
            total_updated += updated_ph

            sql_hours_eff = """
                            UPDATE project_wbs w
                            SET effective_hours = ROUND(COALESCE(SUM(l.effective_hours), 0), 2) FROM project_task l
                LEFT JOIN project_task_type st \
                            ON st.id = l.stage_id
                            WHERE l.project_wbs_id = w.id
                              AND l.category = 'task'
                              AND l.active = TRUE
                              AND (st.id IS NULL \
                               OR LOWER (st.name) NOT LIKE ANY (ARRAY['%%huy%%' \
                                , '%%cancel%%' \
                                , '%%hủy%%' \
                                , '%%huỷ%%']))
                              AND w.id = ANY (%(chunk)s)
                            GROUP BY w.id \
                            """
            cr.execute(sql_hours_eff, {'chunk': tuple(chunk)})
            updated_eh = cr.rowcount
            total_updated += updated_eh

            _logger.info(
                f"Batch chunk {chunk[0]}-{chunk[-1]}: Updated {updated_plan} plan + {updated_actual} actual + {updated_ph} planned_hours + {updated_eh} effective_hours in en_wbs.")

        # Set flag done
        self.env['ir.config_parameter'].sudo().set_param('ngsc_project_wbs.migrated_wbs_percent_v1', 'done')
        _logger.info(f"Migration done for en_wbs: {total_updated} total updates.")
        return True

    def _is_cancelled_record(self, record):
        """Kiểm tra record bị hủy/ẩn hay không."""
        if not record:
            return False

        # Kiểm tra trường active (nếu tồn tại)
        if hasattr(record, "active") and record.active is False:
            return True

        # Kiểm tra trường state (nếu tồn tại)
        if hasattr(record, "state"):
            state = getattr(record, "state", None)
            if state and str(state).strip().lower() in (
                    "cancel", "cancelled", "huy", "hủy", "huỷ", "huy_bo", "hủy_bỏ"
            ):
                return True

        # Kiểm tra stage_id (nếu tồn tại)
        if hasattr(record, "stage_id") and record.stage_id:
            stage_name = record.stage_id.name or ""
            if stage_name.strip().lower() in (
                    'cancel', 'cancelled', 'huy', 'hủy', 'huỷ',
                    'hủy bỏ', 'huy bo', 'đã hủy', 'da huy'
            ):
                return True

        return False

    def _get_holidays_set(self):
        ctx = self.env.context or {}
        holidays = ctx.get("holidays")
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
            if d.weekday() >= 5:
                continue
            if d in holidays_set:
                continue
            workdays += 1
        return workdays

    def _get_all_related_wbs_ids(self):
        """Lấy tất cả WBS cha và con của self, không giới hạn cấp."""
        if not self.ids:
            return []

        # Lấy tất cả con
        self.env.cr.execute("""
                            WITH RECURSIVE all_wbs_down AS (SELECT id, parent_id
                                                            FROM project_task
                                                            WHERE id = ANY (%s)
                                                            UNION
                                                            SELECT t.id, t.parent_id
                                                            FROM project_task t
                                                                     JOIN all_wbs_down aw ON t.parent_id = aw.id)
                            SELECT DISTINCT id
                            FROM all_wbs_down;
                            """, (self.ids,))
        all_down_ids = [r[0] for r in self.env.cr.fetchall()]

        # Lấy tất cả cha
        self.env.cr.execute("""
                            WITH RECURSIVE all_wbs_up AS (SELECT id, parent_id
                                                          FROM project_task
                                                          WHERE id = ANY (%s)
                                                          UNION
                                                          SELECT t.id, t.parent_id
                                                          FROM project_task t
                                                                   JOIN all_wbs_up aw ON t.id = aw.parent_id)
                            SELECT DISTINCT id
                            FROM all_wbs_up;
                            """, (self.ids,))
        all_up_ids = [r[0] for r in self.env.cr.fetchall()]

        # Kết hợp cha + con + bản thân
        all_ids = set(all_down_ids + all_up_ids + self.ids)
        return list(all_ids)

    @api.depends("wbs_task_ids.plan_percent_completed", "wbs_task_ids.stage_id")
    def _compute_plan_percent_completed(self):
        """Tính % hoàn thành kế hoạch (đa cấp, lan truyền lên cha) - TÍNH TỪ CẤP THẤP NHẤT ĐI LÊN."""
        ctx = self.env.context or {}
        # Thêm điều kiện để force recompute khi có context
        force_recompute = ctx.get('force_recompute', False)

        # Nếu không có records nào, return ngay
        if not self:
            return

        # Nếu chỉ có 1 record và không force recompute, có thể skip nếu không có thay đổi
        if len(self) == 1 and not force_recompute:
            current_record = self
            # Kiểm tra nếu các field phụ thuộc không thay đổi
            if not any(field in self._fields for field in
                       ['wbs_task_ids', 'child_ids', 'en_start_date', 'date_deadline', 'stage_id']):
                return
        holidays_set = self._get_holidays_set()

        # Lấy tất cả WBS liên quan (kể cả cha-con)
        all_ids = self._get_all_related_wbs_ids()
        if not all_ids:
            return

        # Lấy toàn bộ task thuộc các WBS này
        self.env.cr.execute("""
                            SELECT t.id,
                                   t.project_wbs_id,
                                   t.parent_id,
                                   t.category,
                                   t.en_start_date,
                                   t.date_deadline,
                                   t.planned_hours,
                                   t.stage_id,
                                   t.active
                            FROM project_task t
                            WHERE t.project_wbs_id = ANY (%s)
                              AND COALESCE(t.active, TRUE) = TRUE
                            """, (all_ids,))
        all_tasks_data = self.env.cr.dictfetchall()

        # Tạo dict và map
        task_dict = {task['id']: task for task in all_tasks_data}
        children_map = {}
        wbs_tasks_map = {}  # Map wbs_id -> list task_ids

        for task in all_tasks_data:
            # Map parent -> children
            parent_id = task.get('parent_id')
            if parent_id:
                children_map.setdefault(parent_id, []).append(task['id'])

            # Map wbs_id -> tasks
            wbs_id = task.get('project_wbs_id')
            if wbs_id:
                wbs_tasks_map.setdefault(wbs_id, []).append(task['id'])

        # Hàm tính % đệ quy cho task
        def calculate_task_percent(task_id):
            task_data = task_dict.get(task_id)
            if not task_data or self._is_cancelled_record(self.env['project.task'].browse(task_id)):
                return 0.0

            # Nếu là task lá (category='task')
            if task_data.get('category') == 'task':
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

                report_date = fields.Date.Date.context_today(self)
                if report_date < start:
                    return 0.0
                elif report_date >= end:
                    return 1.0
                else:
                    plan_to = min(report_date, end)
                    plan_duration_days = self._get_workdays(start, plan_to, holidays_set)
                    val = plan_duration_days / duration_days if duration_days else 0.0
                    return max(0.0, min(1.0, val))

            # Nếu là task cha - tính từ các CON TRỰC TIẾP (đệ quy)
            children_ids = children_map.get(task_id, [])
            if not children_ids:
                return 0.0

            total_weight = 0.0
            weighted_sum = 0.0

            for child_id in children_ids:
                child_data = task_dict.get(child_id)
                if not child_data or self._is_cancelled_record(self.env['project.task'].browse(child_id)):
                    continue

                # GỌI ĐỆ QUY để tính % cho con
                child_percent = calculate_task_percent(child_id)

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

        # Tính % cho từng WBS từ các task gốc (không có parent hoặc parent không cùng WBS)
        wbs_percent_map = {}
        for wbs_id in all_ids:
            task_ids = wbs_tasks_map.get(wbs_id, [])
            if not task_ids:
                wbs_percent_map[wbs_id] = 0.0
                continue

            # Chỉ lấy các task gốc của WBS (không có parent hoặc parent không cùng WBS)
            root_tasks = []
            for task_id in task_ids:
                task_data = task_dict.get(task_id)
                if not task_data:
                    continue
                parent_id = task_data.get('parent_id')
                # Nếu không có parent hoặc parent không thuộc cùng WBS => là task gốc
                if not parent_id or task_dict.get(parent_id, {}).get('project_wbs_id') != wbs_id:
                    root_tasks.append(task_id)

            if not root_tasks:
                wbs_percent_map[wbs_id] = 0.0
                continue

            # Tính weighted average từ các task gốc
            total_weight = 0.0
            weighted_sum = 0.0

            for task_id in root_tasks:
                task_data = task_dict.get(task_id)
                if not task_data or self._is_cancelled_record(self.env['project.task'].browse(task_id)):
                    continue

                # Tính % cho task gốc (đệ quy qua toàn bộ cây con)
                task_percent = calculate_task_percent(task_id)

                # Tính trọng số
                s = task_data.get('en_start_date')
                e = task_data.get('date_deadline')
                planned_hours = task_data.get('planned_hours') or 0.0

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
                weighted_sum += task_percent * duration

            wbs_percent_map[wbs_id] = weighted_sum / total_weight if total_weight else 0.0

        # Cập nhật kết quả
        all_records = self.browse(all_ids)
        for rec in all_records:
            if self._is_cancelled_record(rec):
                rec.plan_percent_completed = 0.0
            else:
                raw_value = wbs_percent_map.get(rec.id, 0.0)
                rec.plan_percent_completed = float_round(raw_value, precision_digits=2)

    @api.depends("wbs_task_ids.actual_percent_completed", "wbs_task_ids.stage_id")
    def _compute_actual_percent_completed(self):
        """Tính % hoàn thành thực tế (đa cấp, lan truyền lên cha) - TÍNH TỪ CẤP THẤP NHẤT ĐI LÊN."""
        holidays_set = self._get_holidays_set()

        all_ids = self._get_all_related_wbs_ids()
        if not all_ids:
            return

        # Lấy toàn bộ task thuộc các WBS này
        self.env.cr.execute("""
                            SELECT t.id,
                                   t.project_wbs_id,
                                   t.parent_id,
                                   t.category,
                                   t.en_start_date,
                                   t.date_deadline,
                                   t.planned_hours,
                                   t.en_progress,
                                   t.stage_id,
                                   t.active
                            FROM project_task t
                            WHERE t.project_wbs_id = ANY (%s)
                              AND COALESCE(t.active, TRUE) = TRUE
                            """, (all_ids,))
        all_tasks_data = self.env.cr.dictfetchall()

        # Tạo dict và map
        task_dict = {task['id']: task for task in all_tasks_data}
        children_map = {}
        wbs_tasks_map = {}  # Map wbs_id -> list task_ids

        for task in all_tasks_data:
            # Map parent -> children
            parent_id = task.get('parent_id')
            if parent_id:
                children_map.setdefault(parent_id, []).append(task['id'])

            # Map wbs_id -> tasks
            wbs_id = task.get('project_wbs_id')
            if wbs_id:
                wbs_tasks_map.setdefault(wbs_id, []).append(task['id'])

        # Hàm tính % đệ quy cho task
        def calculate_task_actual_percent(task_id):
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

            for child_id in children_ids:
                child_data = task_dict.get(child_id)
                if not child_data or self._is_cancelled_record(self.env['project.task'].browse(child_id)):
                    continue

                # GỌI ĐỆ QUY để tính % cho con
                child_percent = calculate_task_actual_percent(child_id)

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

        # Tính % cho từng WBS từ các task gốc
        wbs_percent_map = {}
        for wbs_id in all_ids:
            task_ids = wbs_tasks_map.get(wbs_id, [])
            if not task_ids:
                wbs_percent_map[wbs_id] = 0.0
                continue

            # Chỉ lấy các task gốc của WBS
            root_tasks = []
            for task_id in task_ids:
                task_data = task_dict.get(task_id)
                if not task_data:
                    continue
                parent_id = task_data.get('parent_id')
                if not parent_id or task_dict.get(parent_id, {}).get('project_wbs_id') != wbs_id:
                    root_tasks.append(task_id)

            if not root_tasks:
                wbs_percent_map[wbs_id] = 0.0
                continue

            # Tính weighted average từ các task gốc
            total_weight = 0.0
            weighted_sum = 0.0

            for task_id in root_tasks:
                task_data = task_dict.get(task_id)
                if not task_data or self._is_cancelled_record(self.env['project.task'].browse(task_id)):
                    continue

                # Tính % cho task gốc (đệ quy qua toàn bộ cây con)
                task_percent = calculate_task_actual_percent(task_id)

                # Tính trọng số
                s = task_data.get('en_start_date')
                e = task_data.get('date_deadline')
                planned_hours = task_data.get('planned_hours') or 0.0

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
                weighted_sum += task_percent * duration

            wbs_percent_map[wbs_id] = weighted_sum / total_weight if total_weight else 0.0

        # Cập nhật kết quả
        all_records = self.browse(all_ids)
        for rec in all_records:
            if self._is_cancelled_record(rec):
                rec.actual_percent_completed = 0.0
            else:
                raw_value = wbs_percent_map.get(rec.id, 0.0)
                # ✅ CHỈ LÀM TRÒN KHI GÁN KẾT QUẢ CUỐI
                rec.actual_percent_completed = float_round(raw_value, precision_digits=2)

    @api.depends("wbs_task_ids", "wbs_task_ids.planned_hours")
    def _compute_planned_hours(self):
        for rec in self:
            wbs_phase_ids = rec.wbs_task_ids.filtered(
                lambda x: x.category == "package" and not self._is_cancelled_record(x))
            total = sum(x.planned_hours or 0.0 for x in wbs_phase_ids)
            rec.planned_hours = round(total, 2)

    @api.depends("wbs_task_ids", "wbs_task_ids.effective_hours")
    def _compute_effective_hours(self):
        for rec in self:
            wbs_phase_ids = rec.wbs_task_ids.filtered(
                lambda x: x.category == "package" and not self._is_cancelled_record(x))
            total = sum(x.effective_hours or 0.0 for x in wbs_phase_ids)
            rec.effective_hours = round(total, 2)

    def action_open_wizard_create_stage(self):
        return self.env['project.task'].with_context(
            project_id=self.project_id.id).action_open_wizard_create_task(project_wbs_id=self.id, category="phase")

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type == 'form':
            doc = etree.XML(res.get('arch').encode('utf-8'))
            forms = doc.xpath("//form")
            if forms:
                forms[0].set('show_edit', "state in ['draft']")
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    @api.depends("wbs_task_ids.en_start_date", "wbs_task_ids.date_deadline")
    def _compute_start_date_end_date(self):
        super()._compute_start_date_end_date()
        for rec in self:
            phase_ids = rec.wbs_task_ids.filtered(lambda x: x.category == "phase")
            if not phase_ids:
                continue
            rec.start_date = min(phase_ids.mapped('en_start_date'))
            rec.end_date = max(phase_ids.mapped('date_deadline'))

    def _constrains_workpackage_ids(self):
        super()._constrains_workpackage_ids()
        # TODO 18/07/2025 các gói việc bắt đầu trước 01/07/2025 thì bỏ qua ràng buộc
        timeline_base = "2025-07-01"
        for rec in self:
            packages = rec.wbs_task_ids.filtered(
                lambda x: x.category == "package" and x.en_start_date and x.date_deadline and x.count_subtask < 2
                          and x.stage_id.en_mark not in ['b', 'g'])
            for package in packages:
                number_of_days = (package.date_deadline - package.en_start_date).days + 1
                error = f"Gói việc {package.name} phải có ít nhất 2 gói việc con. Vui lòng bổ sung thêm!"
                if number_of_days > 45 and len(package.child_ids) < 2:
                    raise ValidationError(error)

    def button_duplicate_wbs(self):
        if not self._context.get("copy_wbs", False):
            return super(EnWbs, self).button_duplicate_wbs()
        self._check_resource_planing()
        newest_resource = self.env['en.resource.planning'].search(
            [('project_id', '=', self.project_id.id), ('state', '=', 'approved')],
            order='id desc', limit=1
        )
        new_wbs = self.with_context(copy_wbs=True).copy({
            'version_type': 'plan',
            'resource_plan_id': newest_resource.id,
            'active': True,
            'created_by_wbs_id': self.id,
            'parent_id': self.parent_id.id or self.id
        })
        new_wbs.with_context(copy_wbs=True).write({'resource_planning_link_wbs': newest_resource.id})
        for line in self.wbs_task_ids.filtered(lambda x: not x.parent_id and x.stage_id.en_mark != 'b'):
            line._copy_task_tree(new_wbs=new_wbs)
        return self.open_create_wbs_popup(new_wbs)

    # def button_approved(self):
    #     self = self.sudo()
    #     res = super().button_approved()
    #     if res:
    #         tasks = self.wbs_task_ids.filtered(lambda x: x.category == "task")
    #         for task in tasks:
    #             task = task.sudo()
    #             task.related_task_id.timesheet_ids.ot_id.write({'task_id': task.id})
    #             task.related_task_id.timesheet_ids.write({'task_id': task.id})
    #             self.env['en.overtime.plan'].sudo().search([('en_work_id', '=', task.related_task_id.id)]).write(
    #                 {'en_work_id': task.id})
    #     return res

    @staticmethod
    def find_related_task(task):
        while task:
            if task.project_wbs_state == 'inactive':
                return task
            task = task.related_task_id
        return False

    # Logic mới, move timesheet từ wbs hết hiệu lực sang wbs duyệt mới
    def button_approved(self):
        self = self.sudo()
        overtime_obj = self.env['en.overtime.plan'].sudo()
        res = super().button_approved()
        if res:
            tasks = self.sudo().wbs_task_ids.filtered(lambda x: x.category == "task")
            for task in tasks:
                related_task = task.related_task_id
                if related_task and related_task.project_wbs_state == 'refused':
                    related_task = self.find_related_task(related_task)
                if related_task:
                    related_task.timesheet_ids.ot_id.write({'task_id': task.id})
                    related_task.timesheet_ids.write({'task_id': task.id})
                    overtimes = overtime_obj.search([('en_work_id', '=', related_task.id)])
                    overtimes.write({'en_work_id': task.id})
                    task.write({"task_old_related_id": related_task.id})
        return res


class NewVersionWBSWizard(models.TransientModel):
    _inherit = "new.version.wbs.wizard"

    def button_confirm(self):
        return self.wbs_id.with_context(copy_wbs=True).button_duplicate_wbs()
