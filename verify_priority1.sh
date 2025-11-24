#!/bin/bash

# HDI Attendance - Quick Verification Script
# Kiểm tra nhanh các file đã được tạo/sửa đổi

echo "=================================================="
echo "HDI ATTENDANCE - PRIORITY 1 VERIFICATION"
echo "=================================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Counter
PASS=0
FAIL=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $1"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1 - MISSING"
        ((FAIL++))
    fi
}

check_string_in_file() {
    if grep -q "$2" "$1"; then
        echo -e "${GREEN}✓${NC} $1 contains '$2'"
        ((PASS++))
    else
        echo -e "${RED}✗${NC} $1 missing '$2'"
        ((FAIL++))
    fi
}

echo "1. Checking Model Files..."
echo "----------------------------"
check_file "hdi/hdi_attendance/models/hr_attendance.py"
check_file "hdi/hdi_attendance/models/hr_attendance_explanation.py"
check_file "hdi/hdi_attendance/models/hr_attendance_explanation_detail.py"
check_file "hdi/hdi_attendance/models/submission_type.py"
echo ""

echo "2. Checking Data Files..."
echo "----------------------------"
check_file "hdi/hdi_attendance/data/sequence_data.xml"
check_file "hdi/hdi_attendance/data/system_parameter_data.xml"
check_file "hdi/hdi_attendance/data/submission_type_data.xml"
check_file "hdi/hdi_attendance/data/ir_cron_attendance_log.xml"
echo ""

echo "3. Checking View Files..."
echo "----------------------------"
check_file "hdi/hdi_attendance/views/hr_attendance_views.xml"
check_file "hdi/hdi_attendance/views/hr_attendance_explanation_views.xml"
check_file "hdi/hdi_attendance/views/submission_type_views.xml"
check_file "hdi/hdi_attendance/views/hdi_attendance_menu.xml"
echo ""

echo "4. Checking Security Files..."
echo "----------------------------"
check_file "hdi/hdi_attendance/security/ir.model.access.csv"
echo ""

echo "5. Checking Key Model Implementations..."
echo "----------------------------"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance.py" "en_late"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance.py" "en_soon"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance.py" "color"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance.py" "en_distance"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance.py" "auto_log_out_job"
echo ""

check_string_in_file "hdi/hdi_attendance/models/hr_attendance_explanation.py" "line_ids"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance_explanation.py" "approver_ids"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance_explanation.py" "send_approve"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance_explanation.py" "button_approve"
check_string_in_file "hdi/hdi_attendance/models/hr_attendance_explanation.py" "check_limit_explanation"
echo ""

echo "6. Checking Data Records..."
echo "----------------------------"
check_string_in_file "hdi/hdi_attendance/data/submission_type_data.xml" "submission_type_ma"
check_string_in_file "hdi/hdi_attendance/data/submission_type_data.xml" "submission_type_dcc"
check_string_in_file "hdi/hdi_attendance/data/submission_type_data.xml" "submission_type_dco"
check_string_in_file "hdi/hdi_attendance/data/submission_type_data.xml" "submission_type_tsda"
check_string_in_file "hdi/hdi_attendance/data/submission_type_data.xml" "submission_type_tsnda"
echo ""

check_string_in_file "hdi/hdi_attendance/data/system_parameter_data.xml" "en_max_attendance_request_count"
check_string_in_file "hdi/hdi_attendance/data/system_parameter_data.xml" "en_attendance_request_start"
echo ""

check_string_in_file "hdi/hdi_attendance/data/ir_cron_attendance_log.xml" "ir_cron_auto_logout_attendance"
echo ""

echo "7. Checking View Implementation..."
echo "----------------------------"
check_string_in_file "hdi/hdi_attendance/views/hr_attendance_views.xml" "view_attendance_calendar_hdi"
check_string_in_file "hdi/hdi_attendance/views/hr_attendance_views.xml" "color=\"color\""
check_string_in_file "hdi/hdi_attendance/views/hr_attendance_explanation_views.xml" "line_ids"
check_string_in_file "hdi/hdi_attendance/views/hr_attendance_explanation_views.xml" "approver_ids"
echo ""

echo "8. Checking __manifest__.py..."
echo "----------------------------"
check_string_in_file "hdi/hdi_attendance/__manifest__.py" "sequence_data.xml"
check_string_in_file "hdi/hdi_attendance/__manifest__.py" "system_parameter_data.xml"
check_string_in_file "hdi/hdi_attendance/__manifest__.py" "submission_type_views.xml"
echo ""

echo "9. Checking Security Access Rights..."
echo "----------------------------"
check_string_in_file "hdi/hdi_attendance/security/ir.model.access.csv" "model_hr_attendance_explanation_detail"
check_string_in_file "hdi/hdi_attendance/security/ir.model.access.csv" "model_hr_attendance_explanation_approver"
echo ""

echo ""
echo "=================================================="
echo "VERIFICATION SUMMARY"
echo "=================================================="
echo -e "${GREEN}PASSED:${NC} $PASS checks"
echo -e "${RED}FAILED:${NC} $FAIL checks"
echo ""

if [ $FAIL -eq 0 ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Upgrade module: ./odoo-bin -u hdi_attendance -d <database>"
    echo "2. Test in browser: http://localhost:8069"
    echo "3. Check menu: Chấm công HDI → Chấm công của tôi"
    echo ""
else
    echo -e "${RED}✗ SOME CHECKS FAILED!${NC}"
    echo "Please review the missing files/content above."
    echo ""
fi

echo "=================================================="
