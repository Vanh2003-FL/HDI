from odoo import models, fields, api
from odoo.exceptions import UserError
import base64
import csv
import json
import xlsxwriter
from io import BytesIO, StringIO
import logging

_logger = logging.getLogger(__name__)


class EdiExportWizard(models.TransientModel):
    _name = 'edi.export.wizard'
    _description = 'EDI Export Wizard'

    export_format = fields.Selection([
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xml', 'XML'),
        ('excel', 'Excel'),
    ], string='Export Format', required=True, default='excel')
    
    export_type = fields.Selection([
        ('receipt', 'Receipts'),
        ('delivery', 'Deliveries'),
        ('stock', 'Stock Levels'),
        ('movement', 'Stock Movements'),
    ], string='Export Type', required=True, default='stock')
    
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse')
    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To', default=fields.Date.today)
    
    # Filters
    state = fields.Selection([
        ('all', 'All States'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
    ], string='State', default='all')
    
    # Results
    file_data = fields.Binary(string='File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)
    record_count = fields.Integer(string='Records Exported', readonly=True)

    def action_export(self):
        """Export data to file"""
        self.ensure_one()
        
        try:
            # Get data
            if self.export_type == 'receipt':
                data = self._get_receipts()
            elif self.export_type == 'delivery':
                data = self._get_deliveries()
            elif self.export_type == 'stock':
                data = self._get_stock()
            elif self.export_type == 'movement':
                data = self._get_movements()
            else:
                raise UserError('Unsupported export type')
            
            # Generate file
            if self.export_format == 'csv':
                file_data, file_name = self._generate_csv(data)
            elif self.export_format == 'json':
                file_data, file_name = self._generate_json(data)
            elif self.export_format == 'xml':
                file_data, file_name = self._generate_xml(data)
            elif self.export_format == 'excel':
                file_data, file_name = self._generate_excel(data)
            else:
                raise UserError('Unsupported export format')
            
            self.write({
                'file_data': file_data,
                'file_name': file_name,
                'record_count': len(data),
            })
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'edi.export.wizard',
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(f'Export failed: {str(e)}')

    def _get_receipts(self):
        """Get receipt data"""
        domain = []
        
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        
        receipts = self.env['wms.receipt'].search(domain)
        
        data = []
        for receipt in receipts:
            for line in receipt.line_ids:
                data.append({
                    'receipt_number': receipt.name,
                    'warehouse': receipt.warehouse_id.name,
                    'origin': receipt.origin,
                    'state': receipt.state,
                    'date': receipt.create_date.strftime('%Y-%m-%d'),
                    'product_code': line.product_id.default_code or '',
                    'product_name': line.product_id.name,
                    'ordered_qty': line.ordered_qty,
                    'received_qty': line.received_qty,
                    'uom': line.product_uom_id.name,
                })
        
        return data

    def _get_deliveries(self):
        """Get delivery data"""
        domain = []
        
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        
        deliveries = self.env['wms.delivery'].search(domain)
        
        data = []
        for delivery in deliveries:
            for line in delivery.line_ids:
                data.append({
                    'delivery_number': delivery.name,
                    'warehouse': delivery.warehouse_id.name,
                    'customer': delivery.customer_name,
                    'origin': delivery.origin,
                    'state': delivery.state,
                    'date': delivery.create_date.strftime('%Y-%m-%d'),
                    'product_code': line.product_id.default_code or '',
                    'product_name': line.product_id.name,
                    'ordered_qty': line.ordered_qty,
                    'shipped_qty': line.shipped_qty,
                    'uom': line.product_uom_id.name,
                })
        
        return data

    def _get_stock(self):
        """Get stock level data"""
        domain = [('quantity', '>', 0)]
        
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        quants = self.env['wms.stock.quant'].search(domain)
        
        data = []
        for quant in quants:
            data.append({
                'warehouse': quant.warehouse_id.name,
                'location_code': quant.location_id.code,
                'location_name': quant.location_id.name,
                'product_code': quant.product_id.default_code or '',
                'product_name': quant.product_id.name,
                'quantity': quant.quantity,
                'available_quantity': quant.available_quantity,
                'reserved_quantity': quant.reserved_quantity,
                'status': quant.status,
                'uom': quant.product_uom_id.name,
            })
        
        return data

    def _get_movements(self):
        """Get stock movement data"""
        domain = []
        
        if self.warehouse_id:
            domain.append(('warehouse_id', '=', self.warehouse_id.id))
        
        if self.date_from:
            domain.append(('create_date', '>=', self.date_from))
        
        if self.date_to:
            domain.append(('create_date', '<=', self.date_to))
        
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        
        moves = self.env['wms.stock.move'].search(domain)
        
        data = []
        for move in moves:
            data.append({
                'move_number': move.name,
                'warehouse': move.warehouse_id.name if move.warehouse_id else '',
                'move_type': move.move_type,
                'state': move.state,
                'date': move.create_date.strftime('%Y-%m-%d %H:%M:%S'),
                'product_code': move.product_id.default_code or '',
                'product_name': move.product_id.name,
                'quantity': move.quantity,
                'location_from': move.location_from_id.name,
                'location_to': move.location_to_id.name,
                'origin': move.origin or '',
                'uom': move.product_uom_id.name,
            })
        
        return data

    def _generate_csv(self, data):
        """Generate CSV file"""
        if not data:
            raise UserError('No data to export')
        
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
        
        file_data = base64.b64encode(output.getvalue().encode('utf-8'))
        file_name = f'{self.export_type}_{fields.Date.today().strftime("%Y%m%d")}.csv'
        
        return file_data, file_name

    def _generate_json(self, data):
        """Generate JSON file"""
        json_data = json.dumps(data, indent=2, default=str)
        file_data = base64.b64encode(json_data.encode('utf-8'))
        file_name = f'{self.export_type}_{fields.Date.today().strftime("%Y%m%d")}.json'
        
        return file_data, file_name

    def _generate_xml(self, data):
        """Generate XML file"""
        import xml.etree.ElementTree as ET
        
        root = ET.Element('export')
        root.set('type', self.export_type)
        root.set('date', fields.Date.today().strftime('%Y-%m-%d'))
        
        for row in data:
            item = ET.SubElement(root, 'item')
            for key, value in row.items():
                field = ET.SubElement(item, key)
                field.text = str(value)
        
        xml_string = ET.tostring(root, encoding='utf-8')
        file_data = base64.b64encode(xml_string)
        file_name = f'{self.export_type}_{fields.Date.today().strftime("%Y%m%d")}.xml'
        
        return file_data, file_name

    def _generate_excel(self, data):
        """Generate Excel file"""
        if not data:
            raise UserError('No data to export')
        
        output = BytesIO()
        workbook = xlsxwriter.Workbook(output)
        worksheet = workbook.add_worksheet(self.export_type.title())
        
        # Formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4CAF50',
            'font_color': 'white',
            'border': 1,
        })
        
        cell_format = workbook.add_format({
            'border': 1,
        })
        
        number_format = workbook.add_format({
            'border': 1,
            'num_format': '#,##0.00',
        })
        
        # Headers
        headers = list(data[0].keys())
        for col, header in enumerate(headers):
            worksheet.write(0, col, header.replace('_', ' ').title(), header_format)
        
        # Data
        for row_idx, row_data in enumerate(data, start=1):
            for col_idx, header in enumerate(headers):
                value = row_data[header]
                
                # Determine format
                if isinstance(value, (int, float)):
                    worksheet.write(row_idx, col_idx, value, number_format)
                else:
                    worksheet.write(row_idx, col_idx, value, cell_format)
        
        # Auto-width columns
        for col_idx, header in enumerate(headers):
            max_length = len(header)
            for row_data in data:
                max_length = max(max_length, len(str(row_data[header])))
            worksheet.set_column(col_idx, col_idx, min(max_length + 2, 50))
        
        workbook.close()
        output.seek(0)
        
        file_data = base64.b64encode(output.read())
        file_name = f'{self.export_type}_{fields.Date.today().strftime("%Y%m%d")}.xlsx'
        
        return file_data, file_name
