from odoo import api, models, _, exceptions, fields, SUPERUSER_ID
# Removed invalid import:
# from odoo.osv.expression import Domain
from odoo.addons.ngsd_entrust_dev_helper.tools.number2text import number2text_vn


class Base(models.AbstractModel):
    _inherit = "base"

    def open_form_or_tree_view(self, action, form=False, records=False, context={}, action_name=False, target='current'):
        self = self.sudo()
        if not records:
            records = []
        action = self.env["ir.actions.actions"]._for_xml_id(action)

        if action_name:
            action['name'] = action_name

        if 'views' in action and form:
            action['views'] = [
                (self.env.ref(form).id, 'form')
            ] + [(state, view) for state, view in action['views'] if view != 'form']

        if (not records and context.get(
                'create', self.env[action['res_model']].check_access_rights('create', raise_exception=False)
        )) or len(records) == 1:
            if form:
                action['views'] = [(self.env.ref(form).id, 'form')]
            else:
                action['views'] = [(state, view) for state, view in action['views'] if view == 'form']

            if not action['views']:
                action['views'] = [(False, 'form')]

            if len(records) == 1:
                action['res_id'] = records.id

        elif len(records) > 1:
            action['domain'] = [('id', 'in', records.ids)]

        else:
            return {'type': 'ir.actions.act_window_close'}

        action['target'] = target

        if context:
            action['context'] = context

        return action

    def send_notify(self, message, users, subject='', model_description='', access_link=False):
        self.clear_caches()
        view = self.env['ir.ui.view'].browse(
            self.env['ir.model.data']._xmlid_to_res_id('ngsd_entrust_dev_helper.notify_record_message')
        )

        for record in self.sudo():
            if not record.exists():
                continue

            record.message_subscribe(partner_ids=users.mapped('partner_id').ids)

            if not model_description:
                model_description = self.env['ir.model']._get(record._name).display_name

            values = {
                'object': record,
                'model_description': model_description,
                'message': message,
                'access_link': access_link or record._notify_get_action_link('view'),
            }

            assignation_msg = view._render(values, engine='ir.qweb', minimal_qcontext=True)
            assignation_msg = record.env['mail.render.mixin']._replace_local_links(assignation_msg)

            record.message_notify(
                subject=subject if subject else _('%s', record.display_name),
                body=assignation_msg,
                partner_ids=users.mapped('partner_id').ids,
                record_name=record.display_name,
                email_layout_xmlid='mail.mail_notification_light',
                model_description=model_description,
            )

    def place_value(self, number):
        return "{:,}".format(number)

    def number2text_vn(self, number):
        return number2text_vn(number).capitalize()
