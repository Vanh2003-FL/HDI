# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class HdiPickTask(models.Model):
    _name = 'hdi.pick.task'
    _description = 'Pick Task / Work Order for Warehouse Picking'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, priority desc, create_date'

    # ===== BASIC INFO =====
    name = fields.Char(
        string='Task Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New'),
        tracking=True,
    )

    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking Order',
        required=True,
        index=True,
        ondelete='cascade',
        tracking=True,
    )

    picking_type_id = fields.Many2one(
        related='picking_id.picking_type_id',
        string='Operation Type',
        store=True,
        readonly=True,
    )

    state = fields.Selection([
        ('todo', 'Chờ lấy hàng'),
        ('in_progress', 'Đang lấy hàng'),
        ('done', 'Đã hoàn thành'),
        ('cancel', 'Đã hủy'),
    ], string='Trạng thái', default='todo', required=True, tracking=True)

    # ===== ASSIGNMENT =====
    assigned_user_id = fields.Many2one(
        'res.users',
        string='Nhân viên được gán',
        tracking=True,
        help="Nhân viên kho thực hiện lấy hàng"
    )

    sequence = fields.Integer(
        string='Thứ tự',
        default=10,
        help="Thứ tự ưu tiên lấy hàng (số nhỏ = làm trước)"
    )

    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent'),
    ], string='Độ ưu tiên', default='0')

    # ===== LOCATION & ROUTING =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí lấy hàng',
        required=True,
        tracking=True,
    )

    location_display = fields.Char(
        related='location_id.complete_name',
        string='Vị trí đầy đủ',
        readonly=True,
    )

    coordinate_display = fields.Char(
        related='location_id.coordinate_display',
        string='Tọa độ',
        readonly=True,
    )

    zone = fields.Char(
        string='Khu vực',
        compute='_compute_zone',
        store=True,
        help="Tự động từ location"
    )

    # ===== PRODUCT & QUANTITY =====
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch cần lấy',
        ondelete='set null',
        help="Batch cụ thể cần lấy hàng từ vị trí này"
    )

    planned_qty = fields.Float(
        string='Số lượng cần lấy',
        required=True,
        digits='Product Unit of Measure',
        default=0.0,
    )

    picked_qty = fields.Float(
        string='Số lượng đã lấy',
        digits='Product Unit of Measure',
        tracking=True,
        default=0.0,
    )

    remaining_qty = fields.Float(
        string='Còn lại',
        compute='_compute_remaining_qty',
        store=True,
    )

    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Đơn vị',
        related='product_id.uom_id',
        readonly=True,
    )

    # ===== TIMESTAMPS =====
    start_time = fields.Datetime(
        string='Bắt đầu lấy',
        tracking=True,
    )

    end_time = fields.Datetime(
        string='Hoàn thành',
        tracking=True,
    )

    duration = fields.Float(
        string='Thời gian (phút)',
        compute='_compute_duration',
        store=True,
    )

    # ===== NOTES & ISSUES =====
    notes = fields.Text(string='Ghi chú')

    issue_type = fields.Selection([
        ('not_found', 'Không tìm thấy hàng'),
        ('damaged', 'Hàng bị hư hỏng'),
        ('short_pick', 'Thiếu hàng'),
        ('other', 'Khác'),
    ], string='Vấn đề')

    issue_notes = fields.Text(string='Chi tiết vấn đề')

    # ===== SCAN TRACKING =====
    scanned_barcodes = fields.Text(
        string='Barcode đã quét',
        help="Lưu lại các barcode đã quét để audit"
    )

    scan_count = fields.Integer(
        string='Số lần quét',
        default=0,
    )

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('hdi.pick.task') or _('New')
        return super().create(vals)

    @api.depends('location_id', 'location_id.location_id')
    def _compute_zone(self):
        """Extract zone from location hierarchy"""
        for task in self:
            if task.location_id:
                # Use parent location name as zone
                task.zone = task.location_id.location_id.name if task.location_id.location_id else 'Main'
            else:
                task.zone = ''

    @api.depends('planned_qty', 'picked_qty')
    def _compute_remaining_qty(self):
        for task in self:
            task.remaining_qty = task.planned_qty - task.picked_qty

    @api.depends('start_time', 'end_time')
    def _compute_duration(self):
        for task in self:
            if task.start_time and task.end_time:
                delta = task.end_time - task.start_time
                task.duration = delta.total_seconds() / 60.0
            else:
                task.duration = 0.0

    def action_start_picking(self):
        """Nhân viên bắt đầu lấy hàng"""
        self.ensure_one()
        if self.state != 'todo':
            raise UserError(_('Chỉ có thể bắt đầu task ở trạng thái "Chờ lấy hàng".'))

        self.write({
            'state': 'in_progress',
            'start_time': fields.Datetime.now(),
            'assigned_user_id': self.assigned_user_id.id or self.env.user.id,
        })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Đã bắt đầu'),
                'message': _('Task %s đang được thực hiện') % self.name,
                'type': 'success',
                'sticky': False,
            }
        }

    def action_confirm_picked(self):
        """Xác nhận đã lấy hàng"""
        self.ensure_one()
        if self.state != 'in_progress':
            raise UserError(_('Task phải ở trạng thái "Đang lấy hàng" để xác nhận.'))

        if self.picked_qty <= 0:
            raise UserError(_('Vui lòng nhập số lượng đã lấy.'))

        self.write({
            'state': 'done',
            'end_time': fields.Datetime.now(),
        })

        # Update picking move lines
        self._update_picking_move_lines()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Hoàn thành'),
                'message': _('Đã lấy %s %s') % (self.picked_qty, self.product_uom_id.name),
                'type': 'success',
                'sticky': False,
            }
        }

    def action_report_issue(self):
        """Báo cáo vấn đề khi lấy hàng"""
        self.ensure_one()
        return {
            'name': _('Báo cáo vấn đề'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.pick.task',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {'form_view_initial_mode': 'edit'},
        }

    def _update_picking_move_lines(self):
        """Update stock move lines with picked quantity"""
        self.ensure_one()
        
        # Find relevant move line
        move_line = self.picking_id.move_line_ids.filtered(
            lambda ml: ml.product_id == self.product_id and 
                      ml.location_id == self.location_id and
                      (not self.batch_id or ml.batch_id == self.batch_id)
        )

        if not move_line:
            # Create new move line if not exists
            move = self.picking_id.move_ids.filtered(lambda m: m.product_id == self.product_id)
            if move:
                move_line = self.env['stock.move.line'].create({
                    'move_id': move[0].id,
                    'picking_id': self.picking_id.id,
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_uom_id.id,
                    'location_id': self.location_id.id,
                    'location_dest_id': self.picking_id.location_dest_id.id,
                    'batch_id': self.batch_id.id if self.batch_id else False,
                    'qty_done': self.picked_qty,
                })
        else:
            # Update existing move line
            move_line[0].qty_done += self.picked_qty

    def on_barcode_scanned(self, barcode):
        """Handle barcode scanning during picking"""
        self.ensure_one()
        
        # Log scan
        scanned = self.scanned_barcodes or ''
        self.scanned_barcodes = scanned + '\n' + barcode if scanned else barcode
        self.scan_count += 1

        # Verify batch barcode
        if self.batch_id and self.batch_id.barcode == barcode:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Batch khớp'),
                    'message': _('Batch %s đã xác nhận') % self.batch_id.name,
                    'type': 'success',
                }
            }

        # Verify product barcode
        if self.product_id.barcode == barcode:
            # Auto increment picked qty
            self.picked_qty += 1
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Sản phẩm khớp'),
                    'message': _('Đã quét: %s/%s') % (self.picked_qty, self.planned_qty),
                    'type': 'success',
                }
            }

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Không khớp'),
                'message': _('Barcode %s không khớp với task này') % barcode,
                'type': 'warning',
            }
        }

    @api.constrains('picked_qty', 'planned_qty')
    def _check_picked_qty(self):
        """Cảnh báo nếu lấy nhiều hơn kế hoạch"""
        for task in self:
            if task.picked_qty > task.planned_qty * 1.1:  # Allow 10% over-pick
                raise ValidationError(_(
                    'Số lượng đã lấy (%s) vượt quá 110%% kế hoạch (%s). '
                    'Vui lòng kiểm tra lại.'
                ) % (task.picked_qty, task.planned_qty))
