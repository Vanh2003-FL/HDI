import logging
from datetime import timedelta, datetime
from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProjectProject(models.Model):
    _inherit = "project.project"


    def get_project_stage(self):
        stages = self.env["project.task.type"].search([("project_ids", "!=", False)])
        return {stage.name: stage.id for stage in stages}

    @staticmethod
    def format_date(dt):
        return fields.Date.to_date(dt + timedelta(hours=7)) if isinstance(dt, datetime) else None

    @api.model
    def action_migration_wbs(self):
        projects = self.search([], order="id desc")
        stages = self.get_project_stage()
        for project in projects:
            try:
                with self.env.cr.savepoint():
                    project._migration_wbs_by_project(stages)
            except Exception as e:
                _logger.error(f"==========Error Migration Project WBS {project.name} {e}=============")
        _logger.info("============Hoàn thành Migration WBS phân cấp=============")

    def _migration_wbs_by_project(self, stages):
        if not self:
            return

        def insert_task(values):
            keys = ', '.join(values.keys())
            placeholders = ', '.join(['%s'] * len(values))
            sql = f"""INSERT INTO project_task ({keys}) VALUES ({placeholders}) RETURNING id"""
            self.env.cr.execute(sql, tuple(values.values()))
            return self.env.cr.fetchone()[0]

        project_id = self.id
        company_id = self.company_id.id
        uid = self.env.uid
        now = fields.Datetime.now()
        for wbs in self.en_wbs_ids:
            update_batch = []
            sequence_stage = 1
            for stage in wbs.project_stage_ids.sorted(key="start_date"):
                code = f"P.{sequence_stage}"
                sequence_stage += 1
                name = dict(stage._fields['state'].selection).get(stage.state)
                stage_name = "Hoàn thành" if name == "Đã hoàn thành" else name
                stage_id = stages.get(stage_name)
                task_phase_id = insert_task({
                    "name": stage.name,
                    "category": 'phase',
                    "stage_id": stage_id,
                    "project_id": project_id,
                    "display_project_id": project_id,
                    "project_wbs_id": wbs.id,
                    "stage_type_id": stage.stage_type_id.id,
                    "en_start_date": stage.start_date,
                    "date_deadline": stage.end_date,
                    "actual_start_date": self.format_date(stage.en_real_start_date),
                    "actual_end_date": self.format_date(stage.en_real_end_date),
                    "en_handler": stage.en_approver_id.id or None,
                    "en_approver_id": stage.en_approver_id.id or None,
                    "is_project_milestone": stage.project_milestone,
                    "is_project_payment": stage.payment_milestone,
                    "create_uid": uid,
                    "create_date": now,
                    "kanban_state": 'normal',
                    "company_id": company_id,
                    "en_requester": uid,
                    "en_progress": len(stage.order_line),
                    "active": True,
                    "project_wbs_state": wbs.state,
                    "code": code
                })
                sequence_package = 1
                for package in stage.order_line.filtered(lambda x: not x.parent_id).sorted(key="date_start"):
                    code = f"W.{sequence_package}"
                    sequence_package += 1
                    name = dict(package._fields['state'].selection).get(package.state)
                    stage_name = "Hoàn thành" if name == "Đã hoàn thành" else name
                    stage_id = stages.get(stage_name)
                    task_package_id = insert_task({
                        "parent_id": task_phase_id,
                        "name": package.name,
                        "category": 'package',
                        "stage_id": stage_id,
                        "project_id": project_id,
                        "display_project_id": project_id,
                        "project_wbs_id": wbs.id,
                        "en_start_date": package.date_start,
                        "date_deadline": package.date_end,
                        "actual_start_date": self.format_date(package.en_real_start_date),
                        "actual_end_date": self.format_date(package.en_real_end_date),
                        "en_handler": package.user_id.id or None,
                        "en_approver_id": package.en_approver_id.id or None,
                        "is_project_milestone": package.pj_milestone,
                        "is_hand_over_document": package.handover_doc,
                        "create_uid": uid,
                        "create_date": now,
                        "kanban_state": 'normal',
                        "company_id": company_id,
                        "en_requester": uid,
                        "en_progress": len(package.child_ids) or len(package.task_ids),
                        "active": True,
                        "project_wbs_state": wbs.state,
                        "code": code
                    })
                    sequence_child_package = 1
                    for child in package.child_ids.sorted(key="date_start"):
                        code = f"Z.{sequence_child_package}"
                        sequence_child_package += 1
                        name = dict(child._fields['state'].selection).get(child.state)
                        stage_name = "Hoàn thành" if name == "Đã hoàn thành" else name
                        stage_id = stages.get(stage_name)
                        task_child_package_id = insert_task({
                            "parent_id": task_package_id,
                            "name": child.name,
                            "category": 'child_package',
                            "stage_id": stage_id,
                            "project_id": project_id,
                            "display_project_id": project_id,
                            "project_wbs_id": wbs.id,
                            "en_start_date": child.date_start,
                            "date_deadline": child.date_end,
                            "actual_start_date": self.format_date(child.en_real_start_date),
                            "actual_end_date": self.format_date(child.en_real_end_date),
                            "en_handler": child.user_id.id or None,
                            "en_approver_id": child.en_approver_id.id or None,
                            "is_project_milestone": child.pj_milestone,
                            "is_hand_over_document": child.handover_doc,
                            "create_uid": uid,
                            "create_date": now,
                            "kanban_state": 'normal',
                            "company_id": company_id,
                            "en_requester": uid,
                            "en_progress": len(child.task_ids),
                            "active": True,
                            "project_wbs_state": wbs.state,
                            "code": code
                        })
                        sequence_child_task = 1
                        for task in child.task_ids.sorted(key="en_start_date"):
                            code = f"T.{sequence_child_task}"
                            sequence_child_task += 1
                            update_batch.append((
                                task_child_package_id, 'task', project_id, project_id, wbs.id, wbs.state, uid, now,
                                code, task.id
                            ))
                    if not package.child_ids and package.task_ids:
                        sequence_task = 1
                        for task in package.task_ids.sorted(key="en_start_date"):
                            code = f"T.{sequence_task}"
                            sequence_task += 1
                            update_batch.append((
                                task_package_id, 'task', project_id, project_id, wbs.id, wbs.state, uid, now, code,
                                task.id
                            ))
            if update_batch:
                self.env.cr.executemany("""
                                        UPDATE project_task
                                        SET parent_id          = %s,
                                            category           = %s,
                                            project_id         = %s,
                                            display_project_id = %s,
                                            project_wbs_id     = %s,
                                            project_wbs_state  = %s,
                                            write_uid          = %s,
                                            write_date         = %s,
                                            code               = %s
                                        WHERE id = %s
                                        """, update_batch)

    @api.model
    def action_compute_wbs_project_task(self):
        projects = self.env["project.project"].search([], order="id desc")
        for p in projects:
            tasks = self.env["project.task"].with_context(migration_wbs=True).sudo().search(
                [("category", "!=", False), ("project_id", "=", p.id), ("category", "=", "task"),
                 ("project_wbs_state", "not in", ["refused", "expire"])], order="id asc")
            non_tasks = self.env["project.task"].with_context(migration_wbs=True).sudo().search(
                [("category", "!=", False), ("project_id", "=", p.id), ("category", "not in", ["task"]),
                 ("project_wbs_state", "not in", ["refused", "expire"])], order="id asc")
            tasks._compute_plan_percent_completed()
            tasks._compute_actual_percent_completed()
            non_tasks._compute_planned_hours()
            non_tasks._compute_effective_hours()
            non_tasks._compute_has_child_package()
        _logger.info("============Hoàn thành Migration WBS phân cấp tính toán=============")

    @api.model
    def action_action_migration_resource_planning(self):
        self.env.cr.execute("""update en_resource_detail set project_task_stage_id = null;""")
        ResourceDetail = self.env["en.resource.detail"].with_context(no_constrains=True)

        def get_overlap_days(a_start, a_end, b_start, b_end):
            overlap_start = max(a_start, b_start)
            overlap_end = min(a_end, b_end)
            return max((overlap_end - overlap_start).days + 1, 0)

        wbs = self.env["en.wbs"].search([("state", "in", ['awaiting', 'approved'])], order="id desc")
        for w in wbs:
            resource_planing = self.env["en.resource.planning"].search(
                [('state', '=', 'approved'), ('project_id', '=', w.project_id.id)], order="id desc", limit=1)
            w.write({'resource_planning_link_wbs': resource_planing.id})
            w.resource_planning_link_wbs.write({"wbs_link_resource_planning": w.id})
        resource_plans = self.env["en.resource.planning"].with_context(no_constrains=True).search(
            [("wbs_link_resource_planning", "!=", False), ("state", "not in", ['refused', 'expire'])])
        for resource in resource_plans:
            wbs_phases = resource.wbs_link_resource_planning.wbs_task_ids.filtered(
                lambda t: t.category == "phase" and t.en_start_date and t.date_deadline)
            new_lines = []
            for line in resource.order_line.sorted(key="date_start"):
                if not line.date_start or not line.date_end:
                    continue
                phase_cover = wbs_phases.filtered(
                    lambda p: p.en_start_date <= line.date_start and p.date_deadline >= line.date_end
                ).sorted(key="en_start_date")
                if phase_cover:
                    line.update({'project_task_stage_id': phase_cover[0].id})
                    continue
                raw_overlaps = wbs_phases.filtered(
                    lambda p: p.en_start_date < line.date_end and p.date_deadline > line.date_start
                ).sorted(key="en_start_date")
                phase_overlaps = []
                for phase in raw_overlaps:
                    current_days = get_overlap_days(line.date_start, line.date_end, phase.en_start_date,
                                                    phase.date_deadline)
                    should_add = True
                    for i, selected in enumerate(phase_overlaps):
                        if phase.en_start_date < selected.date_deadline and phase.date_deadline > selected.en_start_date:
                            selected_days = get_overlap_days(line.date_start, line.date_end,
                                                             selected.en_start_date, selected.date_deadline)
                            if current_days > selected_days:
                                phase_overlaps[i] = phase
                            should_add = False
                            break
                    if should_add:
                        phase_overlaps.append(phase)
                if not phase_overlaps:
                    continue
                first_phase = phase_overlaps[0]
                overlap_start = max(line.date_start, first_phase.en_start_date)
                overlap_end = min(line.date_end, first_phase.date_deadline)
                for phase in phase_overlaps[1:]:
                    new_start = max(line.date_start, phase.en_start_date)
                    new_end = min(line.date_end, phase.date_deadline)
                    if new_start <= new_end:
                        new_line_vals = {
                            'order_id': resource.id,
                            'project_task_stage_id': phase.id,
                            'type_id': line.type_id.id,
                            'employee_id': line.employee_id.id,
                            'role_id': line.role_id.id,
                            'job_position_id': line.job_position_id.id,
                            'date_start': new_start,
                            'date_end': new_end,
                            'workload': line.workload,
                        }
                        new_lines.append(new_line_vals)
                line.write({
                    'date_start': overlap_start,
                    'date_end': overlap_end,
                    'project_task_stage_id': first_phase.id,
                })
            if new_lines:
                ResourceDetail.create(new_lines)
        _logger.info("============Hoàn thành Migration nguồn lực=============")
