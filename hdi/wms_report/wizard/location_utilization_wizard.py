# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import io


class LocationUtilizationWizard(models.TransientModel):
    _name = 'location.utilization.wizard'
    _description = 'Location Capacity Utilization Report'

    warehouse_id = fields.Many2one(
        'wms.warehouse',
        string='Warehouse',
        required=True
    )
    
    location_type_ids = fields.Many2many(
        'wms.location.type',
        string='Location Types',
        help='Leave empty for all types'
    )
    
    zone_ids = fields.Many2many(
        'wms.zone',
        string='Zones',
        domain="[('warehouse_id', '=', warehouse_id)]",
        help='Leave empty for all zones'
    )
    
    utilization_threshold = fields.Selection([
        ('all', 'All Locations'),
        ('below_50', 'Below 50%'),
        ('50_to_80', '50% to 80%'),
        ('80_to_90', '80% to 90%'),
        ('above_90', 'Above 90%'),
        ('full', '100% Full')
    ], string='Utilization Threshold', required=True, default='all')
    
    include_blocked = fields.Boolean(
        string='Include Blocked Locations',
        default=False
    )
    
    excel_file = fields.Binary(string='Excel File', readonly=True)
    excel_filename = fields.Char(string='Filename', readonly=True)

    def action_generate_report(self):
        """Generate location utilization report"""
        self.ensure_one()
        return self._generate_excel_report()

    def _get_location_data(self):
        """Get location utilization data"""
        domain = [
            ('warehouse_id', '=', self.warehouse_id.id),
        ]
        
        if self.location_type_ids:
            domain.append(('location_type_id', 'in', self.location_type_ids.ids))
        
        if self.zone_ids:
            domain.append(('zone_id', 'in', self.zone_ids.ids))
        
        if not self.include_blocked:
            domain.append(('status', '!=', 'blocked'))
        
        locations = self.env['wms.location'].search(domain, order='complete_name')
        
        data = []
        for location in locations:
            capacity_percent = location.capacity_percentage
            
            # Apply threshold filter
            if self.utilization_threshold == 'below_50' and capacity_percent >= 50:
                continue
            elif self.utilization_threshold == '50_to_80' and (capacity_percent < 50 or capacity_percent > 80):
                continue
            elif self.utilization_threshold == '80_to_90' and (capacity_percent < 80 or capacity_percent > 90):
                continue
            elif self.utilization_threshold == 'above_90' and capacity_percent <= 90:
                continue
            elif self.utilization_threshold == 'full' and capacity_percent < 100:
                continue
            
            # Count products in location
            product_count = self.env['wms.stock.quant'].search_count([
                ('location_id', '=', location.id),
                ('quantity', '>', 0)
            ])
            
            # Get total stock quantity
            quants = self.env['wms.stock.quant'].search([
                ('location_id', '=', location.id),
                ('quantity', '>', 0)
            ])
            
            total_qty = sum(quants.mapped('quantity'))
            
            data.append({
                'location_code': location.barcode or location.name,
                'location_name': location.complete_name,
                'location_type': location.location_type_id.name,
                'zone': location.zone_id.name if location.zone_id else '',
                'total_capacity': location.capacity_total,
                'used_capacity': location.capacity_used,
                'available_capacity': location.capacity_available,
                'capacity_percent': capacity_percent,
                'status': dict(self.env['wms.location']._fields['status'].selection).get(location.status, ''),
                'product_count': product_count,
                'total_qty': total_qty,
                'allow_mixed': 'Yes' if location.allow_mixed_products else 'No',
            })
        
        return data

    def _generate_excel_report(self):
        """Generate Excel report"""
        try:
            import xlsxwriter
        except ImportError:
            raise UserError(_('Please install xlsxwriter: pip install xlsxwriter'))
        
        data = self._get_location_data()
        
        if not data:
            raise UserError(_('No locations found for the selected criteria.'))
        
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        worksheet = workbook.add_worksheet('Location Utilization')
        
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
        
        # Conditional formats
        green_format = workbook.add_format({'border': 1, 'bg_color': '#C6EFCE', 'num_format': '0.00%'})
        yellow_format = workbook.add_format({'border': 1, 'bg_color': '#FFEB9C', 'num_format': '0.00%'})
        orange_format = workbook.add_format({'border': 1, 'bg_color': '#FFC000', 'num_format': '0.00%'})
        red_format = workbook.add_format({'border': 1, 'bg_color': '#FFC7CE', 'num_format': '0.00%'})
        
        # Title
        worksheet.merge_range('A1:M1', f'LOCATION CAPACITY UTILIZATION - {self.warehouse_id.name}', title_format)
        worksheet.merge_range('A2:M2', f'Generated on {datetime.now().strftime("%d/%m/%Y %H:%M")}', header_format)
        
        # Headers
        row = 3
        headers = ['Location Code', 'Location Name', 'Type', 'Zone', 'Total Capacity',
                   'Used', 'Available', 'Utilization %', 'Status', 'Product Count', 
                   'Total Qty', 'Allow Mixed']
        
        for col, header in enumerate(headers):
            worksheet.write(row, col, header, header_format)
        
        # Data
        row += 1
        for item in data:
            # Choose format based on utilization
            util_percent = item['capacity_percent'] / 100
            if util_percent < 0.5:
                util_format = green_format
            elif util_percent < 0.8:
                util_format = yellow_format
            elif util_percent < 0.9:
                util_format = orange_format
            else:
                util_format = red_format
            
            worksheet.write(row, 0, item['location_code'], cell_format)
            worksheet.write(row, 1, item['location_name'], cell_format)
            worksheet.write(row, 2, item['location_type'], cell_format)
            worksheet.write(row, 3, item['zone'], cell_format)
            worksheet.write(row, 4, item['total_capacity'], number_format)
            worksheet.write(row, 5, item['used_capacity'], number_format)
            worksheet.write(row, 6, item['available_capacity'], number_format)
            worksheet.write(row, 7, util_percent, util_format)
            worksheet.write(row, 8, item['status'], cell_format)
            worksheet.write(row, 9, item['product_count'], number_format)
            worksheet.write(row, 10, item['total_qty'], number_format)
            worksheet.write(row, 11, item['allow_mixed'], cell_format)
            
            row += 1
        
        # Summary
        row += 2
        worksheet.merge_range(row, 0, row, 1, 'SUMMARY', header_format)
        row += 1
        
        # Utilization breakdown
        util_ranges = {
            'Below 50%': (0, 50),
            '50% - 80%': (50, 80),
            '80% - 90%': (80, 90),
            'Above 90%': (90, 100),
            '100% Full': (100, 100)
        }
        
        worksheet.write(row, 0, 'Utilization Range', header_format)
        worksheet.write(row, 1, 'Location Count', header_format)
        worksheet.write(row, 2, 'Avg Utilization', header_format)
        
        for range_name, (min_val, max_val) in util_ranges.items():
            row += 1
            if max_val == 100 and min_val == 100:
                filtered = [d for d in data if d['capacity_percent'] == 100]
            else:
                filtered = [d for d in data if min_val <= d['capacity_percent'] < max_val]
            
            count = len(filtered)
            avg_util = sum(d['capacity_percent'] for d in filtered) / count if count > 0 else 0
            
            worksheet.write(row, 0, range_name, cell_format)
            worksheet.write(row, 1, count, number_format)
            worksheet.write(row, 2, avg_util / 100, percent_format)
        
        # Overall stats
        row += 2
        total_locations = len(data)
        avg_utilization = sum(d['capacity_percent'] for d in data) / total_locations if total_locations > 0 else 0
        total_capacity = sum(d['total_capacity'] for d in data)
        total_used = sum(d['used_capacity'] for d in data)
        
        worksheet.write(row, 0, 'Total Locations:', header_format)
        worksheet.write(row, 1, total_locations, number_format)
        row += 1
        worksheet.write(row, 0, 'Average Utilization:', header_format)
        worksheet.write(row, 1, avg_utilization / 100, percent_format)
        row += 1
        worksheet.write(row, 0, 'Total Warehouse Capacity:', header_format)
        worksheet.write(row, 1, total_capacity, number_format)
        row += 1
        worksheet.write(row, 0, 'Total Used:', header_format)
        worksheet.write(row, 1, total_used, number_format)
        
        # Adjust columns
        worksheet.set_column('A:A', 15)
        worksheet.set_column('B:B', 35)
        worksheet.set_column('C:D', 15)
        worksheet.set_column('E:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 12)
        worksheet.set_column('J:K', 12)
        worksheet.set_column('L:L', 12)
        
        workbook.close()
        output.seek(0)
        
        filename = f'Location_Utilization_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
        self.write({
            'excel_file': base64.b64encode(output.read()),
            'excel_filename': filename
        })
        
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content?model=location.utilization.wizard&id={self.id}&field=excel_file&filename={filename}&download=true',
            'target': 'new',
        }
