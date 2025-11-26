from odoo import models, fields, api, _


class StockLot(models.Model):
    """Enhance Batch với states chi tiết theo yêu cầu"""
    _inherit = 'stock.lot'

    # States theo tài liệu: draft → scanned → placed → confirmed
    batch_state = fields.Selection([
        ('draft', 'Draft'),
        ('scanned', 'Scanned'),
        ('placed', 'Placed in Location'),
        ('confirmed', 'Confirmed'),
    ], string='Batch Status', default='draft', tracking=True,
       help='Batch lifecycle: draft → scanned → placed → confirmed')
    
    # Receipt type cho các luồng nhập khẩu khác nhau
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Production Domestic'),
        ('production_export', 'NK_NV_02: Production Export'),
        ('import', 'NK_NV_03: Import'),
        ('transfer_return', 'NK_NV_04: Transfer/Return'),
    ], string='Receipt Type',
       help='Type of receipt process for this batch')
    
    # Link với Work Order xuất khẩu (cho NK_NV_02)
    work_order_export = fields.Char(
        string='Export Work Order',
        help='Work order reference for export production'
    )
    
    # Thông tin nhập khẩu (cho NK_NV_03)
    invoice_no = fields.Char(
        string='Invoice Number',
        help='Invoice number for imported goods'
    )
    customs_declaration_no = fields.Char(
        string='Customs Declaration',
        help='Customs declaration number'
    )
    sap_document_no = fields.Char(
        string='SAP Document',
        help='SAP document reference'
    )
    
    # Thông tin chuyển kho/trả lại (cho NK_NV_04)
    transfer_document_no = fields.Char(
        string='Transfer Document',
        help='Transfer or return document number'
    )
    
    # Vị trí hiện tại của batch
    current_location_id = fields.Many2one(
        'stock.location',
        string='Current Location',
        compute='_compute_current_location',
        store=True
    )
    
    # QR Code content
    qr_code = fields.Char(
        string='QR Code',
        compute='_compute_qr_code',
        store=True
    )
    
    # Suggested location (from putaway engine)
    suggested_location_id = fields.Many2one(
        'stock.location',
        string='Suggested Location',
        help='AI-suggested putaway location'
    )

    @api.depends('quant_ids', 'quant_ids.location_id')
    def _compute_current_location(self):
        for lot in self:
            quants = lot.quant_ids.filtered(lambda q: q.quantity > 0)
            if quants:
                lot.current_location_id = quants[0].location_id
            else:
                lot.current_location_id = False

    @api.depends('name', 'product_id')
    def _compute_qr_code(self):
        for lot in self:
            if lot.name and lot.product_id:
                lot.qr_code = f"BATCH|{lot.name}|{lot.product_id.default_code or lot.product_id.id}"
            else:
                lot.qr_code = False

    def action_scan(self):
        """Action khi quét QR Batch"""
        self.ensure_one()
        if self.batch_state == 'draft':
            self.batch_state = 'scanned'
            
            # Auto-suggest location using putaway engine
            if self.product_id and not self.suggested_location_id:
                suggestion = self.env['putaway.suggestion'].get_suggested_location(
                    product_id=self.product_id.id,
                    quantity=self.product_qty or 0
                )
                if suggestion:
                    self.suggested_location_id = suggestion.id
        return True

    def action_place(self, location_id):
        """Action đặt batch vào vị trí"""
        self.ensure_one()
        self.write({
            'batch_state': 'placed',
            'current_location_id': location_id,
        })
        return True

    def action_confirm(self):
        """Xác nhận batch đã đặt đúng vị trí"""
        self.ensure_one()
        if self.batch_state != 'placed':
            raise ValidationError(_('Batch must be placed before confirmation.'))
        self.batch_state = 'confirmed'
        return True

    def action_print_batch_label(self):
        """In nhãn Batch với QR code"""
        self.ensure_one()
        return self.env.ref('hdi_stock_batch_flow.action_report_batch_label').report_action(self)
