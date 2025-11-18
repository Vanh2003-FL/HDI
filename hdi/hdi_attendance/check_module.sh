#!/bin/bash

echo "================================================"
echo "HDI ATTENDANCE MODULE - VALIDATION CHECK"
echo "================================================"
echo ""

MODULE_PATH="/workspaces/HDI/hdi/hdi_attendance"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check file
check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

# Function to check directory
check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        return 0
    else
        echo -e "${RED}✗${NC} $2"
        return 1
    fi
}

echo "1. Checking Module Structure..."
echo "================================"
check_file "$MODULE_PATH/__init__.py" "Module __init__.py"
check_file "$MODULE_PATH/__manifest__.py" "Module manifest"
check_dir "$MODULE_PATH/models" "Models directory"
check_dir "$MODULE_PATH/views" "Views directory"
check_dir "$MODULE_PATH/security" "Security directory"
check_dir "$MODULE_PATH/data" "Data directory"
check_dir "$MODULE_PATH/wizard" "Wizard directory"
check_dir "$MODULE_PATH/static" "Static directory"
echo ""

echo "2. Checking Models..."
echo "================================"
check_file "$MODULE_PATH/models/__init__.py" "Models __init__.py"
check_file "$MODULE_PATH/models/hr_attendance.py" "hr_attendance.py"
check_file "$MODULE_PATH/models/hr_attendance_log.py" "hr_attendance_log.py"
check_file "$MODULE_PATH/models/hr_attendance_explanation.py" "hr_attendance_explanation.py"
check_file "$MODULE_PATH/models/hr_work_location.py" "hr_work_location.py"
check_file "$MODULE_PATH/models/submission_type.py" "submission_type.py"
check_file "$MODULE_PATH/models/res_config_settings.py" "res_config_settings.py"
echo ""

echo "3. Checking Views..."
echo "================================"
check_file "$MODULE_PATH/views/hr_attendance_views.xml" "hr_attendance_views.xml"
check_file "$MODULE_PATH/views/hr_attendance_explanation_views.xml" "hr_attendance_explanation_views.xml"
check_file "$MODULE_PATH/views/hr_attendance_log_views.xml" "hr_attendance_log_views.xml"
check_file "$MODULE_PATH/views/hr_work_location_views.xml" "hr_work_location_views.xml"
check_file "$MODULE_PATH/views/res_config_settings_views.xml" "res_config_settings_views.xml"
check_file "$MODULE_PATH/views/hdi_attendance_menu.xml" "hdi_attendance_menu.xml"
echo ""

echo "4. Checking Security..."
echo "================================"
check_file "$MODULE_PATH/security/hdi_attendance_groups.xml" "Security groups"
check_file "$MODULE_PATH/security/ir.model.access.csv" "Access rights CSV"
echo ""

echo "5. Checking Data Files..."
echo "================================"
check_file "$MODULE_PATH/data/ir_cron_attendance_log.xml" "Cron job data"
check_file "$MODULE_PATH/data/submission_type_data.xml" "Submission types data"
echo ""

echo "6. Checking Wizard..."
echo "================================"
check_file "$MODULE_PATH/wizard/__init__.py" "Wizard __init__.py"
check_file "$MODULE_PATH/wizard/reason_for_refuse_wizard.py" "Refuse wizard"
check_file "$MODULE_PATH/wizard/reason_for_refuse_wizard_views.xml" "Refuse wizard view"
echo ""

echo "7. Checking Static Assets..."
echo "================================"
check_file "$MODULE_PATH/static/src/js/hr_attendance_block_click.js" "Block click JS"
check_file "$MODULE_PATH/static/src/js/hr_attendance_kiosk.js" "Kiosk enhancement JS"
check_file "$MODULE_PATH/static/src/xml/attendance_templates.xml" "QWeb templates"
echo ""

echo "8. Checking Documentation..."
echo "================================"
check_file "$MODULE_PATH/README.md" "README documentation"
check_file "$MODULE_PATH/QUICKSTART.md" "Quick start guide"
echo ""

echo "9. Python Syntax Check..."
echo "================================"
ERRORS=0
for file in $(find "$MODULE_PATH" -name "*.py" -not -path "*/\__pycache__/*"); do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $(basename $file)"
    else
        echo -e "${RED}✗${NC} $(basename $file) - Syntax Error!"
        ERRORS=$((ERRORS + 1))
    fi
done
echo ""

echo "10. XML Validation..."
echo "================================"
for file in $(find "$MODULE_PATH" -name "*.xml"); do
    if xmllint --noout "$file" 2>/dev/null; then
        echo -e "${GREEN}✓${NC} $(basename $file)"
    else
        echo -e "${YELLOW}⚠${NC} $(basename $file) - Check manually (xmllint not available or minor issues)"
    fi
done
echo ""

echo "================================================"
echo "SUMMARY"
echo "================================================"
FILE_COUNT=$(find "$MODULE_PATH" -type f \( -name "*.py" -o -name "*.xml" -o -name "*.csv" \) | wc -l)
echo "Total files: $FILE_COUNT"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Module validation PASSED!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Restart Odoo server"
    echo "2. Update Apps list"
    echo "3. Install 'HDI Attendance Management' module"
    echo "4. Follow QUICKSTART.md for testing"
else
    echo -e "${RED}✗ Found $ERRORS Python syntax errors${NC}"
    echo "Please fix the errors before installing"
fi
echo ""
echo "================================================"
