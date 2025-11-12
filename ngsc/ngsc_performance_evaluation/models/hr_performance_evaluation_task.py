# -*- coding: utf-8 -*-
from odoo import models, fields, api
from ..utils.constant import *


class HrPerformanceEvaluationTask(models.Model):
    _name = "ngsc.hr.performance.evaluation.task"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "date_start asc"
    _rec_name = "user_id"
    _description = "Đánh giá hiệu suất công việc"

    name = fields.Char(string="Tên công việc", compute="_compute_task_evaluation", store=True)
    task_id = fields.Many2one("project.task", string="Công việc", compute="_compute_task_evaluation", store=True)
    non_task_id = fields.Many2one("en.nonproject.task", string="Công việc ngoài dự án", compute="_compute_task_evaluation", store=True)
    performance_evaluation_id = fields.Many2one("ngsc.hr.performance.evaluation", string="Đánh giá hiệu suất")
    project_id = fields.Many2one("project.project", string="Dự án", compute="_compute_task_evaluation", store=True)
    user_id = fields.Many2one("res.users", string="Người chịu trách nhiệm", compute="_compute_task_evaluation", store=True)
    date_start = fields.Date(string="Ngày bắt đầu", compute="_compute_task_evaluation", store=True)
    date_end = fields.Date(string="Ngày kết thúc", compute="_compute_task_evaluation", store=True)
    hour_actual = fields.Float(string="Số giờ thực hiện", compute="_compute_task_evaluation", store=True)
    hour_actual_resource = fields.Float(string="Số giờ ghi nhận", compute="_compute_task_evaluation", store=True)
    evaluation = fields.Selection(string="Điểm đánh giá chất lượng", selection=task_evaluation_options, compute="_compute_task_evaluation", store=True)
    quality_evaluation = fields.Float(string="Điểm chất lượng", compute="_compute_quality_evaluation", store=True)
    en_task_type = fields.Selection([
        ('daily', 'Công việc hàng ngày'),
        ('support', 'Công việc kinh doanh'),
        ('waiting_task', 'Công việc trong dự án đang chờ'),
        ('presale', 'Công việc Presale'),
        ('support_project', 'Công việc hỗ trợ dự án')
    ], string='Loại việc', compute="_compute_task_evaluation", store=True)
    task_evaluation_id = fields.Many2one("task.evaluation",string="Công việc đánh giá",  ondelete="cascade")

    @api.depends("evaluation")
    def _compute_quality_evaluation(self):
        for rec in self:
            point = int(rec.evaluation) if rec.evaluation else 0
            if point == 1:
                converted = 0.4
            elif point == 2:
                converted = 0.7
            elif point == 3:
                converted = 1.0
            elif point == 4:
                converted = 1.5
            elif point == 5:
                converted = 2.0
            else:
                converted = 0.0
            rec.quality_evaluation = converted

    @api.depends("task_evaluation_id")
    def _compute_task_evaluation(self):
        for rec in self:
            task_evaluation_id = rec.task_evaluation_id if rec.task_evaluation_id.is_locked else self.env["task.evaluation"]
            rec.name = task_evaluation_id.name or rec.name
            rec.task_id = task_evaluation_id.project_task_id.id or rec.task_id.id
            rec.non_task_id = task_evaluation_id.nonproject_task_id.id or rec.non_task_id.id
            rec.project_id = task_evaluation_id.project_task_id.project_id.id or rec.project_id.id
            rec.user_id = task_evaluation_id.user_id.id or rec.user_id.id
            rec.date_start = task_evaluation_id.date_start or rec.date_start
            rec.date_end = task_evaluation_id.date_end or rec.date_end
            rec.hour_actual = task_evaluation_id.hour_actual or rec.hour_actual
            rec.hour_actual_resource = task_evaluation_id.hour_actual_resource or rec.hour_actual_resource
            rec.evaluation = task_evaluation_id.evaluation or rec.evaluation
            rec.en_task_type = task_evaluation_id.en_task_type or rec.en_task_type