# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io


class InventoryValuationWizard(models.TransientModel):
    _name = 'inventory.valuation.wizard'
    _description = 'Inventory Valuation Report'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    as_of_date = fields.Date(
        string='As of Date',
        required=True,
        default=fields.Date.today
    )
    
    location_ids = fields.Many2many(
        'wms.location',
        string='Locations',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Leave empty for all locations'
    )
    
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Leave empty for all categories'
    )
    
    valuation_method = fields.Selection([
        ('standard', 'Standard Price'),
        ('average', 'Average Cost'),
        ('fifo', 'FIFO Cost')
    ], string='Valuation Method', required=True, default='standard')
    
    status_filter = fields.Selection([
        ('all', 'All Status'),
        ('available', 'Available Only'),
        ('reserved', 'Reserved Only'),
        ('quarantine', 'Quarantine'),
        ('damaged', 'Damaged')
    ], string='Stock Status', required=True, default='all')
    
    group_by = fields.Selection([
        ('product', 'By Product'),
        ('category', 'By Category'),
        ('location', 'By Location')
    ], string='Group By', required=True, default='product')
    
    show_zero_stock = fields.Boolean(
        string='Show Zero Stock',
        default=False
    )
    
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Filename', readonly=True)

    def action_generate_report(self):
        """Generate inventory valuation report"""
        self.ensure_one()
        return self._generate_excel_report()

    def _get_valuation_data(self):
        """Get inventory valuation data"""
        domain = [
            ('warehouse_id', '=', self.warehouse_id.id),
        ]
        
        if not self.show_zero_stock:
            domain.append(('quantity', '>', 0))
        else:
            domain.append(('quantity', '>=', 0))
        
        if self.location_ids:
            domain.append(('location_id', 'in', self.location_ids.ids))
        
        if self.status_filter != 'all':
            domain.append(('status', '=', self.status_filter))
        
        quants = self.env['wms.stock.quant'].search(domain)
        
        # Filter by category if needed
        if self.category_ids:
            quants = quants.filtered(lambda q: q.product_id.categ_id in self.category_ids)
        
        data = []
        for quant in quants:
            # Calculate unit cost based on method
            if self.valuation_method == 'standard':
                unit_cost = quant.product_id.standard_price
            elif self.valuation_method == 'average':
                # Could implement average cost calculation
                unit_cost = quant.product_id.standard_price  # Fallback
            else:  # fifo
                # Could implement FIFO cost calculation
                unit_cost = quant.product_id.standard_price  # Fallback
            
            total_value = quant.quantity * unit_cost
            
            data.append({
                'product_id': quant.product_id.id,
                'product_code': quant.product_id.default_code or '',
                'product_name': quant.product_id.name,
                'category': quant.product_id.categ_id.complete_name,
                'location': quant.location_id.complete_name,
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'reserved_quantity': quant.reserved_quantity,
                'available_quantity': quant.available_quantity,
                'unit_cost': unit_cost,
                'total_value': total_value,
                'status': dict(self.env['wms.stock.quant']._fields['status'].selection).get(quant.status, ''),
                'uom': quant.product_id.uom_id.name,
            })
        
        return data

    def _generate_excel_report(self):
        """Generate Excel report"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        
        data = self._get_valuation_data()
        
        if not data:
            raise UserError(_('No inventory data found.'))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Inventory Valuation')
        
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
        currency_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        
        # Title
        worksheet.merge_range('A1:M1', f'INVENTORY VALUATION REPORT - {self.warehouse_id.name}', title_format)
        worksheet.merge_range('A2:M2', f'As of {self.as_of_date.strftime("%d/%m/%Y")}', header_format)
        
        # Headers
        row = 3
        headers = ['Product Code', 'Product Name', 'Category', 'Location', 'Lot/Serial',
                   'On Hand', 'Reserved', 'Available', 'UOM', 'Unit Cost', 'Total Value', 'Status']
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        
        # Data
        row += 1
        total_value = 0
        total_qty = 0
        
        for item in data:
            worksheet.write(row, 0, item['product_code'], cell_format)
            worksheet.write(row, 1, item['product_name'], cell_format)
            worksheet.write(row, 2, item['category'], cell_format)
            worksheet.write(row, 3, item['location'], cell_format)
            worksheet.write(row, 4, item['lot_name'], cell_format)
            worksheet.write(row, 5, item['quantity'], number_format)
            worksheet.write(row, 6, item['reserved_quantity'], number_format)
            worksheet.write(row, 7, item['available_quantity'], number_format)
            worksheet.write(row, 8, item['uom'], cell_format)
            worksheet.write(row, 9, item['unit_cost'], currency_format)
            worksheet.write(row, 10, item['total_value'], currency_format)
            worksheet.write(row, 11, item['status'], cell_format)
            
            total_value += item['total_value']
            total_qty += item['quantity']
            
            row += 1
        
        # Summary
        row += 1
        worksheet.merge_range(row, 0, row, 4, 'TOTAL', header_format)
        worksheet.write(row, 5, total_qty, header_format)
        worksheet.write(row, 10, total_value, header_format)
        
        # Statistics
        row += 3
        worksheet.merge_range(row, 0, row, 1, 'VALUATION SUMMARY', header_format)
        row += 1
        
        # By status
        status_summary = {}
        for item in data:
            status = item['status']
            if status not in status_summary:
                status_summary[status] = {'qty': 0, 'value': 0}
            status_summary[status]['qty'] += item['quantity']
            status_summary[status]['value'] += item['total_value']
        
        worksheet.write(row, 0, 'Status', header_format)
        worksheet.write(row, 1, 'Quantity', header_format)
        worksheet.write(row, 2, 'Total Value', header_format)
        
        for status, values in status_summary.items():
            row += 1
            worksheet.write(row, 0, status, cell_format)
            worksheet.write(row, 1, values['qty'], number_format)
            worksheet.write(row, 2, values['value'], currency_format)
        
        # Adjust columns
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 25)
        worksheet.set_column('E:E', 15)
        worksheet.set_column('F:H', 12)
        worksheet.set_column('I:I', 8)
        worksheet.set_column('J:K', 15)
        worksheet.set_column('L:L', 12)
        
        workbook.close()
        output.seek(0)
        
        filename = f'Inventory_Valuation_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=inventory.valuation.wizard&id={self.id}&field=excel_file&filename={filename}&download=true',
            'target': 'new',
        }
