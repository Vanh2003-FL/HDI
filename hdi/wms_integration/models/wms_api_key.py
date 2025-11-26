from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import timedelta
import secrets
import hashlib


class WmsApiKey(models.Model):
    _name = 'wms.api.key'
    _description = 'WMS API Key'
    _order = 'create_date desc'

    name = fields.Char(string='Name', required=True, help='API key description')
    key = fields.Char(string='API Key', readonly=True, copy=False, index=True)
    user_id = fields.Many2one('res.users', string='User', required=True, 
                              default=lambda self: self.env.user)
    warehouse_id = fields.Many2one('wms.warehouse', string='Warehouse',
                                   help='Limit API access to specific warehouse')
    active = fields.Boolean(string='Active', default=True)
    last_used_date = fields.Datetime(string='Last Used', readonly=True)
    usage_count = fields.Integer(string='Usage Count', readonly=True, default=0)
    expires_date = fields.Date(string='Expires On')
    ip_whitelist = fields.Text(string='IP Whitelist', 
                               help='Comma-separated list of allowed IP addresses')
    
    # Permissions
    can_query = fields.Boolean(string='Can Query Stock', default=True)
    can_create_receipt = fields.Boolean(string='Can Create Receipt', default=False)
    can_create_delivery = fields.Boolean(string='Can Create Delivery', default=False)
    can_reserve = fields.Boolean(string='Can Reserve Stock', default=False)
    can_move = fields.Boolean(string='Can Move Stock', default=False)
    
    notes = fields.Text(string='Notes')

    @api.model
    def create(self, vals):
        if 'key' not in vals:
            vals['key'] = self._generate_api_key()
        return super(WmsApiKey, self).create(vals)

    def _generate_api_key(self):
        """Generate a secure API key"""
        random_string = secrets.token_hex(32)
        return f"wms_{random_string}"

    def validate_key(self, key, ip_address=None):
        """Validate API key and update usage"""
        api_key = self.search([
            ('key', '=', key),
            ('active', '=', True)
        ], limit=1)
        
        if not api_key:
            return False
        
        # Check expiration
        if api_key.expires_date and fields.Date.today() > api_key.expires_date:
            return False
        
        # Check IP whitelist
        if api_key.ip_whitelist and ip_address:
            allowed_ips = [ip.strip() for ip in api_key.ip_whitelist.split(',')]
            if ip_address not in allowed_ips:
                return False
        
        # Update usage
        api_key.write({
            'last_used_date': fields.Datetime.now(),
            'usage_count': api_key.usage_count + 1
        })
        
        return api_key

    def action_regenerate_key(self):
        """Regenerate API key"""
        self.ensure_one()
        new_key = self._generate_api_key()
        self.write({'key': new_key})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'API Key Regenerated',
                'message': f'New API key: {new_key}',
                'type': 'success',
                'sticky': True,
            }
        }

    def action_deactivate(self):
        """Deactivate API key"""
        self.write({'active': False})


class WmsApiLog(models.Model):
    _name = 'wms.api.log'
    _description = 'WMS API Log'
    _order = 'create_date desc'
    _rec_name = 'endpoint'

    endpoint = fields.Char(string='Endpoint', required=True, index=True)
    method = fields.Selection([
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
    ], string='Method', required=True)
    api_key_id = fields.Many2one('wms.api.key', string='API Key', ondelete='set null')
    user_id = fields.Many2one('res.users', string='User')
    ip_address = fields.Char(string='IP Address')
    request_data = fields.Text(string='Request Data')
    response_data = fields.Text(string='Response Data')
    response_code = fields.Integer(string='Response Code')
    response_time = fields.Float(string='Response Time (ms)')
    success = fields.Boolean(string='Success', compute='_compute_success', store=True)
    error_message = fields.Text(string='Error Message')
    
    @api.depends('response_code')
    def _compute_success(self):
        for record in self:
            record.success = 200 <= record.response_code < 300 if record.response_code else False

    @api.model
    def log_request(self, endpoint, method, api_key_id=None, user_id=None, 
                   ip_address=None, request_data=None, response_data=None, 
                   response_code=200, response_time=0, error_message=None):
        """Create API log entry"""
        return self.create({
            'endpoint': endpoint,
            'method': method,
            'api_key_id': api_key_id,
            'user_id': user_id,
            'ip_address': ip_address,
            'request_data': str(request_data) if request_data else '',
            'response_data': str(response_data) if response_data else '',
            'response_code': response_code,
            'response_time': response_time,
            'error_message': error_message,
        })

    @api.autovacuum
    def _gc_api_logs(self):
        """Delete API logs older than 90 days"""
        limit_date = fields.Datetime.now() - timedelta(days=90)
        old_logs = self.search([('create_date', '<', limit_date)])
        old_logs.unlink()
