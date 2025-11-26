from odoo import models, fields, api
from odoo.exceptions import UserError
import requests
import json
import logging
from datetime import timedelta

_logger = logging.getLogger(__name__)


class WmsWebhook(models.Model):
    _name = 'wms.webhook'
    _description = 'WMS Webhook'
    _order = 'sequence, id'

    name = fields.Char(string='Webhook Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    
    url = fields.Char(string='Webhook URL', required=True,
                     help='HTTP endpoint to call')
    method = fields.Selection([
        ('POST', 'POST'),
        ('PUT', 'PUT'),
    ], string='HTTP Method', default='POST', required=True)
    
    # Events to trigger
    event_receipt_done = fields.Boolean(string='Receipt Done')
    event_delivery_shipped = fields.Boolean(string='Delivery Shipped')
    event_transfer_done = fields.Boolean(string='Transfer Done')
    event_adjustment_done = fields.Boolean(string='Adjustment Done')
    event_stock_low = fields.Boolean(string='Stock Low Warning')
    event_product_expired = fields.Boolean(string='Product Expired')
    
    # Authentication
    auth_type = fields.Selection([
        ('none', 'None'),
        ('basic', 'Basic Auth'),
        ('bearer', 'Bearer Token'),
        ('api_key', 'API Key Header'),
    ], string='Authentication', default='none', required=True)
    
    auth_username = fields.Char(string='Username')
    auth_password = fields.Char(string='Password')
    auth_token = fields.Char(string='Token')
    auth_header_name = fields.Char(string='Header Name', default='X-API-Key')
    auth_header_value = fields.Char(string='Header Value')
    
    # Retry settings
    max_retries = fields.Integer(string='Max Retries', default=3)
    retry_delay = fields.Integer(string='Retry Delay (seconds)', default=60)
    timeout = fields.Integer(string='Timeout (seconds)', default=30)
    
    # Statistics
    total_calls = fields.Integer(string='Total Calls', readonly=True, default=0)
    successful_calls = fields.Integer(string='Successful Calls', readonly=True, default=0)
    failed_calls = fields.Integer(string='Failed Calls', readonly=True, default=0)
    last_call_date = fields.Datetime(string='Last Call', readonly=True)
    last_call_status = fields.Selection([
        ('success', 'Success'),
        ('failed', 'Failed'),
    ], string='Last Call Status', readonly=True)
    
    notes = fields.Text(string='Notes')

    def _prepare_headers(self):
        """Prepare HTTP headers with authentication"""
        self.ensure_one()
        
        headers = {
            'Content-Type': 'application/json',
        }
        
        if self.auth_type == 'bearer':
            headers['Authorization'] = f'Bearer {self.auth_token}'
        elif self.auth_type == 'api_key':
            headers[self.auth_header_name] = self.auth_header_value
        
        return headers

    def _prepare_auth(self):
        """Prepare authentication tuple for basic auth"""
        self.ensure_one()
        
        if self.auth_type == 'basic':
            return (self.auth_username, self.auth_password)
        
        return None

    def send_notification(self, event_type, data):
        """Send webhook notification"""
        self.ensure_one()
        
        payload = {
            'event': event_type,
            'timestamp': fields.Datetime.now().isoformat(),
            'data': data,
        }
        
        headers = self._prepare_headers()
        auth = self._prepare_auth()
        
        retries = 0
        success = False
        error_message = None
        
        while retries <= self.max_retries and not success:
            try:
                if self.method == 'POST':
                    response = requests.post(
                        self.url,
                        json=payload,
                        headers=headers,
                        auth=auth,
                        timeout=self.timeout
                    )
                else:
                    response = requests.put(
                        self.url,
                        json=payload,
                        headers=headers,
                        auth=auth,
                        timeout=self.timeout
                    )
                
                if response.status_code >= 200 and response.status_code < 300:
                    success = True
                    _logger.info(f"Webhook {self.name} sent successfully: {event_type}")
                else:
                    error_message = f"HTTP {response.status_code}: {response.text}"
                    _logger.warning(f"Webhook {self.name} failed: {error_message}")
                
            except Exception as e:
                error_message = str(e)
                _logger.error(f"Webhook {self.name} error: {error_message}")
            
            if not success:
                retries += 1
                if retries <= self.max_retries:
                    import time
                    time.sleep(self.retry_delay * retries)  # Exponential backoff
        
        # Update statistics
        self.write({
            'total_calls': self.total_calls + 1,
            'successful_calls': self.successful_calls + (1 if success else 0),
            'failed_calls': self.failed_calls + (0 if success else 1),
            'last_call_date': fields.Datetime.now(),
            'last_call_status': 'success' if success else 'failed',
        })
        
        # Log webhook call
        self.env['wms.webhook.log'].create({
            'webhook_id': self.id,
            'event_type': event_type,
            'payload': json.dumps(payload, default=str),
            'response_code': response.status_code if 'response' in locals() else 0,
            'response_body': response.text if 'response' in locals() else '',
            'success': success,
            'error_message': error_message,
            'retries': retries,
        })
        
        return success

    @api.model
    def trigger_event(self, event_type, data):
        """Trigger all webhooks for an event type"""
        event_field_map = {
            'receipt_done': 'event_receipt_done',
            'delivery_shipped': 'event_delivery_shipped',
            'transfer_done': 'event_transfer_done',
            'adjustment_done': 'event_adjustment_done',
            'stock_low': 'event_stock_low',
            'product_expired': 'event_product_expired',
        }
        
        field_name = event_field_map.get(event_type)
        if not field_name:
            return
        
        webhooks = self.search([
            (field_name, '=', True),
            ('active', '=', True)
        ])
        
        for webhook in webhooks:
            webhook.send_notification(event_type, data)

    def action_test_webhook(self):
        """Test webhook with sample data"""
        self.ensure_one()
        
        test_data = {
            'test': True,
            'message': 'This is a test notification',
        }
        
        success = self.send_notification('test', test_data)
        
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Webhook Test',
                'message': 'Webhook sent successfully' if success else 'Webhook failed',
                'type': 'success' if success else 'danger',
                'sticky': False,
            }
        }


class WmsWebhookLog(models.Model):
    _name = 'wms.webhook.log'
    _description = 'WMS Webhook Log'
    _order = 'create_date desc'

    webhook_id = fields.Many2one('wms.webhook', string='Webhook', required=True, ondelete='cascade')
    event_type = fields.Char(string='Event Type', required=True)
    payload = fields.Text(string='Payload')
    response_code = fields.Integer(string='Response Code')
    response_body = fields.Text(string='Response Body')
    success = fields.Boolean(string='Success')
    error_message = fields.Text(string='Error Message')
    retries = fields.Integer(string='Retries')

    @api.autovacuum
    def _gc_webhook_logs(self):
        """Delete webhook logs older than 30 days"""
        limit_date = fields.Datetime.now() - timedelta(days=30)
        old_logs = self.search([('create_date', '<', limit_date)])
        old_logs.unlink()
