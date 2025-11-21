#!/usr/bin/env python3
"""
Remove all remaining deprecated XML attributes
"""
import re
from pathlib import Path

def fix_xml_file(file_path):
    """Remove deprecated attributes from XML file"""
    try:
        content = file_path.read_text(encoding='utf-8')
        original = content
        
        # Remove create, edit, delete attributes
        content = re.sub(r'\s+create="[^"]*"', '', content)
        content = re.sub(r'\s+edit="[^"]*"', '', content)
        content = re.sub(r'\s+delete="[^"]*"', '', content)
        
        if content != original:
            file_path.write_text(content, encoding='utf-8')
            print(f"✓ Fixed {file_path}")
            return True
        return False
    except Exception as e:
        print(f"✗ Error fixing {file_path}: {e}")
        return False

def main():
    base_path = Path('.')
    
    files_to_fix = [
        'ngsd/ngsd_base/views/project_project.xml',
        'ngsd/ngsd_base/views/hr_employee.xml',
        'ngsd/approvals/views/approval_request_views.xml',
        'ngsd/helpdesk/views/helpdesk_views.xml',
        'ngsd/helpdesk/views/helpdesk_team_views.xml',
        'ngsc/ngsc_innovation/views/ngsc_innovation_idea_view.xml',
        'ngsc/ngsc_performance_evaluation/views/hr_performance_evaluation_views.xml',
        'ngsc/ngsc_nonproject_resource/views/nonproject_resource_planning_views.xml',
        'ngsc/ngsc_recruitment/views/source_personnel.xml',
    ]
    
    print("🔧 Removing deprecated XML attributes...")
    print("")
    
    fixed = 0
    for file_path in files_to_fix:
        full_path = base_path / file_path
        if full_path.exists():
            if fix_xml_file(full_path):
                fixed += 1
    
    print("")
    print(f"✅ Fixed {fixed} files")

if __name__ == '__main__':
    main()
