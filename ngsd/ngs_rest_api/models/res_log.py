from odoo import models, api, fields
from psycopg2.extensions import AsIs

# Log thêm thời gian bắt đầu request
from odoo.http import request
from odoo.addons.component.core import AbstractComponent
class BaseRESTService(AbstractComponent):
    _inherit = "base.rest.service"

    def _dispatch_with_db_logging(self, method_name, *args, params=None):
        request.__rest_start_time = fields.Datetime.now()
        return super()._dispatch_with_db_logging(method_name, *args, params=params)

    def _log_call_in_db_values(self, _request, *args, params=None, **kw):
        result = super()._log_call_in_db_values(_request, *args, params=params, **kw)
        result.update(request_start_date = request.__rest_start_time)
        return result

# Sửa lỗi có tình huống có call res-api nhưng không có bản ghi log được tạo ra
# Nguyên nhân: Log được tạo ra bằng cách đặt hàm _dispatch trong khối try catch. Nhưng sau khối này còn 1 lệnh env.flush và có exception ở đây -> bị rollback
# Giải pháp: Khi có rollback thì vẫn tạo bản ghi bằng sql thuần
class RESTLog(models.Model):
    _inherit = "rest.log"

    request_start_date = fields.Datetime('Request start at')
                
    @api.model
    def _create_sql(self, cr, stored):
        assert stored

        quote = '"{}"'.format
        # column names, formats and values (for common fields)
        columns0 = [('id', "nextval(%s)", self._sequence)]
        if self._log_access:
            columns0.append(('create_uid', "%s", self._uid))
            columns0.append(('create_date', "%s", AsIs("(now() at time zone 'UTC')")))
            columns0.append(('write_uid', "%s", self._uid))
            columns0.append(('write_date', "%s", AsIs("(now() at time zone 'UTC')")))
        
        # determine column values
        columns = [column for column in columns0 if column[0] not in stored]
        for name, val in sorted(stored.items()):
            field = self._fields[name]
            assert field.store

            if field.column_type:
                col_val = field.convert_to_column(val, self, stored)
                columns.append((name, field.column_format, col_val))

        query = "INSERT INTO {} ({}) VALUES ({}) RETURNING id".format(
            quote(self._table),
            ", ".join(quote(name) for name, fmt, val in columns),
            ", ".join(fmt for name, fmt, val in columns),
        )
        params = [val for name, fmt, val in columns]
        cr.execute(query, params)
        return cr.fetchone()[0]

    @api.model
    def create(self, vals):
        @self.env.cr.postrollback.add
        def create_force_postrollback():
            with self.pool.cursor() as cr_create:
                vals_clone = dict(vals)
                vals_clone.update({
                    'error': 'Có lỗi xảy ra',
                    'state': 'failed',
                })
                self._create_sql(cr_create, vals_clone)
        return super().create(vals)
