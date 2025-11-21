from itertools import chain, repeat
from odoo import models, fields, api, _

concat = chain.from_iterable

def name_boolean_group(id):
    return f'in_group_{id}'

def name_selection_groups(ids):
    return 'sel_groups_' + '_'.join(str(i) for i in ids)

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
    ids = []
    for cmd in commands:
        if isinstance(cmd, (list, tuple)):
            if cmd[0] in (1, 4):
                ids.append(cmd[1])
            elif cmd[0] == 5:
                ids = []
            elif cmd[0] == 6:
                ids = list(cmd[2])
        else:
            ids.append(cmd)
    return ids


class ChangeAccessWizard(models.TransientModel):
    _name = "change.access.wizard"
    _description = "Change Access Wizard"

    user_id = fields.Many2one('res.users', string="User")
    groups_id = fields.Many2many('res.groups', string='Groups')

    def change_access_button(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals = self._remove_reified_groups(vals)
            if vals.get('user_id'):
                self.env['res.users'].browse(vals.get('user_id')).write({'groups_id': vals.get('groups_id')})
        return super().create(vals_list)

    def _remove_reified_groups(self, vals):
        add, rem = [], []
        new_vals = {}
        for key, val in vals.items():
            if is_boolean_group(key):
                (add if val else rem).append(get_boolean_group(key))
            elif is_selection_groups(key):
                rem += get_selection_groups(key)
                if val:
                    add.append(val)
            else:
                new_vals[key] = val

        if 'groups_id' not in vals and (add or rem):
            new_vals['groups_id'] = list(chain(
                zip(repeat(3), rem),
                zip(repeat(4), add)
            ))
        return new_vals

    @api.model
    def default_get(self, fields):
        group_fields, other_fields = partition(is_reified_group, fields)
        if group_fields:
            other_fields.append('groups_id')
        values = super().default_get(other_fields)
        active_id = self.env.context.get('active_id')
        if active_id:
            user = self.env['res.users'].sudo().browse(active_id)
            values.update({
                'user_id': active_id,
                'groups_id': [(6, 0, user.groups_id.ids)]
            })
        self._add_reified_groups(group_fields, values)
        return values

    def read(self, fields=None, load='_classic_read'):
        fields1 = fields or list(self.fields_get())
        group_fields, other_fields = partition(is_reified_group, fields1)

        drop_groups_id = False
        if group_fields and fields:
            if 'groups_id' not in other_fields:
                other_fields.append('groups_id')
                drop_groups_id = True
        res = super().read(other_fields, load=load)

        for vals in res:
            self._add_reified_groups(group_fields, vals)
            if drop_groups_id:
                vals.pop('groups_id', None)
        return res

    def _add_reified_groups(self, fields, vals):
        gids = set(parse_m2m(vals.get('groups_id') or []))
        for f in fields:
            if is_boolean_group(f):
                vals[f] = get_boolean_group(f) in gids
            elif is_selection_groups(f):
                selected = [gid for gid in get_selection_groups(f) if gid in gids]
                vals[f] = selected[-1] if selected else False

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        res = super().fields_get(allfields, attributes)
        for app, kind, gs, cat_name in self.env['res.groups'].sudo().get_groups_by_application():
            if kind == 'selection':
                field_name = name_selection_groups(gs.ids)
                if allfields and field_name not in allfields:
                    continue
                selection_vals = [(g.id, g.name) for g in gs]
                res[field_name] = {
                    'type': 'selection',
                    'string': app.name or _('Other'),
                    'selection': selection_vals,
                    'help': '\n'.join([g.comment for g in gs if g.comment]),
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
