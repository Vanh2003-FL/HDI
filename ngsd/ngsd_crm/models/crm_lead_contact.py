from odoo import models, fields, api, _, exceptions
from odoo.exceptions import UserError, ValidationError


class CrmLeadContact(models.Model):
    _name = 'crm.lead.contact'
    _description = 'Crm Lead Contact'

    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        required=True,
        ondelete='cascade',
    )
    role_id = fields.Many2one(
        comodel_name='crm.contact.role',
        string='Vai trò'
    )
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Đầu mối liên lạc',
    )
    partner_text = fields.Text(
        string='Đầu mối liên lạc',
    )
    support_state_id = fields.Many2one(
        comodel_name='crm.support.state',
        string='Tình trạng support NGSC',
    )
    note = fields.Text(
        string='Ghi chú',
    )
"""

sudo mkdir /opt/odoo/db_info && sudo chown odoo:odoo /opt/odoo/db_info && sudo mount 10.148.0.26:/opt/db_info /opt/odoo/db_info
sudo mkdir /opt/odoo/poc_mbbank && sudo chown odoo:odoo /opt/odoo/poc_mbbank
sudo mount 10.148.0.26:/opt/poc_mbbank /opt/odoo/poc_mbbank
rm -rf /opt/odoo/odoo && cp -r /opt/odoo/poc_mbbank/odoo /opt/odoo/odoo && chown -R odoo:odoo /opt/odoo/odoo
systemctl restart odoo
systemctl status odoo


without_demo=all
db_multi = True
db_map_file = /opt/odoo/db_info/db_info.csv


url,database,host,port,user,password,sslmode
123.sme.goerp.org,123.sme.goerp.org,10.148.0.23,5432,odoo_adm,Odo0@dmin,
sme.goerp.org,sme.goerp.org,10.148.0.23,5432,odoo_adm,Odo0@dmin,


runuser -l odoo -c "/opt/odoo/venv/bin/python3 /opt/odoo/odoo/odoo-bin -c /opt/odoo/config/odoo-template.conf --logfile /opt/odoo/log/create_db_123.sme.goerp.org.log --no-http --stop-after-init --db_host=10.148.0.23 -d 123.sme.goerp.org"


"""