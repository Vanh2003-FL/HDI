# HDI HR Attendance Enhanced - Quick Start

## ✅ ĐÃ TẠO XONG!

Module chấm công hoàn chỉnh đã được tạo tại:
```
/workspaces/HDI/hdi/hdi_hr_attendance_enhanced/
```

## 🎯 Tính năng chính

### 1. Từ NGSD
- ✅ Dropdown chọn địa điểm làm việc (như ảnh)
- ✅ GPS tự động lấy vị trí
- ✅ Hiển thị địa chỉ chi tiết
- ✅ Kiểm tra khoảng cách với văn phòng

### 2. Từ NGSC
- ✅ Queue system (xử lý bất đồng bộ)
- ✅ Chống double-click
- ✅ Offline mode (localStorage)
- ✅ Auto-sync khi online

### 3. Mới (Odoo 18)
- ✅ OWL Components (không dùng jQuery cũ)
- ✅ Kế thừa từ Odoo 18 core
- ✅ Modern UI/UX
- ✅ API REST chuẩn

## 🚀 Cài đặt

### Bước 1: Install geopy
```bash
pip install geopy
```

### Bước 2: Restart Odoo
```bash
# Trong terminal
cd /workspaces/HDI/ngsd
./odoo-bin -c ngsd.conf --stop-after-init
./odoo-bin -c ngsd.conf
```

### Bước 3: Install Module
```
1. Vào Odoo: Settings > Apps
2. Click "Update Apps List"
3. Tìm "HDI HR Attendance Enhanced"
4. Click "Install"
```

## ⚙️ Thiết lập nhanh

### 1. Tạo địa điểm
```
HR > Chấm công Enhanced > Địa điểm làm việc > Create
```

Ví dụ:
- **Tên:** Chi nhánh Hà Nội
- **Địa chỉ:** 48 Tô Hiệu, Hà Nội
- **Vĩ độ:** 21.0285
- **Kinh độ:** 105.8542
- **Bán kính:** 500 (mét)
- **Mặc định:** ☑️

### 2. Config Settings
```
Settings > HR > Attendance Enhanced
```

- ☑️ Bật định vị GPS
- ☑️ Bật Queue System
- ☑️ Cho phép Offline
- ☑️ Kiểm tra bán kính

### 3. Test chấm công
```
HR > Attendance > My Attendances
```

1. Chọn địa điểm: "Chi nhánh Hà Nội"
2. Click icon lớn "Check in"
3. Cho phép GPS
4. Đợi → "Chấm công thành công!"

## 📁 Cấu trúc Files

```
hdi_hr_attendance_enhanced/
├── __init__.py                    # Root init
├── __manifest__.py                # Module config
├── README.md                      # Full documentation
│
├── models/                        # Python models
│   ├── hr_work_location.py       # Quản lý địa điểm
│   ├── hr_attendance.py          # Extend chấm công + GPS
│   ├── hr_attendance_log.py      # Queue system
│   ├── hr_employee.py            # Employee settings
│   └── res_config_settings.py   # Config
│
├── controllers/                   # API endpoints
│   └── main.py                   # REST API
│
├── views/                         # XML views
│   ├── hr_work_location_views.xml
│   ├── hr_attendance_views.xml
│   ├── hr_attendance_log_views.xml
│   └── menu.xml
│
├── static/src/                    # Frontend
│   ├── js/
│   │   └── my_attendances.js     # OWL Component
│   ├── xml/
│   │   └── my_attendances.xml    # Templates
│   └── css/
│       └── attendance.css         # Custom styles
│
├── wizard/                        # Wizards
│   └── attendance_checkin_wizard.py
│
├── security/                      # Quyền
│   ├── ir.model.access.csv
│   └── security.xml
│
└── data/                          # Data mặc định
    ├── ir_config_parameter.xml
    └── ir_cron.xml
```

## 🎨 Giao diện giống ảnh

Module đã implement:

✅ **Xin chào!** (greeting)
✅ **Dropdown Địa điểm** (location selector)
✅ **Icon lớn Check in** (big button)
✅ **Avatar nhân viên** (employee photo)
✅ **Responsive design**

## 🔧 API Endpoints

### 1. Tạo log chấm công
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

### 2. Lấy danh sách địa điểm
```javascript
POST /hr_attendance/get_locations
```

### 3. Check settings
```javascript
POST /hr_attendance/check_settings
```

## 🐛 Debug

### Check logs
```python
# Python shell
self.env['hr.attendance.log'].search([])
```

### Check offline queue
```javascript
// Browser console
localStorage.getItem('attendance_offline_queue')
```

### Test GPS
```javascript
// Browser console
navigator.geolocation.getCurrentPosition(
    pos => console.log(pos.coords),
    err => console.error(err)
)
```

## 📊 Workflow

```
User                    Frontend                Backend                 Database
  │                         │                       │                       │
  │ Click Check-in          │                       │                       │
  ├─────────────────────────>                       │                       │
  │                         │                       │                       │
  │                         │ Get GPS               │                       │
  │                         ├───────────>           │                       │
  │                         │ (latitude, longitude) │                       │
  │                         │                       │                       │
  │                         │ POST /hr_attendance/log                       │
  │                         ├───────────────────────>                       │
  │                         │                       │ Create hr.attendance.log
  │                         │                       ├─────────────────────> │
  │                         │ {success: true}       │                       │
  │                         <───────────────────────┤                       │
  │                         │                       │                       │
  │ "Đã ghi nhận..."        │                       │                       │
  <─────────────────────────┤                       │                       │
  │                         │                       │                       │
  │                         │     [Cron 1 min]      │                       │
  │                         │                       │ Process pending logs  │
  │                         │                       ├─────────────────────> │
  │                         │                       │ Create hr.attendance  │
  │                         │                       ├─────────────────────> │
  │                         │                       │ State = processed ✅  │
```

## ✨ So với NGSD/NGSC

| Tính năng | NGSD | NGSC | HDI Enhanced |
|-----------|:----:|:----:|:------------:|
| Dropdown địa điểm | ✅ | ❌ | ✅ |
| GPS tự động | ✅ | ❌ | ✅ |
| Queue system | ❌ | ✅ | ✅ |
| Chống double-click | ❌ | ✅ | ✅ |
| Offline mode | ❌ | ✅ | ✅ |
| Odoo 18 OWL | ❌ | ❌ | ✅ |
| Kế thừa core | ❌ | ❌ | ✅ |

## 🎓 Next Steps

1. **Test thực tế:** Chấm công với điện thoại
2. **Customize:** Thêm validation rules nếu cần
3. **Report:** Tạo báo cáo chấm công theo địa điểm
4. **Mobile App:** Tích hợp với Odoo Mobile

## 💡 Tips

- **GPS không hoạt động?** → Phải dùng HTTPS
- **Offline queue đầy?** → Check localStorage size
- **Log không xử lý?** → Check cron job active

## 📞 Support

HDI Development Team
Email: dev@hdi.com.vn
