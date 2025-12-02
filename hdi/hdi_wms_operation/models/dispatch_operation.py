from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DispatchOperation(models.Model):
    """
    XK_NV: Xuất kho - Phiếu xuất hàng chính
    Workflow: draft → picking → packed → staged → loaded → shipped
    """
    _name = 'dispatch.operation'
    _description = 'Dispatch Operation - Xuất kho'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'dispatch_date desc'

    name = fields.Char(
        string='Mã phiếu xuất',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    dispatch_date = fields.Datetime(
        string='Ngày xuất kho',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    # State machine
    state = fields.Selection([
        ('draft', 'Nháp'),
        ('picking', 'Đang lấy hàng'),
        ('packed', 'Đã đóng gói'),
        ('staged', 'Tập kết'),
        ('loaded', 'Đã lên xe'),
        ('shipped', 'Đã giao hàng'),
        ('cancel', 'Hủy')
    ], string='Trạng thái', default='draft', tracking=True)
    
    # Customer info
    partner_id = fields.Many2one(
        'res.partner',
        string='Khách hàng',
        required=True,
        tracking=True
    )
    delivery_address = fields.Text(
        string='Địa chỉ giao hàng',
        compute='_compute_delivery_address',
        store=True
    )
    
    # Lines
    line_ids = fields.One2many(
        'dispatch.operation.line',
        'dispatch_id',
        string='Chi tiết xuất kho'
    )
    
    # Staging
    staging_location_id = fields.Many2one(
        'stock.location',
        string='Vị trí tập kết',
        domain=[('usage', '=', 'internal')],
        help='Khu vực tập kết hàng trước khi lên xe'
    )
    
    # Vehicle assignment (optional - requires fleet module)
    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string='Xe giao hàng',
        tracking=True,
        ondelete='set null'
    )
    driver_id = fields.Many2one(
        'res.partner',
        string='Tài xế',
        tracking=True,
        ondelete='set null'
    )
    
    # Warehouse
    warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Kho',
        required=True,
        default=lambda self: self.env['stock.warehouse'].search([('company_id', '=', self.env.company.id)], limit=1)
    )
    
    # Statistics
    total_qty = fields.Float(
        compute='_compute_statistics',
        string='Tổng số lượng',
        store=True
    )
    total_packages = fields.Integer(
        compute='_compute_statistics',
        string='Số kiện',
        store=True
    )
    
    # Approval
    warehouse_manager_id = fields.Many2one(
        'res.users',
        string='Quản lý kho',
        help='Người phê duyệt xuất kho'
    )
    approved_date = fields.Datetime(
        string='Ngày phê duyệt',
        readonly=True
    )
    
    # Related picking (optional)
    picking_id = fields.Many2one(
        'stock.picking',
        string='Stock Picking',
        ondelete='set null'
    )
    
    notes = fields.Text(string='Ghi chú')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company
    )

    @api.depends('partner_id')
    def _compute_delivery_address(self):
        for record in self:
            if record.partner_id:
                address_parts = []
                if record.partner_id.street:
                    address_parts.append(record.partner_id.street)
                if record.partner_id.city:
                    address_parts.append(record.partner_id.city)
                if record.partner_id.state_id:
                    address_parts.append(record.partner_id.state_id.name)
                record.delivery_address = ', '.join(address_parts)
            else:
                record.delivery_address = False

    @api.depends('line_ids.qty_ordered', 'line_ids.package_id')
    def _compute_statistics(self):
        for record in self:
            record.total_qty = sum(line.qty_ordered for line in record.line_ids)
            record.total_packages = len(record.line_ids.mapped('package_id'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('dispatch.operation') or _('XK/New')
        return super().create(vals_list)

    def action_generate_picklist(self):
        """Tạo picklist từ dispatch order"""
        self.ensure_one()
        
        if not self.line_ids:
            raise UserError(_('Cần có ít nhất 1 dòng sản phẩm để tạo picklist.'))
        
        # Check if picking.picklist model exists
        if 'picking.picklist' not in self.env:
            raise UserError(_('Module hdi_stock_dispatch_extension chưa được cài đặt.'))
        
        picklist = self.env['picking.picklist'].create({
            'picklist_date': fields.Datetime.now(),
            'company_id': self.company_id.id,
            'staging_location_id': self.staging_location_id.id if self.staging_location_id else False,
        })
        
        for line in self.line_ids:
            self.env['picklist.line'].create({
                'picklist_id': picklist.id,
                'product_id': line.product_id.id,
                'qty_ordered': line.qty_ordered,
                'location_id': self.warehouse_id.lot_stock_id.id,
            })
        
        self.state = 'picking'
        
        return {
            'type': 'ir.actions.act_window',
            'name': _('Picklist'),
            'res_model': 'picking.picklist',
            'res_id': picklist.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def action_start_packing(self):
        """Bắt đầu đóng gói"""
        self.ensure_one()
        
        if not self.picklist_id or self.picklist_id.state != 'done':
            raise UserError(_('Picklist phải hoàn thành trước khi đóng gói.'))
        
        self.state = 'packed'

    def action_move_to_staging(self):
        """Chuyển hàng đến khu tập kết"""
        self.ensure_one()
        
        if self.state != 'packed':
            raise UserError(_('Hàng phải đóng gói xong mới chuyển tập kết.'))
        
        if not self.staging_location_id:
            raise UserError(_('Chưa xác định vị trí tập kết.'))
        
        self.state = 'staged'

    def action_load_vehicle(self):
        """Lên xe"""
        self.ensure_one()
        
        if self.state != 'staged':
            raise UserError(_('Hàng phải ở khu tập kết mới lên xe được.'))
        
        if not self.vehicle_id:
            raise UserError(_('Chưa phân công xe giao hàng.'))
        
        self.state = 'loaded'

    def action_ship(self):
        """Giao hàng"""
        self.ensure_one()
        
        if self.state != 'loaded':
            raise UserError(_('Hàng phải lên xe rồi mới giao được.'))
        
        self.write({
            'state': 'shipped',
            'warehouse_manager_id': self.env.user.id,
            'approved_date': fields.Datetime.now()
        })

    def action_cancel(self):
        """Hủy phiếu xuất"""
        self.state = 'cancel'


class DispatchOperationLine(models.Model):
    _name = 'dispatch.operation.line'
    _description = 'Dispatch Operation Line'
    _order = 'sequence, id'

    sequence = fields.Integer(string='STT', default=10)
    dispatch_id = fields.Many2one(
        'dispatch.operation',
        string='Dispatch Operation',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Sản phẩm',
        required=True
    )
    qty_ordered = fields.Float(
        string='SL yêu cầu',
        required=True,
        digits='Product Unit of Measure'
    )
    qty_picked = fields.Float(
        string='SL đã lấy',
        digits='Product Unit of Measure',
        default=0.0
    )
    uom_id = fields.Many2one(
        'uom.uom',
        string='ĐVT',
        related='product_id.uom_id',
        readonly=True
    )
    
    # Batch/Lot - FIFO selection
    lot_id = fields.Many2one(
        'stock.lot',
        string='Batch/Lô',
        domain="[('product_id', '=', product_id), ('product_qty', '>', 0)]"
    )
    
    # Package
    package_id = fields.Many2one(
        'stock.quant.package',
        string='Kiện hàng'
    )
    
    notes = fields.Text(string='Ghi chú')
