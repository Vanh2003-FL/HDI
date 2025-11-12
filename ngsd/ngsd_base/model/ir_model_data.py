import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class IrModelData(models.Model):
    _inherit = 'ir.model.data'

    def init(self):
        # Insert data group đã tao thủ công
        try:
            self.env.cr.execute("""
                                INSERT INTO ir_model_data (name, module, model, res_id, noupdate)
                                SELECT 'group_cbf_hcm',
                                       'ngsd_base',
                                       'res.groups',
                                       6161,
                                       true WHERE EXISTS (
                    SELECT 1 FROM res_groups WHERE id = 6161)
                                ON CONFLICT DO NOTHING
                                """)
        except Exception as e:
            # log hoặc bỏ qua
            _logger.error("Không thể insert ir_model_data: %s", e)
