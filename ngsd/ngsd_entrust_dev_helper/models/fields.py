from odoo import fields
from odoo.tools import format_duration

# Legacy support for custom field attributes - these are no longer actively used in Odoo 18
# The conversion tool migrated these, but Odoo 18's view engine handles this differently
# Keeping minimal compatibility layer

_super_convert_to_export = fields.Float.convert_to_export


def convert_to_export(self, value, record):
    if getattr(self, 'float_time', False):
        if not value:
            return ''
        return format_duration(value)
    return _super_convert_to_export(self, value, record)


fields.Float.convert_to_export = convert_to_export
