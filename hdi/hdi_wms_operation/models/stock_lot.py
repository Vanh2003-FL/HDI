from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockLot(models.Model):
    """
    Extend stock.lot để quản lý Batch theo tài liệu
    """
    _inherit = 'stock.lot'

    # Batch State Machine: draft → scanned → placed → confirmed
    batch_state = fields.Selection([
        ('draft', 'Khởi tạo'),
        ('scanned', 'Đã quét'),
        ('placed', 'Đã đặt vào vị trí'),
        ('confirmed', 'Đã xác nhận'),
    ], string='Trạng thái batch', default='draft', tracking=True,
       help='Các trạng thái quy trình batch: Khởi tạo → Đã quét → Đã đặt vào vị trí → Đã xác nhận')
    
    # Batch information
    is_batch = fields.Boolean(
        string='Là batch',
        default=True,
        help='Đánh dấu đây là batch (không phải lot thường)'
    )
    batch_qr_code = fields.Char(
        string='Mã QR batch',
        help='Mã QR của batch để quét'
    )
    batch_printed = fields.Boolean(
        string='Đã in nhãn batch',
        default=False,
        help='Đã in nhãn batch'
    )
    print_date = fields.Datetime(
        string='Ngày in nhãn batch',
        help='Ngày in nhãn batch'
    )
    
    # Location placement
    suggested_location_id = fields.Many2one(
        'stock.location',
        string='Suggested Location',
        help='Vị trí được gợi ý bởi hệ thống'
    )
    actual_location_id = fields.Many2one(
        'stock.location',
        string='Actual Location',
        help='Vị trí thực tế đã đặt'
    )
    location_confirmed = fields.Boolean(
        string='Location Confirmed',
        default=False
    )
    
    # Computed quantity
    product_qty = fields.Float(
        string='Quantity',
        compute='_compute_product_qty',
        digits='Product Unit of Measure',
        help='Total quantity of this lot/batch in stock'
    )
    
    # Receipt Type (NK_NV_01 to NK_NV_04)
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Sản xuất nội địa'),
        ('production_export', 'NK_NV_02: Sản xuất xuất khẩu'),
        ('import', 'NK_NV_03: Nhập khẩu'),
        ('transfer_return', 'NK_NV_04: Chuyển kho/Trả lại'),
    ], string='Receipt Type')
    
    # NK_NV_02: Xuất khẩu - Link with Work Order
    work_order_id = fields.Many2one(
        'mrp.workorder',
        string='Work Order',
        help='Work Order xuất khẩu (cho NK_NV_02)'
    )
    all_barcodes_scanned = fields.Boolean(
        string='All Products Scanned',
        default=False,
        help='Đã quét barcode tất cả sản phẩm (NK_NV_02)'
    )
    
    # NK_NV_03: Nhập khẩu - Additional documents
    invoice_no = fields.Char(
        string='Invoice Number',
        help='Số Invoice (NK_NV_03)'
    )
    customs_no = fields.Char(
        string='Customs Declaration No',
        help='Số tờ khai hải quan (NK_NV_03)'
    )
    sap_doc_no = fields.Char(
        string='SAP Document No',
        help='Số chứng từ SAP (NK_NV_03)'
    )
    
    # NK_NV_04: Transfer/Return
    transfer_doc_no = fields.Char(
        string='Transfer Document No',
        help='Số chứng từ chuyển kho (NK_NV_04)'
    )
    return_doc_no = fields.Char(
        string='Return Document No',
        help='Số phiếu trả lại (NK_NV_04)'
    )

    @api.depends('quant_ids.quantity')
    def _compute_product_qty(self):
        """Compute total quantity from quants"""
        for lot in self:
            lot.product_qty = sum(lot.quant_ids.mapped('quantity'))

    def action_generate_qr(self):
        """Tạo QR code cho batch"""
        self.ensure_one()
        if not self.batch_qr_code:
            # Generate unique QR code
            self.batch_qr_code = f"BATCH-{self.name}-{self.id}"
        return True

    def action_print_batch(self):
        """In batch label"""
        self.ensure_one()
        self.write({
            'batch_printed': True,
            'print_date': fields.Datetime.now(),
        })
        # TODO: Trigger actual print action
        return {
            'type': 'ir.actions.act_window',
            'name': 'Print Batch Label',
            'res_model': 'stock.lot',
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_scan_batch(self):
        """Quét QR Batch"""
        self.write({'batch_state': 'scanned'})
        return True

    def action_suggest_location(self):
        """Gợi ý vị trí đặt hàng"""
        self.ensure_one()
        
        # Use putaway suggestion engine
        suggestion_obj = self.env['putaway.suggestion']
        
        # Get total quantity in this batch
        total_qty = sum(self.quant_ids.mapped('quantity'))
        
        suggested_location = suggestion_obj.get_suggested_location(
            product_id=self.product_id.id,
            quantity=total_qty,
            warehouse_id=None
        )
        
        if suggested_location:
            self.suggested_location_id = suggested_location.id
        
        return True

    def action_place_batch(self):
        """Đặt batch vào vị trí"""
        self.ensure_one()
        
        if not self.actual_location_id:
            if self.suggested_location_id:
                self.actual_location_id = self.suggested_location_id.id
            else:
                raise UserError(_('Please select a location to place the batch.'))
        
        self.write({
            'batch_state': 'placed',
            'location_confirmed': True
        })
        return True

    def action_confirm_batch(self):
        """Xác nhận hoàn tất batch"""
        self.ensure_one()
        
        if not self.location_confirmed:
            raise UserError(_('Please place the batch in a location first.'))
        
        # Validation theo từng loại receipt
        if self.receipt_type == 'production_export':
            if not self.all_barcodes_scanned:
                raise UserError(_('Must scan all product barcodes for export production (NK_NV_02).'))
        
        if self.receipt_type == 'import':
            if not all([self.invoice_no, self.customs_no, self.sap_doc_no]):
                raise UserError(_('Missing import documents: Invoice, Customs, SAP Doc (NK_NV_03).'))
        
        if self.receipt_type == 'transfer_return':
            if not (self.transfer_doc_no or self.return_doc_no):
                raise UserError(_('Missing transfer/return document number (NK_NV_04).'))
        
        self.batch_state = 'confirmed'
        return True

    def action_reset_batch(self):
        """Reset batch về draft"""
        self.write({
            'batch_state': 'draft',
            'location_confirmed': False,
        })
        return True

    @api.model
    def scan_batch_qr(self, qr_code):
        """
        API để quét QR batch từ thiết bị
        """
        batch = self.search([('batch_qr_code', '=', qr_code)], limit=1)
        
        if not batch:
            return {
                'success': False,
                'message': f'Batch with QR {qr_code} not found'
            }
        
        batch.action_scan_batch()
        
        return {
            'success': True,
            'batch': batch,
            'message': 'Batch scanned successfully'
        }
