(models.Model):
    _inherit = 'stock.quant'
    
    is_odd = fields.Boolean(string='Is Odd Item', default=False)
    odd_reason = fields.Char(string='Odd Reason')
