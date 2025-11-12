# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, Command
from odoo.exceptions import ValidationError, UserError
from itertools import groupby
import math
from dateutil.relativedelta import relativedelta
from datetime import timedelta
from pytz import timezone, UTC
from datetime import datetime, time

from odoo.addons.calendar.models.calendar_event import Meeting
from odoo.osv.expression import AND
from itertools import repeat


def name_get(self):
    """ Hide private events' name for events which don't belong to the current user
    """
    hidden = self.filtered(lambda evt: evt.is_private_booking)
    shown = self - hidden
    shown_names = super(Meeting, shown).name_get()
    obfuscated_names = [(eid, 'Riêng tư') for eid in hidden.ids]
    return shown_names + obfuscated_names


def _read(self, fields):
    if self.env.is_system():
        super(Meeting, self)._read(fields)
        return

    fields = set(fields)
    private_fields = fields - self._get_public_fields()
    if not private_fields:
        super(Meeting, self)._read(fields)
        return

    private_fields.add('partner_ids')
    super(Meeting, self)._read(fields | {'privacy', 'user_id', 'partner_ids'})
    others_private_events = self.filtered(lambda evt: evt.is_private_booking)
    if not others_private_events:
        return

    for field_name in private_fields:
        field = self._fields[field_name]
        replacement = field.convert_to_cache(
            'Riêng tư' if field_name == 'name' else False,
            others_private_events)
        self.env.cache.update(others_private_events, field, repeat(replacement))


Meeting.name_get = name_get
Meeting._read = _read


class RoomBooking(models.Model):
    _inherit = 'calendar.event'
    _order = "start desc, id"

    is_private_booking = fields.Boolean(compute='_compute_is_private_booking')

    @api.depends_context('uid')
    @api.depends('privacy', 'user_id', 'partner_ids')
    def _compute_is_private_booking(self):
        for rec in self:
            is_private_booking = False
            if rec.privacy == 'private' and not self.env.is_system() and not self.env.user.has_group('ngsd_base.group_hcns') \
                and rec.user_id.id != self.env.uid and self.env.user.partner_id not in rec.partner_ids:
                is_private_booking = True
            rec.is_private_booking = is_private_booking

    @api.model
    def _default_partners(self):
        """ When active_model is res.partner, the current partners should be attendees """
        partners = self.env.user.partner_id
        active_id = self._context.get('active_id')
        if self._context.get('active_model') == 'res.partner' and active_id and active_id not in partners.ids:
            partners |= self.env['res.partner'].browse(active_id)
        return partners

    room_id = fields.Many2one("room.room", string="Phòng họp", group_expand="_read_group_room_id", tracking=4, required=True)
    office_id = fields.Many2one(related="room_id.office_id", string="Văn phòng", store=True)
    price = fields.Float('Giá (VNĐ)', compute='_get_price', store=True)
    department_id = fields.Many2one("hr.department", string="Trung tâm/Ban", related='user_id.employee_id.department_id')
    en_department_id = fields.Many2one(string="Phòng", related='user_id.employee_id.en_department_id')

    rounded_duration = fields.Float(string="Thời lượng làm tròn", compute='_get_rounded_duration', store=True)
    start_date = fields.Date(store=False)
    stop_date = fields.Date(store=False)
    is_online = fields.Boolean("Họp online", default=False)
    videocall_channel_id = fields.Many2one('mail.channel', 'Kênh thảo luận', compute="_compute_videocall_location", store=True)
    videocall_location = fields.Char(compute="_compute_videocall_location", store=True, readonly=False)

    number_participants = fields.Integer('Số người tham gia')
    partner_ids = fields.Many2many(
        'res.partner', 'calendar_event_res_partner_rel',
        string='Attendees', default=_default_partners, domain="[('is_employee', '=', True)]")
    is_locked = fields.Boolean("Đã khóa", compute="_compute_is_locked", store=False)
    privacy = fields.Selection(default='private')

    @api.depends("stop")
    def _compute_is_locked(self):
        for rec in self:
            rec.is_locked = rec._origin and rec.stop and rec.stop <= fields.Datetime.now()

    @api.depends("is_online")
    def _compute_videocall_location(self):
        for record in self:
            channel = record.videocall_channel_id
            url = record.videocall_location
            if not record.is_online and channel:
                url = ""
            elif record.is_online and channel:
                url = self.get_base_url() + f"/chat/{channel.id}/{channel.uuid}"
            elif record.is_online and not channel:
                MAIL_CHANNEL = self.env['mail.channel']
                channel = MAIL_CHANNEL.create([{
                    'channel_type': 'group',
                    'default_display_mode': "video_full_screen",
                    'name': record.name or "Cuộc họp online",
                }])
                channel.channel_change_description(record.recurrence_id.name if record.recurrency else record.display_time)
                url = self.get_base_url() + f"/chat/{channel.id}/{channel.uuid}"

            record.videocall_channel_id = channel
            record.videocall_location = url

    @api.depends("duration")
    def _get_rounded_duration(self):
        for rec in self:
            rec.rounded_duration = math.ceil(rec.duration)

    @api.depends('stop', 'start', 'allday')
    def _compute_duration(self):
        for event in self:
            duration = self._get_duration(event.start, event.stop)
            if event.allday and event.start and event.stop:
                work_hours = self.env.company.resource_calendar_id.get_work_hours_count(event.start, event.stop, compute_leaves=False)
                duration = work_hours
            event.duration = duration

    @api.onchange("room_id")
    def _get_price(self):
        for rec in self:
            rec.price = rec.room_id.price

    @api.constrains("start", "stop")
    def _check_date_boundaries(self):
        for booking in self:
            if booking.room_id and booking.start >= booking.stop:
                raise ValidationError(_(
                    "The start date of %(booking_name)s must be earlier than the end date.",
                    booking_name=booking.name
                ))

    def write(self, vals):
        if not self._context.get('skip_locked'):
            if self and any(rec.is_locked for rec in self):
                raise UserError('Bạn không thể chỉnh sửa lịch họp trong quá khứ. Vui lòng liên hệ quản trị viên để được hỗ trợ')
        return super().write(vals)

    def unlink(self):
        for rec in self:
            if rec.start <= fields.Datetime.now() and not self._context.get('delete'):
                raise UserError('Bạn không thể xóa lịch họp đã và đang bắt đầu. Vui lòng liên hệ quản trị viên để được xử lý')
        return super().unlink()

    def grouped_room_id(self):
        result = {}
        bookings = self.filtered('room_id')
        for k, v in groupby(bookings, lambda s: s.room_id):
            result[k] = self.browse([x.id for x in v])
        return result

    def get_start_day_time(self):
        if not self.start_date:
            return 8
        working_calendar = self.env.company.resource_calendar_id
        hour = working_calendar.plan_hours(0, self.start_date + relativedelta(hour=0, minute=0, second=0), compute_leaves=True)
        return 8

    def get_end_day_time(self):
        return 18

    @api.onchange('start_date', 'stop_date', 'allday')
    def _onchange_date(self):
        """ This onchange is required for cases where the stop/start is False and we set an allday event.
            The inverse method is not called in this case because start_date/stop_date are not used in any
            compute/related, so we need an onchange to set the start/stop values in the form view
        """
        for event in self:
            if event.stop_date and event.start_date:
                start_day_time = event.get_start_day_time()
                end_day_time = event.get_end_day_time()
                event.with_context(is_calendar_event_new=True).update({
                    'start': fields.Datetime.from_string(event.start_date) + relativedelta(hour=start_day_time, hours=-7),
                    'stop': fields.Datetime.from_string(event.stop_date) + relativedelta(hour=end_day_time, hours=-7),
                })

    @api.depends('allday', 'start', 'stop')
    def _compute_dates(self):
        """ Adapt the value of start_date(time)/stop_date(time)
            according to start/stop fields and allday. Also, compute
            the duration for not allday meeting ; otherwise the
            duration is set to zero, since the meeting last all the day.
        """
        for meeting in self:
            if meeting.allday and meeting.start and meeting.stop:
                meeting.start_date = (meeting.start + relativedelta(hours=7)) .date()
                meeting.stop_date = (meeting.stop + relativedelta(hours=7)).date()
            else:
                meeting.start_date = False
                meeting.stop_date = False

    def _inverse_dates(self):
        """ This method is used to set the start and stop values of all day events.
            The calendar view needs date_start and date_stop values to display correctly the allday events across
            several days. As the user edit the {start,stop}_date fields when allday is true,
            this inverse method is needed to update the  start/stop value and have a relevant calendar view.
        """

        for meeting in self:
            if meeting.allday:

                # Convention break:
                # stop and start are NOT in UTC in allday event
                # in this case, they actually represent a date
                # because fullcalendar just drops times for full day events.
                # i.e. Christmas is on 25/12 for everyone
                # even if people don't celebrate it simultaneously
                start_day_time = meeting.get_start_day_time()
                end_day_time = meeting.get_end_day_time()
                enddate = fields.Datetime.from_string(meeting.stop_date)
                enddate = enddate + relativedelta(hour=end_day_time,hours=-7)

                startdate = fields.Datetime.from_string(meeting.start_date)
                startdate = startdate  + relativedelta(hour=start_day_time, hours=-7)

                meeting.write({
                    'start': startdate.replace(tzinfo=None),
                    'stop': enddate.replace(tzinfo=None)
                })

    @api.constrains("start", "stop", "room_id")
    def _check_unique_slot(self):
        min_start = min(self.mapped("start"))
        max_stop = max(self.mapped("stop"))
        bookings_by_room = self.search([("room_id", "in", self.room_id.ids), ("start", "<", max_stop), ("stop", ">", min_start)]).grouped_room_id()
        for booking in self:
            if bookings_by_room.get(booking.room_id) and bookings_by_room[booking.room_id].filtered(
                lambda b: b.id != booking.id and b.start < booking.stop and b.stop > booking.start
            ):
                raise ValidationError(_(
                    "Phòng %(room_name)s đã được đặt trong khoảng thời gian đã chọn.",
                    room_name=booking.room_id.name
                ))

    @api.model
    def _get_public_fields(self):
        return super()._get_public_fields() | {'room_id', 'office_id'}

    @api.model
    def _read_group_room_id(self, rooms, domain, order):
        # Display all the rooms in the gantt view even if they have no booking,
        # and order them by office first, then by usual order (because the
        # office name is shown in the display name)
        if self.env.context.get("room_booking_gantt_show_all_rooms"):
            room_ids = rooms._search([], order="office_id," + order)
            return rooms.browse(room_ids)
        return rooms

    # def button_cancel(self):
    #     self.toggle_active()

    def _sync_activities(self, fields):
        res = super()._sync_activities(fields)
        # update activities
        for event in self:
            if event.activity_ids:
                activity_values = {}
                if 'room_id' in fields:
                    activity_values['room_id'] = event.room_id.id
                if activity_values.keys():
                    event.activity_ids.write(activity_values)
        return res

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        if attributes and not 'readonly' in attributes:
            return res
        for fname in res:
            if res[fname]['readonly']:
                continue
            res[fname].update({
                'readonly_domain': "[('is_locked', '=', True)]"
            })
        return res
