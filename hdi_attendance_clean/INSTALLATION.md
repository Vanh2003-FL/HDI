# INSTALLATION GUIDE - HDI Attendance Module

## Tóm tắt

Module HDI Attendance đã được refactor hoàn toàn để:
✅ Inherit hr.attendance thay vì tạo model mới
✅ Thêm GPS tracking cho check-in/check-out  
✅ Thêm work location selector
✅ Calendar view với color coding
✅ JavaScript customization cho MyAttendances widget

## Files đã sẵn sàng

Tất cả files trong `/workspaces/HDI/hdi_attendance_clean/` đã được:
- ✅ Syntax check passed (Python & XML)
- ✅ Model references updated (hdi.attendance → hr.attendance)
- ✅ Security files updated
- ✅ JavaScript/Templates created với Odoo 18 syntax

## Bước cài đặt nhanh

### 1. Copy module sang máy local

```bash
# Trên máy local của bạn (/home/va/odoo18)
# Giả sử bạn đã clone workspace này về local

# Option A: Nếu có git sync
cd /home/va/odoo18/ProjectOdoo/odoo/hdi/
git pull  # hoặc sync từ workspace

# Option B: Copy trực tiếp
cp -r /path/to/workspace/HDI/hdi_attendance_clean /home/va/odoo18/ProjectOdoo/odoo/hdi/
```

### 2. Update module list

```bash
cd /home/va/odoo18/ProjectOdoo/odoo
python odoo-bin -d hdi_odoo --update=all --stop-after-init
```

### 3. Install module

**Option A: Qua UI (Recommended)**
1. Start Odoo: `python odoo-bin -d hdi_odoo`
2. Vào **Apps**
3. Bỏ filter "Apps" (click vào chip "Apps" để remove)
4. Search "HDI Attendance"
5. Click **Install**

**Option B: Command line**
```bash
python odoo-bin -d hdi_odoo -i hdi_attendance_clean --stop-after-init
python odoo-bin -d hdi_odoo  # Start normally
```

### 4. Cấu hình ban đầu

#### A. Tạo Work Locations
1. Login as admin
2. Vào **Chấm công HDI > Cấu hình > Địa điểm làm việc**
3. Tạo ít nhất 1 location:
   - Tên: "Văn phòng Hà Nội"
   - Địa chỉ: "Số 1, Đường ABC, Hà Nội"
   - Active: ✅

#### B. Phân quyền Users
1. Vào **Settings > Users & Companies > Users**
2. Chọn user cần phân quyền
3. Tab "Access Rights" > Tìm "Attendance"
4. Chọn:
   - **Attendance User**: Cho nhân viên thường
   - **Attendance Manager**: Cho quản lý

### 5. Test ngay

1. **Test Check-in:**
   - Vào **Chấm công HDI > Chấm công của tôi**
   - Xem widget có hiển thị không
   - Chọn location từ dropdown
   - Click "Check In"
   - Cho phép browser truy cập location (nếu hỏi)
   - Verify: Record được tạo với GPS coordinates

2. **Test Calendar:**
   - Switch sang view Calendar
   - Verify: Event hiển thị với màu đỏ (chưa checkout)

3. **Test Check-out:**
   - Click "Check Out"
   - Verify: GPS coordinates checkout được lưu
   - Verify: Calendar event chuyển màu xanh (nếu đủ giờ)

## Troubleshooting

### Issue: Module không hiển thị trong Apps

**Solution:**
```bash
# Clear cache và update
python odoo-bin -d hdi_odoo --update=all --stop-after-init
# Restart và thử lại
python odoo-bin -d hdi_odoo
```

### Issue: Widget không hiển thị location dropdown

**Possible causes:**
1. JavaScript chưa load:
   ```bash
   # Clear assets
   python odoo-bin -d hdi_odoo -u hdi_attendance_clean --stop-after-init
   # Clear browser cache: Ctrl+Shift+Del
   ```

2. Check browser console (F12) for errors

3. Verify assets trong `__manifest__.py`:
   ```python
   'assets': {
       'web.assets_backend': [
           'hdi_attendance_clean/static/src/js/**/*',
           'hdi_attendance_clean/static/src/xml/**/*',
       ],
   }
   ```

### Issue: GPS không hoạt động

**Solutions:**
1. Chỉ hoạt động trên:
   - HTTPS connections
   - localhost/127.0.0.1
   
2. Check browser permissions:
   - Chrome: Settings > Privacy and security > Site Settings > Location
   - Firefox: about:preferences#privacy > Permissions > Location
   
3. Verify code trong browser console:
   ```javascript
   navigator.geolocation.getCurrentPosition(
       pos => console.log('GPS OK:', pos.coords),
       err => console.log('GPS Error:', err)
   );
   ```

### Issue: ImportError hoặc AttributeError

**Check:**
```bash
# Verify Python syntax
cd /home/va/odoo18/ProjectOdoo/odoo/hdi/hdi_attendance_clean
python3 -m py_compile models/*.py

# Check logs
tail -f /var/log/odoo/odoo.log
# hoặc
python odoo-bin -d hdi_odoo --log-level=debug
```

### Issue: View không hiển thị đúng

**Check XML:**
```bash
# Validate XML
xmllint --noout views/*.xml
xmllint --noout static/src/xml/*.xml

# Re-install
python odoo-bin -d hdi_odoo -u hdi_attendance_clean --stop-after-init
```

### Issue: Access denied

**Check security:**
1. Verify user có group "Attendance User" hoặc "Attendance Manager"
2. Check `security/ir.model.access.csv`:
   ```csv
   access_hr_attendance_user,access.hr.attendance.user,hr_attendance.model_hr_attendance,group_attendance_user,1,1,1,0
   ```
3. Re-install module để apply security:
   ```bash
   python odoo-bin -d hdi_odoo -u hdi_attendance_clean --stop-after-init
   ```

## Verification Checklist

Sau khi cài đặt, verify các items sau:

- [ ] Module appears in Apps list
- [ ] Module installs without errors
- [ ] Menu "Chấm công HDI" appears in main menu
- [ ] Submenu "Chấm công của tôi" accessible
- [ ] Work location management accessible (as manager)
- [ ] Can create work locations
- [ ] MyAttendances widget displays
- [ ] Location dropdown shows in widget
- [ ] Check-in button works
- [ ] GPS coordinates captured on check-in
- [ ] Location saved to attendance record
- [ ] Check-out button works
- [ ] GPS coordinates captured on check-out
- [ ] Calendar view displays events
- [ ] Calendar events have colors (red/green)
- [ ] List view has decoration colors
- [ ] Form view shows all fields including GPS
- [ ] Manager can view all attendances
- [ ] User can only see own attendances
- [ ] Pivot/Graph views work

## Files Structure Summary

```
hdi_attendance_clean/
├── README.md                    ← Full documentation
├── CHANGES.md                   ← Migration guide
├── INSTALLATION.md             ← This file
├── __init__.py
├── __manifest__.py             ← Dependencies, data files, assets
│
├── models/
│   ├── __init__.py
│   ├── attendance.py           ← Inherit hr.attendance + GPS fields
│   ├── employee.py             ← get_working_locations(), attendance_manual()
│   └── work_location.py        ← Work location model
│
├── views/
│   ├── attendance_views.xml    ← List, form, calendar, kanban views
│   ├── work_location_views.xml ← Location management views
│   └── menu_views.xml          ← Menu structure
│
├── security/
│   ├── attendance_security.xml ← Security groups
│   └── ir.model.access.csv    ← Access rights
│
└── static/src/
    ├── js/
    │   └── hdi_attendance.js   ← Patch MyAttendances widget
    └── xml/
        └── hdi_attendance.xml  ← QWeb templates
```

## Key Implementation Details

### Backend (Python)

**attendance.py:**
- Inherits `hr.attendance`
- Adds: work_location_id, GPS coordinates (checkin/checkout), color, warning_message
- Overrides: create(), write() to capture GPS from context

**employee.py:**
- Extends `hr.employee`
- Methods: get_working_locations(), get_en_checked_diff_ok(), attendance_manual()
- attendance_manual() captures GPS and location from JS context

### Frontend (JavaScript)

**hdi_attendance.js:**
- Patches MyAttendances.prototype
- willStart(): Loads working locations
- _manual_attendance(): Gets GPS, passes to backend via context

**hdi_attendance.xml:**
- Inherits HrAttendanceMyMainMenu template
- Injects location dropdown before employee greeting

### Context Flow

```
JavaScript (hdi_attendance.js)
    ↓ _manual_attendance()
    ↓ Gets GPS: navigator.geolocation.getCurrentPosition()
    ↓ Gets location: hdiLocationSelect.value
    ↓
    ↓ Pass context: {latitude, longitude, hdi_location_id}
    ↓
Python (employee.py)
    ↓ attendance_manual()
    ↓ Calls super (hr.attendance)
    ↓
Python (attendance.py)  
    ↓ create() or write()
    ↓ Captures from context:
    ↓   - vals['checkin_latitude'] = context.get('latitude')
    ↓   - vals['checkin_longitude'] = context.get('longitude')
    ↓   - vals['work_location_id'] = context.get('hdi_location_id')
    ↓
Database (hr_attendance table)
    ↓ Saved with GPS and location
```

## Support

Nếu gặp vấn đề:

1. **Check logs:**
   ```bash
   tail -f /var/log/odoo/odoo.log
   ```

2. **Debug mode:**
   ```bash
   python odoo-bin -d hdi_odoo --log-level=debug
   ```

3. **Browser console:** F12 để xem JavaScript errors

4. **Database query:**
   ```sql
   -- Check if records are created with GPS
   SELECT employee_id, check_in, check_out, 
          checkin_latitude, checkin_longitude,
          work_location_id
   FROM hr_attendance 
   ORDER BY check_in DESC 
   LIMIT 10;
   ```

## Next Steps

1. ✅ Install module
2. ✅ Create work locations  
3. ✅ Assign user permissions
4. ✅ Test check-in/check-out
5. ✅ Verify GPS tracking
6. 📋 User training
7. 📋 Document business processes
8. 📋 Monitor and optimize

Good luck! 🚀
