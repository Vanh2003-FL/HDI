from odoo import api, fields, models


class ThemeOption(models.Model):
    _name = "theme.option"
    _description = "Theme Option"

    name = fields.Char("Tên giao diện", required=True)
    background_color = fields.Char("Màu nền", help="Ví dụ: #ffffff", default="#ffffff")
    theme_image = fields.Binary("Ảnh nền", attachment=True)
    header_color = fields.Char("Màu tiêu đề", help="Ví dụ: #714B67", default="#71639e")
    button_color = fields.Char("Màu nút", help="Ví dụ: #714B67", default="#71639e")
    active_theme = fields.Boolean("Trạng thái sử dụng", default=False, readonly=True)

    # Màu mặc định của Odoo
    DEFAULT_COLORS = {
        'background_color': '#ffffff',
        'header_color': '#71639e',
        'button_color': '#71639e',
        'background_image': '',
        'gradient_color': '#71639e'
    }

    def action_activate_theme(self):
        """Kích hoạt theme này"""
        # Tắt tất cả theme khác
        self.sudo().search([('id', '!=', self.id)]).write({'active_theme': False})

        # Bật theme này
        self.active_theme = True

        # Lưu config vào system parameters
        ICP = self.env['ir.config_parameter'].sudo()
        ICP.set_param('theme.background_color',
                      self.background_color or self.DEFAULT_COLORS['background_color'])
        ICP.set_param('theme.header_color', self.header_color or self.DEFAULT_COLORS['header_color'])
        ICP.set_param('theme.button_color', self.button_color or self.DEFAULT_COLORS['button_color'])
        ICP.set_param('theme.gradient_color', self.background_color or self.DEFAULT_COLORS['gradient_color'])

        # Xử lý ảnh nền
        if self.theme_image:
            attachment = self.env['ir.attachment'].search([
                ('res_model', '=', 'theme.option'),
                ('res_field', '=', 'theme_image'),
                ('res_id', '=', self.id)
            ], limit=1)

            if attachment:
                image_url = '/web/image/%s' % attachment.id
                ICP.set_param('theme.background_image', image_url)
        else:
            ICP.set_param('theme.background_image', '')

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_deactivate_theme(self):
        """Tắt theme này và trở về giao diện mặc định"""
        self.active_theme = False
        self._reset_to_default_theme()

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def _reset_to_default_theme(self):
        """Reset tất cả settings về mặc định của Odoo"""
        ICP = self.env['ir.config_parameter'].sudo()

        for key, default_value in self.DEFAULT_COLORS.items():
            ICP.set_param(f'theme.{key}', default_value)

        return True


    @api.model
    def unlink_theme(self, theme_id):
        """
        Xóa một theme theo ID.
        Nếu theme đang active, sẽ reset về theme mặc định.
        Không cần ghi đè unlink().
        """
        theme = self.browse(theme_id)
        if not theme:
            return False

        # Kiểm tra theme đang active
        if theme.active_theme:
            # Reset về mặc định trước khi xóa
            self._reset_to_default_theme()

        # Xóa theme
        theme.unlink()
        return True

    def write(self, vals):
        """Override write để tự động cập nhật giao diện nếu theme đang active"""
        # Lưu trạng thái trước khi viết
        was_active = self.filtered(lambda t: t.active_theme)

        result = super(ThemeOption, self).write(vals)

        # Nếu theme đang active, cập nhật luôn config
        for theme in self.filtered(lambda t: t.active_theme):
            ICP = self.env['ir.config_parameter'].sudo()

            # Cập nhật màu nếu có trong vals
            for field_name, param_key, default_val in [
                ('background_color', 'theme.background_color', self.DEFAULT_COLORS['background_color']),
                ('header_color', 'theme.header_color', self.DEFAULT_COLORS['header_color']),
                ('button_color', 'theme.button_color', self.DEFAULT_COLORS['button_color']),
                ('background_color', 'theme.gradient_color', self.DEFAULT_COLORS['gradient_color']),
            ]:
                if field_name in vals:
                    ICP.set_param(param_key, getattr(theme, field_name) or default_val)

            # Cập nhật ảnh nền nếu thay đổi
            if 'theme_image' in vals:
                if theme.theme_image:
                    attachment = self.env['ir.attachment'].search([
                        ('res_model', '=', 'theme.option'),
                        ('res_field', '=', 'theme_image'),
                        ('res_id', '=', theme.id)
                    ], limit=1)
                    if attachment:
                        image_url = '/web/image/%s' % attachment.id
                        ICP.set_param('theme.background_image', image_url)
                else:
                    ICP.set_param('theme.background_image', '')

        # Nếu đang tắt theme (active_theme từ True -> False)
        if 'active_theme' in vals and not vals['active_theme']:
            deactivating_themes = was_active
            # Nếu không còn theme active nào, reset về mặc định
            if deactivating_themes and not self.search([('active_theme', '=', True)]):
                self._reset_to_default_theme()

        return result

    def get_bg_image_data_uri(self):
        """Trả về data URI để hiển thị ảnh trong CSS"""
        self.ensure_one()
        if not self.theme_image:
            return ''
        # Nếu theme_image là bytes, decode sang str
        img_str = self.theme_image.decode() if isinstance(self.theme_image, bytes) else self.theme_image
        return f"data:image/png;base64,{img_str}"