# HDI Attendance Management

Module quản lý chấm công cho Odoo 18

## Tính năng

✅ **Quản lý chấm công**
- Check-in / Check-out
- Tính tự động giờ làm việc
- GPS tracking

✅ **Quản lý địa điểm làm việc**
- Nhiều địa điểm
- GPS coordinates
- Radius validation

✅ **Tích hợp**
- Mail tracking
- Activity management
- Chatter

## Cài đặt

1. Copy thư mục `hdi_attendance_clean` vào `addons/` của Odoo
2. Restart Odoo server với addons-path
3. Vào Apps → Update Apps List
4. Tìm "HDI Attendance" và Install

## Sử dụng

**Menu:** HDI Attendance
- Attendances: Quản lý chấm công
- Work Locations: Quản lý địa điểm

## Phân quyền

- **Attendance User**: Xem/sửa chấm công của mình
- **Attendance Manager**: Quản lý tất cả chấm công

## Technical

- Odoo Version: 18.0
- Dependencies: base, hr, mail
- Models: hdi.attendance, hdi.work.location
