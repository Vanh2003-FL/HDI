# -*- coding: utf-8 -*-

# Import skill models first (before hr_employee)
from . import hr_skill
from . import hr_employee_skill

# Then other models  
from . import hr_employee
from . import hr_department
from . import hr_job
from . import hdi_organizational_models
from . import hdi_skills_competency
from . import hdi_performance_evaluation
from . import hr_leave
from . import hr_leave_extensions
from . import hr_evaluation
from . import hr_contract
# from . import hr_payroll  # Commented out - hr_payroll module may not be available
# from . import hr_work_entry  # Commented out - hr_work_entry module may not be available
from . import hdi_contract_payroll
from . import hdi_leave_advanced
from . import hdi_payroll_components
from . import res_config_settings
from . import res_config_extensions
