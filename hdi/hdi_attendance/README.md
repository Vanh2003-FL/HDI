# HDI Attendance Management System

Module chấm công HDI dựa trên kiến trúc NGSC/NGSD cho Odoo 18.

## Tính năng chính

### ✅ Chấm công cơ bản
- **Check In/Out Interface**: Giao diện chấm công thân thiện
- **My Attendance**: Xem chấm công cá nhân
- **Attendance History**: Lịch sử chấm công đầy đủ

### 🌍 GPS & Geolocation
- Hỗ trợ định vị GPS khi chấm công
- Quản lý địa điểm làm việc
- Kiểm tra bán kính cho phép chấm công

### 📝 Giải trình chấm công
- Giải trình khi quên chấm công
- Quy trình phê duyệt giải trình
- Các loại giải trình: Quên check in/out, Đi muộn, Về sớm, WFH, Công tác, v.v.

### ⚡ Xử lý bất đồng bộ
- Chống bấm nút 2 lần
- Ghi log chấm công bất đồng bộ
- Cron job xử lý log tự động

### 🔐 Bảo mật & Phân quyền
- Phân quyền theo vai trò (User/Manager)
- Record rules bảo mật dữ liệu
- Audit trail đầy đủ

## Cài đặt

### 1. Yêu cầu
```bash
# Module dependencies
- base
- hr
- hr_attendance
- hdi_hr
- hdi_hr_attendance_geolocation
```

### 2. Cài đặt module
```bash
# Vào Apps trong Odoo
# Search: "HDI Attendance"
# Click Install
```

### 3. Cấu hình

Vào **Settings > Attendances > HDI Attendance Settings**:

- ☑️ **Yêu cầu định vị GPS**: Bắt buộc GPS khi chấm công
- ☑️ **Cho phép chấm công thủ công**: Cho phép nhân viên tự chấm công
- **Số ngày yêu cầu giải trình**: Thời hạn tạo giải trình (mặc định: 7 ngày)

### 4. Thiết lập địa điểm làm việc

Vào **Attendances > Configuration > Địa điểm làm việc**:

1. Tạo địa điểm mới
2. Nhập tọa độ GPS (Latitude/Longitude)
3. Đặt bán kính cho phép (mặc định: 100m)

## Sử dụng

### Chấm công (Check In/Out)

1. Vào **Attendances > Check In / Check Out**
2. Click vào avatar của bạn
3. Hệ thống tự động lấy GPS (nếu bật)
4. Click **Check In** hoặc **Check Out**

### Xem chấm công của tôi

Vào **Attendances > Chấm công của tôi**

### Tạo giải trình

1. Vào **Attendances > Giải trình chấm công > Giải trình của tôi**
2. Click **Create**
3. Chọn loại giải trình
4. Nhập lý do và đính kèm tài liệu
5. Click **Gửi phê duyệt**

### Phê duyệt giải trình (Manager)

1. Vào **Attendances > Giải trình chấm công > Tất cả giải trình**
2. Click vào giải trình cần duyệt
3. Click **Phê duyệt** hoặc **Từ chối**

## Kiến trúc

### Models
- `hr.attendance` (extend): Bản ghi chấm công
- `hr.attendance.log`: Log xử lý bất đồng bộ
- `hr.attendance.explanation`: Giải trình chấm công
- `hr.work.location`: Địa điểm làm việc
- `submission.type`: Loại giải trình

### Views
- Attendance views (extend Odoo standard)
- Explanation views (tree/form/search)
- Log views (monitoring)
- Configuration views

### Security
- Groups: `group_attendance_user`, `group_attendance_manager`
- Record rules: Own records + Manager access
- Access rights: Full CRUD control

### Automation
- Cron: Process pending attendance logs (every 5 minutes)
- Sequence: Auto-generate explanation numbers

## Tích hợp với NGSC/NGSD

Module này kế thừa từ:
- **NGSD**: `ngs_attendance` - Core attendance features
- **NGSC**: `ngs_hr_attendance_async` - Async processing
- **NGSC**: `ngsc_timesheet_checkout` - Timesheet integration

## Troubleshooting

### GPS không hoạt động
- Kiểm tra trình duyệt có cho phép GPS không
- Đảm bảo đang truy cập qua HTTPS
- Kiểm tra setting "Yêu cầu định vị GPS"

### Giải trình không được phê duyệt
- Kiểm tra user có quyền Manager không
- Xem lại workflow: Draft → Submitted → Approved

### Log chưa được xử lý
- Kiểm tra Cron job có chạy không
- Vào Settings > Technical > Scheduled Actions
- Tìm "Process Pending Attendance Logs"

## Phát triển

### Extend module

```python
# Extend attendance model
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    custom_field = fields.Char('Custom Field')
```

### Add new submission type

```xml
<record id="submission_type_custom" model="submission.type">
    <field name="name">Custom Type</field>
    <field name="code">CUSTOM</field>
    <field name="sequence">100</field>
</record>
```

## Support

- **Author**: HDI Development Team
- **Website**: https://hdi.com.vn
- **Version**: 18.0.1.0.0
- **License**: LGPL-3

## Changelog

### Version 18.0.1.0.0 (2025-11-18)
- Initial release
- Core attendance features
- GPS geolocation support
- Explanation system
- Async processing with logs
- Manager approval workflow
