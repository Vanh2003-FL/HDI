from odoo import api, fields, models 

class TableCriteriaApi(models.Model):
    _name = 'table.criteria.api'
    _description = 'TableCriteriaApi'
    _rec_name = 'criteria_lv1'

    criteria_lv1 = fields.Char('Tiêu chí lv1')
    criteria_lv2 = fields.Char('Tiêu chí lv2')

