from odoo import fields, models, api


class NonProjectTask(models.Model):
    _inherit = "en.nonproject.task"

    crm_lead_id = fields.Many2one("crm.lead", string="Cơ hội")
    partner_id = fields.Many2one("res.partner", string="Liên hệ", related="crm_lead_id.partner_id",
                                 readonly=True, store=True)