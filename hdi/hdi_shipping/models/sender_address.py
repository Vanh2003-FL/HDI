from odoo import models, fields, api


class SenderAddress(models.Model):
    _name = 'sender.address'
    _description = 'Sender Address'

    user_id = fields.Many2one('res.users', string='Người dùng', required=True, default=lambda self: self.env.user)
    name = fields.Char(string='Tên người gửi', required=True)
    phone = fields.Char(string='Điện thoại')
    email = fields.Char(string='Email')
    
    # Address fields
    street = fields.Char(string='Đường')
    street2 = fields.Char(string='Đường 2')
    city = fields.Char(string='Thành phố')
    state_id = fields.Many2one('res.country.state', string='Tỉnh/Thành')
    zip = fields.Char(string='Mã bưu điện')
    country_id = fields.Many2one('res.country', string='Quốc gia', default=lambda self: self.env.ref('base.vn'))
    
    full_address = fields.Char(string='Địa chỉ đầy đủ', compute='_compute_full_address', store=True)
    
    is_default = fields.Boolean(string='Địa chỉ mặc định', default=False)
    active = fields.Boolean(string='Kích hoạt', default=True)
    
    @api.depends('street', 'street2', 'city', 'state_id', 'zip', 'country_id')
    def _compute_full_address(self):
        """Compute full address"""
        for address in self:
            parts = []
            if address.street:
                parts.append(address.street)
            if address.street2:
                parts.append(address.street2)
            if address.city:
                parts.append(address.city)
            if address.state_id:
                parts.append(address.state_id.name)
            if address.zip:
                parts.append(address.zip)
            if address.country_id:
                parts.append(address.country_id.name)
            address.full_address = ', '.join(parts)
    
    def set_as_default(self):
        """Set this address as default and unset others for this user"""
        self.env['sender.address'].search([('user_id', '=', self.user_id.id), ('id', '!=', self.id)]).write({'is_default': False})
        self.write({'is_default': True})
