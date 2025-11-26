from odoo import http
from odoo.http import request, Response
import json
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class WmsApiController(http.Controller):
    
    def _authenticate(self):
        """Authenticate API request"""
        api_key = request.httprequest.headers.get('X-API-Key')
        if not api_key:
            return None, {'error': 'API key missing', 'code': 401}
        
        ip_address = request.httprequest.remote_addr
        api_key_obj = request.env['wms.api.key'].sudo().validate_key(api_key, ip_address)
        
        if not api_key_obj:
            return None, {'error': 'Invalid or expired API key', 'code': 401}
        
        return api_key_obj, None

    def _log_request(self, endpoint, method, api_key_id, response_data, response_code, start_time, error=None):
        """Log API request"""
        response_time = (datetime.now() - start_time).total_seconds() * 1000
        request.env['wms.api.log'].sudo().log_request(
            endpoint=endpoint,
            method=method,
            api_key_id=api_key_id,
            user_id=request.env.user.id,
            ip_address=request.httprequest.remote_addr,
            request_data=request.httprequest.data.decode('utf-8') if request.httprequest.data else None,
            response_data=json.dumps(response_data),
            response_code=response_code,
            response_time=response_time,
            error_message=error
        )

    def _response(self, data, status=200):
        """Format JSON response"""
        return Response(
            json.dumps(data, ensure_ascii=False, indent=2, default=str),
            content_type='application/json',
            status=status
        )

    @http.route('/api/wms/stock/query', type='http', auth='none', methods=['POST'], csrf=False)
    def query_stock(self, **kwargs):
        """Query stock levels"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        if not api_key.can_query:
            return self._response({'error': 'Permission denied'}, 403)
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            domain = []
            if api_key.warehouse_id:
                domain.append(('warehouse_id', '=', api_key.warehouse_id.id))
            
            if data.get('product_code'):
                product = request.env['product.product'].sudo().search([
                    ('default_code', '=', data['product_code'])
                ], limit=1)
                if product:
                    domain.append(('product_id', '=', product.id))
            
            if data.get('location_code'):
                location = request.env['wms.location'].sudo().search([
                    ('code', '=', data['location_code'])
                ], limit=1)
                if location:
                    domain.append(('location_id', '=', location.id))
            
            quants = request.env['wms.stock.quant'].sudo().search(domain)
            
            result = {
                'success': True,
                'data': [{
                    'product_code': q.product_id.default_code,
                    'product_name': q.product_id.name,
                    'location_code': q.location_id.code,
                    'location_name': q.location_id.name,
                    'quantity': q.quantity,
                    'available_quantity': q.available_quantity,
                    'reserved_quantity': q.reserved_quantity,
                    'uom': q.product_uom_id.name,
                } for q in quants]
            }
            
            self._log_request('/api/wms/stock/query', 'POST', api_key.id, result, 200, start_time)
            return self._response(result)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in query_stock: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/stock/query', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)

    @http.route('/api/wms/receipt/create', type='http', auth='none', methods=['POST'], csrf=False)
    def create_receipt(self, **kwargs):
        """Create receipt"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        if not api_key.can_create_receipt:
            return self._response({'error': 'Permission denied'}, 403)
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            if not data.get('warehouse_code'):
                return self._response({'error': 'warehouse_code required'}, 400)
            
            warehouse = request.env['wms.warehouse'].sudo().search([
                ('code', '=', data['warehouse_code'])
            ], limit=1)
            
            if not warehouse:
                return self._response({'error': 'Warehouse not found'}, 404)
            
            # Create receipt
            receipt_vals = {
                'warehouse_id': warehouse.id,
                'origin': data.get('origin', 'API'),
                'notes': data.get('notes', ''),
            }
            
            receipt = request.env['wms.receipt'].sudo().create(receipt_vals)
            
            # Create lines
            for line_data in data.get('lines', []):
                product = request.env['product.product'].sudo().search([
                    ('default_code', '=', line_data.get('product_code'))
                ], limit=1)
                
                if not product:
                    continue
                
                request.env['wms.receipt.line'].sudo().create({
                    'receipt_id': receipt.id,
                    'product_id': product.id,
                    'ordered_qty': line_data.get('quantity', 0),
                    'notes': line_data.get('notes', ''),
                })
            
            result = {
                'success': True,
                'data': {
                    'receipt_id': receipt.id,
                    'receipt_number': receipt.name,
                    'state': receipt.state,
                }
            }
            
            self._log_request('/api/wms/receipt/create', 'POST', api_key.id, result, 201, start_time)
            return self._response(result, 201)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in create_receipt: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/receipt/create', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)

    @http.route('/api/wms/delivery/create', type='http', auth='none', methods=['POST'], csrf=False)
    def create_delivery(self, **kwargs):
        """Create delivery"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        if not api_key.can_create_delivery:
            return self._response({'error': 'Permission denied'}, 403)
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            # Validate required fields
            if not data.get('warehouse_code'):
                return self._response({'error': 'warehouse_code required'}, 400)
            
            warehouse = request.env['wms.warehouse'].sudo().search([
                ('code', '=', data['warehouse_code'])
            ], limit=1)
            
            if not warehouse:
                return self._response({'error': 'Warehouse not found'}, 404)
            
            # Create delivery
            delivery_vals = {
                'warehouse_id': warehouse.id,
                'origin': data.get('origin', 'API'),
                'customer_name': data.get('customer_name', ''),
                'delivery_address': data.get('delivery_address', ''),
                'notes': data.get('notes', ''),
            }
            
            delivery = request.env['wms.delivery'].sudo().create(delivery_vals)
            
            # Create lines
            for line_data in data.get('lines', []):
                product = request.env['product.product'].sudo().search([
                    ('default_code', '=', line_data.get('product_code'))
                ], limit=1)
                
                if not product:
                    continue
                
                request.env['wms.delivery.line'].sudo().create({
                    'delivery_id': delivery.id,
                    'product_id': product.id,
                    'ordered_qty': line_data.get('quantity', 0),
                    'notes': line_data.get('notes', ''),
                })
            
            result = {
                'success': True,
                'data': {
                    'delivery_id': delivery.id,
                    'delivery_number': delivery.name,
                    'state': delivery.state,
                }
            }
            
            self._log_request('/api/wms/delivery/create', 'POST', api_key.id, result, 201, start_time)
            return self._response(result, 201)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in create_delivery: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/delivery/create', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)

    @http.route('/api/wms/stock/reserve', type='http', auth='none', methods=['POST'], csrf=False)
    def reserve_stock(self, **kwargs):
        """Reserve stock"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        if not api_key.can_reserve:
            return self._response({'error': 'Permission denied'}, 403)
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            product = request.env['product.product'].sudo().search([
                ('default_code', '=', data.get('product_code'))
            ], limit=1)
            
            if not product:
                return self._response({'error': 'Product not found'}, 404)
            
            location = request.env['wms.location'].sudo().search([
                ('code', '=', data.get('location_code'))
            ], limit=1) if data.get('location_code') else None
            
            quantity = data.get('quantity', 0)
            
            # Reserve stock
            reserved = request.env['wms.stock.quant'].sudo().reserve_stock(
                product_id=product.id,
                quantity=quantity,
                location_id=location.id if location else None,
                origin=data.get('origin', 'API')
            )
            
            result = {
                'success': reserved,
                'data': {
                    'product_code': product.default_code,
                    'reserved_quantity': quantity if reserved else 0,
                }
            }
            
            self._log_request('/api/wms/stock/reserve', 'POST', api_key.id, result, 200, start_time)
            return self._response(result)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in reserve_stock: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/stock/reserve', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)

    @http.route('/api/wms/stock/move', type='http', auth='none', methods=['POST'], csrf=False)
    def move_stock(self, **kwargs):
        """Move stock"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        if not api_key.can_move:
            return self._response({'error': 'Permission denied'}, 403)
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            product = request.env['product.product'].sudo().search([
                ('default_code', '=', data.get('product_code'))
            ], limit=1)
            
            if not product:
                return self._response({'error': 'Product not found'}, 404)
            
            location_from = request.env['wms.location'].sudo().search([
                ('code', '=', data.get('location_from_code'))
            ], limit=1)
            
            location_to = request.env['wms.location'].sudo().search([
                ('code', '=', data.get('location_to_code'))
            ], limit=1)
            
            if not location_from or not location_to:
                return self._response({'error': 'Location not found'}, 404)
            
            quantity = data.get('quantity', 0)
            
            # Create stock move
            move = request.env['wms.stock.move'].sudo().create({
                'product_id': product.id,
                'quantity': quantity,
                'product_uom_id': product.uom_id.id,
                'location_from_id': location_from.id,
                'location_to_id': location_to.id,
                'move_type': 'transfer',
                'origin': data.get('origin', 'API'),
            })
            
            move.action_done()
            
            result = {
                'success': True,
                'data': {
                    'move_id': move.id,
                    'product_code': product.default_code,
                    'quantity': quantity,
                    'location_from': location_from.code,
                    'location_to': location_to.code,
                }
            }
            
            self._log_request('/api/wms/stock/move', 'POST', api_key.id, result, 201, start_time)
            return self._response(result, 201)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in move_stock: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/stock/move', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)

    @http.route('/api/wms/barcode/scan', type='http', auth='none', methods=['POST'], csrf=False)
    def barcode_scan(self, **kwargs):
        """Process barcode scan"""
        start_time = datetime.now()
        api_key, error = self._authenticate()
        
        if error:
            return self._response(error, error['code'])
        
        try:
            data = json.loads(request.httprequest.data.decode('utf-8'))
            
            warehouse = request.env['wms.warehouse'].sudo().search([
                ('code', '=', data.get('warehouse_code'))
            ], limit=1)
            
            if not warehouse:
                return self._response({'error': 'Warehouse not found'}, 404)
            
            result = request.env['wms.barcode.scan'].sudo().process_scan(
                barcode=data.get('barcode'),
                operation_type=data.get('operation_type'),
                warehouse_id=warehouse.id,
                **data
            )
            
            self._log_request('/api/wms/barcode/scan', 'POST', api_key.id, result, 200, start_time)
            return self._response(result)
            
        except Exception as e:
            error_msg = str(e)
            _logger.error(f"API Error in barcode_scan: {error_msg}")
            result = {'error': error_msg}
            self._log_request('/api/wms/barcode/scan', 'POST', api_key.id, result, 500, start_time, error_msg)
            return self._response(result, 500)
