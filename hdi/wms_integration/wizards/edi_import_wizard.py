from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import csv
import json
import xml.etree.ElementTree as ET
from io import StringIO
import logging

_logger = logging.getLogger(__name__)


class EdiImportWizard(models.TransientModel):
    _name = 'edi.import.wizard'
    _description = 'EDI Import Wizard'

    file_format = fields.Selection([
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
    ], string='File Format', required=True, default='csv')
    
    file_data = fields.Binary(string='File', required=True)
    file_name = fields.Char(string='File Name')
    
    import_type = fields.Selection([
        ('receipt', 'Receipt'),
        ('delivery', 'Delivery'),
        ('product', 'Product'),
        ('location', 'Location'),
    ], string='Import Type', required=True, default='receipt')
    
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse', required=True)
    
    # Mapping rules
    product_field = fields.Selection([
        ('default_code', 'Internal Reference'),
        ('barcode', 'Barcode'),
        ('name', 'Name'),
    ], string='Product Field', default='default_code')
    
    location_field = fields.Selection([
        ('code', 'Code'),
        ('barcode', 'Barcode'),
        ('name', 'Name'),
    ], string='Location Field', default='code')
    
    # Options
    create_missing = fields.Boolean(string='Create Missing Items', default=False,
                                     help='Create products/locations if not found')
    skip_errors = fields.Boolean(string='Skip Errors', default=True,
                                 help='Continue import on errors')
    
    # Results
    result_message = fields.Text(string='Result', readonly=True)
    imported_count = fields.Integer(string='Imported', readonly=True)
    error_count = fields.Integer(string='Errors', readonly=True)

    def action_import(self):
        """Import data from file"""
        self.ensure_one()
        
        try:
            file_content = base64.b64decode(self.file_data).decode('utf-8')
            
            if self.file_format == 'csv':
                data = self._parse_csv(file_content)
            elif self.file_format == 'json':
                data = self._parse_json(file_content)
            elif self.file_format == 'xml':
                data = self._parse_xml(file_content)
            else:
                raise UserError('Unsupported file format')
            
            # Process data
            if self.import_type == 'receipt':
                result = self._import_receipts(data)
            elif self.import_type == 'delivery':
                result = self._import_deliveries(data)
            elif self.import_type == 'product':
                result = self._import_products(data)
            elif self.import_type == 'location':
                result = self._import_locations(data)
            else:
                raise UserError('Unsupported import type')
            
            self.write({
                'result_message': result['message'],
                'imported_count': result['imported'],
                'error_count': result['errors'],
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'edi.import.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(f'Import failed: {str(e)}')

    def _parse_csv(self, content):
        """Parse CSV file"""
        data = []
        reader = csv.DictReader(StringIO(content))
        for row in reader:
            data.append(row)
        return data

    def _parse_json(self, content):
        """Parse JSON file"""
        return json.loads(content)

    def _parse_xml(self, content):
        """Parse XML file"""
        root = ET.fromstring(content)
        data = []
        
        for item in root.findall('.//item'):
            row = {}
            for child in item:
                row[child.tag] = child.text
            data.append(row)
        
        return data

    def _import_receipts(self, data):
        """Import receipts"""
        imported = 0
        errors = 0
        messages = []
        
        for row in data:
            try:
                # Get or create receipt
                origin = row.get('origin', 'EDI Import')
                receipt = self.env['wms.receipt'].search([
                    ('origin', '=', origin),
                    ('state', '=', 'draft')
                ], limit=1)
                
                if not receipt:
                    receipt = self.env['wms.receipt'].create({
                        'warehouse_id': self.warehouse_id.id,
                        'origin': origin,
                        'notes': row.get('notes', ''),
                    })
                
                # Find product
                product = self._find_product(row.get('product'))
                if not product:
                    if self.create_missing:
                        product = self.env['product.product'].create({
                            'name': row.get('product_name', row.get('product')),
                            'default_code': row.get('product'),
                            'type': 'product',
                        })
                    else:
                        raise ValueError(f"Product not found: {row.get('product')}")
                
                # Create line
                self.env['wms.receipt.line'].create({
                    'receipt_id': receipt.id,
                    'product_id': product.id,
                    'ordered_qty': float(row.get('quantity', 0)),
                    'notes': row.get('line_notes', ''),
                })
                
                imported += 1
                
            except Exception as e:
                errors += 1
                messages.append(f"Row error: {str(e)}")
                if not self.skip_errors:
                    raise
        
        message = f"Imported: {imported}\nErrors: {errors}\n" + '\n'.join(messages[:10])
        return {'imported': imported, 'errors': errors, 'message': message}

    def _import_deliveries(self, data):
        """Import deliveries"""
        imported = 0
        errors = 0
        messages = []
        
        for row in data:
            try:
                # Get or create delivery
                origin = row.get('origin', 'EDI Import')
                delivery = self.env['wms.delivery'].search([
                    ('origin', '=', origin),
                    ('state', '=', 'draft')
                ], limit=1)
                
                if not delivery:
                    delivery = self.env['wms.delivery'].create({
                        'warehouse_id': self.warehouse_id.id,
                        'origin': origin,
                        'customer_name': row.get('customer_name', ''),
                        'delivery_address': row.get('delivery_address', ''),
                        'notes': row.get('notes', ''),
                    })
                
                # Find product
                product = self._find_product(row.get('product'))
                if not product:
                    raise ValueError(f"Product not found: {row.get('product')}")
                
                # Create line
                self.env['wms.delivery.line'].create({
                    'delivery_id': delivery.id,
                    'product_id': product.id,
                    'ordered_qty': float(row.get('quantity', 0)),
                    'notes': row.get('line_notes', ''),
                })
                
                imported += 1
                
            except Exception as e:
                errors += 1
                messages.append(f"Row error: {str(e)}")
                if not self.skip_errors:
                    raise
        
        message = f"Imported: {imported}\nErrors: {errors}\n" + '\n'.join(messages[:10])
        return {'imported': imported, 'errors': errors, 'message': message}

    def _import_products(self, data):
        """Import products"""
        imported = 0
        errors = 0
        messages = []
        
        for row in data:
            try:
                vals = {
                    'name': row.get('name', row.get('product_name')),
                    'default_code': row.get('default_code', row.get('product_code')),
                    'barcode': row.get('barcode', ''),
                    'type': 'product',
                    'list_price': float(row.get('list_price', 0)),
                    'standard_price': float(row.get('standard_price', 0)),
                }
                
                # Check if exists
                existing = self.env['product.product'].search([
                    ('default_code', '=', vals['default_code'])
                ], limit=1)
                
                if existing:
                    existing.write(vals)
                else:
                    self.env['product.product'].create(vals)
                
                imported += 1
                
            except Exception as e:
                errors += 1
                messages.append(f"Row error: {str(e)}")
                if not self.skip_errors:
                    raise
        
        message = f"Imported: {imported}\nErrors: {errors}\n" + '\n'.join(messages[:10])
        return {'imported': imported, 'errors': errors, 'message': message}

    def _import_locations(self, data):
        """Import locations"""
        imported = 0
        errors = 0
        messages = []
        
        for row in data:
            try:
                vals = {
                    'name': row.get('name'),
                    'code': row.get('code'),
                    'barcode': row.get('barcode', ''),
                    'warehouse_id': self.warehouse_id.id,
                    'location_type': row.get('location_type', 'storage'),
                    'capacity': float(row.get('capacity', 0)),
                }
                
                # Check if exists
                existing = self.env['wms.location'].search([
                    ('code', '=', vals['code']),
                    ('warehouse_id', '=', self.warehouse_id.id)
                ], limit=1)
                
                if existing:
                    existing.write(vals)
                else:
                    self.env['wms.location'].create(vals)
                
                imported += 1
                
            except Exception as e:
                errors += 1
                messages.append(f"Row error: {str(e)}")
                if not self.skip_errors:
                    raise
        
        message = f"Imported: {imported}\nErrors: {errors}\n" + '\n'.join(messages[:10])
        return {'imported': imported, 'errors': errors, 'message': message}

    def _find_product(self, value):
        """Find product by configured field"""
        if not value:
            return None
        
        return self.env['product.product'].search([
            (self.product_field, '=', value)
        ], limit=1)

    def _find_location(self, value):
        """Find location by configured field"""
        if not value:
            return None
        
        return self.env['wms.location'].search([
            (self.location_field, '=', value),
            ('warehouse_id', '=', self.warehouse_id.id)
        ], limit=1)
