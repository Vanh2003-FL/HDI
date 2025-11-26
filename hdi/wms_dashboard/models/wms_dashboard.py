# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta


class WmsDashboard(models.Model):
    _name = 'wms.dashboard'
    _description = 'WMS Dashboard'

    name = fields.Char(string='Dashboard Name', default='WMS Dashboard')
    
    # This model is used to provide dashboard data via API
    # No actual records are stored
    
    @api.model
    def get_dashboard_data(self, warehouse_id=None):
        """Get comprehensive dashboard data"""
        
        if not warehouse_id:
            warehouse = self.env['wms.warehouse'].search([], limit=1)
            warehouse_id = warehouse.id if warehouse else None
        
        if not warehouse_id:
            return {'error': 'No warehouse found'}
        
        warehouse = self.env['wms.warehouse'].browse(warehouse_id)
        
        return {
            'warehouse_info': self._get_warehouse_info(warehouse),
            'stock_overview': self._get_stock_overview(warehouse),
            'capacity_data': self._get_capacity_data(warehouse),
            'operations_data': self._get_operations_data(warehouse),
            'alerts': self._get_alerts(warehouse),
            'top_products': self._get_top_products(warehouse),
            'movement_trends': self._get_movement_trends(warehouse),
            'performance_metrics': self._get_performance_metrics(warehouse),
        }
    
    def _get_warehouse_info(self, warehouse):
        """Basic warehouse information"""
        return {
            'id': warehouse.id,
            'name': warehouse.name,
            'code': warehouse.code,
            'zone_count': len(warehouse.zone_ids),
            'location_count': self.env['wms.location'].search_count([('warehouse_id', '=', warehouse.id)]),
        }
    
    def _get_stock_overview(self, warehouse):
        """Current stock levels"""
        quants = self.env['wms.stock.quant'].search([('warehouse_id', '=', warehouse.id)])
        
        total_qty = sum(quants.mapped('quantity'))
        available_qty = sum(quants.mapped('available_quantity'))
        reserved_qty = sum(quants.mapped('reserved_quantity'))
        
        # Count by status
        status_counts = {}
        for status in ['available', 'reserved', 'quarantine', 'damaged']:
            status_quants = quants.filtered(lambda q: q.status == status)
            status_counts[status] = {
                'count': len(status_quants),
                'quantity': sum(status_quants.mapped('quantity'))
            }
        
        # Product count
        product_count = len(set(quants.mapped('product_id').ids))
        
        # Stock value (using standard price)
        total_value = sum(q.quantity * q.product_id.standard_price for q in quants)
        
        return {
            'total_quantity': total_qty,
            'available_quantity': available_qty,
            'reserved_quantity': reserved_qty,
            'product_count': product_count,
            'total_value': total_value,
            'by_status': status_counts,
        }
    
    def _get_capacity_data(self, warehouse):
        """Warehouse capacity utilization"""
        return {
            'warehouse_capacity': warehouse.capacity_total,
            'warehouse_used': warehouse.capacity_used,
            'warehouse_available': warehouse.capacity_available,
            'warehouse_percent': warehouse.capacity_percentage,
            'zones': [
                {
                    'name': zone.name,
                    'type': zone.zone_type,
                    'capacity': zone.capacity_total,
                    'used': zone.capacity_used,
                    'percent': zone.capacity_percentage,
                    'color': zone.color,
                } for zone in warehouse.zone_ids
            ]
        }
    
    def _get_operations_data(self, warehouse):
        """Pending operations counts"""
        today = fields.Date.today()
        
        # Receipts
        receipts_pending = self.env['wms.receipt'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        receipts_today = self.env['wms.receipt'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('date', '=', today),
            ('state', '=', 'done')
        ])
        
        # Deliveries
        deliveries_pending = self.env['wms.delivery'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        deliveries_today = self.env['wms.delivery'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('date', '=', today),
            ('state', '=', 'done')
        ])
        
        # Transfers
        transfers_pending = self.env['wms.transfer'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        
        # Adjustments
        adjustments_pending = self.env['wms.adjustment'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('state', 'not in', ['done', 'cancel'])
        ])
        
        return {
            'receipts': {
                'pending': receipts_pending,
                'completed_today': receipts_today,
            },
            'deliveries': {
                'pending': deliveries_pending,
                'completed_today': deliveries_today,
            },
            'transfers': {
                'pending': transfers_pending,
            },
            'adjustments': {
                'pending': adjustments_pending,
            }
        }
    
    def _get_alerts(self, warehouse):
        """Get system alerts"""
        alerts = []
        
        # Low stock alerts
        products = self.env['product.product'].search([('type', '=', 'product')])
        for product in products:
            if hasattr(product, 'min_stock') and product.min_stock > 0:
                quants = self.env['wms.stock.quant'].search([
                    ('product_id', '=', product.id),
                    ('warehouse_id', '=', warehouse.id),
                    ('status', '=', 'available')
                ])
                total_qty = sum(quants.mapped('available_quantity'))
                
                if total_qty < product.min_stock:
                    alerts.append({
                        'type': 'low_stock',
                        'severity': 'warning',
                        'message': f'Low stock: {product.name} ({total_qty}/{product.min_stock})',
                        'product_id': product.id,
                    })
        
        # Expiring products (within 30 days)
        expiry_date = fields.Date.today() + timedelta(days=30)
        expiring_quants = self.env['wms.stock.quant'].search([
            ('warehouse_id', '=', warehouse.id),
            ('expiration_date', '<=', expiry_date),
            ('expiration_date', '>=', fields.Date.today()),
            ('quantity', '>', 0)
        ])
        
        for quant in expiring_quants:
            days_to_expiry = (quant.expiration_date - fields.Date.today()).days
            alerts.append({
                'type': 'expiring',
                'severity': 'danger' if days_to_expiry <= 7 else 'warning',
                'message': f'Expiring in {days_to_expiry} days: {quant.product_id.name} (Lot: {quant.lot_id.name if quant.lot_id else "N/A"})',
                'product_id': quant.product_id.id,
                'days': days_to_expiry,
            })
        
        # Over capacity locations
        locations = self.env['wms.location'].search([
            ('warehouse_id', '=', warehouse.id),
            ('capacity_percentage', '>', 90)
        ])
        
        for location in locations:
            alerts.append({
                'type': 'capacity',
                'severity': 'danger' if location.capacity_percentage >= 100 else 'warning',
                'message': f'Location {location.complete_name} at {location.capacity_percentage:.0f}% capacity',
                'location_id': location.id,
            })
        
        return alerts
    
    def _get_top_products(self, warehouse):
        """Top 10 products by movement (last 30 days)"""
        date_from = fields.Date.today() - timedelta(days=30)
        
        moves = self.env['wms.stock.move'].search([
            ('date', '>=', date_from),
            ('state', '=', 'done'),
            '|',
            ('location_id.warehouse_id', '=', warehouse.id),
            ('location_dest_id.warehouse_id', '=', warehouse.id)
        ])
        
        # Count movements per product
        product_movements = {}
        for move in moves:
            product_id = move.product_id.id
            if product_id not in product_movements:
                product_movements[product_id] = {
                    'product_id': product_id,
                    'product_name': move.product_id.name,
                    'product_code': move.product_id.default_code or '',
                    'movement_count': 0,
                    'total_qty': 0,
                }
            product_movements[product_id]['movement_count'] += 1
            product_movements[product_id]['total_qty'] += move.product_uom_qty
        
        # Sort by movement count
        top_products = sorted(product_movements.values(), key=lambda x: x['movement_count'], reverse=True)[:10]
        
        return top_products
    
    def _get_movement_trends(self, warehouse):
        """Movement trends for last 7 days"""
        trends = []
        
        for i in range(6, -1, -1):
            date = fields.Date.today() - timedelta(days=i)
            
            receipts = self.env['wms.receipt'].search_count([
                ('warehouse_id', '=', warehouse.id),
                ('date', '=', date),
                ('state', '=', 'done')
            ])
            
            deliveries = self.env['wms.delivery'].search_count([
                ('warehouse_id', '=', warehouse.id),
                ('date', '=', date),
                ('state', '=', 'done')
            ])
            
            transfers = self.env['wms.transfer'].search_count([
                ('warehouse_id', '=', warehouse.id),
                ('date', '=', date),
                ('state', '=', 'done')
            ])
            
            trends.append({
                'date': date.strftime('%d/%m'),
                'receipts': receipts,
                'deliveries': deliveries,
                'transfers': transfers,
            })
        
        return trends
    
    def _get_performance_metrics(self, warehouse):
        """Performance KPIs"""
        today = fields.Date.today()
        month_start = today.replace(day=1)
        
        # Average time to process receipt (from arrived to done)
        receipts = self.env['wms.receipt'].search([
            ('warehouse_id', '=', warehouse.id),
            ('date', '>=', month_start),
            ('state', '=', 'done')
        ])
        
        avg_receipt_time = 0
        if receipts:
            receipt_times = []
            for receipt in receipts:
                if receipt.create_date and receipt.write_date:
                    time_diff = (receipt.write_date - receipt.create_date).total_seconds() / 3600
                    receipt_times.append(time_diff)
            avg_receipt_time = sum(receipt_times) / len(receipt_times) if receipt_times else 0
        
        # Average time to process delivery
        deliveries = self.env['wms.delivery'].search([
            ('warehouse_id', '=', warehouse.id),
            ('date', '>=', month_start),
            ('state', '=', 'done')
        ])
        
        avg_delivery_time = 0
        if deliveries:
            delivery_times = []
            for delivery in deliveries:
                if delivery.create_date and delivery.write_date:
                    time_diff = (delivery.write_date - delivery.create_date).total_seconds() / 3600
                    delivery_times.append(time_diff)
            avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
        
        # Order fulfillment rate
        total_deliveries = len(deliveries)
        on_time_deliveries = self.env['wms.delivery'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('date', '>=', month_start),
            ('state', '=', 'done'),
            ('date', '<=', fields.Date.today())
        ])
        fulfillment_rate = (on_time_deliveries / total_deliveries * 100) if total_deliveries > 0 else 0
        
        # Inventory accuracy (adjustments vs total inventory)
        adjustments = self.env['wms.adjustment'].search_count([
            ('warehouse_id', '=', warehouse.id),
            ('date', '>=', month_start),
            ('state', '=', 'done'),
            ('has_variance', '=', True)
        ])
        total_products = self.env['wms.stock.quant'].search_count([('warehouse_id', '=', warehouse.id)])
        accuracy_rate = ((total_products - adjustments) / total_products * 100) if total_products > 0 else 100
        
        return {
            'avg_receipt_time_hours': round(avg_receipt_time, 2),
            'avg_delivery_time_hours': round(avg_delivery_time, 2),
            'fulfillment_rate_percent': round(fulfillment_rate, 2),
            'inventory_accuracy_percent': round(accuracy_rate, 2),
            'total_receipts_month': len(receipts),
            'total_deliveries_month': len(deliveries),
        }
    
    @api.model
    def get_warehouse_list(self):
        """Get list of warehouses for selection"""
        warehouses = self.env['wms.warehouse'].search([])
        return [{'id': w.id, 'name': w.name} for w in warehouses]
