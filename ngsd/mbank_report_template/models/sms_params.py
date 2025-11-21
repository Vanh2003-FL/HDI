from odoo import fields, models, api, exceptions


class XSMSParams(models.Model):
    _name = "x.sms.params"
    _inherit = "mail.render.mixin"


    sub_object = fields.Many2one('ir.model', 'Sub-model', readonly=True, related="en_report_template_id.model_id")
    en_report_template_id = fields.Many2one('en.report.template', 'Mẫu in')
    model_object_field = fields.Many2one(store=True, string='Trường')
    sub_model_object_field = fields.Many2one(store=True, string='Trường liên quan')
    null_value = fields.Char(store=True)
    copyvalue = fields.Char(store=True, string='Params sử dụng')

    # Overrides of mail.render.mixin
    @api.depends('sub_object')
    def _compute_render_model(self):
        for template in self:
            template.render_model = template.sub_object.model

    @api.onchange('model_object_field', 'sub_model_object_field', 'null_value')
    def _onchange_dynamic_placeholder(self):
        """ Generate the dynamic placeholder """
        if self.model_object_field:
            if self.model_object_field.ttype in ['many2one', 'one2many', 'many2many']:
                model = self.env['ir.model']._get(self.model_object_field.relation)
                if model:
                    self.sub_object = model.id
                    sub_field_name = self.sub_model_object_field.name
                    self.copyvalue = self._build_expression(self.model_object_field.name,
                                                            sub_field_name, self.null_value or False)
            else:
                self.sub_object = False
                self.sub_model_object_field = False
                self.copyvalue = self._build_expression(self.model_object_field.name, False, self.null_value or False)
        else:
            self.sub_object = False
            self.sub_model_object_field = False
            if self.null_value:
                self.copyvalue = self._build_expression_null(self.null_value)
            else:
                self.copyvalue = False

    @api.model
    def _build_expression_null(self, null_value):
        expression = ''
        if null_value:
            expression = "{{"
            if null_value:
                expression += "'''%s'''" % null_value
            expression += " }}"
        return expression
