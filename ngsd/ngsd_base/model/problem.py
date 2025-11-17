from odoo import api, fields, models, _


class InfExpand(models.Model):
    _name = 'en.inf.expand'
    _description = 'Hạng mục'

    name = fields.Char(string='Tên', required=True)


class Problem(models.Model):
    _name = 'en.problem'
    _description = 'Các vấn đề'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    overdue_ok = fields.Boolean(string='🪙', compute='_compute_overdue_ok', search='_search_overdue_ok')

    @api.depends('date_end')
    def _compute_overdue_ok(self):
        self.overdue_ok = False

    def _search_overdue_ok(self, operator, value):
        if operator not in ['=', '!='] or not isinstance(value, bool):
            raise UserError('Operation not supported')
        if operator != '=':
            value = not value
        self._cr.execute("""
            SELECT id FROM en_problem
            WHERE 
            deadline IS NOT NULL AND
            ((date_end IS NOT NULL AND deadline < date_end) OR
            (date_end IS NULL AND deadline < NOW()))
        """)
        return [('id', 'in' if value else 'not in', [r[0] for r in self._cr.fetchall()])]

    project_id = fields.Many2one(string='Dự án', readonly=False, comodel_name='project.project', required=True, ondelete='cascade')
    project_stage_id = fields.Many2one(string='Giai đoạn', comodel_name='en.project.stage', domain="[('project_id','=',project_id)]")
    en_creator_id = fields.Many2one(string='Người phản ánh', comodel_name='res.users', default=lambda self: self.env.user, required=True)
    en_create_date = fields.Datetime(string='Ngày phản ánh', default=lambda self: fields.Datetime.now(), required=True)
    name = fields.Char(string='Tên', required=True)
    inf_expand_id = fields.Many2one(string='Hạng mục', comodel_name='en.inf.expand')
    deadline = fields.Datetime(string='Hạn hoàn thành')

    @api.constrains('en_create_date', 'deadline')
    def _constrains_deadline(self):
        if any(rec.en_create_date and rec.deadline and rec.en_create_date > rec.deadline for rec in self):
            raise exceptions.ValidationError('Hạn hoàn thành phải lớn hơn hoặc bằng Ngày phản ánh!')

    priority = fields.Selection(string='Mức độ ưu tiên', selection=[('0', 'Không nghiêm trọng'), ('1', 'Thấp'), ('2', 'Trung bình'), ('3', 'Cao'), ('4', 'Rất nghiêm trọng'), ], default='2')
    problem_level_id = fields.Many2one('en.problem.level', string='Mức độ vấn đề')
    priority_id = fields.Many2one('en.problem.priority', string='Mức độ ưu tiên')


    date_end = fields.Datetime(string='Ngày đóng')

    @api.constrains('en_create_date', 'date_end')
    def _constrains_deadline(self):
        if any(rec.en_create_date and rec.date_end and rec.en_create_date > rec.date_end for rec in self):
            raise exceptions.ValidationError('Bạn phải nhập ”Ngày đóng ≥ Ngày phản ánh"')

    pic_id = fields.Many2one(string='Người chịu trách nhiệm', comodel_name='res.users', default=lambda self: self.env.user)
    tic_id = fields.Many2one(string='Nhóm chịu trách nhiệm', comodel_name='crm.team', default=lambda self: self.env.user.sale_team_id)
    stage_id = fields.Many2one(string='Tình trạng', comodel_name='en.risk.stage', index=True,
                               default=lambda self: self.env['en.risk.stage'].search([], limit=1), readonly=False, store=True,
                               copy=False, group_expand='_read_group_stage_ids')

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        stage_ids = stages._search([], order=order, access_rights_uid=SUPERUSER_ID)
        return stages.browse(stage_ids)

    description = fields.Html(string='Mô tả')
    solution_plan = fields.Text(string='Phương án giải quyết')
    effect = fields.Html(string='Ảnh hưởng')

    def name_get(self):
        return [(rec.id, f'[ISSUE_{rec.id}] {rec.name}') for rec in self]


class ProblemLevel(models.Model):
    _name = 'en.problem.level'
    _description = 'Mức độ vấn đề'

    name = fields.Char('Mức độ vấn đề', required=1)


class ProblemPriority(models.Model):
    _name = 'en.problem.priority'
    _description = 'Mức độ ưu tiên'

    name = fields.Char('Mức độ ưu tiên', required=1)
