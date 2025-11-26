# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io


class StockMovementReportWizard(models.TransientModel):
    _name = 'stock.movement.report.wizard'
    _description = 'Stock Movement History Report'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    date_from = fields.Date(
        string='Date From',
        required=True
    )
    
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Leave empty for all products'
    )
    
    location_ids = fields.Many2many(
        'wms.location',
        string='Locations',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Source or destination locations'
    )
    
    move_type = fields.Selection([
        ('all', 'All Movements'),
        ('receipt', 'Receipts'),
        ('delivery', 'Deliveries'),
        ('transfer', 'Transfers'),
        ('adjustment', 'Adjustments')
    ], string='Movement Type', required=True, default='all')
    
    state = fields.Selection([
        ('all', 'All States'),
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('assigned', 'Assigned'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='State', required=True, default='done')
    
    group_by = fields.Selection([
        ('date', 'By Date'),
        ('product', 'By Product'),
        ('location', 'By Location'),
        ('move_type', 'By Movement Type')
    ], string='Group By', required=True, default='date')
    
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Filename', readonly=True)

    def action_generate_report(self):
        """Generate stock movement report"""
        self.ensure_one()
        return self._generate_excel_report()

    def _get_movement_data(self):
        """Get stock movements"""
        domain = [
            ('date', '>=', self.date_from),
            ('date', '<=', self.date_to),
        ]
        
        if self.state != 'all':
            domain.append(('state', '=', self.state))
        
        if self.move_type != 'all':
            domain.append(('move_type', '=', self.move_type))
        
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        if self.location_ids:
            domain.extend([
                '|',
                ('location_id', 'in', self.location_ids.ids),
                ('location_dest_id', 'in', self.location_ids.ids)
            ])
        
        # Filter by warehouse
        warehouse_location_ids = self.env['wms.location'].search([
            ('warehouse_id', '=', self.warehouse_id.id)
        ]).ids
        
        domain.extend([
            '|',
            ('location_id', 'in', warehouse_location_ids),
            ('location_dest_id', 'in', warehouse_location_ids)
        ])
        
        moves = self.env['wms.stock.move'].search(domain, order='date, id')
        
        data = []
        for move in moves:
            data.append({
                'date': move.date,
                'name': move.name,
                'product_code': move.product_id.default_code or '',
                'product_name': move.product_id.name,
                'quantity': move.product_uom_qty,
                'uom': move.product_id.uom_id.name,
                'location_from': move.location_id.complete_name if move.location_id else '',
                'location_to': move.location_dest_id.complete_name if move.location_dest_id else '',
                'move_type': dict(self.env['wms.stock.move']._fields['move_type'].selection).get(move.move_type, ''),
                'state': dict(self.env['wms.stock.move']._fields['state'].selection).get(move.state, ''),
                'origin': move.origin or '',
                'lot_name': move.lot_id.name if move.lot_id else '',
            })
        
        return data

    def _generate_excel_report(self):
        """Generate Excel report"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        
        data = self._get_movement_data()
        
        if not data:
            raise UserError(_('No movements found for the selected criteria.'))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Movements')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center',
            'bg_color': '#4472C4', 'font_color': 'white'
        })
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'bg_color': '#D9E1F2', 'border': 1
        })
        cell_format = workbook.add_format({'border': 1})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy hh:mm'})
        
        # Title
        worksheet.merge_range('A1:L1', f'STOCK MOVEMENT REPORT - {self.warehouse_id.name}', title_format)
        worksheet.merge_range('A2:L2', f'{self.date_from.strftime("%d/%m/%Y")} - {self.date_to.strftime("%d/%m/%Y")}', header_format)
        
        # Headers
        row = 3
        headers = ['Date', 'Reference', 'Product Code', 'Product Name', 'Lot/Serial',
                   'Quantity', 'UOM', 'From Location', 'To Location', 'Move Type', 'Status', 'Origin']
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        
        # Data
        row += 1
        for item in data:
            worksheet.write(row, 0, item['date'].strftime('%d/%m/%Y %H:%M') if item['date'] else '', cell_format)
            worksheet.write(row, 1, item['name'], cell_format)
            worksheet.write(row, 2, item['product_code'], cell_format)
            worksheet.write(row, 3, item['product_name'], cell_format)
            worksheet.write(row, 4, item['lot_name'], cell_format)
            worksheet.write(row, 5, item['quantity'], number_format)
            worksheet.write(row, 6, item['uom'], cell_format)
            worksheet.write(row, 7, item['location_from'], cell_format)
            worksheet.write(row, 8, item['location_to'], cell_format)
            worksheet.write(row, 9, item['move_type'], cell_format)
            worksheet.write(row, 10, item['state'], cell_format)
            worksheet.write(row, 11, item['origin'], cell_format)
            row += 1
        
        # Summary
        row += 1
        worksheet.merge_range(row, 0, row, 4, 'TOTAL MOVEMENTS', header_format)
        worksheet.write(row, 5, len(data), header_format)
        
        # Adjust columns
        worksheet.set_column('A:A', 18)
        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:F', 12)
        worksheet.set_column('G:G', 8)
        worksheet.set_column('H:I', 25)
        worksheet.set_column('J:K', 15)
        worksheet.set_column('L:L', 20)
        
        workbook.close()
        output.seek(0)
        
        filename = f'Stock_Movement_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=stock.movement.report.wizard&id={self.id}&field=excel_file&filename={filename}&download=true',
            'target': 'new',
        }
