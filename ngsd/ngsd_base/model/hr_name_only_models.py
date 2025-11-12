from odoo import *
from odoo import _
from odoo.exceptions import UserError
from odoo import _, api, fields, models


org_chart_classes = {
    0: "level-0",
    1: "level-1",
    2: "level-2",
    3: "level-3",
    4: "level-4",
}


class BFSI(models.Model):
    _name = 'en.bfsi'
    _description = 'Phân khúc khách hàng BFSI'

    name = fields.Char(string='Tên')


class NameArea(models.Model):
    _name = 'en.name.area'
    _description = 'Khu vực'

    name = fields.Char(string='Khu vực')
    block_ids = fields.One2many('en.name.block', 'area_id', string='Khối')
    en_project_implementation_id = fields.Many2one(string='Giám đốc triển khai', comodel_name='res.users')

    @api.model
    def get_organization_data(self):
        domain_area = []
        domain_department = []
        domain_block = []

        en_fiscal_year_id = int(self.env['ir.config_parameter'].sudo().get_param('en_fiscal_year_id'))
        if not en_fiscal_year_id:
            raise UserError('Vui lòng thiết lập năm tài chính!')
        en_fiscal_year = self.env['en.fiscal.year'].browse(en_fiscal_year_id)
        date_from = en_fiscal_year.start_date
        date_to = en_fiscal_year.end_date

        if self._context.get('en_department_ids'):
            domain_department += [('id', 'in', self._context.get('en_department_ids'))]
            departments = self.env['hr.department'].search(domain_department)
            domain_block += [('id', 'in', departments.block_id.ids)]

        if self._context.get('en_block_ids'):
            domain_block += [('id', 'in', self._context.get('en_block_ids'))]
        if domain_block:
            blocks = self.env['en.name.block'].search(domain_block)
            domain_area += [('id', 'in', blocks.area_id.ids)]

        if self._context.get('en_area_ids'):
            domain_area += [('id', 'in', self._context.get('en_area_ids'))]

        areas = self.search(domain_area)

        data = {"id": None, "name": "NGSC", "title": "Công ty Cổ phần Tư vấn Công nghệ NGS", "children": []}

        for area in areas:
            boundary_area = 0
            employee_area = self.env['hr.employee'].sudo().search_count([('en_area_id', '=', area.id)])
            children_area = []
            if area.block_ids:
                for block in area.block_ids.filtered_domain(domain_block):
                    boundary_block = 0
                    employee_block = self.env['hr.employee'].sudo().search_count([('en_block_id', '=', block.id)])
                    children_block = []
                    if block.department_ids:
                        for department in block.department_ids.filtered_domain(domain_department):
                            boundary_department = sum(self.env['hr.boundary.master'].sudo().search([('department_id', '=', department.id), ('date', '>=', date_from), ('date', '<=', date_to)]).mapped('hr_boundary'))
                            employee_department = self.env['hr.employee'].sudo().search_count([('department_id', '=', department.id)])
                            title = f'Nhân viên hiện tại: {employee_department}<br/>Định biên: {boundary_department}'
                            department_data = {
                                "id": department.id,
                                "name": department.name,
                                "title": title,
                                "className": org_chart_classes[2],
                            }
                            if department.en_department_ids:
                                department_data['children'] = []
                                for en_department in department.en_department_ids:
                                    employee_en_department = self.env['hr.employee'].sudo().search_count([('en_department_id', '=', en_department.id)])
                                    title = f'Nhân viên hiện tại: {employee_en_department}'
                                    en_department_data = {
                                        "id": en_department.id,
                                        "name": en_department.name,
                                        "title": title,
                                        "className": org_chart_classes[3],
                                    }
                                    department_data['children'].append(en_department_data)
                            children_block.append(department_data)
                            boundary_block += boundary_department
                    title_block = f'Nhân viên hiện tại: {employee_block}<br/>Định biên: {boundary_block}'
                    block_data = {
                        "id": block.id,
                        "name": block.name,
                        "title": title_block,
                        "className": org_chart_classes[1],
                        "hybrid": True
                    }
                    if children_block:
                        block_data['children'] = children_block
                    children_area.append(block_data)
                    boundary_area += boundary_block
            title_area = f'Nhân viên hiện tại: {employee_area}<br/>Định biên: {boundary_area}'
            child_data = {
                "id": area.id,
                "name": area.name,
                "title": title_area,
                "className": org_chart_classes[0],
            }
            if children_area:
                child_data['children'] = children_area
            # data.get("children").append(child_data)
            data.get("children").append(child_data)
        return data


class NameLevel(models.Model):
    _name = 'en.name.level'
    _description = 'Cấp bậc'

    sequence = fields.Integer('Vị trí sơ đồ', default=1)
    name = fields.Char(string='Cấp bậc')
    # code = fields.Char(string='Ký hiệu')


class NameBlock(models.Model):
    _name = 'en.name.block'
    _description = 'Khối'

    name = fields.Char(string='Tên Khối', required=True)
    code = fields.Char(string='Mã khối')
    en_department_ids = fields.One2many(comodel_name='en.department', string='Phòng', inverse_name='block_id')
    hr_job_ids = fields.One2many(comodel_name='hr.job', string='Vị trí', inverse_name='block_id')
    area_id = fields.Many2one('en.name.area', string='Khu vực', required=True)
    department_ids = fields.One2many('hr.department', 'block_id', string='Trung tâm/Ban')
    active = fields.Boolean(string='Lưu trữ', default=True)
    en_project_implementation_id = fields.Many2one('res.users', 'Trưởng khối')
    en_area_ids = fields.Many2many("en.name.area", "en_block_en_area_rel", "en_block_id", "en_area_id",
                                   string="Khu vực khác")

    def unlink(self):
        list_name = [rec.name for rec in self if any(department.block_id for department in rec.department_ids)]
        if list_name:
            raise UserError(f"Khối {','.join(list_name)} đang có Trung tâm/ban gắn với nó, vui lòng kiểm tra lại!")
        return super().unlink()


class Department(models.Model):
    _name = 'en.department'
    _description = 'Phòng'

    name = fields.Char(string='Tên Phòng')
    code = fields.Char(string='Mã Phòng')
    block_id = fields.Many2one(comodel_name='en.name.block', string='Tên khối', related='department_id.block_id', store=True)
    department_id = fields.Many2one('hr.department', 'Tên Trung tâm/Ban', required=True)
    manager_id = fields.Many2one('hr.employee', 'Trưởng phòng')
    deputy_manager_id = fields.Many2one(string='Phó phòng', comodel_name='hr.employee')
    active = fields.Boolean(string='Hoạt động', default=True)
    hr_employee_ids = fields.One2many(comodel_name='hr.employee', inverse_name='en_department_id', domain=[('is_hidden','=', False)], string='Nhân viên')
    count_hr_employee = fields.Integer(string='Nhân viên', compute='compute_count_hr_employee_ids')
    code_block = fields.Char(string='Mã khối', related='block_id.code', store=True)

    @api.depends('hr_employee_ids')
    def compute_count_hr_employee_ids(self):
        for rec in self:
            rec.count_hr_employee = len(rec.hr_employee_ids)


class Role(models.Model):
    _name = 'en.role'
    _description = 'Vai trò'

    name = fields.Char(string='Tên vai trò')
    from_groups_with_love = fields.One2many(string='Nhóm quyền đại diện', comodel_name='res.groups', inverse_name='from_role_with_love', readonly=True)

    def should_we_make_group(self):
        rec = self
        vals = {'name': f'{rec.name}', 'from_role_with_love': rec.id, 'category_id': self.env.ref('base.module_category_usability').id}
        if not rec.from_groups_with_love:
            self.env['res.groups'].sudo().create(vals)
        else:
            rec.from_groups_with_love.sudo().write(vals)
        return rec.from_groups_with_love


class JobPosition(models.Model):
    _name = 'en.job.position'
    _description = 'Vị trí'
    _parent_store = True
    _order = 'sequence asc,id desc'

    def _get_employee_data(self, level=0):
        return {
            "id": self.id,
            "name": self.name,
            "title": self.job_id.name,
            "className": org_chart_classes[level],
        }

    @api.constrains("parent_id")
    def _check_parent_id(self):
        if not self._check_recursion():
            raise ValidationError(_("You cannot assign manager recursively."))

    sequence = fields.Integer(string='Cấp độ', default=0, required=True)
    name = fields.Char(string='Vị trí')
    parent_path = fields.Char(index=True)
    parent_id = fields.Many2one(string='Vị trí cấp trên', comodel_name='en.job.position')
    child_ids = fields.One2many(string='Vị trí cấp dưới', comodel_name='en.job.position', inverse_name='parent_id')


class ProjectType(models.Model):
    _name = 'en.project.type'
    _description = 'Loại dự án'

    name = fields.Char(string='Loại dự án')
    is_presale = fields.Boolean('Presale')


class ProjectModel(models.Model):
    _name = 'en.project.model'
    _description = 'Mô hình thực hiện dự án'

    name = fields.Char(string='Mô hình thực hiện dự án')


class Branch(models.Model):
    _name = 'en.branch'
    _description = 'Ngành'

    name = fields.Char(string='Ngành')


class Type(models.Model):
    _name = 'en.type'
    _description = 'Loại nhân sự'

    name = fields.Char(string='Loại nhân sự')
    internal_ok = fields.Boolean(string='Nội bộ', default=True)
    en_internal = fields.Boolean(string='Nội bộ', default=False)
    is_intern = fields.Boolean(string='Thực tập sinh', default=False)
    is_hidden = fields.Boolean(string='Nguồn lực ẩn')
    is_os = fields.Boolean('OS')



class ViewUnit(models.Model):
    _name = 'en.view.unit'
    _description = 'Đơn vị xem'

    name = fields.Char(string='Đơn vị xem')


class ListProject(models.Model):
    _name = 'en.list.project'
    _description = 'Danh mục dự án'

    name = fields.Char(string='Danh mục dự án')


class CustomerType(models.Model):
    _name = 'en.customer.type'
    _description = 'Loại khách hàng'

    name = fields.Char(string='Loại khách hàng')


class ProjectTypeSource(models.Model):
    _name = 'project.type.source'
    _description = "Loại hình cung cấp dự án"

    name = fields.Char(string="Loại hình", required=True)


class StageType(models.Model):
    _name = 'en.stage.type'
    _description = "Loại giai đoạn"

    name = fields.Char(string="Tên loại giai đoạn", required=True)

class HrJob(models.Model):
    _inherit = 'hr.job'
    _description = 'Vị trí công việc'

    block_id = fields.Many2one(comodel_name='en.name.block', string='Tên khối')
    en_department_id = fields.Many2one(comodel_name='en.department', string='Tên phòng', domain="[('department_id', '=', department_id)]")
    department_id = fields.Many2one(domain="['&',('block_id', '=?', block_id), '|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    cap_bac_level_id = fields.Many2one(comodel_name='en.name.level', string='Cấp bậc')
    ky_hieu_level_id = fields.Char(related='hr_symbol_id.name', string='Ký hiệu')
    active = fields.Boolean(string='Lưu trữ', default=True)
    hr_boundary_master_ids = fields.One2many(comodel_name='hr.boundary.master', string='Phòng', inverse_name='hr_job_id')
    family_id = fields.Many2one(comodel_name='hr.family', string='Family', domain="[('parent_id','=', False)]")
    sub_family_id = fields.Many2one(comodel_name='hr.family', string='Sub-Family', domain="[('parent_id','!=', False), ('parent_id', '=?', family_id)]")
    job_code_id = fields.Many2one(comodel_name='job.code', string='Job code')
    level_id = fields.Many2one(comodel_name='hr.level', string='Level', domain="[('parent_id','=', False)]")
    sub_level_id = fields.Many2one(comodel_name='hr.level', string='Sub-Level',domain="[('parent_id','!=', False), ('parent_id', '=?', level_id)]")
    hr_symbol_id = fields.Many2one(comodel_name='hr.symbol', string='Ký hiệu')


    @api.onchange('department_id')
    def get_block_id(self):
        self.block_id = self.department_id.block_id

    @api.onchange('sub_family_id')
    def get_family_id(self):
        if not self.family_id:
            self.family_id = self.sub_family_id.parent_id

    @api.onchange('sub_level_id')
    def get_level_id(self):
        if not self.level_id:
            self.level_id = self.sub_level_id.parent_id

    @api.onchange('level_id')
    def get_sub_level_id(self):
        if self.sub_level_id.parent_id != self.level_id:
            self.sub_level_id = False

    @api.onchange('family_id')
    def get_sub_family_id(self):
        if self.sub_family_id.parent_id != self.family_id:
            self.sub_family_id = False


class HrSymbol(models.Model):
    _name = 'hr.symbol'
    _description = 'Ký hiệu'


    name = fields.Char(string='Ký hiệu', required=True)

class HrFamily(models.Model):
    _name = 'hr.family'
    _description = 'Family'
    _parent_store = True

    name = fields.Char(string='Tên Family', required=True)
    parent_id = fields.Many2one('hr.family', string='Family')
    sub_family = fields.One2many('hr.family', 'parent_id', string='Sub-Family')
    parent_path = fields.Char(index=True)

class JobCode(models.Model):
    _name = 'job.code'
    _description = 'mã công việc'


    name = fields.Char(string='Job code', required=True)

class HrLevel(models.Model):
    _name = 'hr.level'
    _description = 'Cấp độ'
    _parent_store = True


    name = fields.Char(string='Tên Level', required='True')
    parent_id = fields.Many2one(comodel_name='hr.level', string='Level')
    sub_level = fields.One2many(comodel_name='hr.level', inverse_name='parent_id', string='Sub-Level')
    parent_path = fields.Char(index=True)