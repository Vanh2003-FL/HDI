# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import math
from dateutil.relativedelta import relativedelta
from random import randint

from odoo import api, Command, fields, models, tools, _
from odoo.addons.iap.tools import iap_tools
from odoo.osv import expression
from odoo.exceptions import AccessError, UserError
from datetime import datetime
from pytz import timezone, utc
from collections import defaultdict
from dateutil import tz

TICKET_PRIORITY = [
    ('0', 'All'),
    ('1', 'Low priority'),
    ('2', 'High priority'),
    ('3', 'Urgent'),
]


def make_aware(dt):
    """ Return ``dt`` with an explicit timezone, together with a function to
        convert a datetime to the same (naive or aware) timezone as ``dt``.
    """
    if dt.tzinfo:
        return dt, lambda val: val.astimezone(dt.tzinfo)
    else:
        return dt.replace(tzinfo=utc), lambda val: val.astimezone(utc).replace(tzinfo=None)


class HelpdeskTag(models.Model):
    _name = 'helpdesk.tag'
    _description = 'Helpdesk Tags'
    _order = 'name'

    def _get_default_color(self):
        return randint(1, 11)

    name = fields.Char(required=True, translate=True)
    color = fields.Integer('Color', default=_get_default_color)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]


class HelpdeskTicketType(models.Model):
    _name = 'helpdesk.ticket.type'
    _description = 'Helpdesk Ticket Type'
    _order = 'sequence'

    name = fields.Char(required=True, translate=True)
    sequence = fields.Integer(default=10)
    manual_deadline = fields.Boolean('Tự điền hạn xử lý', default=False)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Type name already exists !"),
    ]


class HelpdeskSLAStatus(models.Model):
    _name = 'helpdesk.sla.status'
    _description = "Ticket SLA Status"
    _table = 'helpdesk_sla_status'
    _order = 'deadline ASC, sla_stage_id'
    _rec_name = 'sla_id'

    ticket_id = fields.Many2one('helpdesk.ticket', string='Ticket', required=True, ondelete='cascade', index=True)
    sla_id = fields.Many2one('helpdesk.sla', required=True, ondelete='cascade')
    sla_stage_id = fields.Many2one('helpdesk.stage', related='sla_id.stage_id', store=True)  # need to be stored for the search in `_sla_reach`
    deadline = fields.Datetime("Deadline", compute='_compute_deadline', compute_sudo=True, store=True)
    reached_datetime = fields.Datetime("Reached Date", help="Datetime at which the SLA stage was reached for the first time")
    status = fields.Selection([('failed', 'Failed'), ('reached', 'Reached'), ('ongoing', 'Ongoing')], string="Status", compute='_compute_status', compute_sudo=True, search='_search_status')
    color = fields.Integer("Color Index", compute='_compute_color')
    exceeded_days = fields.Float("Excedeed Working Days", compute='_compute_exceeded_days', compute_sudo=True, store=True, help="Working days exceeded for reached SLAs compared with deadline. Positive number means the SLA was eached after the deadline.")

    def _compute_deadline(self):
        for status in self:
            if (status.deadline and status.reached_datetime) or (status.deadline and not status.sla_id.exclude_stage_ids) or (status.status == 'failed'):
                continue
            working_calendar = status.ticket_id.team_id.resource_calendar_id
            if not working_calendar:
                # Normally, having a working_calendar is mandatory
                status.deadline = deadline
                continue

            if status.sla_id.exclude_stage_ids:
                if status.ticket_id.stage_id in status.sla_id.exclude_stage_ids:
                    # We are in the freezed time stage: No deadline
                    status.deadline = False
                    continue

            avg_hour = working_calendar.hours_per_day or 8 #default to 8 working hours/day
            time_days = math.floor(status.sla_id.time / avg_hour)
            if time_days > 0:
                deadline = working_calendar.plan_days(time_days + 1, deadline, compute_leaves=True)
                # We should also depend on ticket creation time, otherwise for 1 day SLA, all tickets
                # created on monday will have their deadline filled with tuesday 8:00
                deadline = deadline.replace(hour=create_dt.hour, minute=create_dt.minute, second=create_dt.second, microsecond=create_dt.microsecond)

            sla_hours = status.sla_id.time % avg_hour

            if status.sla_id.exclude_stage_ids:
                sla_hours += status._get_freezed_hours(working_calendar)

                # Except if ticket creation time is later than the end time of the working day
                deadline_for_working_cal = working_calendar.plan_hours(0, deadline)
                if deadline_for_working_cal and deadline.day < deadline_for_working_cal.day:
                    deadline = deadline.replace(hour=0, minute=0, second=0, microsecond=0)
            # We should execute the function plan_hours in any case because, in a 1 day SLA environment,
            # if I create a ticket knowing that I'm not working the day after at the same time, ticket
            # deadline will be set at time I don't work (ticket creation time might not be in working calendar).
            status.deadline = working_calendar.plan_hours(sla_hours, deadline, compute_leaves=True)

    @api.depends('deadline', 'reached_datetime')
    def _compute_status(self):
        for status in self:
            if status.reached_datetime and status.deadline:  # if reached_datetime, SLA is finished: either failed or succeeded
                status.status = 'reached' if status.reached_datetime < status.deadline else 'failed'
            else:  # if not finished, deadline should be compared to now()
                status.status = 'ongoing' if not status.deadline or status.deadline > fields.Datetime.now() else 'failed'

    @api.model
    def _search_status(self, operator, value):
        """ Supported operators: '=', 'in' and their negative form. """
        # constants
        datetime_now = fields.Datetime.now()
        positive_domain = {
            'failed': ['|', '&', ('reached_datetime', '=', True), ('deadline', '<=', 'reached_datetime'), '&', ('reached_datetime', '=', False), ('deadline', '<=', fields.Datetime.to_string(datetime_now))],
            'reached': ['&', ('reached_datetime', '=', True), ('reached_datetime', '<', 'deadline')],
            'ongoing': ['|', ('deadline', '=', False), '&', ('reached_datetime', '=', False), ('deadline', '>', fields.Datetime.to_string(datetime_now))]
        }
        # in/not in case: we treat value as a list of selection item
        if not isinstance(value, list):
            value = [value]
        # transform domains
        if operator in expression.NEGATIVE_TERM_OPERATORS:
            # "('status', 'not in', [A, B])" tranformed into "('status', '=', C) OR ('status', '=', D)"
            domains_to_keep = [dom for key, dom in positive_domain if key not in value]
            return expression.OR(domains_to_keep)
        else:
            return expression.OR(positive_domain[value_item] for value_item in value)

    @api.depends('status')
    def _compute_color(self):
        for status in self:
            if status.status == 'failed':
                status.color = 1
            elif status.status == 'reached':
                status.color = 10
            else:
                status.color = 0

    @api.depends('deadline', 'reached_datetime')
    def _compute_exceeded_days(self):
        for status in self:
            if status.reached_datetime and status.deadline and status.ticket_id.team_id.resource_calendar_id:
                if status.reached_datetime <= status.deadline:
                    start_dt = status.reached_datetime
                    end_dt = status.deadline
                    factor = -1
                else:
                    start_dt = status.deadline
                    end_dt = status.reached_datetime
                    factor = 1
                duration_data = status.ticket_id.team_id.resource_calendar_id.get_work_duration_data(start_dt, end_dt, compute_leaves=True)
                status.exceeded_days = duration_data['days'] * factor
            else:
                status.exceeded_days = False

    def _get_freezed_hours(self, working_calendar):
        self.ensure_one()
        hours_freezed = 0

        field_stage = self.env['ir.model.fields']._get(self.ticket_id._name, "stage_id")
        freeze_stages = self.sla_id.exclude_stage_ids.ids
        tracking_lines = self.ticket_id.message_ids.tracking_value_ids.filtered(lambda tv: tv.field == field_stage).sorted(key="create_date")

        if not tracking_lines:
            return 0

        old_time = self.ticket_id.create_date
        for tracking_line in tracking_lines:
            if tracking_line.old_value_integer in freeze_stages:
                # We must use get_work_hours_count to compute real waiting hours (as the deadline computation is also based on calendar)
                hours_freezed += working_calendar.get_work_hours_count(old_time, tracking_line.create_date)
            old_time = tracking_line.create_date
        if tracking_lines[-1].new_value_integer in freeze_stages:
            # the last tracking line is not yet created
            hours_freezed += working_calendar.get_work_hours_count(old_time, fields.Datetime.now())
        return hours_freezed


class HelpdeskTicket(models.Model):
    _name = 'helpdesk.ticket'
    _description = 'Helpdesk Ticket'
    _order = 'priority desc, id desc'
    _inherit = ['portal.mixin', 'mail.thread.cc', 'utm.mixin', 'rating.mixin', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        result = super(HelpdeskTicket, self).default_get(fields)
        if result.get('team_id') and fields:
            team = self.env['helpdesk.team'].browse(result['team_id'])
            if 'user_id' in fields and 'user_id' not in result:  # if no user given, deduce it from the team
                result['user_id'] = team._determine_user_to_assign()[team.id].id
            if 'stage_id' in fields and 'stage_id' not in result:  # if no stage given, deduce it from the team
                result['stage_id'] = team._determine_stage()[team.id].id
        return result

    def _default_team_id(self):
        team_id = self.env['helpdesk.team'].search([('member_ids', 'in', self.env.uid)], limit=1).id
        if not team_id:
            team_id = self.env['helpdesk.team'].search([], limit=1).id
        return team_id

    @api.model
    def _read_group_stage_ids(self, stages, domain, order):
        # write the domain
        # - ('id', 'in', stages.ids): add columns that should be present
        # - OR ('team_ids', '=', team_id) if team_id: add team columns
        search_domain = [('id', 'in', stages.ids)]
        if self.env.context.get('default_team_id'):
            search_domain = ['|', ('team_ids', 'in', self.env.context['default_team_id'])] + search_domain

        return stages.search(search_domain, order=order)

    @api.onchange('is_internal')
    def _onchange_is_internal(self):
        if self.is_internal:
            self.partner_id = False

    name = fields.Char(string='Subject', required=True, index=True)
    team_id = fields.Many2one('helpdesk.team', string='Helpdesk Team', default=_default_team_id, index=True)
    use_sla = fields.Boolean(related='team_id.use_sla')
    description = fields.Html(string='Mô tả - không sd')
    active = fields.Boolean(default=True)
    ticket_type_id = fields.Many2one('helpdesk.ticket.type', string="Type", required=True)
    tag_ids = fields.Many2many('helpdesk.tag', string='Tags')
    company_id = fields.Many2one(related='team_id.company_id', string='Company', store=True, readonly=True)
    color = fields.Integer(string='Color Index')
    kanban_state = fields.Selection([
        ('normal', 'Grey'),
        ('done', 'Green'),
        ('blocked', 'Red')], string='Kanban State',
        default='normal', required=True)
    kanban_state_label = fields.Char(compute='_compute_kanban_state_label', string='Column Status', tracking=True)
    legend_blocked = fields.Char(related='stage_id.legend_blocked', string='Kanban Blocked Explanation', readonly=True, related_sudo=False)
    legend_done = fields.Char(related='stage_id.legend_done', string='Kanban Valid Explanation', readonly=True, related_sudo=False)
    legend_normal = fields.Char(related='stage_id.legend_normal', string='Kanban Ongoing Explanation', readonly=True, related_sudo=False)
    domain_user_ids = fields.Many2many('res.users', compute='_compute_domain_user_ids')
    user_id = fields.Many2one(
        'res.users', string='Assigned to', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, tracking=True,
        domain=lambda self: [('groups_id', 'in', self.env.ref('helpdesk.group_helpdesk_user').id)])
    partner_id = fields.Many2one('res.partner', string='Customer')
    partner_ticket_ids = fields.Many2many('helpdesk.ticket', compute='_compute_partner_ticket_count', string="Partner Tickets", compute_sudo=True)
    partner_ticket_count = fields.Integer('Number of other tickets from the same partner', compute='_compute_partner_ticket_count', compute_sudo=True)
    # Used to submit tickets from a contact form
    partner_name = fields.Char(string='Customer Name', compute='_compute_partner_name', store=True, readonly=False)
    partner_email = fields.Char(string='Customer Email', compute='_compute_partner_email', store=True, readonly=False)
    partner_phone = fields.Char(string='Customer Phone', compute='_compute_partner_phone', store=True, readonly=False)
    commercial_partner_id = fields.Many2one(related="partner_id.commercial_partner_id")
    closed_by_partner = fields.Boolean('Closed by Partner', readonly=True, help="If checked, this means the ticket was closed through the customer portal by the customer.")
    # Used in message_get_default_recipients, so if no partner is created, email is sent anyway
    email = fields.Char(related='partner_email', string='Email on Customer', readonly=False)
    priority = fields.Selection(TICKET_PRIORITY, string='Priority', default='0')
    stage_id = fields.Many2one(
        'helpdesk.stage', string='Stage', compute='_compute_user_and_stage_ids', store=True,
        readonly=False, ondelete='restrict', tracking=True, group_expand='_read_group_stage_ids',
        copy=False, index=True, domain="[('team_ids', '=', team_id)]")
    date_last_stage_update = fields.Datetime("Last Stage Update", copy=False, readonly=True)
    # next 4 fields are computed in write (or create)
    assign_date = fields.Datetime("First assignment date")
    assign_hours = fields.Integer("Time to first assignment (hours)", compute='_compute_assign_hours', store=True, help="This duration is based on the working calendar of the team")
    close_date = fields.Datetime("Close date", copy=False)
    close_hours = fields.Integer("Time to close (hours)", compute='_compute_close_hours', store=True, help="This duration is based on the working calendar of the team")
    open_hours = fields.Integer("Open Time (hours)", compute='_compute_open_hours', search='_search_open_hours', help="This duration is not based on the working calendar of the team")
    # SLA relative
    sla_ids = fields.Many2many('helpdesk.sla', 'helpdesk_sla_status', 'ticket_id', 'sla_id', string="SLAs", copy=False)
    sla_status_ids = fields.One2many('helpdesk.sla.status', 'ticket_id', string="SLA Status")
    sla_reached_late = fields.Boolean("Has SLA reached late", compute='_compute_sla_reached_late', compute_sudo=True, store=True)
    sla_deadline = fields.Datetime("SLA Deadline", compute='_compute_sla_deadline', compute_sudo=True, store=True, help="The closest deadline of all SLA applied on this ticket")
    sla_fail = fields.Boolean("Failed SLA Policy", compute='_compute_sla_fail', search='_search_sla_fail')
    sla_success = fields.Boolean("Success SLA Policy", compute='_compute_sla_success', search='_search_sla_success')

    use_credit_notes = fields.Boolean(related='team_id.use_credit_notes', string='Use Credit Notes')
    use_coupons = fields.Boolean(related='team_id.use_coupons', string='Use Coupons')
    use_product_returns = fields.Boolean(related='team_id.use_product_returns', string='Use Returns')
    use_product_repairs = fields.Boolean(related='team_id.use_product_repairs', string='Use Repairs')
    use_rating = fields.Boolean(related='team_id.use_rating', string='Use Customer Ratings')
    project_id = fields.Many2one('project.project', string='Dự án', required=True)
    create_uid_migrate = fields.Many2one('res.users', string='Người yêu cầu - không sd')

    # field date log ticket
    date_log = fields.Datetime(string='Ngày log ticket', default=lambda self: fields.Datetime.now(), required=True)
    is_internal = fields.Boolean(related='project_id.is_internal', store=True)

    @api.onchange('project_id')
    def change_project_id(self):
        if self.project_id.partner_id:
            self.partner_id = self.project_id.partner_id

    # customer portal: include comment and incoming emails in communication history
    website_message_ids = fields.One2many(domain=lambda self: [('model', '=', self._name), ('message_type', 'in', ['email', 'comment'])])

    @api.depends('stage_id', 'kanban_state')
    def _compute_kanban_state_label(self):
        for ticket in self:
            if ticket.kanban_state == 'normal':
                ticket.kanban_state_label = ticket.legend_normal
            elif ticket.kanban_state == 'blocked':
                ticket.kanban_state_label = ticket.legend_blocked
            else:
                ticket.kanban_state_label = ticket.legend_done

    @api.depends('team_id')
    def _compute_domain_user_ids(self):
        helpdesk_user_group_id = self.env.ref('helpdesk.group_helpdesk_user').id
        helpdesk_manager_group_id = self.env.ref('helpdesk.group_helpdesk_manager').id
        users_data = self.env['res.users'].read_group(
            [('groups_id', 'in', [helpdesk_user_group_id, helpdesk_manager_group_id])],
            ['ids:array_agg(id)', 'groups_id'],
            ['groups_id'],
        )
        mapped_data = {data['groups_id'][0]: data['ids'] for data in users_data}
        for ticket in self:
            if ticket.team_id and ticket.team_id.privacy == 'invite' and ticket.team_id.visibility_member_ids:
                manager_ids = mapped_data.get(helpdesk_manager_group_id, [])
                ticket.domain_user_ids = [Command.set(manager_ids + ticket.team_id.visibility_member_ids.ids)]
            else:
                user_ids = mapped_data.get(helpdesk_user_group_id, [])
                ticket.domain_user_ids = [Command.set(user_ids)]

    def _compute_access_url(self):
        super(HelpdeskTicket, self)._compute_access_url()
        for ticket in self:
            ticket.access_url = '/my/ticket/%s' % ticket.id

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_reached_late(self):
        """ Required to do it in SQL since we need to compare 2 columns value """
        mapping = {}
        if self.ids:
            self.env.cr.execute("""
                SELECT ticket_id, COUNT(id) AS reached_late_count
                FROM helpdesk_sla_status
                WHERE ticket_id IN %s AND deadline < reached_datetime
                GROUP BY ticket_id
            """, (tuple(self.ids),))
            mapping = dict(self.env.cr.fetchall())

        for ticket in self:
            ticket.sla_reached_late = mapping.get(ticket.id, 0) > 0

    @api.depends('sla_status_ids.deadline', 'sla_status_ids.reached_datetime')
    def _compute_sla_deadline(self):
        """ Keep the deadline for the last stage (closed one), so a closed ticket can have a status failed.
            Note: a ticket in a closed stage will probably have no deadline
        """
        for ticket in self:
            deadline = False
            status_not_reached = ticket.sla_status_ids.filtered(lambda status: not status.reached_datetime and status.deadline)
            ticket.sla_deadline = min(status_not_reached.mapped('deadline')) if status_not_reached else deadline

    @api.depends('sla_deadline', 'sla_reached_late')
    def _compute_sla_fail(self):
        now = fields.Datetime.now()
        for ticket in self:
            if ticket.sla_deadline:
                ticket.sla_fail = (ticket.sla_deadline < now) or ticket.sla_reached_late
            else:
                ticket.sla_fail = ticket.sla_reached_late

    @api.model
    def _search_sla_fail(self, operator, value):
        datetime_now = fields.Datetime.now()
        if (value and operator in expression.NEGATIVE_TERM_OPERATORS) or (not value and operator not in expression.NEGATIVE_TERM_OPERATORS):  # is not failed
            return ['&', ('sla_reached_late', '=', False), '|', ('sla_deadline', '=', False), ('sla_deadline', '>=', datetime_now)]
        return ['|', ('sla_reached_late', '=', True), ('sla_deadline', '<', datetime_now)]  # is failed

    @api.depends('sla_deadline', 'sla_reached_late')
    def _compute_sla_success(self):
        now = fields.Datetime.now()
        for ticket in self:
            ticket.sla_success = (ticket.sla_deadline and ticket.sla_deadline > now)

    @api.model
    def _search_sla_success(self, operator, value):
        datetime_now = fields.Datetime.now()
        if (value and operator in expression.NEGATIVE_TERM_OPERATORS) or (not value and operator not in expression.NEGATIVE_TERM_OPERATORS):  # is failed
            return [('sla_status_ids.reached_datetime', '>', datetime_now), ('sla_reached_late', '!=', False)]
        return [('sla_status_ids.reached_datetime', '<', datetime_now), ('sla_reached_late', '=', False)]  # is success

    @api.depends('team_id')
    def _compute_user_and_stage_ids(self):
        for ticket in self.filtered(lambda ticket: ticket.team_id):
            if not ticket.user_id:
                ticket.user_id = ticket.team_id._determine_user_to_assign()[ticket.team_id.id]
            if not ticket.stage_id or ticket.stage_id not in ticket.team_id.stage_ids:
                ticket.stage_id = ticket.team_id._determine_stage()[ticket.team_id.id]

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_name = ticket.partner_id.name

    @api.depends('partner_id')
    def _compute_partner_email(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_email = ticket.partner_id.email

    @api.depends('partner_id')
    def _compute_partner_phone(self):
        for ticket in self:
            if ticket.partner_id:
                ticket.partner_phone = ticket.partner_id.phone

    @api.depends('partner_id', 'partner_email', 'partner_phone')
    def _compute_partner_ticket_count(self):

        def _get_email_to_search(email):
            domain = tools.email_domain_extract(email)
            return ("@" + domain) if domain and domain not in iap_tools._MAIL_DOMAIN_BLACKLIST else email

        for ticket in self:
            domain = []
            partner_ticket = ticket
            if ticket.partner_email:
                email_search = _get_email_to_search(ticket.partner_email)
                domain = expression.OR([domain, [('partner_email', 'ilike', email_search)]])
            if ticket.partner_phone:
                domain = expression.OR([domain, [('partner_phone', 'ilike', ticket.partner_phone)]])
            if ticket.partner_id:
                domain = expression.OR([domain, [("partner_id", "child_of", ticket.partner_id.commercial_partner_id.id)]])
            if domain:
                partner_ticket = self.search(domain)
            ticket.partner_ticket_ids = partner_ticket
            ticket.partner_ticket_count = len(partner_ticket) - 1 if partner_ticket else 0

    @api.depends('assign_date')
    def _compute_assign_hours(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.date_log)
            if create_date and ticket.assign_date and ticket.team_id.resource_calendar_id:
                duration_data = ticket.team_id.resource_calendar_id.get_work_duration_data(create_date, fields.Datetime.from_string(ticket.assign_date), compute_leaves=True)
                ticket.assign_hours = duration_data['hours']
            else:
                ticket.assign_hours = False

    @api.depends('date_log', 'close_date')
    def _compute_close_hours(self):
        for ticket in self:
            create_date = fields.Datetime.from_string(ticket.date_log)
            if create_date and ticket.close_date:
                duration_data = ticket.team_id.resource_calendar_id.get_work_duration_data(create_date, fields.Datetime.from_string(ticket.close_date), compute_leaves=True)
                ticket.close_hours = duration_data['hours']
            else:
                ticket.close_hours = False

    @api.depends('close_hours')
    def _compute_open_hours(self):
        for ticket in self:
            if ticket.date_log:  # fix from https://github.com/odoo/enterprise/commit/928fbd1a16e9837190e9c172fa50828fae2a44f7
                if ticket.close_date:
                    time_difference = ticket.close_date - fields.Datetime.from_string(ticket.date_log)
                else:
                    time_difference = fields.Datetime.now() - fields.Datetime.from_string(ticket.date_log)
                ticket.open_hours = (time_difference.seconds) / 3600 + time_difference.days * 24
            else:
                ticket.open_hours = 0

    @api.model
    def _search_open_hours(self, operator, value):
        dt = fields.Datetime.now() - relativedelta.relativedelta(hours=value)

        d1, d2 = False, False
        if operator in ['<', '<=', '>', '>=']:
            d1 = ['&', ('close_date', '=', False), ('date_log', expression.TERM_OPERATORS_NEGATION[operator], dt)]
            d2 = ['&', ('close_date', '!=', False), ('close_hours', operator, value)]
        elif operator in ['=', '!=']:
            subdomain = ['&', ('date_log', '>=', dt.replace(minute=0, second=0, microsecond=0)), ('date_log', '<=', dt.replace(minute=59, second=59, microsecond=99))]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                subdomain = expression.distribute_not(subdomain)
            d1 = expression.AND([[('close_date', '=', False)], subdomain])
            d2 = ['&', ('close_date', '!=', False), ('close_hours', operator, value)]
        return expression.OR([d1, d2])

    # ------------------------------------------------------------
    # ORM overrides
    # ------------------------------------------------------------

    def name_get(self):
        result = []
        for ticket in self:
            result.append((ticket.id, "%s (#%d)" % (ticket.name, ticket._origin.id)))
        return result

    @api.model
    def create_action(self, action_ref, title, search_view_ref):
        action = self.env["ir.actions.actions"]._for_xml_id(action_ref)
        if title:
            action['display_name'] = title
        if search_view_ref:
            action['search_view_id'] = self.env.ref(search_view_ref).read()[0]
        action['views'] = [(False, view) for view in action['view_mode'].split(",")]

        return {'action': action}

    @api.model_create_multi
    def create(self, list_value):
        now = fields.Datetime.now()
        # determine user_id and stage_id if not given. Done in batch.
        teams = self.env['helpdesk.team'].browse([vals['team_id'] for vals in list_value if vals.get('team_id')])
        team_default_map = dict.fromkeys(teams.ids, dict())
        for team in teams:
            team_default_map[team.id] = {
                'stage_id': team._determine_stage()[team.id].id,
                'user_id': team._determine_user_to_assign()[team.id].id
            }

        # Manually create a partner now since 'generate_recipients' doesn't keep the name. This is
        # to avoid intrusive changes in the 'mail' module
        # TDE TODO: to extract and clean in mail thread
        for vals in list_value:
            partner_id = vals.get('partner_id', False)
            partner_name = vals.get('partner_name', False)
            partner_email = vals.get('partner_email', False)
            if partner_name and partner_email and not partner_id:
                parsed_name, parsed_email = self.env['res.partner']._parse_partner_name(partner_email)
                if not parsed_name:
                    parsed_name = partner_name
                try:
                    vals['partner_id'] = self.env['res.partner'].find_or_create(
                        tools.formataddr((partner_name, parsed_email))
                    ).id
                except UnicodeEncodeError:
                    # 'formataddr' doesn't support non-ascii characters in email. Therefore, we fall
                    # back on a simple partner creation.
                    vals['partner_id'] = self.env['res.partner'].create({
                        'name': partner_name,
                        'email': partner_email,
                    }).id
            if not 'en_code' in vals or not vals['en_code']:
                vals['en_code'] = self.env['ir.sequence'].next_by_code('code.helpdesk.ticket')
            # if not vals.get('date_log'):
            #     vals['date_log'] = self.env.cr.now()

        # determine partner email for ticket with partner but no email given
        partners = self.env['res.partner'].browse([vals['partner_id'] for vals in list_value if 'partner_id' in vals and vals.get('partner_id') and 'partner_email' not in vals])
        partner_email_map = {partner.id: partner.email for partner in partners}
        partner_name_map = {partner.id: partner.name for partner in partners}

        for vals in list_value:
            if vals.get('team_id'):
                team_default = team_default_map[vals['team_id']]
                if 'stage_id' not in vals:
                    vals['stage_id'] = team_default['stage_id']
                # Note: this will break the randomly distributed user assignment. Indeed, it will be too difficult to
                # equally assigned user when creating ticket in batch, as it requires to search after the last assigned
                # after every ticket creation, which is not very performant. We decided to not cover this user case.
                if 'user_id' not in vals:
                    vals['user_id'] = team_default['user_id']
                if vals.get('user_id'):  # if a user is finally assigned, force ticket assign_date and reset assign_hours
                    vals['assign_date'] = fields.Datetime.now()
                    vals['assign_hours'] = 0

            # set partner email if in map of not given
            if vals.get('partner_id') in partner_email_map:
                vals['partner_email'] = partner_email_map.get(vals['partner_id'])
            # set partner name if in map of not given
            if vals.get('partner_id') in partner_name_map:
                vals['partner_name'] = partner_name_map.get(vals['partner_id'])

            if vals.get('stage_id'):
                vals['date_last_stage_update'] = now

        # context: no_log, because subtype already handle this
        tickets = super(HelpdeskTicket, self).create(list_value)
        self._ticket_message_auto_subscribe_notify({ticket: ticket.handler_id - self.env.user for ticket in tickets})
        # make customer follower
        for ticket in tickets:
            if ticket.partner_id:
                ticket.message_subscribe(partner_ids=ticket.partner_id.ids)

            ticket._portal_ensure_token()

        # apply SLA
        tickets.sudo()._sla_apply()

        return tickets

    def write(self, vals):
        # we set the assignation date (assign_date) to now for tickets that are being assigned for the first time
        # same thing for the closing date
        time_now = datetime.now()
        customer_resource_calendar_id = False
        priority_working_hours = False
        if vals.get('project_id'):
            customer_resource_calendar_id = self.env['project.project'].browse(vals.get('project_id')).customer_resource_calendar_id
        if vals.get('priority_id'):
            priority_working_hours = self.env['helpdesk.priority'].browse(vals.get('priority_id')).en_progress_working_hours
        assigned_tickets = closed_tickets = self.browse()
        if vals.get('user_id'):
            assigned_tickets = self.filtered(lambda ticket: not ticket.assign_date)

        if vals.get('stage_id'):
            stage = self.env['helpdesk.stage'].browse(vals.get('stage_id'))
            if stage.en_state == 'received' and not self.en_day_rep:
                vals['en_day_rep'] = fields.Datetime.now()
            if stage.en_state == 'compelete':
                vals['en_day_com'] = fields.Datetime.now()
            if stage.en_state == 'close':
                vals['en_date_end'] = fields.Datetime.now()
                self._notify_when_ticket_done()
            if self.env['helpdesk.stage'].browse(vals.get('stage_id')).is_close:
                closed_tickets = self.filtered(lambda ticket: not ticket.close_date)
            else:  # auto reset the 'closed_by_partner' flag
                vals['closed_by_partner'] = False
                vals['close_date'] = False
            if stage.en_state == 'wait':
                vals['date_pending'] = time_now
            # tính thời gian trì hoãn
            if self.stage_id.en_state == 'wait' and stage.en_state != 'wait':
                if (not self.project_id.customer_resource_calendar_id and not customer_resource_calendar_id) or (not self.priority_id.en_progress_working_hours and not priority_working_hours):
                    vals['total_time_pending'] = self.total_time_pending + ((time_now - self.date_pending).total_seconds()/3600) if self.date_pending else self.total_time_pending
                if self.project_id.customer_resource_calendar_id and not customer_resource_calendar_id and (self.priority_id.en_progress_working_hours or priority_working_hours):
                    vals['total_time_pending'] = self.total_time_pending + self.cal_number_hours(self.date_pending, time_now, self.project_id.customer_resource_calendar_id) if self.date_pending else self.total_time_pending
                if customer_resource_calendar_id and (self.priority_id.en_progress_working_hours or priority_working_hours):
                    vals['total_time_pending'] = self.total_time_pending + self.cal_number_hours(self.date_pending, time_now, customer_resource_calendar_id) if self.date_pending else self.total_time_pending

        now = fields.Datetime.now()

        # update last stage date when changing stage
        if 'stage_id' in vals:
            vals['date_last_stage_update'] = now
            if 'kanban_state' not in vals:
                vals['kanban_state'] = 'normal'
        old_user_ids = {t: t.handler_id for t in self}
        res = super(HelpdeskTicket, self - assigned_tickets - closed_tickets).write(vals)
        res &= super(HelpdeskTicket, assigned_tickets - closed_tickets).write(dict(vals, **{
            'assign_date': now,
        }))
        res &= super(HelpdeskTicket, closed_tickets - assigned_tickets).write(dict(vals, **{
            'close_date': now,
        }))
        res &= super(HelpdeskTicket, assigned_tickets & closed_tickets).write(dict(vals, **{
            'assign_date': now,
            'close_date': now,
        }))
        self._ticket_message_auto_subscribe_notify({ticket: ticket.handler_id - old_user_ids[ticket] - self.env.user for ticket in self})
        if vals.get('partner_id'):
            self.message_subscribe([vals['partner_id']])

        # SLA business
        sla_triggers = self._sla_reset_trigger()
        if any(field_name in sla_triggers for field_name in vals.keys()):
            self.sudo()._sla_apply(keep_reached=True)
        if 'stage_id' in vals:
            self.sudo()._sla_reach(vals['stage_id'])

        return res

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        if default is None:
            default = {}
        default['en_code'] = self.env['ir.sequence'].next_by_code('code.helpdesk.ticket')
        default['date_log'] = datetime.now()
        return super(HelpdeskTicket, self).copy(default)

    # ------------------------------------------------------------
    # Actions and Business methods
    # ------------------------------------------------------------

    @api.model
    def _sla_reset_trigger(self):
        """ Get the list of field for which we have to reset the SLAs (regenerate) """
        return ['team_id', 'priority', 'ticket_type_id', 'tag_ids', 'partner_id']

    def _sla_apply(self, keep_reached=False):
        """ Apply SLA to current tickets: erase the current SLAs, then find and link the new SLAs to each ticket.
            Note: transferring ticket to a team "not using SLA" (but with SLAs defined), SLA status of the ticket will be
            erased but nothing will be recreated.
            :returns recordset of new helpdesk.sla.status applied on current tickets
        """
        # get SLA to apply
        sla_per_tickets = self._sla_find()

        # generate values of new sla status
        sla_status_value_list = []
        for tickets, slas in sla_per_tickets.items():
            sla_status_value_list += tickets._sla_generate_status_values(slas, keep_reached=keep_reached)

        sla_status_to_remove = self.mapped('sla_status_ids')
        if keep_reached:  # keep only the reached one to avoid losing reached_date info
            sla_status_to_remove = sla_status_to_remove.filtered(lambda status: not status.reached_datetime)

        # if we are going to recreate many sla.status, then add norecompute to avoid 2 recomputation (unlink + recreate). Here,
        # `norecompute` will not trigger recomputation. It will be done on the create multi (if value list is not empty).
        if sla_status_value_list:
            sla_status_to_remove.with_context(norecompute=True)

        # unlink status and create the new ones in 2 operations (recomputation optimized)
        sla_status_to_remove.unlink()
        return self.env['helpdesk.sla.status'].create(sla_status_value_list)

    def _sla_find_extra_domain(self):
        self.ensure_one()
        return [
            '|', '|', ('partner_ids', 'parent_of', self.partner_id.ids), ('partner_ids', 'child_of', self.partner_id.ids), ('partner_ids', '=', False)
        ]

    def _sla_find(self):
        """ Find the SLA to apply on the current tickets
            :returns a map with the tickets linked to the SLA to apply on them
            :rtype : dict {<helpdesk.ticket>: <helpdesk.sla>}
        """
        tickets_map = {}
        sla_domain_map = {}

        def _generate_key(ticket):
            """ Return a tuple identifying the combinaison of field determining the SLA to apply on the ticket """
            fields_list = self._sla_reset_trigger()
            key = list()
            for field_name in fields_list:
                if ticket._fields[field_name].type == 'many2one':
                    key.append(ticket[field_name].id)
                else:
                    key.append(ticket[field_name])
            return tuple(key)

        for ticket in self:
            if ticket.team_id.use_sla:  # limit to the team using SLA
                key = _generate_key(ticket)
                # group the ticket per key
                tickets_map.setdefault(key, self.env['helpdesk.ticket'])
                tickets_map[key] |= ticket
                # group the SLA to apply, by key
                if key not in sla_domain_map:
                    sla_domain_map[key] = expression.AND([[
                        ('team_id', '=', ticket.team_id.id), ('priority', '<=', ticket.priority),
                        ('stage_id.sequence', '>=', ticket.stage_id.sequence),
                        '|', ('ticket_type_id', '=', ticket.ticket_type_id.id), ('ticket_type_id', '=', False)], ticket._sla_find_extra_domain()])

        result = {}
        for key, tickets in tickets_map.items():  # only one search per ticket group
            domain = sla_domain_map[key]
            slas = self.env['helpdesk.sla'].search(domain)
            result[tickets] = slas.filtered(lambda s: s.tag_ids <= tickets.tag_ids)  # SLA to apply on ticket subset
        return result

    def _sla_generate_status_values(self, slas, keep_reached=False):
        """ Return the list of values for given SLA to be applied on current ticket """
        status_to_keep = dict.fromkeys(self.ids, list())

        # generate the map of status to keep by ticket only if requested
        if keep_reached:
            for ticket in self:
                for status in ticket.sla_status_ids:
                    if status.reached_datetime:
                        status_to_keep[ticket.id].append(status.sla_id.id)

        # create the list of value, and maybe exclude the existing ones
        result = []
        for ticket in self:
            for sla in slas:
                if not (keep_reached and sla.id in status_to_keep[ticket.id]):
                    result.append({
                        'ticket_id': ticket.id,
                        'sla_id': sla.id,
                        'reached_datetime': fields.Datetime.now() if ticket.stage_id == sla.stage_id else False # in case of SLA on first stage
                    })

        return result

    def _sla_reach(self, stage_id):
        """ Flag the SLA status of current ticket for the given stage_id as reached, and even the unreached SLA applied
            on stage having a sequence lower than the given one.
        """
        stage = self.env['helpdesk.stage'].browse(stage_id)
        stages = self.env['helpdesk.stage'].search([('sequence', '<=', stage.sequence), ('team_ids', 'in', self.mapped('team_id').ids)])  # take previous stages
        self.env['helpdesk.sla.status'].search([
            ('ticket_id', 'in', self.ids),
            ('sla_stage_id', 'in', stages.ids),
            ('reached_datetime', '=', False),
        ]).write({'reached_datetime': fields.Datetime.now()})

    def assign_ticket_to_self(self):
        self.ensure_one()
        self.handler_id = self.env.user

    def action_open_helpdesk_ticket(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("helpdesk.helpdesk_ticket_action_main_tree")
        action.update({
            'domain': [('id', '!=', self.id), ('id', 'in', self.partner_ticket_ids.ids)],
            'context': {'create': False},
        })
        return action

    # ------------------------------------------------------------
    # Messaging API
    # ------------------------------------------------------------

    #DVE FIXME: if partner gets created when sending the message it should be set as partner_id of the ticket.
    def _message_get_suggested_recipients(self):
        recipients = super(HelpdeskTicket, self)._message_get_suggested_recipients()
        try:
            for ticket in self:
                if ticket.partner_id and ticket.partner_id.email:
                    ticket._message_add_suggested_recipient(recipients, partner=ticket.partner_id, reason=_('Customer'))
                elif ticket.partner_email:
                    ticket._message_add_suggested_recipient(recipients, email=ticket.partner_email, reason=_('Customer Email'))
        except AccessError:  # no read access rights -> just ignore suggested recipients because this implies modifying followers
            pass
        return recipients

    def _ticket_email_split(self, msg):
        email_list = tools.email_split((msg.get('to') or '') + ',' + (msg.get('cc') or ''))
        # check left-part is not already an alias
        return [
            x for x in email_list
            if x.split('@')[0] not in self.mapped('team_id.alias_name')
        ]

    @api.model
    def message_new(self, msg, custom_values=None):
        values = dict(custom_values or {}, partner_email=msg.get('from'), partner_id=msg.get('author_id'))
        ticket = super(HelpdeskTicket, self.with_context(mail_notify_author=True)).message_new(msg, custom_values=values)
        partner_ids = [x.id for x in self.env['mail.thread']._mail_find_partner_from_emails(self._ticket_email_split(msg), records=ticket) if x]
        customer_ids = [p.id for p in self.env['mail.thread']._mail_find_partner_from_emails(tools.email_split(values['partner_email']), records=ticket) if p]
        partner_ids += customer_ids
        if customer_ids and not values.get('partner_id'):
            ticket.partner_id = customer_ids[0]
        if partner_ids:
            ticket.message_subscribe(partner_ids)
        return ticket

    def message_update(self, msg, update_vals=None):
        partner_ids = [x.id for x in self.env['mail.thread']._mail_find_partner_from_emails(self._ticket_email_split(msg), records=self) if x]
        if partner_ids:
            self.message_subscribe(partner_ids)
        return super(HelpdeskTicket, self).message_update(msg, update_vals=update_vals)

    def _message_post_after_hook(self, message, msg_vals):
        if self.partner_email and self.partner_id and not self.partner_id.email:
            self.partner_id.email = self.partner_email

        if self.partner_email and not self.partner_id:
            # we consider that posting a message with a specified recipient (not a follower, a specific one)
            # on a document without customer means that it was created through the chatter using
            # suggested recipients. This heuristic allows to avoid ugly hacks in JS.
            new_partner = message.partner_ids.filtered(lambda partner: partner.email == self.partner_email)
            if new_partner:
                self.search([
                    ('partner_id', '=', False),
                    ('partner_email', '=', new_partner.email),
                    ('stage_id.fold', '=', False)]).write({'partner_id': new_partner.id})
        return super(HelpdeskTicket, self)._message_post_after_hook(message, msg_vals)

    def _track_template(self, changes):
        res = super(HelpdeskTicket, self)._track_template(changes)
        ticket = self[0]
        if 'stage_id' in changes and ticket.stage_id.template_id:
            res['stage_id'] = (ticket.stage_id.template_id, {
                'auto_delete_message': True,
                'subtype_id': self.env['ir.model.data']._xmlid_to_res_id('mail.mt_note'),
                'email_layout_xmlid': 'mail.mail_notification_light'
            }
        )
        return res

    def _creation_subtype(self):
        return self.env.ref('helpdesk.mt_ticket_new')

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'stage_id' in init_values:
            return self.env.ref('helpdesk.mt_ticket_stage')
        return super(HelpdeskTicket, self)._track_subtype(init_values)

    def _notify_get_groups(self, msg_vals=None):
        """ Handle helpdesk users and managers recipients that can assign
        tickets directly from notification emails. Also give access button
        to portal and portal customers. If they are notified they should
        probably have access to the document. """
        groups = super(HelpdeskTicket, self)._notify_get_groups(msg_vals=msg_vals)

        self.ensure_one()
        for group_name, _group_method, group_data in groups:
            if group_name != 'customer':
                group_data['has_button_access'] = True

        if self.user_id:
            return groups

        local_msg_vals = dict(msg_vals or {})
        take_action = self._notify_get_action_link('assign', **local_msg_vals)
        helpdesk_actions = [{'url': take_action, 'title': _('Assign to me')}]
        helpdesk_user_group_id = self.env.ref('helpdesk.group_helpdesk_user').id
        new_groups = [(
            'group_helpdesk_user',
            lambda pdata: pdata['type'] == 'user' and helpdesk_user_group_id in pdata['groups'],
            {'actions': helpdesk_actions}
        )]
        return new_groups + groups

    def _notify_get_reply_to(self, default=None, records=None, company=None, doc_names=None):
        """ Override to set alias of tickets to their team if any. """
        aliases = self.mapped('team_id').sudo()._notify_get_reply_to(default=default, records=None, company=company, doc_names=None)
        res = {ticket.id: aliases.get(ticket.team_id.id) for ticket in self}
        leftover = self.filtered(lambda rec: not rec.team_id)
        if leftover:
            res.update(super(HelpdeskTicket, leftover)._notify_get_reply_to(default=default, records=None, company=company, doc_names=doc_names))
        return res

    # ------------------------------------------------------------
    # Rating Mixin
    # ------------------------------------------------------------

    def rating_apply(self, rate, token=None, feedback=None, subtype_xmlid=None):
        return super(HelpdeskTicket, self).rating_apply(rate, token=token, feedback=feedback, subtype_xmlid="helpdesk.mt_ticket_rated")

    def _rating_get_parent_field_name(self):
        return 'team_id'

    # ---------------------------------------------------
    # Mail gateway
    # ---------------------------------------------------

    def _mail_get_message_subtypes(self):
        res = super()._mail_get_message_subtypes()
        if len(self) == 1 and self.team_id:
            team = self.team_id
            optional_subtypes = [('use_credit_notes', self.env.ref('helpdesk.mt_ticket_refund_posted')),
                                 ('use_product_returns', self.env.ref('helpdesk.mt_ticket_return_done')),
                                 ('use_product_repairs', self.env.ref('helpdesk.mt_ticket_repair_done'))]
            for field, subtype in optional_subtypes:
                if not team[field] and subtype in res:
                    res -= subtype
        return res

    priority_id = fields.Many2one('helpdesk.priority', string='Mức độ ưu tiên', domain="[('id', 'in', domain_priority_ids), ('en_priority', '!=', '')]", required=True)
    job_name = fields.Char('Tên gói việc - không sd')
    urgency_id = fields.Many2one('helpdesk.urgency', string='Độ phức tạp', required=True)
    infulence_id = fields.Many2one('helpdesk.infulence', string='Mức độ ảnh hưởng', required=True)
    resource_id = fields.Many2one('helpdesk.source', string='Nguồn tiếp nhận', required=True)
    supervisor_id = fields.Many2one('res.users', string='Người chịu trách nhiệm', required=True)
    handler_id = fields.Many2many('res.users', string='Người xử lý', required=True)

    en_dl_rep = fields.Datetime(string='Hạn phản hồi', compute='_get_en_dl_rep', store=True)

    domain_priority_ids = fields.Many2many('helpdesk.priority', compute='_compute_domain_priority')
    user_request_id = fields.Many2one('res.users', 'Người yêu cầu', default=lambda self: self.env.uid)

    @api.depends('project_id', 'priority_id.en_project_apply_ids', 'priority_id.en_rule_default')
    def _compute_domain_priority(self):
        for rec in self:
            if not rec.project_id:
                rec.domain_priority_ids = False
            else:
                all_priority_of_project = self.env['helpdesk.priority'].search([
                    ('en_project_apply_ids', 'in', [rec.project_id.id])
                ])
                if all_priority_of_project:
                    rec.domain_priority_ids = all_priority_of_project
                else:
                    rec.domain_priority_ids = self.env['helpdesk.priority'].search([
                    ('en_rule_default', '=', True)
                ])

    @api.depends('date_log', 'priority_id', 'priority_id.en_time_rep', 'priority_id.en_progress_working_hours', 'project_id.customer_resource_calendar_id')
    def _get_en_dl_rep(self):
        for rec in self:
            en_dl_rep = False
            if rec.date_log and rec.priority_id.en_time_rep and not rec.priority_id.en_progress_working_hours:
                h, m = divmod(rec.priority_id.en_time_rep, 1)
                m = int(m*60)
                en_dl_rep = rec.date_log + relativedelta(hours=h, minutes=m)
            elif rec.date_log and rec.priority_id.en_time_rep and rec.priority_id.en_progress_working_hours and rec.project_id.customer_resource_calendar_id:
                en_dl_rep = self.cal_time_progress(rec.date_log, rec.priority_id.en_time_rep, rec.project_id.customer_resource_calendar_id)
            rec.en_dl_rep = en_dl_rep

    en_day_rep = fields.Datetime(string='Ngày phản hồi thực tế', readonly=1, copy=False)
    manual_deadline = fields.Boolean(related='ticket_type_id.manual_deadline', store=True)
    en_dl = fields.Datetime(string='Hạn xử lý', compute='_get_en_dl', store=True)

    @api.depends('date_log', 'priority_id', 'priority_id.en_time_action', 'priority_id.en_progress_working_hours', 'project_id.customer_resource_calendar_id', 'total_time_pending')
    def _get_en_dl(self):
        for rec in self:
            if rec.manual_deadline:
                rec.en_dl = rec.en_dl
                continue
            en_dl = False
            if rec.date_log and rec.priority_id.en_time_action and (not rec.priority_id.en_progress_working_hours or not rec.project_id.customer_resource_calendar_id):
                h, m = divmod(rec.priority_id.en_time_action + rec.total_time_pending, 1)
                m = int(m*60)
                en_dl = rec.date_log + relativedelta(hours=h, minutes=m)
            elif rec.date_log and rec.priority_id.en_time_action and rec.priority_id.en_progress_working_hours and rec.project_id.customer_resource_calendar_id:
                time_action = rec.priority_id.en_time_action + rec.total_time_pending
                en_dl = self.cal_time_progress(rec.date_log, time_action, rec.project_id.customer_resource_calendar_id)
            rec.en_dl = en_dl

    en_day_com = fields.Datetime(string='Ngày hoàn thành thực tế', readonly=1, copy=False)
    en_date_end = fields.Datetime(string='Ngày đóng', readonly=1, copy=False)
    en_stage_type_id = fields.Many2one('en.project.stage', string='Giai đoạn dự án', required=True)
    en_stage_type_domain = fields.Many2many('en.project.stage', string='Giai đoạn dự án - không sd', compute="_get_en_stage_type_domain")

    @api.depends('project_id')
    def _get_en_stage_type_domain(self):
        for rec in self:
            en_stage_type_domain = self.env['en.project.stage']
            if rec.project_id:
                en_stage_type_domain |= self.env['en.project.stage'].search([('wbs_version.state', '=', 'approved'), ('wbs_version.project_id', '=', rec.project_id.id)])
                if self._context.get('view_internal_project') and rec.sudo().project_id.is_internal:
                    en_stage_type_domain |= self.env['en.project.stage'].sudo().search([('wbs_version.state', '=', 'approved'), ('wbs_version.project_id', '=', rec.project_id.id)])
            rec.en_stage_type_domain = en_stage_type_domain

    workpackage_id = fields.Many2one('en.workpackage', string='Tên gói việc', required=True)
    workpackage_domain = fields.Many2many('en.workpackage', compute='_get_workpackage_domain')

    @api.depends('en_stage_type_id')
    def _get_workpackage_domain(self):
        for rec in self:
            rec.workpackage_domain = rec.en_stage_type_id.order_line

    en_code = fields.Char('Mã ticket')
    en_rs_overdue = fields.Text('Lý do quá hạn')
    en_sla_feedback = fields.Float('%SLA phản hồi')
    en_prercent_sla_process = fields.Float('%SLA xử lý')
    en_feedback = fields.Selection(string="Tình trạng phản hồi", selection=[
        ('on_time', 'Đúng hạn'),
        ('due', 'Đến hạn'),
        ('overdue', 'Trễ hạn'),
        ('undue','Chưa đến hạn'), ],
        required=False, compute='_compute_en_feedback')
    en_sla_process = fields.Selection(string="Tình trạng xử lý", selection=[
        ('on_time', 'Đúng hạn'),
        ('due', 'Đến hạn'),
        ('overdue', 'Trễ hạn'),
        ('undue', 'Chưa đến hạn'), ],
        required=False,
        compute='_compute_en_sla_process')
    en_text_describe = fields.Html('Mô tả (dữ liệu cũ)', required=False)
    en_text_reason = fields.Html('Nguyên nhân (dữ liệu cũ)')
    en_text_solution = fields.Html('Giải pháp (dữ liệu cũ)')
    en_type_request_id = fields.Many2one('en.type.request', 'Loại yêu cầu', required=True)
    en_system_id = fields.Many2one('en.system', 'Hệ thống', required=True)
    en_subsystem_id = fields.Many2one('en.subsystem', 'Phân hệ', required=True)

    text_description = fields.Html('Mô tả', required=True)
    text_reason = fields.Html('Nguyên nhân')
    text_solution = fields.Html('Giải pháp')

    @api.depends('en_dl_rep', 'en_day_rep')
    def _compute_en_feedback(self):
        for rec in self:
            rec.en_feedback = ''
            today = datetime.now().date()
            if not rec.en_dl_rep:
                continue
            rec.en_feedback = 'overdue'
            if not rec.en_day_rep:
                if today < rec.en_dl_rep.date():
                    rec.en_feedback = 'undue'
                elif today == rec.en_dl_rep.date():
                    rec.en_feedback = 'due'
            else:
                if rec.en_day_rep <= rec.en_dl_rep:
                    rec.en_feedback = 'on_time'

    def cal_time_progress(self, date, hours, working_calendar):
        working_calendar = working_calendar
        start_date = date
        deadline = date
        if not working_calendar:
            return date
        avg_hour = working_calendar.hours_per_day or 8  # default to 8 working hours/day
        time_days = math.floor(hours / avg_hour)
        if time_days > 0:
            deadline = working_calendar.plan_days(time_days + 1, deadline, compute_leaves=True)
            create_dt = working_calendar.plan_hours(0, start_date)
            deadline = deadline and deadline.replace(hour=create_dt.hour,
                                                     minute=create_dt.minute,
                                                     second=create_dt.second,
                                                     microsecond=create_dt.microsecond)
        sla_hours = hours % avg_hour
        deadline = working_calendar.plan_hours(sla_hours, deadline, compute_leaves=True)
        return deadline

    date_pending = fields.Datetime('Ngày trì hoãn gần nhất')
    total_time_pending = fields.Float('Tổng thời gian trì hoãn', copy=False)

    def cal_number_hours(self, from_datetime, to_datetime, working_calendar, compute_leaves=True, domain=None):
        working_calendar = working_calendar
        from_datetime, dummy = make_aware(from_datetime)
        to_datetime, dummy = make_aware(to_datetime)
        # actual hours per day
        if compute_leaves:
            intervals = working_calendar._work_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        else:
            intervals = working_calendar._attendance_intervals_batch(from_datetime, to_datetime, domain=domain)[False]
        day_hours = defaultdict(float)
        for start, stop, meta in intervals:
            day_hours[start.date()] += (stop - start).total_seconds() / 3600
        total_hours = sum(day_hours.values())
        return total_hours

    @api.depends('en_dl', 'en_day_com')
    def _compute_en_sla_process(self):
        for rec in self:
            rec.en_sla_process = ''
            today = datetime.now().date()
            if not rec.en_dl:
                continue
            rec.en_sla_process = 'overdue'
            if not rec.en_day_com:
                if today < rec.en_dl.date():
                    rec.en_sla_process = 'undue'
                elif today == rec.en_dl.date():
                    rec.en_sla_process = 'due'
            else:
                if rec.en_day_com <= rec.en_dl:
                    rec.en_sla_process = 'on_time'

    @api.onchange('project_id')
    def _onchange_project_id(self):
        for rec in self:
            rec.priority_id = False

    def _message_auto_subscribe_followers(self, updated_values, default_subtype_ids):
        return []

    @api.model
    def _ticket_message_auto_subscribe_notify(self, users_per_ticket):
        # Utility method to send assignation notification upon writing/creation.
        template_id = self.env['ir.model.data']._xmlid_to_res_id('helpdesk.ticket_message_user_assigned', raise_if_not_found=False)
        if not template_id:
            return
        view = self.env['ir.ui.view'].browse(template_id)
        ticket_model_description = self.env['ir.model']._get(self._name).display_name
        for ticket, users in users_per_ticket.items():
            if not users:
                continue
            values = {
                'object': ticket,
                'model_description': ticket_model_description,
                'access_link': ticket._notify_get_action_link('view'),
            }
            for user in users:
                values.update(assignee_name=user.sudo().name)
                assignation_msg = view._render(values, engine='ir.qweb', minimal_qcontext=True)
                assignation_msg = self.env['mail.render.mixin']._replace_local_links(assignation_msg)
                ticket.message_notify(
                    subject=_('Bạn đã được phân công cho %s', ticket.display_name),
                    body=assignation_msg,
                    partner_ids=user.partner_id.ids,
                    record_name=ticket.display_name,
                    email_layout_xmlid='mail.mail_notification_light',
                    model_description=ticket_model_description,
                )

    @api.model
    def _notify_when_ticket_done(self):
        for ticket in self:
            # Lấy thông tin người tạo ticket
            recipient = ticket.create_uid

            # Chuẩn bị thông tin cho email
            ticket_url = ticket._notify_get_action_link('view')  # Lấy URL để xem ticket

            # Tạo template email (nếu chưa có, bạn cần tạo trước)
            template = self.env.ref('helpdesk.mail_template_ticket_closed')
            if template:
                # Gửi email với context để truyền dữ liệu động
                template.with_context(
                    ticket_url=ticket_url
                ).send_mail(
                    ticket.id,
                    force_send=True,
                    email_values={'recipient_ids': [(4, recipient.partner_id.id)]}
                )


class HelpDeskPriority(models.Model):
    _name = 'helpdesk.priority'
    _description = 'Mức độ ưu tiên'

    name = fields.Char('Tên', required=1)
    en_time_rep = fields.Float('Thời gian phản hồi', required=1)
    en_time_action = fields.Float('Thời gian xử lý', required=1)
    en_priority = fields.Selection(string="Mức độ ưu tiên", selection=[
        ('very_high', 'Rất cao'),
        ('high', 'Cao'),
        ('medium', 'Trung bình'),
        ('short', 'Thấp'), ], required=False, )
    en_project_apply_ids = fields.Many2many(comodel_name="project.project", string="Áp dụng cho dự án", )
    en_rule_default = fields.Boolean('Công thức mặc định', default=False)
    en_progress_working_hours = fields.Boolean('Xử lý trong thời gian làm việc')

    @api.constrains('en_priority', 'en_project_apply_ids')
    def _constrains_project_priority(self):
        for rec in self:
            all_priority = self.env['helpdesk.priority'].search(
                [('id', '!=', rec.id), ('en_priority', '=', rec.en_priority),
                 ('en_project_apply_ids', 'in', rec.en_project_apply_ids.ids)])
            if all_priority:
                raise UserError('Bạn không thể gắn 1 dự án với nhiều option đã có')

    @api.onchange('en_rule_default', 'en_priority')
    def _constrains_rule_priority(self):
        for rec in self:
            if rec.en_rule_default:
                all_rule_priority = self.env['helpdesk.priority'].search(
                    [('id', '!=', rec._origin.id), ('en_rule_default', '=', True),
                     ('en_priority', '=', rec.en_priority)])
                if all_rule_priority:
                    raise UserError('Bạn không thể gắn 1 công thức mặc định với nhiều option đã có')


    @api.constrains('en_time_rep')
    def check_en_time_rep(self):
        for rec in self:
            if rec.en_time_rep <= 0:
                raise UserError('Thời gian phản hồi phải lớn hơn 0')

    @api.constrains('en_time_action')
    def check_en_time_action(self):
        for rec in self:
            if rec.en_time_action <= 0:
                raise UserError('Thời gian xử lý phải lớn hơn 0')


class HelpDeskUrgency(models.Model):
    _name = 'helpdesk.urgency'
    _description = 'Mức độ cấp bách'

    name = fields.Char('Tên', required=1)


class HelpDeskInfulence(models.Model):
    _name = 'helpdesk.infulence'
    _description = 'Mức độ ảnh hưởng'

    name = fields.Char('Tên', required=1)


class HelpDeskSource(models.Model):
    _name = 'helpdesk.source'
    _description = 'Nguồn tiếp nhận'

    name = fields.Char('Tên', required=1)

class EnTypeRequest(models.Model):
    _name = 'en.type.request'
    _description = 'Loại yêu cầu'

    name = fields.Char('Tên loại yêu cầu', required=True)

class EnSubsystem(models.Model):
    _name = 'en.subsystem'
    _description = 'Phân hệ'

    name = fields.Char('Tên phân hệ', required=True)

class EnSystem(models.Model):
    _name = 'en.system'
    _description = 'Hệ thống'

    name = fields.Char('Tên hệ thống', required=True)
