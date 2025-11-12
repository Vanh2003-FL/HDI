QUERY_SYNC_UNIT_HIERARCHY = """
WITH deleted AS (
    DELETE FROM ngsc_unit_hierarchy RETURNING id
),

block_inserted AS (
    INSERT INTO ngsc_unit_hierarchy (name, unit_type, block_id, active)
    SELECT block.name, 'block', block.id, block.active
    FROM en_name_block AS block
    RETURNING id, block_id
),

department_inserted AS (
    INSERT INTO ngsc_unit_hierarchy (name, unit_type, department_id, parent_id, active)
    SELECT dept.name, 'department', dept.id, block_h.id, dept.active
    FROM hr_department AS dept
    JOIN en_name_block AS block ON dept.block_id = block.id
    JOIN block_inserted AS block_h ON block_h.block_id = block.id
    RETURNING id, department_id
)

INSERT INTO ngsc_unit_hierarchy (name, unit_type, en_department_id, parent_id, active)
SELECT en_dept.name, 'en_department', en_dept.id, dept_h.id, en_dept.active
FROM en_department AS en_dept
JOIN hr_department AS dept ON en_dept.department_id = dept.id
JOIN department_inserted AS dept_h ON dept_h.department_id = dept.id;

WITH emp_hierarchy AS (
  SELECT
    he.id as employee_id,
    COALESCE(uh1.id, uh2.id, uh3.id) as new_unit_id
  FROM hr_employee he
  LEFT JOIN ngsc_unit_hierarchy uh1
    ON uh1.unit_type = 'en_department' AND uh1.en_department_id = he.en_department_id
  LEFT JOIN ngsc_unit_hierarchy uh2
    ON uh2.unit_type = 'department' AND uh2.department_id = he.department_id
  LEFT JOIN hr_department d
    ON d.id = he.department_id
  LEFT JOIN ngsc_unit_hierarchy uh3
    ON uh3.unit_type = 'block' AND uh3.block_id = d.block_id
)
UPDATE hr_employee
SET unit_id = eh.new_unit_id
FROM emp_hierarchy eh
WHERE hr_employee.id = eh.employee_id;
"""

QUERY_UPDATE_UNIT_HIERARCHY = """
WITH emp_hierarchy AS (
  SELECT
    he.id as employee_id,
    COALESCE(uh1.id, uh2.id, uh3.id) as new_unit_id
  FROM hr_employee he
  LEFT JOIN ngsc_unit_hierarchy uh1
    ON uh1.unit_type = 'en_department' AND uh1.en_department_id = he.en_department_id
  LEFT JOIN ngsc_unit_hierarchy uh2
    ON uh2.unit_type = 'department' AND uh2.department_id = he.department_id
  LEFT JOIN hr_department d
    ON d.id = he.department_id
  LEFT JOIN ngsc_unit_hierarchy uh3
    ON uh3.unit_type = 'block' AND uh3.block_id = d.block_id
    WHERE he.id = %s
)
UPDATE hr_employee
SET unit_id = eh.new_unit_id
FROM emp_hierarchy eh
WHERE hr_employee.id = eh.employee_id;
"""