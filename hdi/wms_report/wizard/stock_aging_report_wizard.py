# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io


class StockAgingReportWizard(models.TransientModel):
    _name = 'stock.aging.report.wizard'
    _description = 'Stock Aging Report Wizard'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    location_ids = fields.Many2many(
        'wms.location',
        string='Locations',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Leave empty for all locations'
    )
    
    product_ids = fields.Many2many(
        'product.product',
        string='Products',
        domain=[('type', '=', 'product')],
        help='Leave empty for all products'
    )
    
    as_of_date = fields.Date(
        string='As of Date',
        required=True,
        default=fields.Date.today
    )
    
    aging_type = fields.Selection([
        ('fifo', 'FIFO (In Date)'),
        ('fefo', 'FEFO (Expiry Date)')
    ], string='Aging Type', required=True, default='fifo')
    
    aging_periods = fields.Selection([
        ('30_60_90', '0-30, 31-60, 61-90, 90+'),
        ('60_120_180', '0-60, 61-120, 121-180, 180+'),
        ('90_180_365', '0-90, 91-180, 181-365, 365+'),
        ('custom', 'Custom Periods')
    ], string='Aging Periods', required=True, default='30_60_90')
    
    custom_period_1 = fields.Integer(string='Period 1 (days)', default=30)
    custom_period_2 = fields.Integer(string='Period 2 (days)', default=60)
    custom_period_3 = fields.Integer(string='Period 3 (days)', default=90)
    
    group_by = fields.Selection([
        ('product', 'Product'),
        ('location', 'Location'),
        ('lot', 'Lot/Serial'),
    ], string='Group By', required=True, default='product')
    
    show_zero_stock = fields.Boolean(
        string='Show Zero Stock',
        default=False
    )
    
    output_format = fields.Selection([
        ('excel', 'Excel'),
        ('pdf', 'PDF')
    ], string='Output Format', required=True, default='excel')
    
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Filename', readonly=True)

    def action_generate_report(self):
        """Generate stock aging report"""
        self.ensure_one()
        
        if self.output_format == 'excel':
            return self._generate_excel_report()
        else:
            return self._generate_pdf_report()

    def _get_aging_periods(self):
        """Get aging period configuration"""
        if self.aging_periods == 'custom':
            return [self.custom_period_1, self.custom_period_2, self.custom_period_3]
        elif self.aging_periods == '30_60_90':
            return [30, 60, 90]
        elif self.aging_periods == '60_120_180':
            return [60, 120, 180]
        else:  # 90_180_365
            return [90, 180, 365]

    def _get_stock_data(self):
        """Get stock quants with aging information"""
        domain = [
            ('warehouse_id', '=', self.warehouse_id.id),
            ('quantity', '>', 0) if not self.show_zero_stock else ('quantity', '>=', 0)
        ]
        
        if self.location_ids:
            domain.append(('location_id', 'in', self.location_ids.ids))
        if self.product_ids:
            domain.append(('product_id', 'in', self.product_ids.ids))
        
        quants = self.env['wms.stock.quant'].search(domain)
        
        # Calculate aging
        data = []
        for quant in quants:
            aging_date = quant.in_date if self.aging_type == 'fifo' else quant.removal_date
            if not aging_date:
                aging_days = 0
            else:
                aging_days = (fields.Date.today() - aging_date.date()).days
            
            data.append({
                'product_id': quant.product_id,
                'product_name': quant.product_id.name,
                'product_code': quant.product_id.default_code or '',
                'location_id': quant.location_id,
                'location_name': quant.location_id.complete_name,
                'lot_id': quant.lot_id,
                'lot_name': quant.lot_id.name if quant.lot_id else '',
                'quantity': quant.quantity,
                'uom': quant.product_id.uom_id.name,
                'in_date': quant.in_date,
                'expiration_date': quant.expiration_date,
                'aging_days': aging_days,
                'status': quant.status,
            })
        
        return data

    def _generate_excel_report(self):
        """Generate Excel report using xlsxwriter"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        
        # Get data
        data = self._get_stock_data()
        
        if not data:
            raise UserError(_('No data found for the selected criteria.'))
        
        # Create Excel file
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Stock Aging Report')
        
        # Formats
        title_format = workbook.add_format({
            'bold': True, 'font_size': 16, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#4472C4', 'font_color': 'white'
        })
        header_format = workbook.add_format({
            'bold': True, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#D9E1F2', 'border': 1
        })
        cell_format = workbook.add_format({'border': 1, 'valign': 'vcenter'})
        number_format = workbook.add_format({'border': 1, 'num_format': '#,##0.00'})
        date_format = workbook.add_format({'border': 1, 'num_format': 'dd/mm/yyyy'})
        
        # Title
        worksheet.merge_range('A1:L1', f'STOCK AGING REPORT - {self.warehouse_id.name}', title_format)
        worksheet.merge_range('A2:L2', f'As of {self.as_of_date.strftime("%d/%m/%Y")}', header_format)
        
        # Headers
        row = 3
        headers = ['Product Code', 'Product Name', 'Location', 'Lot/Serial', 
                   'Quantity', 'UOM', 'In Date', 'Expiry Date', 'Aging Days', 
                   'Status', 'Period 1', 'Period 2']
        
        periods = self._get_aging_periods()
        headers[10] = f'0-{periods[0]} days'
        headers[11] = f'{periods[0]+1}-{periods[1]} days'
        headers.append(f'{periods[1]+1}-{periods[2]} days')
        headers.append(f'{periods[2]+1}+ days')
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        
        # Data rows
        row += 1
        for item in data:
            aging = item['aging_days']
            
            # Determine which period
            period_qty = [0, 0, 0, 0]
            if aging <= periods[0]:
                period_qty[0] = item['quantity']
            elif aging <= periods[1]:
                period_qty[1] = item['quantity']
            elif aging <= periods[2]:
                period_qty[2] = item['quantity']
            else:
                period_qty[3] = item['quantity']
            
            worksheet.write(row, 0, item['product_code'], cell_format)
            worksheet.write(row, 1, item['product_name'], cell_format)
            worksheet.write(row, 2, item['location_name'], cell_format)
            worksheet.write(row, 3, item['lot_name'], cell_format)
            worksheet.write(row, 4, item['quantity'], number_format)
            worksheet.write(row, 5, item['uom'], cell_format)
            worksheet.write(row, 6, item['in_date'].strftime('%d/%m/%Y') if item['in_date'] else '', date_format)
            worksheet.write(row, 7, item['expiration_date'].strftime('%d/%m/%Y') if item['expiration_date'] else '', date_format)
            worksheet.write(row, 8, aging, number_format)
            worksheet.write(row, 9, dict(self.env['wms.stock.quant']._fields['status'].selection).get(item['status'], ''), cell_format)
            worksheet.write(row, 10, period_qty[0], number_format)
            worksheet.write(row, 11, period_qty[1], number_format)
            worksheet.write(row, 12, period_qty[2], number_format)
            worksheet.write(row, 13, period_qty[3], number_format)
            
            row += 1
        
        # Summary
        row += 1
        worksheet.merge_range(row, 0, row, 3, 'TOTAL', header_format)
        for col in range(10, 14):
            formula = f'=SUM({xlsxwriter.utility.xl_col_to_name(col)}5:{xlsxwriter.utility.xl_col_to_name(col)}{row})'
            worksheet.write_formula(row, col, formula, header_format)
        
        # Adjust column widths
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 25)
        worksheet.set_column('D:D', 15)
        worksheet.set_column('E:E', 12)
        worksheet.set_column('F:F', 8)
        worksheet.set_column('G:H', 12)
        worksheet.set_column('I:I', 12)
        worksheet.set_column('J:J', 12)
        worksheet.set_column('K:N', 15)
        
        workbook.close()
        output.seek(0)
        
        # Save to wizard
        filename = f'Stock_Aging_Report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        # Return download action
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=stock.aging.report.wizard&id={self.id}&field=excel_file&filename={filename}&download=true',
            'target': 'new',
        }

    def _generate_pdf_report(self):
        """Generate PDF report (placeholder - would need QWeb report)"""
        raise UserError(_('PDF export will be available in next version. Please use Excel for now.'))
