from odoo import models, fields, api, _


class StockLot(models.Model):
    """Enhance Batch với states chi tiết theo yêu cầu"""
    _inherit = 'stock.lot'

    # States theo tài liệu: draft → scanned → placed → confirmed
    batch_state = fields.Selection([
        ('draft', 'Khởi tạo'),
        ('scanned', 'Đã quét'),
        ('placed', 'Đã đặt vào vị trí'),
        ('confirmed', 'Đã xác nhận'),
    ], string='Trạng thái batch', default='draft', tracking=True,
       help='Quy trình trạng thái batch: Khởi tạo → Đã quét → Đã đặt vào vị trí → Đã xác nhận')
    
    # Receipt type cho các luồng nhập khẩu khác nhau
    receipt_type = fields.Selection([
        ('production_domestic', 'NK_NV_01: Sản xuất nội địa'),
        ('production_export', 'NK_NV_02: Sản xuất xuất khẩu'),
        ('import', 'NK_NV_03: Nhập khẩu'),
        ('transfer_return', 'NK_NV_04: Điều chuyển/Trả lại'),
    ], string='Loại nhập kho',
       help='Loại nghiệp vụ nhập kho cho batch này')
    
    # Link với Work Order xuất khẩu (cho NK_NV_02)
    work_order_export = fields.Char(
        string='Lệnh sản xuất xuất khẩu',
        help='Tham chiếu lệnh sản xuất cho xuất khẩu'
    )
    
    # Thông tin nhập khẩu (cho NK_NV_03)
    invoice_no = fields.Char(
        string='Số hóa đơn',
        help='Số hóa đơn cho hàng nhập khẩu'
    )
    customs_declaration_no = fields.Char(
        string='Số tờ khai hải quan',
        help='Số tờ khai hải quan'
    )
    sap_document_no = fields.Char(
        string='Số chứng từ SAP',
        help='Tham chiếu chứng từ SAP'
    )
    
    # Thông tin chuyển kho/trả lại (cho NK_NV_04)
    transfer_document_no = fields.Char(
        string='Số chứng từ điều chuyển/trả lại',
        help='Số chứng từ điều chuyển hoặc trả lại'
    )
    
    # Vị trí hiện tại của batch
    current_location_id = fields.Many2one(
        'stock.location',
        string='Vị trí hiện tại',
        compute='_compute_current_location',
        store=True
    )
    
    # QR Code content
    qr_code = fields.Char(
        string='Mã QR',
        compute='_compute_qr_code',
        store=True
    )
    
    # Suggested location (from putaway engine)
    suggested_location_id = fields.Many2one(
        'stock.location',
        string='Vị trí đề xuất',
        help='Vị trí kho đề xuất bởi AI'
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
