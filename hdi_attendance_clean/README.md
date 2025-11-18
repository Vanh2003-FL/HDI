# HDI Attendance Module - Odoo 18

Module quản lý chấm công cho HDI với GPS tracking và work location.

## Tính năng

### Backend
- **Inherit hr.attendance**: Kế thừa module hr_attendance của Odoo 18
- **GPS Tracking**: Tự động lưu tọa độ GPS khi check-in và check-out
- **Work Location**: Quản lý địa điểm làm việc
- **Color Coding**: Màu đỏ cho bản ghi chưa check-out hoặc không đủ giờ, xanh cho hoàn thành
- **Computed Fields**: 
  - `warning_message`: Cảnh báo nếu chưa checkout hoặc không đủ giờ
  - `color`: Màu sắc cho calendar view

### Frontend  
- **Location Selector**: Dropdown chọn địa điểm khi check-in/check-out
- **GPS Capture**: Tự động lấy tọa độ GPS từ trình duyệt
- **MyAttendances Widget**: Customize widget chấm công của Odoo với location selector
- **Calendar View**: Hiển thị chấm công theo lịch với color coding

### Views
- **List View**: Danh sách chấm công với decoration màu
- **Form View**: Chi tiết chấm công với GPS coordinates trong notebook
- **Calendar View**: Lịch chấm công với màu sắc theo trạng thái
- **Kanban View**: Card view với icons và thông tin chi tiết
- **Pivot/Graph View**: Báo cáo và biểu đồ

## Cấu trúc thư mục

```
hdi_attendance_clean/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── attendance.py      # Inherit hr.attendance với GPS fields
│   ├── employee.py        # Extend hr.employee với location methods
│   └── work_location.py   # Model quản lý địa điểm làm việc
├── views/
│   ├── attendance_views.xml    # List, form, calendar, kanban views
│   ├── work_location_views.xml # Work location management
│   └── menu_views.xml          # Menu structure
├── security/
│   ├── attendance_security.xml # Security groups
│   └── ir.model.access.csv    # Access rights
└── static/
    └── src/
        ├── js/
        │   └── hdi_attendance.js   # JavaScript customization
        └── xml/
            └── hdi_attendance.xml  # QWeb templates
```

## Cài đặt

### 1. Copy module vào Odoo addons

```bash
# Giả sử Odoo của bạn ở /home/va/odoo18/ProjectOdoo/odoo
cp -r /workspaces/HDI/hdi_attendance_clean /home/va/odoo18/ProjectOdoo/odoo/hdi/hdi_attendance_clean
```

### 2. Cập nhật apps list

```bash
cd /home/va/odoo18/ProjectOdoo/odoo
python odoo-bin -d hdi_odoo -u all --stop-after-init
```

### 3. Cài đặt module

**Option 1: Qua UI**
- Vào Apps
- Bỏ filter "Apps"
- Tìm "HDI Attendance"
- Click Install

**Option 2: Qua command line**
```bash
python odoo-bin -d hdi_odoo -i hdi_attendance_clean --stop-after-init
```

### 4. Khởi động Odoo

```bash
python odoo-bin -d hdi_odoo
```

## Dependencies

Module này phụ thuộc vào:
- `hr_attendance`: Module chấm công chuẩn của Odoo 18
- `mail`: Mail tracking

Odoo sẽ tự động cài đặt các dependencies này nếu chưa có.

## Cấu hình

### 1. Tạo Work Locations

1. Vào **Chấm công HDI > Cấu hình > Địa điểm làm việc**
2. Click **Tạo**
3. Nhập thông tin:
   - Tên địa điểm
   - Địa chỉ
   - GPS coordinates (optional)
   - Company (optional - để trống cho all companies)

### 2. Phân quyền

Module có 2 nhóm quyền:
- **Attendance User**: Xem và tạo chấm công của mình
- **Attendance Manager**: Quản lý tất cả chấm công

Vào **Settings > Users** để phân quyền cho users.

## Sử dụng

### Check-in / Check-out

1. Vào **Chấm công HDI > Chấm công của tôi**
2. Widget MyAttendances sẽ hiển thị với:
   - Dropdown chọn location
   - Nút Check In / Check Out
   - Greeting message với thông tin nhân viên
3. Click **Check In**:
   - Chọn location từ dropdown
   - Hệ thống tự động lấy GPS coordinates
   - Tạo attendance record mới
4. Click **Check Out**:
   - Tự động lấy GPS coordinates
   - Cập nhật check_out time và worked_hours

### Xem lịch chấm công

1. Vào **Chấm công HDI > Chấm công của tôi**
2. Chọn view **Calendar**
3. Màu sắc:
   - 🟢 Xanh: Check-out hoàn thành và đủ giờ (≥7.5h)
   - 🔴 Đỏ: Chưa check-out hoặc không đủ giờ

### Manager view

1. Vào **Chấm công HDI > Tất cả chấm công**
2. Xem tất cả attendance records của nhân viên
3. Filter, group, search theo nhiều tiêu chí
4. Export dữ liệu nếu cần

## Technical Details

### Model: hr.attendance (inherit)

**Added Fields:**
- `work_location_id`: Many2one to hdi.work.location
- `checkin_latitude`: Float (10, 7) - GPS latitude khi check-in
- `checkin_longitude`: Float (10, 7) - GPS longitude khi check-in  
- `checkout_latitude`: Float (10, 7) - GPS latitude khi check-out
- `checkout_longitude`: Float (10, 7) - GPS longitude khi check-out
- `color`: Integer (computed) - Màu cho calendar view
- `warning_message`: Text (computed) - Cảnh báo nếu có vấn đề

**Overridden Methods:**
- `create()`: Capture GPS và location từ context khi check-in
- `write()`: Capture GPS từ context khi check-out

### Model: hr.employee (inherit)

**Added Fields:**
- `default_work_location_id`: Many2one to hdi.work.location
- `attendance_count`: Integer (computed) - Số lượng attendance records

**Added Methods:**
- `get_working_locations()`: Trả về list locations cho employee
- `get_en_checked_diff_ok()`: Check xem có thể checkout ở location khác không
- `attendance_manual()`: Override để capture GPS và location từ context

### JavaScript: MyAttendances Widget Patch

File: `static/src/js/hdi_attendance.js`

**Functionality:**
- Patch MyAttendances.prototype
- `willStart()`: Load working locations cho dropdown
- `_manual_attendance()`: Pass GPS coordinates và location_id vào context

**Context passed to backend:**
```javascript
{
    latitude: <GPS latitude>,
    longitude: <GPS longitude>,
    hdi_location_id: <selected location id>
}
```

### Templates: QWeb

File: `static/src/xml/hdi_attendance.xml`

**Template Inheritance:**
- Inherit `HrAttendanceMyMainMenu`
- Inject location dropdown before employee name
- Bootstrap 5 styling

## Troubleshooting

### Module không hiển thị trong Apps
```bash
# Update apps list
python odoo-bin -d hdi_odoo -u all --stop-after-init
```

### Lỗi khi cài đặt
```bash
# Check logs
tail -f /var/log/odoo/odoo.log

# Hoặc chạy với debug
python odoo-bin -d hdi_odoo -i hdi_attendance_clean --log-level=debug
```

### GPS không hoạt động
- Đảm bảo trình duyệt cho phép location access
- Chỉ hoạt động trên HTTPS hoặc localhost
- Check browser console cho errors

### Views không hiển thị đúng
```bash
# Clear browser cache
# Hoặc restart Odoo với assets clear
python odoo-bin -d hdi_odoo -u hdi_attendance_clean --stop-after-init
```

## Notes

- Module này inherit hr_attendance, không tạo model mới
- GPS tracking chỉ hoạt động trên browsers hỗ trợ Geolocation API
- Calendar color coding dựa trên check_out status và worked_hours
- Work locations có thể specific cho company hoặc shared across companies

## Author

HDI Team

## License

LGPL-3
