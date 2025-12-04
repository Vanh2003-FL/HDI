# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockPickingBarcodeScanner(models.TransientModel):
    """
    Wizard for barcode scanning during receiving/shipping
    Provides step-by-step UI for warehouse operators
    """
    _name = 'stock.picking.barcode.scanner'
    _description = 'Picking Barcode Scanner'
    
    # ===== REFERENCE =====
    picking_id = fields.Many2one(
        'stock.picking',
        string='Picking',
        required=True,
        ondelete='cascade',
    )
    
    batch_id = fields.Many2one(
        'hdi.batch',
        string='Current Batch',
        help="Batch being scanned"
    )
    
    # ===== SCAN MODE =====
    scan_detail_level = fields.Selection(
        related='picking_id.scan_detail_level',
        string='Chi tiết quét',
        readonly=True,
    )
    
    # ===== SCAN STATE =====
    state = fields.Selection([
        ('scan_batch', 'Quét QR Batch'),
        ('scan_products', 'Quét Sản phẩm'),
        ('confirm', 'Xác nhận'),
    ], string='Trạng thái', default='scan_batch', required=True)
    
    # ===== SCANNED DATA =====
    scanned_batch_barcode = fields.Char(
        string='Mã QR Batch đã quét',
        readonly=True,
    )
    
    scanned_product_ids = fields.One2many(
        'stock.picking.scanned.product',
        'scanner_id',
        string='Sản phẩm đã quét',
    )
    
    total_scanned_qty = fields.Float(
        compute='_compute_scanned_qty',
        string='Tổng số lượng đã quét',
    )
    
    expected_qty = fields.Float(
        related='batch_id.planned_quantity',
        string='Số lượng dự kiến',
    )
    
    # ===== CURRENT SCAN =====
    current_barcode = fields.Char(
        string='Quét barcode',
        help="Nhập hoặc quét barcode tại đây"
    )
    
    # ===== MESSAGES =====
    message = fields.Html(
        string='Thông báo',
        compute='_compute_message',
    )
    
    scan_complete = fields.Boolean(
        compute='_compute_scan_complete',
        string='Đã quét đủ',
    )
    
    @api.depends('scanned_product_ids', 'scanned_product_ids.quantity')
    def _compute_scanned_qty(self):
        """Calculate total scanned quantity"""
        for scanner in self:
            scanner.total_scanned_qty = sum(scanner.scanned_product_ids.mapped('quantity'))
    
    @api.depends('state', 'batch_id', 'scan_detail_level', 'total_scanned_qty', 'expected_qty')
    def _compute_message(self):
        """Display helpful messages based on current state"""
        for scanner in self:
            if scanner.state == 'scan_batch':
                scanner.message = """
                <div class="alert alert-info">
                    <h4>🎯 Bước 1: Quét QR Batch</h4>
                    <p>Quét mã QR trên kẹp hàng để bắt đầu</p>
                </div>
                """
            
            elif scanner.state == 'scan_products':
                if scanner.scan_detail_level == 'batch_only':
                    scanner.message = f"""
                    <div class="alert alert-success">
                        <h4>✅ Đã quét Batch: {scanner.scanned_batch_barcode}</h4>
                        <p><strong>Chế độ: Quét Batch only</strong></p>
                        <p>Không cần quét từng sản phẩm. Click "Hoàn thành" để tiếp tục.</p>
                    </div>
                    """
                else:
                    remaining = scanner.expected_qty - scanner.total_scanned_qty
                    progress = (scanner.total_scanned_qty / scanner.expected_qty * 100) if scanner.expected_qty else 0
                    
                    scanner.message = f"""
                    <div class="alert alert-warning">
                        <h4>📦 Bước 2: Quét Sản phẩm</h4>
                        <p><strong>Batch:</strong> {scanner.scanned_batch_barcode}</p>
                        <p><strong>Đã quét:</strong> {scanner.total_scanned_qty:.0f} / {scanner.expected_qty:.0f}</p>
                        <div class="progress">
                            <div class="progress-bar" style="width: {progress}%">{progress:.0f}%</div>
                        </div>
                        <p class="mt-2"><strong>Còn lại:</strong> {remaining:.0f} sản phẩm</p>
                    </div>
                    """
            
            elif scanner.state == 'confirm':
                scanner.message = """
                <div class="alert alert-success">
                    <h4>✅ Hoàn thành quét</h4>
                    <p>Tất cả sản phẩm đã được quét xong. Click "Xác nhận" để hoàn tất.</p>
                </div>
                """
    
    @api.depends('scan_detail_level', 'state', 'total_scanned_qty', 'expected_qty')
    def _compute_scan_complete(self):
        """Check if scanning is complete"""
        for scanner in self:
            if scanner.scan_detail_level == 'batch_only':
                scanner.scan_complete = scanner.state == 'scan_products'
            else:
                scanner.scan_complete = (
                    scanner.state == 'scan_products' and 
                    scanner.total_scanned_qty >= scanner.expected_qty
                )
    
    @api.onchange('current_barcode')
    def _onchange_current_barcode(self):
        """Process barcode when scanned/entered"""
        if not self.current_barcode:
            return
        
        barcode = self.current_barcode.strip()
        self.current_barcode = False  # Clear for next scan
        
        if self.state == 'scan_batch':
            self._process_batch_barcode(barcode)
        elif self.state == 'scan_products':
            self._process_product_barcode(barcode)
    
    def _process_batch_barcode(self, barcode):
        """Process scanned Batch QR code"""
        # Find batch by barcode
        batch = self.env['hdi.batch'].search([
            ('barcode', '=', barcode),
            ('picking_id', '=', self.picking_id.id),
        ], limit=1)
        
        if not batch:
            raise UserError(_('Không tìm thấy Batch với mã QR: %s') % barcode)
        
        # Update scanner state
        self.batch_id = batch
        self.scanned_batch_barcode = barcode
        
        # Move to next step
        if self.scan_detail_level == 'batch_only':
            self.state = 'confirm'
        else:
            self.state = 'scan_products'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Đã quét Batch'),
                'message': _('Batch %s - %s') % (batch.name, batch.product_id.name if batch.product_id else 'Mixed'),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def _process_product_barcode(self, barcode):
        """Process scanned product barcode"""
        if self.scan_detail_level == 'batch_only':
            raise UserError(_('Chế độ hiện tại không yêu cầu quét sản phẩm'))
        
        # Find product by barcode
        product = self.env['product.product'].search([
            ('barcode', '=', barcode)
        ], limit=1)
        
        if not product:
            raise UserError(_('Không tìm thấy sản phẩm với barcode: %s') % barcode)
        
        # Check if product matches batch
        if self.batch_id.product_id and product != self.batch_id.product_id:
            raise UserError(_(
                'Sản phẩm không khớp!\n'
                'Batch: %s\n'
                'Đã quét: %s'
            ) % (self.batch_id.product_id.name, product.name))
        
        # Add to scanned products
        existing = self.scanned_product_ids.filtered(lambda l: l.product_id == product)
        if existing:
            existing.quantity += 1
        else:
            self.env['stock.picking.scanned.product'].create({
                'scanner_id': self.id,
                'product_id': product.id,
                'barcode': barcode,
                'quantity': 1,
            })
        
        # Check if complete
        if self.total_scanned_qty >= self.expected_qty:
            self.state = 'confirm'
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('✅ Đã quét'),
                'message': _('%s - Tổng: %d') % (product.name, self.total_scanned_qty),
                'type': 'success',
                'sticky': False,
            }
        }
    
    def action_complete(self):
        """Complete scanning and update batch"""
        self.ensure_one()
        
        if not self.scan_complete:
            raise UserError(_('Chưa quét đủ số lượng!'))
        
        # Update batch with scanned data
        if self.scan_detail_level != 'batch_only':
            # Create quants or update batch quantity from scanned products
            # This will be implemented in Phase 2 with proper quant creation
            pass
        
        # Close wizard
        return {'type': 'ir.actions.act_window_close'}


class StockPickingScannedProduct(models.TransientModel):
    """Temporary storage for scanned products"""
    _name = 'stock.picking.scanned.product'
    _description = 'Scanned Product Line'
    
    scanner_id = fields.Many2one(
        'stock.picking.barcode.scanner',
        string='Scanner',
        required=True,
        ondelete='cascade',
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True,
    )
    
    barcode = fields.Char(string='Barcode')
    
    quantity = fields.Float(
        string='Số lượng',
        default=1.0,
    )
    
    lot_id = fields.Many2one(
        'stock.lot',
        string='Lot/Serial',
    )
