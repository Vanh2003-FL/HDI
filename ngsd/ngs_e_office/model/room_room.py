# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from uuid import uuid4

from odoo import api, fields, models, _
from odoo.tools.translate import html_translate
from dateutil.relativedelta import relativedelta


class Room(models.Model):
    _name = "room.room"
    _inherit = ["mail.thread"]
    _description = "Room"
    _order = "name, id"

    # Configuration
    name = fields.Char(string="Tên phòng họp", required=True, tracking=2)
    description = fields.Html(string="Dịch vụ")
    office_id = fields.Many2one("room.office", string="Văn phòng", required=True, tracking=3)
    company_id = fields.Many2one(related="office_id.company_id", string="Công ty", store=True)
    room_booking_ids = fields.One2many("calendar.event", "room_id", string="Bookings")
    short_code = fields.Char("Mã phòng họp", copy=False, required=True, tracking=1)
    # Technical/Statistics
    # access_token = fields.Char("Access Token", default=lambda self: str(uuid4()), copy=False, readonly=True, required=True)
    bookings_count = fields.Integer("Bookings Count", compute="_compute_bookings_count")
    is_available = fields.Boolean(string="Is Room Currently Available", compute="_compute_is_available")
    next_booking_start = fields.Datetime("Next Booking Start", compute="_compute_next_booking_start")
    next_booking_start_view = fields.Text("Next Booking Start View", compute="_compute_next_booking_start")
    room_booking_url = fields.Char("Room Booking URL", compute="_compute_room_booking_url")
    # Frontend design fields
    # bookable_background_color = fields.Char("Available Background Color", default="#83c5be")
    # booked_background_color = fields.Char("Booked Background Color", default="#dd2d4a")
    room_background_image = fields.Image("Background Image")

    acreage = fields.Float('Diện tích (m2)')
    persion_capacity = fields.Integer('Sức chứa (người)')
    price = fields.Float('Đơn giá (VNĐ/giờ)')
    active = fields.Boolean('Hoạt động', default=True)

    _sql_constraints = [
        # ("uniq_access_token", "unique(access_token)", "The access token must be unique"),
        ("uniq_short_code", "unique(short_code)", "The short code must be unique."),
    ]

    @api.depends("room_booking_ids")
    def _compute_bookings_count(self):
        bookings_count_by_room = dict([(x.get('room_id')[0], x.get('room_id_count')) for x in self.env["calendar.event"].read_group(
            [("stop", ">=", fields.Datetime.now()), ("room_id", "in", self.ids)],
            ["room_id"],
            ["room_id"]
        )])
        for room in self:
            room.bookings_count = bookings_count_by_room.get(room, 0)

    # @api.depends("office_id")
    # def _compute_display_name(self):
    #     super()._compute_display_name()
    #     for room in self:
    #         room.display_name = f"{room.office_id.name} - {room.name}"

    @api.depends("room_booking_ids")
    def _compute_is_available(self):
        now = fields.Datetime.now()
        booked_rooms = self.env["calendar.event"].search([("start", "<=", now), ("stop", ">=", now), ("room_id", "in", self.ids)]).room_id.ids
        for room in self:
            room.is_available = room.id not in booked_rooms

    @api.depends("is_available", "room_booking_ids")
    def _compute_next_booking_start(self):
        now = fields.Datetime.now()
        today = fields.Date.Date.context_today(self)
        next_booking_start_by_room = dict([(x.get('room_id')[0], x.get('start')) for x in self.env["calendar.event"].read_group(
            [("start", ">", now), ("room_id", "in", self.filtered('is_available').ids)],
            ["start:min"],
            ["room_id"],
        )])
        for room in self:
            room.next_booking_start = next_booking_start_by_room.get(room.id)
            if not room.next_booking_start:
                next_booking_start_view = ''
            else:
                next_booking_start_date = (room.next_booking_start + relativedelta(hours=7)).date()
                if next_booking_start_date == today:
                    next_booking_start_view = room.next_booking_start.strftime('%I:%M %p')
                else:
                    next_booking_start_view = next_booking_start_date.strftime('%d/%m/%Y')
            room.next_booking_start_view = next_booking_start_view

    @api.depends("short_code")
    def _compute_room_booking_url(self):
        for room in self:
            room.room_booking_url = f"{room.get_base_url()}/room/{room.short_code}/book"

    # ------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------

    def action_open_booking_view(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_url",
            "url": self.room_booking_url,
            "target": "new",
        }

    def action_view_bookings(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": "calendar.event",
            "name": _("Bookings"),
            "domain": [("room_id", "in", self.ids)],
            "context": {"default_room_id": self.id if len(self) == 1 else False},
            "view_mode": "calendar,gantt,kanban,tree,form",
        }
