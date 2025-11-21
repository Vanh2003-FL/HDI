# Copyright 2020 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models, api, _, exceptions
from odoo.exceptions import ValidationError

org_chart_classes = {
    0: "level-0",
    1: "level-1",
    2: "level-2",
    3: "level-3",
    4: "level-4",
}


class HrOrgChartReport(models.AbstractModel):
    _name = "hr.org.chart.report"
    _description = "Sơ đồ tổ chức theo hình cây"

    @api.model
    def get_organization_data(self):
        domain_area = []
        domain_department = []
        domain_block = []

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

        areas = self.env['en.name.area']    .search(domain_area)

        data = {"id": None, "name": "NGSC", "title": "Công ty Cổ phần Tư vấn Công nghệ NGS", "children": []}

        for area in areas:
            children_area = []
            if area.block_ids:
                for block in area.block_ids.filtered_domain(domain_block):
                    children_block = []
                    if block.department_ids:
                        for department in block.department_ids.filtered_domain(domain_department):
                            title = department.manager_id.name
                            department_data = {
                                "id": department.id,
                                "name": f'Trưởng Trung tâm/Ban {department.name}' ,
                                "title": title or 'Trống',
                                "className": org_chart_classes[2],
                            }
                            if department.en_department_ids:
                                department_data['children'] = []
                                for en_department in department.en_department_ids:
                                    title = en_department.manager_id.name
                                    en_department_data = {
                                        "id": en_department.id,
                                        "name": f'Trưởng phòng {en_department.name}',
                                        "title": title or 'Trống',
                                        "className": org_chart_classes[3],
                                    }
                                    all_level = self.env['hr.employee'].sudo().search([('en_department_id', '=', en_department.id)]).en_level_id
                                    if all_level:
                                        depth_level = max(all_level.mapped('sequence'))
                                        en_department_data['children'] = self._get_children_data(en_department, 1, depth_level)
                                    department_data['children'].append(en_department_data)
                            children_block.append(department_data)
                    title_block = block.en_project_implementation_id.name
                    block_data = {
                        "id": block.id,
                        "name": f'Trưởng khối {block.name}',
                        "title": title_block or 'Trống',
                        "className": org_chart_classes[1],
                    }
                    if children_block:
                        block_data['children'] = children_block
                    children_area.append(block_data)
            title_area = ''
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

    # def get_employee_data(self, en_department, depth_level):
    #     res = []
    #     for depth in depth_level:
    #         employees = self.env['hr.employee'].sudo().search([('en_department_id', '=', en_department.id), ('en_level_id.sequence', '=', depth)])

    @api.model
    def _get_children_data(self, en_department, level, max_level, path=False, is_emty=False):
        children = []
        employee_domain = [('en_department_id', '=', en_department.id), ('en_level_id.sequence', '=', level)]
        if path:
            employee_domain += [('parent_path_chart', 'ilike', f'%{path}/%')]
        domain = employee_domain
        if is_emty:
            domain += [('parent_path_chart', 'ilike', f'%/False LV{level-1}/')]
        employees = self.env['hr.employee'].sudo().search(domain)
        employees -= en_department.manager_id
        for employee in employees:
            data = self._get_employee_data(employee, level + 3)
            if level < max_level:
                data["children"] = self._get_children_data(en_department, level + 1, max_level, path=employee.parent_path_chart)
            children.append(data)
        if self.env['hr.employee'].sudo().search([('en_department_id', '=', en_department.id), ('parent_path_chart', 'ilike', f'{path or ""}/False LV{level}')]):
            data_emty = {
                "id": 1,
                "name": self.env['en.name.level'].search([('sequence', '=', level)], limit=1).name,
                "title": 'Trống',
                "className": org_chart_classes.get(level + 3),
            }
            if level < max_level:
                data_emty["children"] = self._get_children_data(en_department, level + 1, max_level, path=f'{path or ""}/False LV{level}', is_emty=True)
            children.append(data_emty)
        return children

    def _get_employee_data(self, employee, level):
        res = {
            "id": employee.id,
            "title": employee.name,
            "name": employee.job_id.name,
            "className": org_chart_classes.get(level),
        }
        return res
