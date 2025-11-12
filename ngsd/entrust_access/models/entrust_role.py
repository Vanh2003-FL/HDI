import itertools
from itertools import chain, repeat

from lxml import etree
from lxml.builder import E

from odoo import api, fields, models, _
from odoo.tools import partition, pycompat

concat = chain.from_iterable


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


class EntrustRole(models.Model):
    _name = 'entrust.role'
    _description = 'Role'

    def _default_groups(self):
        default_user = self.env.ref('base.default_user', raise_if_not_found=False)
        return default_user.sudo().groups_id

    name = fields.Char('Vai trò', required=True, translate=True)
    user_ids = fields.Many2many('res.users', 'res_users_roles_rel', 'rid', 'uid', string="Người dùng", readonly=False)
    groups_id = fields.Many2many('res.groups', 'res_groups_roles_rel', 'rid', 'gid', string='Quyền truy cập',
                                 default=_default_groups)
    disallowed_menu_ids = fields.Many2many('ir.ui.menu', string='Not-allowed Menu')
    _sql_constraints = [
        ('name_company_uniq', 'unique(name)',
         'Tên vai trò phải là duy nhất!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        new_vals_list = [self._remove_reified_groups(vals) for vals in vals_list]
        records = super(EntrustRole, self).create(new_vals_list)
        for record in records:
            if hasattr(record, 'user_ids'):
                record.user_ids.reload_groups_id()
        return records

    def write(self, values):
        values = self._remove_reified_groups(values)
        res = super(EntrustRole, self).write(values)
        self.user_ids.reload_groups_id()
        return res

    def unlink(self):
        user_ids = self.user_ids.reload_groups_id()
        res = super(EntrustRole, self).unlink()
        user_ids.reload_groups_id()
        self.env['ir.actions.actions'].clear_caches()
        return res

    @api.model
    def default_get(self, fields):
        group_fields, fields = partition(is_reified_group, fields)
        fields1 = (fields + ['groups_id']) if group_fields else fields
        values = super(EntrustRole, self).default_get(fields1)
        self._add_reified_groups(group_fields, values)
        return values

    def read(self, fields=None, load='_classic_read'):
        # determine whether reified groups fields are required, and which ones
        fields1 = fields or list(self.fields_get())
        group_fields, other_fields = partition(is_reified_group, fields1)

        # read regular fields (other_fields); add 'groups_id' if necessary
        drop_groups_id = False
        if group_fields and fields:
            if 'groups_id' not in other_fields:
                other_fields.append('groups_id')
                drop_groups_id = True
        else:
            other_fields = fields

        res = super(EntrustRole, self).read(other_fields, load=load)

        # post-process result to add reified group fields
        if group_fields:
            for values in res:
                self._add_reified_groups(group_fields, values)
                if drop_groups_id:
                    values.pop('groups_id', None)
        return res

    def _add_reified_groups(self, fields, values):
        """ add the given reified group fields into `values` """
        gids = set(parse_m2m(values.get('groups_id') or []))
        for f in fields:
            if is_boolean_group(f):
                values[f] = get_boolean_group(f) in gids
            elif is_selection_groups(f):
                selected = [gid for gid in get_selection_groups(f) if gid in gids]
                # if 'Internal User' is in the group, this is the "User Type" group
                # and we need to show 'Internal User' selected, not Public/Portal.
                if self.env.ref('base.group_user').id in selected:
                    values[f] = self.env.ref('base.group_user').id
                else:
                    values[f] = selected and selected[-1] or False

    def _remove_reified_groups(self, values):
        add, rem = [], []
        values1 = {}

        for key, val in values.items():
            if is_boolean_group(key):
                (add if val else rem).append(get_boolean_group(key))
            elif is_selection_groups(key):
                rem += get_selection_groups(key)
                if val:
                    add.append(val)
            else:
                values1[key] = val

        if 'groups_id' not in values and (add or rem):
            # remove group ids in `rem` and add group ids in `add`
            values1['groups_id'] = list(itertools.chain(
                zip(repeat(3), rem),
                zip(repeat(4), add)
            ))

        return values1

    @api.model
    def fields_get(self, allfields=None, attributes=None):
      # Lấy tất cả field từ model cha
      res = super(EntrustRole, self).fields_get(allfields)

      # Nếu có attributes muốn lấy riêng
      if attributes:
        filtered_res = {}
        for fname, fvals in res.items():
          filtered_res[fname] = {k: fvals[k] for k in attributes if k in fvals}
        res = filtered_res

      # add reified groups fields
      for app, kind, gs, category_name in self.env[
        'res.groups'].sudo().get_groups_by_application():
        if kind == 'selection':
          selection_vals = [(False, '')]
          if app.xml_id == 'base.module_category_user_type':
            selection_vals = []
          field_name = name_selection_groups(gs.ids)
          if allfields and field_name not in allfields:
            continue
          tips = ['%s: %s' % (g.name, g.comment) for g in gs if g.comment]
          res[field_name] = {
            'type': 'selection',
            'string': app.name or _('Other'),
            'selection': selection_vals + [(g.id, g.name) for g in gs],
            'help': '\n'.join(tips),
            'exportable': False,
            'selectable': False,
          }
        else:
          for g in gs:
            field_name = name_boolean_group(g.id)
            if allfields and field_name not in allfields:
              continue
            res[field_name] = {
              'type': 'boolean',
              'string': g.name,
              'help': g.comment,
              'exportable': False,
              'selectable': False,
            }
      return res
