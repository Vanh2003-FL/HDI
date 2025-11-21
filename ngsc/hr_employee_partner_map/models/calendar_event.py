from odoo import models, fields, api, _


class CalendarEvent(models.Model):
    _inherit = 'calendar.event'

    partner_ids = fields.Many2many(
        'res.partner',
        string='Attendees',
    )

    def _get_available_partner_ids(self):
        """Trả về tất cả partner hiện có + partner từ bảng mapping (hr.employee.partner)."""
        partners = self.env['res.partner'].sudo().search([])
        mapped_partners = self.env['hr.employee.partner'].sudo().mapped('partner_id')
        return (partners | mapped_partners).ids

    @api.onchange('partner_ids')
    def _onchange_partner_ids(self):
        """Domain cho dropdown inline (autocomplete)."""
        return {
            'domain': {'partner_ids': [('id', 'in', self._get_available_partner_ids())]}
        }

    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        Inject available_partner_ids vào context của view (để popup Many2many dùng context này).
        Lưu ý: ta truyền context trong view result, popup query sẽ nhận được context đó.
        """
        res = super(CalendarEvent, self).fields_view_get(view_id=view_id, view_type=view_type,
                                                         toolbar=toolbar, submenu=submenu)
        # Chỉ thêm context cho form view (đủ để popup nhận)
        if view_type == 'form':
            if 'context' not in res:
                res['context'] = {}
            # copy để an toàn nếu res['context'] là string hoặc dict
            try:
                current_ctx = dict(res.get('context') or {})
            except Exception:
                current_ctx = {}
            current_ctx['available_partner_ids'] = self._get_available_partner_ids()
            res['context'] = current_ctx
        return res
