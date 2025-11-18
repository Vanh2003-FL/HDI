# Quick Start Guide - HDI Attendance

## Cài đặt nhanh

### 1. Restart Odoo Server
```bash
# Nếu dùng docker
docker restart <odoo_container>

# Hoặc restart service
sudo systemctl restart odoo
```

### 2. Update Apps List
1. Vào Odoo
2. Bật Developer Mode: Settings > Activate Developer Mode
3. Vào Apps
4. Click "Update Apps List"
5. Search "HDI Attendance"

### 3. Install Module
1. Tìm module "HDI Attendance Management"
2. Click "Install"
3. Đợi cài đặt hoàn tất

## Test cơ bản

### Test 1: Chấm công cơ bản
```
1. Vào Attendances menu
2. Click "Check In / Check Out"
3. Chọn địa điểm (nếu có)
4. Click "Bấm vào check in" button
5. Kiểm tra thông báo thành công
```

### Test 2: Xem chấm công của tôi
```
1. Vào Attendances > Chấm công của tôi
2. Kiểm tra danh sách chấm công
3. Click vào 1 record để xem chi tiết
```

### Test 3: Tạo giải trình
```
1. Vào Attendances > Giải trình chấm công > Giải trình của tôi
2. Click Create
3. Điền thông tin:
   - Nhân viên: (tự động)
   - Ngày: Hôm nay
   - Loại giải trình: Quên chấm công vào
   - Lý do: "Test giải trình"
4. Click "Gửi phê duyệt"
5. Kiểm tra trạng thái chuyển sang "Đã gửi"
```

### Test 4: Phê duyệt giải trình (với Manager role)
```
1. Login với user có quyền Manager
2. Vào Attendances > Giải trình chấm công > Tất cả giải trình
3. Click vào giải trình cần duyệt
4. Click "Phê duyệt"
5. Kiểm tra trạng thái chuyển sang "Đã duyệt"
```

### Test 5: Cấu hình GPS
```
1. Vào Settings > Attendances
2. Scroll xuống "HDI Attendance Settings"
3. Bật "Yêu cầu định vị GPS khi chấm công"
4. Save
5. Test lại chấm công - browser sẽ hỏi quyền GPS
```

### Test 6: Địa điểm làm việc
```
1. Vào Attendances > Configuration > Địa điểm làm việc
2. Click Create
3. Điền:
   - Tên: "Văn phòng Hà Nội"
   - Địa chỉ: "123 Đường ABC, Hà Nội"
   - Vĩ độ: 21.0285
   - Kinh độ: 105.8542
   - Bán kính: 100
4. Save
```

## Kiểm tra Logs

### Attendance Logs
```
1. Vào Settings > Technical > Database Structure > Models
2. Tìm "hr.attendance.log"
3. Click "Records"
4. Kiểm tra các log đã được tạo
```

### Cron Job
```
1. Vào Settings > Technical > Automation > Scheduled Actions
2. Tìm "HDI: Process Pending Attendance Logs"
3. Kiểm tra:
   - Active: ✓
   - Interval: 5 Minutes
   - Next Execution: (thời gian tiếp theo)
4. Click "Run Manually" để test
```

## Common Issues

### Module không xuất hiện trong Apps
```bash
# Kiểm tra manifest
cat /workspaces/HDI/hdi/hdi_attendance/__manifest__.py

# Kiểm tra log lỗi
tail -f /var/log/odoo/odoo.log
```

### Lỗi import models
```python
# Kiểm tra __init__.py files
cat /workspaces/HDI/hdi/hdi_attendance/__init__.py
cat /workspaces/HDI/hdi/hdi_attendance/models/__init__.py
```

### Access Rights Error
```
1. Vào Settings > Users & Companies > Users
2. Chọn user của bạn
3. Tab "Access Rights"
4. Kiểm tra có group "Attendance / Officer" hoặc "Manager"
```

### GPS không hoạt động
```
- Truy cập qua HTTPS (không phải HTTP)
- Cho phép GPS trong browser settings
- Kiểm tra console browser (F12) xem có lỗi không
```

## Debug Tips

### Enable Debug Mode
```
Settings > Activate Developer Mode (with Assets)
```

### View Logs
```
Settings > Technical > Logging
```

### Check Database
```sql
-- Kiểm tra records
SELECT * FROM hr_attendance ORDER BY id DESC LIMIT 10;
SELECT * FROM hr_attendance_log ORDER BY id DESC LIMIT 10;
SELECT * FROM hr_attendance_explanation ORDER BY id DESC LIMIT 10;
```

### Test Python Code
```python
# Vào Settings > Technical > Python Code
# Test code:
model = env['hr.attendance']
records = model.search([], limit=5)
for rec in records:
    print(rec.employee_id.name, rec.check_in)
```

## Performance Check

### Records Count
```
Attendances: ~1000 records = OK
Logs: ~5000 records = OK (auto cleanup recommended)
Explanations: ~500 records = OK
```

### Cron Performance
```
Processing time: < 1 second for 100 logs = Good
Memory usage: < 50MB = Good
```

## Next Steps

1. ✅ Install module
2. ✅ Basic configuration
3. ✅ Test all features
4. 📝 Create test data
5. 👥 Train users
6. 🚀 Go live!

## Support Commands

```bash
# Update module
./odoo-bin -u hdi_attendance -d <database_name>

# Check module status
./odoo-bin shell -d <database_name>
>>> env['ir.module.module'].search([('name', '=', 'hdi_attendance')])

# View logs
tail -f /var/log/odoo/odoo.log | grep hdi_attendance
```
