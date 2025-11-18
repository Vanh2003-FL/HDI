#!/bin/bash

# HDI HR Attendance Enhanced - Installation Check Script

echo "=========================================="
echo "HDI HR Attendance Enhanced"
echo "Installation Check Script"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check counter
PASS=0
FAIL=0

# Check function
check() {
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✅ PASS${NC}: $1"
        ((PASS++))
    else
        echo -e "${RED}❌ FAIL${NC}: $1"
        ((FAIL++))
    fi
}

echo "1. Checking module directory..."
test -d "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced"
check "Module directory exists"

echo "2. Checking __manifest__.py..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/__manifest__.py"
check "Manifest file exists"

echo "3. Checking models..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/models/hr_attendance.py"
check "hr_attendance.py exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/models/hr_attendance_log.py"
check "hr_attendance_log.py exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/models/hr_work_location.py"
check "hr_work_location.py exists"

echo "4. Checking controllers..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/controllers/main.py"
check "Controller main.py exists"

echo "5. Checking views..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/views/hr_attendance_views.xml"
check "Attendance views exist"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/views/menu.xml"
check "Menu views exist"

echo "6. Checking static files..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/static/src/js/my_attendances.js"
check "JavaScript file exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/static/src/xml/my_attendances.xml"
check "XML template exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/static/src/css/attendance.css"
check "CSS file exists"

echo "7. Checking security..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/security/ir.model.access.csv"
check "Access rights file exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/security/security.xml"
check "Security XML exists"

echo "8. Checking data files..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/data/ir_config_parameter.xml"
check "Config parameters exist"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/data/ir_cron.xml"
check "Cron jobs exist"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/data/demo_data.xml"
check "Demo data exists"

echo "9. Checking documentation..."
test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/README.md"
check "README.md exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/QUICKSTART.md"
check "QUICKSTART.md exists"

test -f "/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/INSTALL.md"
check "INSTALL.md exists"

echo "10. Checking Python dependencies..."
python3 -c "import geopy" 2>/dev/null
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ PASS${NC}: geopy installed"
    ((PASS++))
else
    echo -e "${YELLOW}⚠️  WARNING${NC}: geopy not installed (run: pip install geopy)"
    echo "   Module will work without geopy but no address reverse geocoding"
fi

echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo -e "${GREEN}Passed: $PASS${NC}"
echo -e "${RED}Failed: $FAIL${NC}"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Module is ready to install.${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Install geopy: pip install geopy"
    echo "2. Restart Odoo"
    echo "3. Apps > Update Apps List"
    echo "4. Search: HDI HR Attendance Enhanced"
    echo "5. Install"
    echo ""
    echo "See INSTALL.md for detailed instructions."
    exit 0
else
    echo -e "${RED}❌ Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
