# HDI HR Attendance Enhanced

## 📋 Tổng quan

Module chấm công hoàn chỉnh cho Odoo 18, kết hợp tính năng tốt nhất từ NGSD và NGSC.

## ✨ Tính năng chính

### 1. Chọn địa điểm làm việc (từ NGSD)
- ✅ Dropdown chọn địa điểm trước khi chấm công
- ✅ Quản lý nhiều địa điểm (văn phòng, chi nhánh, remote)
- ✅ Địa điểm mặc định cho mỗi nhân viên
- ✅ Cho phép/không cho phép checkout khác địa điểm

### 2. GPS Geolocation (từ NGSD + HDI)
- ✅ Tự động lấy GPS khi check-in/check-out
- ✅ Reverse geocoding: GPS → Địa chỉ
- ✅ Link Google Maps để xem vị trí
- ✅ Tính khoảng cách đến văn phòng (Haversine formula)
- ✅ Cảnh báo khi chấm công ngoài bán kính cho phép

### 3. Queue System (từ NGSC)
- ✅ Xử lý chấm công bất đồng bộ
- ✅ Model `hr.attendance.log` làm queue
- ✅ Cron job xử lý pending logs (1 phút/lần)
- ✅ Cron job retry failed logs (5 phút/lần)
- ✅ Workflow phê duyệt (approve/reject)

### 4. Chống Double-Click (từ NGSC)
- ✅ Prevent duplicate clicks trong 3 giây
- ✅ Hiển thị thông báo "Đã bấm rồi, vui lòng chờ"
- ✅ Disable button khi đang xử lý
- ✅ Visual feedback (spinner)

### 5. Offline Mode (từ NGSC)
- ✅ Lưu chấm công vào localStorage khi offline
- ✅ Auto-sync khi online trở lại
- ✅ Queue offline data
- ✅ Event listener: `window.addEventListener('online')`

### 6. Giao diện đẹp (từ NGSD + Custom)
- ✅ "Xin chào!" với avatar nhân viên
- ✅ Icon lớn "Bấm vào check in"
- ✅ Dropdown địa điểm rõ ràng
- ✅ Responsive, mobile-friendly
- ✅ Animation smooth

## 🏗️ Cấu trúc Module

```
hdi_hr_attendance_enhanced/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── hr_work_location.py      # Quản lý địa điểm
│   ├── hr_attendance.py          # Extend chấm công + GPS
│   ├── hr_attendance_log.py      # Queue system
│   ├── hr_employee.py            # Employee settings
│   └── res_config_settings.py   # Config
├── controllers/
│   ├── __init__.py
│   └── main.py                   # API endpoints
├── views/
│   ├── hr_work_location_views.xml
│   ├── hr_attendance_views.xml
│   ├── hr_attendance_log_views.xml
│   └── menu.xml
├── static/
│   ├── src/
│   │   ├── js/
│   │   │   └── my_attendances.js   # OWL Component
│   │   ├── xml/
│   │   │   └── my_attendances.xml  # Templates
│   │   └── css/
│   │       └── attendance.css      # Custom styles
├── wizard/
│   ├── __init__.py
│   ├── attendance_checkin_wizard.py
│   └── attendance_checkin_wizard_views.xml
├── security/
│   ├── ir.model.access.csv
│   └── security.xml
└── data/
    ├── ir_config_parameter.xml
    └── ir_cron.xml
```

## 🚀 Cài đặt

### 1. Dependencies

```bash
pip install geopy
```

### 2. Module depends

```python
'depends': [
    'hr_attendance',  # Odoo 18 core
    'hdi_hr',        # HDI base HR module
]
```

### 3. Install module

```bash
# Trong Odoo
Apps > Update Apps List
Tìm "HDI HR Attendance Enhanced"
Click Install
```

## ⚙️ Cấu hình

### Settings > HR > Attendance Enhanced

1. **Geolocation**
   - ☑️ Bật định vị GPS
   - ☐ Bắt buộc GPS (nếu bật, không có GPS = không chấm được)

2. **Queue System**
   - ☑️ Bật Queue System
   - ☑️ Auto-process logs

3. **Offline Mode**
   - ☑️ Cho phép offline
   - Logs sẽ lưu localStorage

4. **Validation**
   - ☑️ Kiểm tra bán kính
   - Bán kính mặc định: 500m

## 📱 Sử dụng

### 1. Thiết lập địa điểm

```
HR > Chấm công Enhanced > Địa điểm làm việc
```

- Tạo địa điểm: Văn phòng Hà Nội, HCM, Remote...
- Nhập GPS: Vĩ độ, Kinh độ
- Set bán kính: 500m
- Đánh dấu "Mặc định" cho 1 địa điểm

### 2. Chấm công (User)

```
HR > Attendance > My Attendances
```

1. Chọn địa điểm từ dropdown
2. Click icon lớn "Check in"
3. Trình duyệt xin GPS → Allow
4. Đợi 2-3 giây
5. Thông báo "Chấm công thành công!"

### 3. Xem logs (HR Manager)

```
HR > Chấm công Enhanced > Attendance Logs
```

- Filter: Pending, Processing, Processed, Failed
- Thao tác: Process, Approve, Reject
- Xem retry_count, error_message

## 🔧 API Endpoints

### 1. Create Log

```javascript
POST /hr_attendance/log
{
    "employee_id": 1,
    "action": "check_in",
    "timestamp": "2025-11-18 10:00:00",
    "latitude": 21.0285,
    "longitude": 105.8542,
    "work_location_id": 1
}
```

### 2. Get Locations

```javascript
POST /hr_attendance/get_locations
// Returns: {success: true, locations: [...], default_id: 1}
```

### 3. Check Settings

```javascript
POST /hr_attendance/check_settings
// Returns: {geolocation_enabled: true, queue_enabled: true, ...}
```

## 🔄 Workflow

```
User clicks Check-in
  ↓
JS: Get GPS location
  ↓
JS: Send to /hr_attendance/log API
  ↓
Controller: Create hr.attendance.log (state=pending)
  ↓
Cron (1 min): Process pending logs
  ↓
Log.action_process() → Create hr.attendance
  ↓
State = processed ✅
```

## 📊 So sánh với NGSD/NGSC

| Tính năng | NGSD | NGSC | HDI Enhanced |
|-----------|------|------|--------------|
| Dropdown địa điểm | ✅ | ❌ | ✅ |
| GPS Geolocation | ✅ | ❌ | ✅ |
| Khoảng cách + radius | ✅ | ❌ | ✅ |
| Queue system | ❌ | ✅ | ✅ |
| Chống double-click | ❌ | ✅ | ✅ |
| Offline mode | ❌ | ✅ | ✅ |
| Odoo 18 OWL | ❌ | ❌ | ✅ |
| Kế thừa core | ❌ | ❌ | ✅ |

## 🐛 Troubleshooting

### GPS không hoạt động?

1. Check HTTPS (GPS chỉ work trên HTTPS)
2. Browser phải allow location
3. Check console: `navigator.geolocation`

### Log không được xử lý?

1. Check cron job active
2. Check logs: `hr.attendance.log` state
3. Retry manual: Click "Xử lý ngay"

### Offline queue không sync?

1. Check `window.addEventListener('online')`
2. Check localStorage: `attendance_offline_queue`
3. Manual flush: `flushOfflineQueue()`

## 📝 Notes

- **Odoo 18**: Module sử dụng OWL components, không dùng legacy jQuery
- **Core inheritance**: Kế thừa `hr.attendance` từ Odoo core, không override toàn bộ
- **Geopy**: Cần install `pip install geopy` để reverse geocoding

## 👨‍💻 Developer

HDI Development Team - 2025

## 📄 License

LGPL-3
