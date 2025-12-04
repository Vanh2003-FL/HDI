# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class HdiPickSuggestion(models.Model):
    _name = 'hdi.pick.suggestion'
    _description = 'Pick Location Suggestion (FIFO/FEFO)'
    _order = 'sequence, priority desc'

    # ===== REFERENCE =====
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking Order',
        required=True,
        ondelete='cascade',
    )

    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )

    quantity_needed = fields.Float(
        string='Số lượng cần',
        required=True,
        digits='Product Unit of Measure',
    )

    # ===== SUGGESTED SOURCE =====
    location_id = fields.Many2one(
        'stock.location',
        string='Vị trí lấy hàng',
        required=True,
    )

    batch_id = fields.Many2one(
        'hdi.batch',
        string='Batch đề xuất',
        help="Batch cụ thể nên lấy từ vị trí này"
    )

    quantity_to_pick = fields.Float(
        string='Số lượng lấy',
        required=True,
        digits='Product Unit of Measure',
        help="Số lượng đề xuất lấy từ vị trí/batch này"
    )

    available_qty = fields.Float(
        string='Tồn kho khả dụng',
        help="Số lượng có sẵn tại vị trí này"
    )

    # ===== PRIORITY & SCORING =====
    sequence = fields.Integer(
        string='Thứ tự',
        default=10,
        help="Thứ tự lấy hàng (1 = lấy trước)"
    )

    priority = fields.Integer(
        string='Điểm ưu tiên',
        help="Điểm tính toán dựa trên FIFO/FEFO"
    )

    # ===== FIFO/FEFO DATA =====
    inbound_date = fields.Datetime(
        string='Ngày nhập kho',
        help="Ngày batch/quant được nhập kho"
    )

    expiration_date = fields.Date(
        string='Hạn sử dụng',
        help="Hạn sử dụng của lot/batch (cho FEFO)"
    )

    lot_id = fields.Many2one(
        'stock.production.lot',
        string='Lot/Serial',
    )

    # ===== LOCATION INFO =====
    coordinate_display = fields.Char(
        related='location_id.coordinate_display',
        string='Tọa độ',
    )

    location_priority = fields.Integer(
        related='location_id.location_priority',
        string='Độ ưu tiên vị trí',
    )

    # ===== REASONS =====
    pick_reason = fields.Text(
        string='Lý do chọn',
        help="Giải thích tại sao chọn vị trí/batch này"
    )

    # ===== STATUS =====
    state = fields.Selection([
        ('suggested', 'Được đề xuất'),
        ('assigned', 'Đã gán task'),
        ('picked', 'Đã lấy'),
        ('cancelled', 'Đã hủy'),
    ], string='Trạng thái', default='suggested')

    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.model
    def generate_pick_suggestions(self, picking, strategy='fifo'):
        """
        Generate pick suggestions for a picking order using FIFO/FEFO strategy
        
        Args:
            picking: stock.picking record
            strategy: 'fifo' (First In First Out) or 'fefo' (First Expire First Out)
        
        Returns:
            recordset of hdi.pick.suggestion
        """
        if picking.picking_type_id.code != 'outgoing':
            raise UserError(_('Pick suggestions chỉ áp dụng cho phiếu xuất kho.'))

        suggestions = []
        sequence = 1

        # Process each move in picking
        for move in picking.move_ids.filtered(lambda m: m.state not in ['cancel', 'done']):
            product = move.product_id
            qty_needed = move.product_uom_qty
            qty_remaining = qty_needed

            # Find available quants for this product
            quants = self._find_available_quants(
                product=product,
                location=picking.location_id,
                strategy=strategy,
            )

            if not quants:
                # No stock available
                suggestions.append({
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity_needed': qty_needed,
                    'location_id': picking.location_id.id,
                    'quantity_to_pick': 0,
                    'available_qty': 0,
                    'sequence': sequence,
                    'priority': 0,
                    'pick_reason': 'Không có tồn kho',
                    'state': 'cancelled',
                })
                sequence += 1
                continue

            # Allocate quantity from quants following FIFO/FEFO
            for quant in quants:
                if qty_remaining <= 0:
                    break

                # Calculate quantity to pick from this quant
                available = quant.quantity - quant.reserved_quantity
                if available <= 0:
                    continue

                qty_to_pick = min(available, qty_remaining)

                # Build reason text
                reasons = []
                if strategy == 'fifo':
                    reasons.append(f'FIFO: Nhập {quant.in_date.strftime("%d/%m/%Y") if quant.in_date else "N/A"}')
                elif strategy == 'fefo' and quant.lot_id and quant.lot_id.expiration_date:
                    reasons.append(f'FEFO: HSD {quant.lot_id.expiration_date.strftime("%d/%m/%Y")}')
                
                if quant.location_id.location_priority:
                    reasons.append(f'Vị trí ưu tiên {quant.location_id.location_priority}')
                
                if quant.batch_id:
                    reasons.append(f'Batch {quant.batch_id.name}')

                suggestions.append({
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity_needed': qty_needed,
                    'location_id': quant.location_id.id,
                    'batch_id': quant.batch_id.id if quant.batch_id else False,
                    'lot_id': quant.lot_id.id if quant.lot_id else False,
                    'quantity_to_pick': qty_to_pick,
                    'available_qty': available,
                    'sequence': sequence,
                    'priority': self._calculate_priority(quant, strategy),
                    'inbound_date': quant.in_date,
                    'expiration_date': quant.lot_id.expiration_date if quant.lot_id else False,
                    'pick_reason': '\n'.join(reasons),
                    'state': 'suggested',
                })

                qty_remaining -= qty_to_pick
                sequence += 1

            # If still have remaining qty, create a warning suggestion
            if qty_remaining > 0:
                suggestions.append({
                    'picking_id': picking.id,
                    'product_id': product.id,
                    'quantity_needed': qty_needed,
                    'location_id': picking.location_id.id,
                    'quantity_to_pick': -qty_remaining,  # Negative indicates shortage
                    'available_qty': 0,
                    'sequence': sequence,
                    'priority': -999,
                    'pick_reason': f'⚠️ THIẾU HÀNG: Còn thiếu {qty_remaining} {product.uom_id.name}',
                    'state': 'cancelled',
                })
                sequence += 1

        # Create suggestion records
        if suggestions:
            return self.create(suggestions)
        else:
            return self.env['hdi.pick.suggestion']

    def _find_available_quants(self, product, location, strategy='fifo'):
        """
        Find available quants for picking
        
        Returns: stock.quant recordset ordered by strategy
        """
        domain = [
            ('product_id', '=', product.id),
            ('location_id', 'child_of', location.id),
            ('quantity', '>', 0),
        ]

        # Order by strategy
        if strategy == 'fefo':
            # FEFO: Earliest expiration first
            order = 'lot_id.expiration_date ASC NULLS LAST, in_date ASC, location_id.location_priority ASC'
        else:
            # FIFO: First in first out
            order = 'in_date ASC, location_id.location_priority ASC'

        quants = self.env['stock.quant'].search(domain, order=order)
        return quants

    def _calculate_priority(self, quant, strategy):
        """
        Calculate priority score for a quant
        Higher score = pick first
        """
        priority = 100

        # FIFO/FEFO bonus
        if strategy == 'fifo' and quant.in_date:
            # Older = higher priority (using days ago)
            days_ago = (fields.Datetime.now() - quant.in_date).days
            priority += days_ago

        elif strategy == 'fefo' and quant.lot_id and quant.lot_id.expiration_date:
            # Closer to expiration = higher priority
            days_until_expire = (quant.lot_id.expiration_date - fields.Date.today()).days
            priority += max(0, 365 - days_until_expire)

        # Location priority bonus
        if quant.location_id.location_priority:
            priority += (100 - quant.location_id.location_priority)

        # Batch bonus (prefer full batches)
        if quant.batch_id and quant.batch_id.state == 'stored':
            priority += 20

        return priority

    def action_create_pick_task(self):
        """Create pick task from this suggestion"""
        self.ensure_one()
        
        if self.state != 'suggested':
            raise UserError(_('Chỉ có thể tạo task từ gợi ý đang ở trạng thái "Được đề xuất".'))

        if self.quantity_to_pick <= 0:
            raise UserError(_('Không thể tạo task cho gợi ý có số lượng <= 0.'))

        # Create pick task
        task = self.env['hdi.pick.task'].create({
            'picking_id': self.picking_id.id,
            'location_id': self.location_id.id,
            'product_id': self.product_id.id,
            'batch_id': self.batch_id.id if self.batch_id else False,
            'planned_qty': self.quantity_to_pick,
            'sequence': self.sequence,
            'notes': self.pick_reason,
        })

        self.state = 'assigned'

        return {
            'name': _('Pick Task'),
            'type': 'ir.actions.act_window',
            'res_model': 'hdi.pick.task',
            'res_id': task.id,
            'view_mode': 'form',
            'target': 'current',
        }
