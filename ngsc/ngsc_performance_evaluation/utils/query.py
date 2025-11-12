QUERY_GET_UNIT_HIERARCHY = """
select uh.id as unit_id
from hr_employee he
         left join ngsc_unit_hierarchy uh
                   on (he.en_department_id = uh.en_department_id
                       or he.department_id = uh.department_id
                       or he.en_block_id = uh.block_id)
where he.id = %s
order by case
             when he.en_department_id = uh.en_department_id then 1
             when he.department_id = uh.department_id then 2
             when he.en_block_id = uh.block_id then 3
             else 4
             end
limit 1;
"""