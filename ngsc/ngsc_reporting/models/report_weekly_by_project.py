import json
from datetime import date, datetime, timedelta
import unicodedata

from odoo import models, api, _, exceptions
from odoo.exceptions import ValidationError, UserError
from odoo.tools import float_utils


def handle_date(obj):
    if isinstance(obj, (date, datetime)):  # Sử dụng tuple để kiểm tra cả date và datetime
        return obj.strftime("%d-%m-%Y")
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class ReportWeeklyByProject(models.TransientModel):
    _name = 'report.weekly.by.project'

    @api.model
    def get_all_projects(self):
        projects = []
        data = self.env['project.project'].search([])
        for record in data:
            projects.append({'id': record.id, 'name': record.name, 'code': record.en_code})
        return projects

    @api.model
    def get_detail_project(self, _id, _date):
        project = self.env['project.project'].search([('id', '=', int(_id))])

        return {
            'name': project.name,
            'en_code': project.en_code,
            'department': project.en_department_id.name,
            'manager': project.user_id.name,
            'type': project.en_project_type_id.name,
            'date_start': handle_date(project.date_start),
            'date_end': handle_date(project.date),
            'dateReport': handle_date(datetime.strptime(_date, "%Y-%m-%d"))
        }

    def validate_dates(self, start_date, end_date):
        if start_date and end_date:
            if start_date > end_date:
                raise UserError("Ngày bắt đầu không được lớn hơn ngày kết thúc")

    @api.model
    def get_cumulative_index(self, _id, start_date, end_date):
        """
        TÍNH KDA và các chỉ số
        - KDA, TDA: luôn tính cumulative đến end_date (giữ logic cũ)
        - SLA: tính theo khoảng thời gian nếu có start_date, ngược lại tính cumulative
        """
        self.validate_dates(start_date, end_date)

        # Xử lý ngày
        if hasattr(end_date, 'date'):
            end_date = end_date.date()

        # Xử lý start_date - có thể là None hoặc chuỗi rỗng
        if start_date:
            if hasattr(start_date, 'date'):
                start_date = start_date.date()
        else:
            start_date = None

        """
        KDA - LUÔN tính cumulative đến end_date (giữ nguyên logic cũ)
        """
        # Calculate mm_in_plan
        self.env.cr.execute("""
            SELECT SUM(value)
            FROM project_resource_summary
            WHERE project_id = %s
            AND criteria_type = %s
            AND TO_DATE(month, 'MM/YYYY') <= %s
        """, (_id, 'plan', end_date))
        mm_in_plan = self.env.cr.fetchone()[0] or 0.0

        # Calculate mm_actual
        self.env.cr.execute("""
            SELECT SUM(value)
            FROM project_resource_summary
            WHERE project_id = %s
            AND criteria_type = %s
            AND TO_DATE(month, 'MM/YYYY') <= %s
        """, (_id, 'actual', end_date))
        mm_actual = self.env.cr.fetchone()[0] or 0.0

        # Calculate KDA: mm_actual / mm_in_plan, return 0 if mm_in_plan is 0
        if float_utils.float_is_zero(mm_in_plan, precision_digits=6):
            kda = 0.0
        else:
            kda = round((mm_actual * 100) / mm_in_plan, 2)

        """
        TDA - LUÔN tính cumulative (giữ nguyên logic cũ)
        """
        self.env.cr.execute("""
            SELECT plan_percent_completed, actual_percent_completed
            FROM en_wbs
            WHERE project_id = %s
            AND version_type = 'baseline'
            AND state = 'approved'
            AND active = true
        """, (_id, ))
        wbs = self.env.cr.fetchone()
        plan = wbs[0] if wbs else 0.0
        actual = wbs[1] if wbs else 0.0

        if float_utils.float_is_zero(plan, precision_digits=6):
            tda = 0.0
        else:
            tda = round((actual * 100) / plan, 2)

        """
        SLA Phản hồi - TÍNH THEO KHOẢNG THỜI GIAN NẾU CÓ START_DATE
        """
        if start_date:
            # Tính SLA trong khoảng thời gian từ start_date đến end_date
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND en_day_rep IS NOT NULL
                AND en_dl_rep IS NOT NULL
                AND ht.active = TRUE
                AND en_day_rep <= en_dl_rep
                AND date_log BETWEEN %s AND %s
            """, (_id, start_date, end_date))
            on_time_tickets = self.env.cr.fetchone()[0] or 0

            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE ht.project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_dl_rep IS NOT NULL
                AND ht.active = TRUE
                AND ht.en_dl_rep BETWEEN %s AND %s
            """, (_id, start_date, end_date))
            due_tickets = self.env.cr.fetchone()[0] or 0
        else:
            # Logic cũ - tính cumulative đến end_date
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND en_day_rep IS NOT NULL
                AND en_dl_rep IS NOT NULL
                AND ht.active = TRUE
                AND en_day_rep <= en_dl_rep
                AND date_log <= %s
            """, (_id, end_date))
            on_time_tickets = self.env.cr.fetchone()[0] or 0

            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE ht.project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_dl_rep IS NOT NULL
                AND ht.active = TRUE
                AND ht.en_dl_rep <= %s
            """, (_id, end_date))
            due_tickets = self.env.cr.fetchone()[0] or 0

        # Xử lý trường hợp fallback nếu không có ticket
        if float_utils.float_is_zero(due_tickets, precision_digits=6):
            if start_date:
                self.env.cr.execute("""
                    SELECT 
                        COALESCE(SUM(total_ticket_ontime_feedback), 0) AS ontime_feedback,
                        COALESCE(SUM(total_ticket_due_feedback), 0)    AS due_feedback
                    FROM en_work_plans ewp
                    WHERE project_id = %s
                    AND date_work_plan BETWEEN %s AND %s
                """, (_id, start_date, end_date))
            else:
                self.env.cr.execute("""
                    SELECT 
                        COALESCE(SUM(total_ticket_ontime_feedback), 0) AS ontime_feedback,
                        COALESCE(SUM(total_ticket_due_feedback), 0)    AS due_feedback
                    FROM en_work_plans ewp
                    WHERE project_id = %s
                    AND date_work_plan <= %s
                """, (_id, end_date))

            row = self.env.cr.fetchone()
            ontime_feedback = row[0]
            due_feedback = row[1]
            sla_response = round((ontime_feedback * 100.0) / due_feedback, 2) if due_feedback else 0.0
        else:
            sla_response = round((on_time_tickets * 100) / due_tickets, 2)

        """
        SLA Xử lý - TÍNH THEO KHOẢNG THỜI GIAN NẾU CÓ START_DATE
        """
        if start_date:
            # Tính SLA trong khoảng thời gian từ start_date đến end_date
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE ht.project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_day_com IS NOT NULL
                AND ht.en_dl IS NOT NULL
                AND ht.active = TRUE
                AND ht.en_day_com <= ht.en_dl
                AND ht.date_log BETWEEN %s AND %s
            """, (_id, start_date, end_date))
            on_time_tickets_process = self.env.cr.fetchone()[0] or 0

            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE project_id = %s 
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_dl IS NOT NULL
                AND ht.active = TRUE
                AND en_dl BETWEEN %s AND %s
            """, (_id, start_date, end_date))
            due_tickets_process = self.env.cr.fetchone()[0] or 0
        else:
            # Logic cũ - tính cumulative đến end_date
            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE ht.project_id = %s
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_day_com IS NOT NULL
                AND ht.en_dl IS NOT NULL
                AND ht.active = TRUE
                AND ht.en_day_com <= ht.en_dl
                AND ht.date_log <= %s
            """, (_id, end_date))
            on_time_tickets_process = self.env.cr.fetchone()[0] or 0

            self.env.cr.execute("""
                SELECT COUNT(*)
                FROM helpdesk_ticket ht
                JOIN helpdesk_stage hs ON ht.stage_id = hs.id
                WHERE project_id = %s 
                AND hs.en_state NOT IN ('cancel', 'wait')
                AND ht.en_dl IS NOT NULL
                AND ht.active = TRUE
                AND en_dl <= %s
            """, (_id, end_date))
            due_tickets_process = self.env.cr.fetchone()[0] or 0

        # Xử lý trường hợp fallback nếu không có ticket
        if float_utils.float_is_zero(due_tickets_process, precision_digits=6):
            if start_date:
                self.env.cr.execute("""
                    SELECT 
                        COALESCE(SUM(total_ticket_ontime_process), 0) AS ontime_process,
                        COALESCE(SUM(total_ticket_due_process), 0)    AS due_process
                    FROM en_work_plans ewp
                    WHERE project_id = %s
                    AND date_work_plan BETWEEN %s AND %s
                """, (_id, start_date, end_date))
            else:
                self.env.cr.execute("""
                    SELECT 
                        COALESCE(SUM(total_ticket_ontime_process), 0) AS ontime_process,
                        COALESCE(SUM(total_ticket_due_process), 0)    AS due_process
                    FROM en_work_plans ewp
                    WHERE project_id = %s
                    AND date_work_plan <= %s
                """, (_id, end_date))

            row = self.env.cr.fetchone()
            ontime_process = row[0]
            due_process = row[1]
            sla_process = round((ontime_process * 100.0) / due_process, 2) if due_process else 0.0
        else:
            sla_process = round((on_time_tickets_process * 100) / due_tickets_process, 2)

        return {
            'kda': kda,
            'tda': tda,
            'sla_response': sla_response,
            'sla_process': sla_process
        }

    @api.model
    def _is_support_project(self, _id):
        self.env.cr.execute("""
                            SELECT pt.name
                            FROM project_project pp
                                     JOIN en_project_type pt ON pp.en_project_type_id = pt.id
                            WHERE pp.id = %s
                            """, (_id,))
        row = self.env.cr.fetchone()
        if not row:
            return False

        db_name = unicodedata.normalize('NFC', str(row[0]).strip().lower())
        target = unicodedata.normalize('NFC', 'hỗ trợ vận hành')

        return db_name == target

    @api.model
    def get_tasks_in_week(self, _id, _date):
        format_date = "%Y-%m-%d"
        to_date = datetime.strptime(_date, format_date)
        from_date = to_date - timedelta(days=7)

        is_support_project = self._is_support_project(_id)

        if is_support_project:
            # Đối với dự án "Hỗ trợ vận hành": lấy công việc có date_deadline SAU ngày báo cáo
            self.env.cr.execute("""
                                SELECT pt.name,
                                       pt.date_deadline,
                                       task.name                                  AS task_type_name,
                                       pt.category,
                                       COALESCE(pt.actual_percent_completed, 0.0) AS actual_percent_completed,
                                       phase.name                                 AS phase_name
                                FROM project_project pp
                                         JOIN en_wbs wbs ON pp.id = wbs.project_id
                                         JOIN project_task pt ON pt.project_wbs_id = wbs.id
                                         JOIN project_task_type task ON pt.stage_id = task.id
                                         LEFT JOIN (SELECT id, name, parent_id
                                                    FROM project_task p
                                                    WHERE p.project_id = %s AND p.category IS NOT NULL) phase
                                                   ON phase.id = pt.parent_id
                                WHERE pp.id = %s
                                  AND wbs.version_type = 'baseline'
                                  AND wbs.state = 'approved'
                                  AND pt.category = 'package'
                                  AND pt.date_deadline > %s
                                ORDER BY pt.date_deadline ASC
                                """, (_id, _id, to_date))
        else:
            # Logic cũ cho các dự án khác
            self.env.cr.execute("""
                                SELECT pt.name,
                                       pt.date_deadline,
                                       task.name                                  AS task_type_name,
                                       pt.category,
                                       COALESCE(pt.actual_percent_completed, 0.0) AS actual_percent_completed,
                                       phase.name                                 AS phase_name
                                FROM project_project pp
                                         JOIN en_wbs wbs ON pp.id = wbs.project_id
                                         JOIN project_task pt ON pt.project_wbs_id = wbs.id
                                         JOIN project_task_type task ON pt.stage_id = task.id
                                         LEFT JOIN (SELECT id, name, parent_id
                                                    FROM project_task p
                                                    WHERE p.project_id = %s AND p.category IS NOT NULL) phase
                                                   ON phase.id = pt.parent_id
                                WHERE pp.id = %s
                                  AND wbs.version_type = 'baseline'
                                  AND wbs.state = 'approved'
                                  AND pt.category = 'package'
                                  AND pt.stage_id != (
                    SELECT id
                    FROM project_task_type task
                    JOIN project_task_type_rel rel ON rel.type_id = task.id
                    WHERE rel.project_id = %s
                                    ORDER BY sequence DESC
                                    LIMIT 1
                                    )
                                  AND pt.date_deadline BETWEEN %s
                                  AND %s
                                ORDER BY pt.date_deadline DESC
                                """, (_id, _id, _id, from_date, to_date))

        fetched_data = self.env.cr.dictfetchall()
        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_tasks_not_completed(self, _id, _date):
        format_date = "%Y-%m-%d"
        to_date = datetime.strptime(_date, format_date)
        from_date = to_date - timedelta(days=7)

        is_support_project = self._is_support_project(_id)

        if is_support_project:
            # Đối với dự án "Hỗ trợ vận hành": lấy công việc có date_deadline TRƯỚC ngày báo cáo
            self.env.cr.execute("""
                                SELECT pt.name,
                                       pt.date_deadline,
                                       task.name                                  AS task_type_name,
                                       pt.category,
                                       COALESCE(pt.actual_percent_completed, 0.0) AS actual_percent_completed,
                                       phase.name                                 AS phase_name
                                FROM project_project pp
                                         JOIN en_wbs wbs ON pp.id = wbs.project_id
                                         JOIN project_task pt ON pt.project_wbs_id = wbs.id
                                         JOIN project_task_type task ON pt.stage_id = task.id
                                         LEFT JOIN (SELECT id, name, parent_id
                                                    FROM project_task p
                                                    WHERE p.project_id = %s AND p.category IS NOT NULL) phase
                                                   ON phase.id = pt.parent_id
                                WHERE pp.id = %s
                                  AND wbs.version_type = 'baseline'
                                  AND wbs.state = 'approved'
                                  AND pt.category = 'package'
                                  AND pt.stage_id IN (SELECT task.id
                                                      FROM project_task_type task
                                                               JOIN project_task_type_rel rel ON rel.type_id = task.id
                                                      WHERE rel.project_id = %s
                                                        AND task.is_closed = false)
                                  AND pt.date_deadline < %s
                                ORDER BY pt.date_deadline DESC
                                """, (_id, _id, _id, to_date))
        else:
            # Logic cũ cho các dự án khác
            self.env.cr.execute("""
                                SELECT pt.name,
                                       pt.date_deadline,
                                       task.name                                  AS task_type_name,
                                       pt.category,
                                       COALESCE(pt.actual_percent_completed, 0.0) AS actual_percent_completed,
                                       phase.name                                 AS phase_name
                                FROM project_project pp
                                         JOIN en_wbs wbs ON pp.id = wbs.project_id
                                         JOIN project_task pt ON pt.project_wbs_id = wbs.id
                                         JOIN project_task_type task ON pt.stage_id = task.id
                                         LEFT JOIN (SELECT id, name, parent_id
                                                    FROM project_task p
                                                    WHERE p.project_id = %s AND p.category IS NOT NULL) phase
                                                   ON phase.id = pt.parent_id
                                WHERE pp.id = %s
                                  AND wbs.version_type = 'baseline'
                                  AND wbs.state = 'approved'
                                  AND pt.category = 'package'
                                  AND pt.stage_id IN (SELECT task.id
                                                      FROM project_task_type task
                                                               JOIN project_task_type_rel rel ON rel.type_id = task.id
                                                      WHERE rel.project_id = %s
                                                        AND task.is_closed = false)
                                  AND pt.date_deadline < %s
                                ORDER BY pt.date_deadline DESC
                                """, (_id, _id, _id, from_date))

        fetched_data = self.env.cr.dictfetchall()
        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_tasks_next_week(self, _id, _date):
        format_date = "%Y-%m-%d"
        from_date = datetime.strptime(_date, format_date)
        from_date = from_date + timedelta(days=1)
        to_date = from_date + timedelta(days=14)

        self.env.cr.execute("""
                SELECT
                    pt.name,
                    pt.date_deadline,
                    task.name AS task_type_name,
                    pt.category,
                    COALESCE(pt.actual_percent_completed, 0.0) AS actual_percent_completed,
                    phase.name AS phase_name
                FROM project_project pp
                JOIN en_wbs wbs ON pp.id = wbs.project_id
                JOIN project_task pt ON pt.project_wbs_id = wbs.id
                JOIN project_task_type task ON pt.stage_id = task.id
                LEFT JOIN (SELECT id, name, parent_id FROM project_task p WHERE p.project_id = %s AND p.category IS NOT NULL) phase ON phase.id = pt.parent_id
                WHERE pp.id = %s
                AND wbs.version_type = 'baseline'
                AND wbs.state = 'approved'
                AND pt.category = 'package'
                AND pt.date_deadline BETWEEN %s AND %s
                ORDER BY pt.date_deadline DESC
        """, (_id, _id, from_date, to_date))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_docs_complete_in_week(self, _id, _date):
        format_date = "%Y-%m-%d"
        to_date = datetime.strptime(_date, format_date)
        from_date = to_date - timedelta(days=7)

        self.env.cr.execute("""
                SELECT d.name, d.handover_date, d.state, en_stage_type.name AS phase_type
                FROM en_project_document d
                LEFT JOIN  en_stage_type ON en_stage_type.id = d.en_state
                WHERE d.project_id = %s 
                AND d.handover_date BETWEEN %s AND %s 
                ORDER BY d.handover_date DESC
        """, (_id, from_date, to_date))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_docs_pending(self, _id, _date):
        format_date = "%Y-%m-%d"
        to_date = datetime.strptime(_date, format_date)
        from_date = to_date - timedelta(days=7)

        self.env.cr.execute("""
                SELECT d.name, d.handover_date, d.state, en_stage_type.name AS phase_type
                FROM en_project_document d
                LEFT JOIN  en_stage_type ON en_stage_type.id = d.en_state
                WHERE d.project_id = %s 
                AND d.handover_date < %s 
                AND d.state = 'new'
                ORDER BY d.handover_date DESC
        """, (_id, from_date))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_docs_next_week(self, _id, _date):
        format_date = "%Y-%m-%d"
        from_date = datetime.strptime(_date, format_date)
        from_date = from_date + timedelta(days=1)
        to_date = from_date + timedelta(days=14)

        self.env.cr.execute("""
                    SELECT d.name, d.handover_date, d.state, en_stage_type.name AS phase_type
                    FROM en_project_document d
                    LEFT JOIN  en_stage_type ON en_stage_type.id = d.en_state
                    WHERE d.project_id = %s 
                    AND d.handover_date BETWEEN %s AND %s 
                    ORDER BY d.handover_date DESC
            """, (_id, from_date, to_date))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_project_risks(self, _id, _date):
        self.env.cr.execute("""
                    SELECT r.id, r.name as name, en_risk_level.name as level, r.recover, r.deadline, en_risk_stage.name as stage, ps.name as phase
                    FROM en_risk r
                    LEFT JOIN en_risk_level ON r.risk_level_id = en_risk_level.id
                    JOIN en_risk_stage ON r.stage_id = en_risk_stage.id AND en_risk_stage.name NOT IN ('Hoàn thành', 'Hủy', 'Đã đóng', 'Bàn giao')
                    LEFT JOIN en_project_stage ps ON ps.id = r.project_stage_id 
                    WHERE r.project_id = %s
                    ORDER BY r.deadline DESC;
                """, (_id,))
        fetched_data = self.env.cr.dictfetchall()

        if not fetched_data:
            for item in fetched_data:
                item['risk_leftover'] = []
        else:
            ids = [item['id'] for item in fetched_data]
            ids_tuple = tuple(ids)

            self.env.cr.execute("""
                SELECT *
                FROM en_risk_leftover
                WHERE risk_id IN %s
            """, (ids_tuple,))
            risk_leftover_records = self.env.cr.dictfetchall()

            risk_leftover_map = {}
            for record in risk_leftover_records:
                risk_id = record['risk_id']
                if risk_id not in risk_leftover_map:
                    risk_leftover_map[risk_id] = []
                risk_leftover_map[risk_id].append(record)

            for item in fetched_data:
                item_id = item['id']
                item['risk_leftover'] = risk_leftover_map.get(item_id, [])

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_project_problems(self, _id, _date):
        self.env.cr.execute("""
            SELECT p.name as name, effect, solution_plan, deadline, en_risk_stage.name as stage, ps.name as phase
            FROM en_problem p
            JOIN en_risk_stage ON p.stage_id = en_risk_stage.id AND en_risk_stage.name NOT IN ('Hoàn thành', 'Hủy', 'Đã đóng', 'Bàn giao')
            LEFT JOIN en_project_stage ps ON ps.id = p.project_stage_id 
            WHERE project_id = %s
            ORDER BY deadline DESC;
        """, (_id,))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_project_surveys(self, _id, _date):
        self.env.cr.execute("""
                SELECT date, point, customer_comment, phase
                FROM qa_survey
                WHERE project_id = %s
                ORDER BY date DESC;
            """, (_id,))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)

    @api.model
    def get_project_qa_evaluation(self, _id, _date):
        format_date = "%Y-%m-%d"
        to_date = datetime.strptime(_date, format_date)
        from_date = to_date - timedelta(days=30)

        self.env.cr.execute("""
                            SELECT date, slow_progress, not_stay_on_track, non_compliance, acceptance_payment
                            FROM qa_evaluate
                            WHERE project_id = %s
                              AND date BETWEEN %s
                              AND %s
                            ORDER BY date DESC;
                            """, (_id, from_date, to_date))
        fetched_data = self.env.cr.dictfetchall()

        return json.dumps(fetched_data, default=handle_date, ensure_ascii=False)
