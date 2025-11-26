from odoo import models, fields, api
from odoo.exceptions import ValidationError


class WmsBarcodeScan(models.Model):
    _name = 'wms.barcode.scan'
    _description = 'WMS Barcode Scan'
    _order = 'create_date desc'

    name = fields.Char(string='Scan Reference', required=True, readonly=True, 
                       copy=False, default=lambda self: 'New')
    barcode = fields.Char(string='Barcode', required=True, index=True)
    scan_type = fields.Selection([
        ('product', 'Product'),
        ('location', 'Location'),
        ('lot', 'Lot/Serial'),
        ('package', 'Package'),
    ], string='Scan Type', required=True)
    
    operation_type = fields.Selection([
        ('query', 'Query Stock'),
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery'),
        ('transfer', 'Transfer'),
        ('picking', 'Picking'),
        ('putaway', 'Putaway'),
        ('counting', 'Cycle Counting'),
    ], string='Operation', required=True)
    
    user_id = fields.Many2one('res.users', string='User', required=True,
                             default=lambda self: self.env.user)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    # Scanned data
    product_id = fields.Many2one('product.product', string='Product')
    location_id = fields.Many2one('wms.location', string='Location')
    lot_id = fields.Many2one('stock.lot', string='Lot/Serial')
    quantity = fields.Float(string='Quantity', default=1.0)
    
    # Related document
    receipt_id = fields.Many2one('wms.receipt', string='Receipt')
    delivery_id = fields.Many2one('wms.delivery', string='Delivery')
    transfer_id = fields.Many2one('wms.transfer', string='Transfer')
    adjustment_id = fields.Many2one('wms.adjustment', string='Adjustment')
    
    # Result
    result_message = fields.Text(string='Result Message')
    success = fields.Boolean(string='Success', default=True)
    
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('wms.barcode.scan') or 'New'
        return super(WmsBarcodeScan, self).create(vals)

    @api.model
    def process_scan(self, barcode, operation_type, warehouse_id, **kwargs):
        """Process barcode scan and return result"""
        scan_type, scan_result = self._identify_barcode(barcode)
        
        vals = {
            'barcode': barcode,
            'scan_type': scan_type,
            'operation_type': operation_type,
            'warehouse_id': warehouse_id,
        }
        
        # Update vals based on scan type
        if scan_type == 'product' and scan_result:
            vals['product_id'] = scan_result.id
        elif scan_type == 'location' and scan_result:
            vals['location_id'] = scan_result.id
        elif scan_type == 'lot' and scan_result:
            vals['lot_id'] = scan_result.id
        
        # Process based on operation type
        result = self._process_operation(operation_type, scan_type, scan_result, **kwargs)
        
        vals.update({
            'result_message': result.get('message', ''),
            'success': result.get('success', True),
            'quantity': kwargs.get('quantity', 1.0),
        })
        
        # Create scan record
        scan = self.create(vals)
        
        return {
            'scan_id': scan.id,
            'scan_type': scan_type,
            'success': result.get('success', True),
            'message': result.get('message', ''),
            'data': result.get('data', {}),
        }

    def _identify_barcode(self, barcode):
        """Identify what the barcode represents"""
        # Check barcode rules first
        rule = self.env['wms.barcode.rule'].search([
            ('barcode_pattern', '=', barcode[:3])  # First 3 chars as prefix
        ], limit=1)
        
        if rule:
            return rule.entity_type, rule._get_entity(barcode)
        
        # Default checks
        # Check product
        product = self.env['product.product'].search([
            '|', ('barcode', '=', barcode),
            ('default_code', '=', barcode)
        ], limit=1)
        if product:
            return 'product', product
        
        # Check location
        location = self.env['wms.location'].search([
            ('barcode', '=', barcode)
        ], limit=1)
        if location:
            return 'location', location
        
        # Check lot/serial
        lot = self.env['stock.lot'].search([
            ('name', '=', barcode)
        ], limit=1)
        if lot:
            return 'lot', lot
        
        return 'unknown', None

    def _process_operation(self, operation_type, scan_type, scan_result, **kwargs):
        """Process scan based on operation type"""
        if operation_type == 'query':
            return self._process_query(scan_type, scan_result)
        elif operation_type == 'receipt':
            return self._process_receipt(scan_type, scan_result, **kwargs)
        elif operation_type == 'delivery':
            return self._process_delivery(scan_type, scan_result, **kwargs)
        elif operation_type == 'picking':
            return self._process_picking(scan_type, scan_result, **kwargs)
        elif operation_type == 'putaway':
            return self._process_putaway(scan_type, scan_result, **kwargs)
        elif operation_type == 'counting':
            return self._process_counting(scan_type, scan_result, **kwargs)
        
        return {'success': False, 'message': 'Unknown operation type'}

    def _process_query(self, scan_type, scan_result):
        """Query stock information"""
        if not scan_result:
            return {'success': False, 'message': 'Item not found'}
        
        data = {}
        
        if scan_type == 'product':
            # Get stock by location
            quants = self.env['wms.stock.quant'].search([
                ('product_id', '=', scan_result.id),
                ('quantity', '>', 0)
            ])
            data = {
                'product': scan_result.name,
                'total_quantity': sum(quants.mapped('quantity')),
                'locations': [{
                    'location': q.location_id.name,
                    'quantity': q.quantity,
                    'available': q.available_quantity,
                } for q in quants]
            }
            message = f"Product: {scan_result.name}\nTotal: {data['total_quantity']}"
            
        elif scan_type == 'location':
            # Get products in location
            quants = self.env['wms.stock.quant'].search([
                ('location_id', '=', scan_result.id),
                ('quantity', '>', 0)
            ])
            data = {
                'location': scan_result.name,
                'product_count': len(quants),
                'products': [{
                    'product': q.product_id.name,
                    'quantity': q.quantity,
                } for q in quants]
            }
            message = f"Location: {scan_result.name}\nProducts: {data['product_count']}"
        
        else:
            message = f"Found {scan_type}: {scan_result.name}"
        
        return {'success': True, 'message': message, 'data': data}

    def _process_receipt(self, scan_type, scan_result, **kwargs):
        """Process receipt scan"""
        receipt_id = kwargs.get('receipt_id')
        if not receipt_id:
            return {'success': False, 'message': 'Receipt not specified'}
        
        receipt = self.env['wms.receipt'].browse(receipt_id)
        
        if scan_type == 'product':
            # Find matching line
            line = receipt.line_ids.filtered(
                lambda l: l.product_id.id == scan_result.id and l.state != 'done'
            )
            if line:
                return {
                    'success': True,
                    'message': f'Product: {scan_result.name}\nExpected: {line[0].ordered_qty}\nReceived: {line[0].received_qty}',
                    'data': {'line_id': line[0].id}
                }
            else:
                return {'success': False, 'message': 'Product not in receipt'}
        
        elif scan_type == 'location':
            # Validate putaway location
            if not scan_result.can_stock:
                return {'success': False, 'message': 'Location cannot store products'}
            return {
                'success': True,
                'message': f'Putaway to: {scan_result.name}',
                'data': {'location_id': scan_result.id}
            }
        
        return {'success': False, 'message': 'Invalid scan for receipt'}

    def _process_delivery(self, scan_type, scan_result, **kwargs):
        """Process delivery scan"""
        delivery_id = kwargs.get('delivery_id')
        if not delivery_id:
            return {'success': False, 'message': 'Delivery not specified'}
        
        delivery = self.env['wms.delivery'].browse(delivery_id)
        
        if scan_type == 'product':
            # Find matching line
            line = delivery.line_ids.filtered(
                lambda l: l.product_id.id == scan_result.id and l.state != 'done'
            )
            if line:
                return {
                    'success': True,
                    'message': f'Product: {scan_result.name}\nOrdered: {line[0].ordered_qty}\nPicked: {line[0].picked_qty}',
                    'data': {'line_id': line[0].id}
                }
            else:
                return {'success': False, 'message': 'Product not in delivery'}
        
        return {'success': False, 'message': 'Invalid scan for delivery'}

    def _process_picking(self, scan_type, scan_result, **kwargs):
        """Process picking scan"""
        if scan_type == 'product':
            # Show pick locations
            quants = self.env['wms.stock.quant'].search([
                ('product_id', '=', scan_result.id),
                ('available_quantity', '>', 0)
            ], order='location_id')
            
            if quants:
                locations_text = '\n'.join([
                    f"{q.location_id.name}: {q.available_quantity}"
                    for q in quants[:5]
                ])
                return {
                    'success': True,
                    'message': f'Pick {scan_result.name} from:\n{locations_text}',
                    'data': {'quants': quants.ids}
                }
            else:
                return {'success': False, 'message': 'No stock available'}
        
        return {'success': False, 'message': 'Scan product to pick'}

    def _process_putaway(self, scan_type, scan_result, **kwargs):
        """Process putaway scan"""
        if scan_type == 'location':
            # Suggest putaway location based on rules
            return {
                'success': True,
                'message': f'Putaway to: {scan_result.name}\nCapacity: {scan_result.capacity_percentage:.1f}%',
                'data': {'location_id': scan_result.id}
            }
        
        return {'success': False, 'message': 'Scan location for putaway'}

    def _process_counting(self, scan_type, scan_result, **kwargs):
        """Process cycle counting scan"""
        location_id = kwargs.get('location_id')
        
        if scan_type == 'product' and location_id:
            quant = self.env['wms.stock.quant'].search([
                ('product_id', '=', scan_result.id),
                ('location_id', '=', location_id)
            ], limit=1)
            
            system_qty = quant.quantity if quant else 0.0
            return {
                'success': True,
                'message': f'Product: {scan_result.name}\nSystem: {system_qty}',
                'data': {'system_quantity': system_qty}
            }
        
        return {'success': False, 'message': 'Scan product in counting location'}


class WmsBarcodeRule(models.Model):
    _name = 'wms.barcode.rule'
    _description = 'WMS Barcode Rule'
    _order = 'sequence, id'

    name = fields.Char(string='Rule Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    barcode_pattern = fields.Char(string='Barcode Pattern', required=True,
                                   help='Pattern to match (e.g., PRD for products starting with PRD)')
    entity_type = fields.Selection([
        ('product', 'Product'),
        ('location', 'Location'),
        ('lot', 'Lot/Serial'),
        ('package', 'Package'),
    ], string='Entity Type', required=True)
    
    field_to_match = fields.Selection([
        ('barcode', 'Barcode'),
        ('default_code', 'Internal Reference'),
        ('name', 'Name'),
    ], string='Field to Match', default='barcode', required=True)
    
    notes = fields.Text(string='Notes')

    def _get_entity(self, barcode):
        """Get entity based on rule"""
        self.ensure_one()
        
        model_map = {
            'product': 'product.product',
            'location': 'wms.location',
            'lot': 'stock.lot',
            'package': 'stock.quant.package',
        }
        
        model_name = model_map.get(self.entity_type)
        if not model_name:
            return None
        
        domain = [(self.field_to_match, '=', barcode)]
        return self.env[model_name].search(domain, limit=1)
