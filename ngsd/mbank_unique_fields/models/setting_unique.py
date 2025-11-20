from odoo import models, fields, api, _
from collections import defaultdict
from odoo.fields import Domain


class SettingUnique(models.Model):
    _name = 'en.setting.unique'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Quy tắc trùng dữ liệu'

    CRITICAL_FIELDS = ['model_id', 'active', 'field_ids']

    def _get_actions(self, records):
        """ Return the actions of the given triggers for records' model. The
            returned actions' context contain an object to manage processing.
        """
        if '__action_done' not in self._context:
            self = self.with_context(__action_done={})
        domain = [('model_name', '=', records._name)]
        actions = self.with_context(active_test=True).sudo().search(domain)
        return actions.with_env(self.env)

    def _check_trigger_fields(self, record):
        """ Return whether any of the trigger fields has been modified on ``record``. """
        self_sudo = self.sudo()
        if not self_sudo.field_ids:
            # all fields are implicit triggers
            return True

        if not self._context.get('old_values'):
            # this is a create: all fields are considered modified
            return True

        # Note: old_vals are in the format of read()
        old_vals = self._context['old_values'].get(record.id, {})

        def differ(name):
            field = record._fields[name]
            return (
                    name in old_vals and
                    field.convert_to_cache(record[name], record, validate=False) !=
                    field.convert_to_cache(old_vals[name], record, validate=False)
            )

        return any(differ(field.name) for field in self_sudo.field_ids)

    def _process(self, records):
        self = self.sudo()
        """ Process action ``self`` on the ``records`` that have not been done yet. """
        # filter out the records on which self has already been done
        action_done = self._context['__action_done']
        records_done = action_done.get(self, records.browse())
        records -= records_done
        if not records:
            return

        # mark the remaining records as done (to avoid recursive processing)
        action_done = dict(action_done)
        action_done[self] = records_done + records
        self = self.with_context(__action_done=action_done)
        records = records.with_context(__action_done=action_done)

        # modify records
        values = {}
        if 'date_action_last' in records._fields:
            values['date_action_last'] = fields.Datetime.now()
        if values:
            records.write(values)

        # execute actions
        for record in records:
            # we process the action if any watched field has been modified
            msg = []
            for rule in self:
                domain = []
                if rule.ttype == 'all':
                    expr = expression.AND
                elif rule.ttype == 'any':
                    expr = expression.OR
                else:
                    continue
                for key in rule.field_ids:
                    domain = expr([domain, [(key.name, '=', record[key.name] if key.ttype != 'many2one' else record[key.name].id)]])
                if record.sudo().search_count(domain) > 1:
                    msg += [f'+ {rule.name}']
            if msg:
                raise exceptions.ValidationError('\n'.join(['Bản ghi trùng dữ liệu theo các quy tắc:'] + msg))

    @api.model_create_multi
    def create(self, vals_list):
        res = super().create(vals_list)
        self._update_registry()
        return res

    def write(self, vals):
        res = super().write(vals)
        if set(vals).intersection(self.CRITICAL_FIELDS):
            self._update_registry()
        return res

    def _update_registry(self):
        """ Update the registry after a modification on action rules. """
        if self.env.registry.ready and not self.env.context.get('import_file'):
            # re-install the model patches, and notify other workers
            self._unregister_hook()
            self._register_hook()
            self.env.registry.registry_invalidated = True

    def _unregister_hook(self):
        """ Remove the patches installed by _register_hook() """
        NAMES = ['create', 'write']
        for Model in self.env.registry.values():
            for name in NAMES:
                try:
                    delattr(Model, name)
                except AttributeError:
                    pass

    def _register_hook(self):
        """ Patch models that should trigger action rules based on creation,
            modification, deletion of records and form onchanges.
        """

        #
        # Note: the patched methods must be defined inside another function,
        # otherwise their closure may be wrong. For instance, the function
        # create refers to the outer variable 'create', which you expect to be
        # bound to create itself. But that expectation is wrong if create is
        # defined inside a loop; in that case, the variable 'create' is bound to
        # the last function defined by the loop.
        #

        def make_create():
            """ Instanciate a create method that processes action rules. """

            @api.model_create_multi
            def create(self, vals_list, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['en.setting.unique']._get_actions(self)
                if not actions:
                    return create.origin(self, vals_list, **kw)
                # call original method
                records = create.origin(self.with_env(actions.env), vals_list, **kw)
                # check postconditions, and execute actions on the records that satisfy them
                actions.with_context(old_values=None)._process(records)
                return records.with_env(self.env)

            return create

        def make_write():
            """ Instanciate a write method that processes action rules. """

            def write(self, vals, **kw):
                # retrieve the action rules to possibly execute
                actions = self.env['en.setting.unique']._get_actions(self)
                if not (actions and self):
                    return write.origin(self, vals, **kw)
                records = self.with_env(actions.env).filtered('id')
                # read old values before the update
                old_values = {
                    old_vals.pop('id'): old_vals
                    for old_vals in (records.read(list(vals)) if vals else [])
                }
                # call original method
                write.origin(self.with_env(actions.env), vals, **kw)
                # execute actions on the records
                actions.with_context(old_values=old_values)._process(records)
                return True

            return write

        patched_models = defaultdict(set)

        def patch(model, name, method):
            """ Patch method `name` on `model`, unless it has been patched already. """
            if model not in patched_models[name]:
                patched_models[name].add(model)
                ModelClass = type(model)
                origin = getattr(ModelClass, name)
                method.origin = origin
                wrapped = api.propagate(origin, method)
                wrapped.origin = origin
                setattr(ModelClass, name, wrapped)

        # retrieve all actions, and patch their corresponding model
        for action_rule in self.with_context({}).search([]):
            Model = self.env.get(action_rule.model_name)

            # Do not crash if the model of the base_action_rule was uninstalled
            if Model is None:
                _logger.warning("Action rule with ID %d depends on model %s" % (action_rule.id, action_rule.model_name))
                continue

            patch(Model, 'create', make_create())
            patch(Model, 'write', make_write())

    name = fields.Char(tracking=True, string='Tên quy tắc', required=True)
    model_id = fields.Many2one(tracking=True, string='Loại dữ liệu', comodel_name='ir.model', required=True, ondelete='cascade')
    model_name = fields.Char(related='model_id.model')
    ttype = fields.Selection(tracking=True, string='Loại trùng', selection=[('all', 'Trùng tất cả các trường'), ('any', 'Trùng một trong các trường')], required=True,
                             help="""Cài đặt cách thức bản ghi trùng được định nghĩa\n
                                    Trùng tất cả các trường: 2 bản ghi được định nghĩa là trùng nhau khi tất cả các trường được chọn có giá trị giống hệt nhau, nếu chỉ giống 1 hoặc 1 số trong các trường thì hiểu là không trùng\n
                                    Trùng một trong các trường: 2 bản ghi được định nghĩa là trùng nhau khi một trong các trường được chọn trùng giá trị""")
    field_ids = fields.Many2many(tracking=True, string='Các trường', domain="[('ttype','not in',['many2many','one2many','binary']),('model_id','=',model_id),('store','=',True),('readonly','=',False)]", comodel_name='ir.model.fields', required=True)
    active = fields.Boolean(tracking=True, string='Hoạt động', default=True)

    @api.onchange('model_id')
    def _en_onchange_model_id(self):
        self.field_ids = False
