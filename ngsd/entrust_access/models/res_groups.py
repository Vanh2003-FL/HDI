from odoo import models, fields, api, _

from lxml import etree
from lxml.builder import E

def name_boolean_group(id):
    return 'in_group_' + str(id)


def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(it) for it in ids)


def is_boolean_group(name):
    return name.startswith('in_group_')


def is_selection_groups(name):
    return name.startswith('sel_groups_')


def is_reified_group(name):
    return is_boolean_group(name) or is_selection_groups(name)


def get_boolean_group(name):
    return int(name[9:])


def get_selection_groups(name):
    return [int(v) for v in name[11:].split('_')]


def parse_m2m(commands):
    "return a list of ids corresponding to a many2many value"
    ids = []
    for command in commands:
        if isinstance(command, (tuple, list)):
            if command[0] in (1, 4):
                ids.append(command[1])
            elif command[0] == 5:
                ids = []
            elif command[0] == 6:
                ids = list(command[2])
        else:
            ids.append(command)
    return ids


class Groups(models.Model):
    _inherit = 'res.groups'

    roles = fields.Many2many('entrust.role', 'res_groups_roles_rel', 'gid', 'rid')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(Groups, self).create(vals_list)
        for rec in records:
            rec._update_role_groups_view()
        self.env['ir.actions.actions'].clear_caches()
        return records

    def write(self, values):
        res = super(Groups, self).write(values)
        if self._context.get('install_mode'):
            return res
        self._update_role_groups_view()
        self.env['ir.actions.actions'].clear_caches()
        return res

    def unlink(self):
        res = super(Groups, self).unlink()
        self._update_role_groups_view()
        self.env['ir.actions.actions'].clear_caches()
        return res

    @api.model
    def _update_role_groups_view(self):
        self = self.with_context(lang=None)
        view = self.env.ref('entrust_access.role_groups_view', raise_if_not_found=False)
        if view and view.exists() and view._name == 'ir.ui.view':
            group_no_one = view.env.ref('base.group_no_one')
            group_employee = view.env.ref('base.group_user')
            xml1, xml2, xml3 = [], [], []
            xml_by_category = {}
            xml1.append(E.separator(string='User Type', groups='base.group_no_one'))

            user_type_field_name = ''
            user_type_readonly = str({})
            sorted_tuples = sorted(self.get_groups_by_application(), key=lambda t: t[0].xml_id != 'base.module_category_user_type')
            for app, kind, gs, category_name in sorted_tuples:  # we process the user type first
                attrs = {}
                if app.xml_id in self._get_hidden_extra_categories():
                    attrs['groups'] = 'base.group_no_one'

                if app.xml_id == 'base.module_category_user_type':
                    field_name = name_selection_groups(gs.ids)
                    user_type_field_name = field_name
                    user_type_readonly = str({'readonly': [(user_type_field_name, '!=', group_employee.id)]})
                    attrs['widget'] = 'radio'
                    attrs['groups'] = 'base.group_no_one'
                    xml1.append(E.field(name=field_name, **attrs))
                    xml1.append(E.newline())

                elif kind == 'selection':
                    field_name = name_selection_groups(gs.ids)
                    if category_name not in xml_by_category:
                        xml_by_category[category_name] = []
                        xml_by_category[category_name].append(E.newline())
                    xml_by_category[category_name].append(E.field(name=field_name, **attrs))
                    xml_by_category[category_name].append(E.newline())

                else:
                    app_name = app.name or 'Other'
                    xml3.append(E.separator(string=app_name, **attrs))
                    for g in gs:
                        field_name = name_boolean_group(g.id)
                        if g == group_no_one:
                            xml3.append(E.field(name=field_name, invisible="1", **attrs))
                        else:
                            xml3.append(E.field(name=field_name, **attrs))

            xml3.append({'class': "o_label_nowrap"})
            if user_type_field_name:
                user_type_attrs = {'invisible': [(user_type_field_name, '!=', group_employee.id)]}
            else:
                user_type_attrs = {}

            for xml_cat in sorted(xml_by_category.keys(), key=lambda it: it[0]):
                xml_cat_name = xml_cat[1]
                master_category_name = (_(xml_cat_name))
                xml2.append(E.group(*(xml_by_category[xml_cat]), col="2", string=master_category_name))

            xml = E.field(
                E.group(*(xml1), col="2"),
                E.group(*(xml2), col="2"),
                E.group(*(xml3), col="4"), name="groups_id", position="replace")
            xml.addprevious(etree.Comment("GENERATED AUTOMATICALLY BY GROUPS"))
            xml_content = etree.tostring(xml, pretty_print=True, encoding="unicode")

            new_context = dict(view._context)
            new_context.pop('install_filename', None)  # don't set arch_fs for this computed view
            new_context['lang'] = None
            view.with_context(new_context).write({'arch': xml_content})


class ModuleCategory(models.Model):
    _inherit = "ir.module.category"

    def write(self, values):
        res = super().write(values)
        if "name" in values:
            self.env["res.groups"]._update_role_groups_view()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["res.groups"]._update_role_groups_view()
        return res
