# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io


class AbcAnalysisWizard(models.TransientModel):
    _name = 'abc.analysis.wizard'
    _description = 'ABC Analysis Wizard'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    date_from = fields.Date(
        string='Date From',
        required=True,
        default=lambda self: fields.Date.today().replace(day=1)
    )
    
    date_to = fields.Date(
        string='Date To',
        required=True,
        default=fields.Date.today
    )
    
    analysis_type = fields.Selection([
        ('value', 'By Value (Revenue)'),
        ('quantity', 'By Quantity (Units Sold)'),
        ('movement', 'By Movement Frequency')
    ], string='Analysis Type', required=True, default='value')
    
    category_ids = fields.Many2many(
        'product.category',
        string='Product Categories',
        help='Leave empty for all categories'
    )
    
    class_a_percent = fields.Float(
        string='Class A (%)',
        default=80.0,
        help='Top products contributing to this % of total value'
    )
    
    class_b_percent = fields.Float(
        string='Class B (%)',
        default=15.0,
        help='Next products contributing to this % of total value'
    )
    
    # Class C is automatically remaining %
    
    update_product_classification = fields.Boolean(
        string='Update Product ABC Classification',
        default=False,
        help='Update abc_classification field on products'
    )
    
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Filename', readonly=True)

    @api.constrains('class_a_percent', 'class_b_percent')
    def _check_percentages(self):
        for wizard in self:
            if wizard.class_a_percent + wizard.class_b_percent >= 100:
                raise UserError(_('Sum of Class A and Class B must be less than 100%'))

    def action_generate_report(self):
        """Generate ABC analysis report"""
        self.ensure_one()
        return self._generate_excel_report()

    def _get_product_data(self):
        """Get product data based on analysis type"""
        
        # Build product domain
        product_domain = [('type', '=', 'product')]
        if self.category_ids:
            product_domain.append(('categ_id', 'in', self.category_ids.ids))
        
        products = self.env['product.product'].search(product_domain)
        
        if not products:
            raise UserError(_('No products found for the selected criteria.'))
        
        data = []
        
        if self.analysis_type == 'value':
            # Calculate revenue from deliveries
            for product in products:
                deliveries = self.env['wms.delivery.line'].search([
                    ('product_id', '=', product.id),
                    ('delivery_id.warehouse_id', '=', self.warehouse_id.id),
                    ('delivery_id.date', '>=', self.date_from),
                    ('delivery_id.date', '<=', self.date_to),
                    ('delivery_id.state', '=', 'done')
                ])
                
                total_qty = sum(deliveries.mapped('delivered_qty'))
                total_value = total_qty * product.standard_price  # Could use lst_price for revenue
                
                if total_value > 0 or total_qty > 0:
                    data.append({
                        'product_id': product.id,
                        'product_code': product.default_code or '',
                        'product_name': product.name,
                        'category': product.categ_id.name,
                        'quantity': total_qty,
                        'unit_price': product.standard_price,
                        'total_value': total_value,
                        'uom': product.uom_id.name,
                    })
        
        elif self.analysis_type == 'quantity':
            # Calculate total quantity moved
            for product in products:
                moves = self.env['wms.stock.move'].search([
                    ('product_id', '=', product.id),
                    ('location_dest_id.warehouse_id', '=', self.warehouse_id.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done'),
                    ('move_type', '=', 'delivery')
                ])
                
                total_qty = sum(moves.mapped('product_uom_qty'))
                
                if total_qty > 0:
                    data.append({
                        'product_id': product.id,
                        'product_code': product.default_code or '',
                        'product_name': product.name,
                        'category': product.categ_id.name,
                        'quantity': total_qty,
                        'unit_price': product.standard_price,
                        'total_value': total_qty * product.standard_price,
                        'uom': product.uom_id.name,
                    })
        
        else:  # movement frequency
            # Count number of movements
            for product in products:
                move_count = self.env['wms.stock.move'].search_count([
                    ('product_id', '=', product.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to),
                    ('state', '=', 'done')
                ])
                
                if move_count > 0:
                    data.append({
                        'product_id': product.id,
                        'product_code': product.default_code or '',
                        'product_name': product.name,
                        'category': product.categ_id.name,
                        'quantity': move_count,
                        'unit_price': 0,
                        'total_value': move_count,  # Use count as value
                        'uom': 'movements',
                    })
        
        if not data:
            raise UserError(_('No data found for the selected period.'))
        
        # Sort by total value descending
        data.sort(key=lambda x: x['total_value'], reverse=True)
        
        # Calculate cumulative percentages and assign ABC class
        total_value = sum(item['total_value'] for item in data)
        cumulative = 0
        
        for item in data:
            cumulative += item['total_value']
            cumulative_percent = (cumulative / total_value * 100) if total_value > 0 else 0
            
            if cumulative_percent <= self.class_a_percent:
                abc_class = 'a'
            elif cumulative_percent <= (self.class_a_percent + self.class_b_percent):
                abc_class = 'b'
            else:
                abc_class = 'c'
            
            item['cumulative_value'] = cumulative
            item['cumulative_percent'] = cumulative_percent
            item['percent_of_total'] = (item['total_value'] / total_value * 100) if total_value > 0 else 0
            item['abc_class'] = abc_class
        
        return data

    def _generate_excel_report(self):
        """Generate Excel ABC analysis report"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        
        data = self._get_product_data()
        
        # Update product classifications if requested
        if self.update_product_classification:
            for item in data:
                product = self.env['product.product'].browse(item['product_id'])
                product.write({'abc_classification': item['abc_class']})
        
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('ABC Analysis')
        
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
        percent_format = workbook.add_format({'border': 1, 'num_format': '0.00%'})
        
        class_a_format = workbook.add_format({'border': 1, 'bg_color': '#C6EFCE'})  # Green
        class_b_format = workbook.add_format({'border': 1, 'bg_color': '#FFEB9C'})  # Yellow
        class_c_format = workbook.add_format({'border': 1, 'bg_color': '#FFC7CE'})  # Red
        
        # Title
        worksheet.merge_range('A1:J1', f'ABC ANALYSIS - {self.warehouse_id.name}', title_format)
        worksheet.merge_range('A2:J2', f'{self.date_from.strftime("%d/%m/%Y")} - {self.date_to.strftime("%d/%m/%Y")}', header_format)
        
        # Headers
        row = 3
        headers = ['Product Code', 'Product Name', 'Category', 'Quantity', 'UOM', 
                   'Unit Price', 'Total Value', '% of Total', 'Cumulative %', 'ABC Class']
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        
        # Data
        row += 1
        for item in data:
            # Choose format based on ABC class
            if item['abc_class'] == 'a':
                abc_format = class_a_format
            elif item['abc_class'] == 'b':
                abc_format = class_b_format
            else:
                abc_format = class_c_format
            
            worksheet.write(row, 0, item['product_code'], cell_format)
            worksheet.write(row, 1, item['product_name'], cell_format)
            worksheet.write(row, 2, item['category'], cell_format)
            worksheet.write(row, 3, item['quantity'], number_format)
            worksheet.write(row, 4, item['uom'], cell_format)
            worksheet.write(row, 5, item['unit_price'], number_format)
            worksheet.write(row, 6, item['total_value'], number_format)
            worksheet.write(row, 7, item['percent_of_total'] / 100, percent_format)
            worksheet.write(row, 8, item['cumulative_percent'] / 100, percent_format)
            worksheet.write(row, 9, item['abc_class'].upper(), abc_format)
            
            row += 1
        
        # Summary
        row += 2
        class_counts = {'a': 0, 'b': 0, 'c': 0}
        class_values = {'a': 0, 'b': 0, 'c': 0}
        
        for item in data:
            class_counts[item['abc_class']] += 1
            class_values[item['abc_class']] += item['total_value']
        
        total_value = sum(class_values.values())
        
        worksheet.merge_range(row, 0, row, 1, 'SUMMARY', header_format)
        row += 1
        
        worksheet.write(row, 0, 'Class', header_format)
        worksheet.write(row, 1, 'Product Count', header_format)
        worksheet.write(row, 2, '% of Products', header_format)
        worksheet.write(row, 3, 'Total Value', header_format)
        worksheet.write(row, 4, '% of Value', header_format)
        
        for abc_class in ['a', 'b', 'c']:
            row += 1
            fmt = class_a_format if abc_class == 'a' else (class_b_format if abc_class == 'b' else class_c_format)
            
            worksheet.write(row, 0, abc_class.upper(), fmt)
            worksheet.write(row, 1, class_counts[abc_class], number_format)
            worksheet.write(row, 2, class_counts[abc_class] / len(data), percent_format)
            worksheet.write(row, 3, class_values[abc_class], number_format)
            worksheet.write(row, 4, class_values[abc_class] / total_value if total_value > 0 else 0, percent_format)
        
        # Adjust columns
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 12)
        worksheet.set_column('E:E', 8)
        worksheet.set_column('F:G', 15)
        worksheet.set_column('H:I', 12)
        worksheet.set_column('J:J', 10)
        
        workbook.close()
        output.seek(0)
        
        filename = f'ABC_Analysis_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=abc.analysis.wizard&id={self.id}&field=excel_file&filename={filename}&download=true',
            'target': 'new',
        }
