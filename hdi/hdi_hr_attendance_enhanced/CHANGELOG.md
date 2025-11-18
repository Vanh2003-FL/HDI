# Changelog

## [1.0.0] - 2025-11-18

### Added (Tính năng mới)

#### Từ NGSD (ngs_attendance)
- ✅ Dropdown chọn địa điểm làm việc (model: hr.work.location)
- ✅ GPS Geolocation tự động khi check-in/check-out
- ✅ Reverse geocoding: GPS → Địa chỉ (sử dụng geopy/Nominatim)
- ✅ Tính khoảng cách đến văn phòng (Haversine formula)
- ✅ Cảnh báo khi chấm công ngoài bán kính cho phép
- ✅ Link Google Maps để xem vị trí chấm công
- ✅ Quản lý nhiều địa điểm (văn phòng, chi nhánh, remote)
- ✅ Địa điểm mặc định cho mỗi nhân viên

#### Từ NGSC (ngs_hr_attendance_async)
- ✅ Queue system: Model hr.attendance.log
- ✅ Xử lý chấm công bất đồng bộ
- ✅ Chống double-click (prevent duplicate trong 3 giây)
- ✅ Offline mode: Lưu vào localStorage khi mất mạng
- ✅ Auto-sync khi online trở lại
- ✅ Workflow phê duyệt (approve/reject logs)
- ✅ Cron job: Process pending logs (1 phút)
- ✅ Cron job: Retry failed logs (5 phút)
- ✅ Retry mechanism (tối đa 3 lần)

#### Mới - Kế thừa Odoo 18 Core
- ✅ OWL Components (patch MyAttendances)
- ✅ Kế thừa hr_attendance từ Odoo 18 core
- ✅ Modern JavaScript (ES6+, no jQuery legacy)
- ✅ REST API endpoints (/hr_attendance/log, /get_locations, /check_settings)
- ✅ Responsive UI với Bootstrap 5
- ✅ Animation smooth (CSS transitions)
- ✅ Mobile-friendly design

#### Models
- ✅ hr.work.location (extend): GPS, radius, default location
- ✅ hr.attendance (extend): GPS fields, work_location_id, distance calculation
- ✅ hr.attendance.log (new): Queue system
- ✅ hr.employee (extend): default_work_location_id, allow_different_checkout_location
- ✅ res.config.settings (extend): Module settings

#### Views
- ✅ Work Location management views (tree, form, search)
- ✅ Attendance views with GPS fields
- ✅ Attendance Log views (tree, form, search, filters)
- ✅ Enhanced My Attendances template (dropdown địa điểm)
- ✅ Menu structure

#### Controllers
- ✅ /hr_attendance/log - Tạo log chấm công
- ✅ /hr_attendance/get_locations - Lấy danh sách địa điểm
- ✅ /hr_attendance/check_settings - Kiểm tra cấu hình

#### Security
- ✅ Access rights: User, Officer, Manager
- ✅ Record rules: Employee own logs, HR full access
- ✅ Security groups: Attendance Officer, Administrator

#### Data
- ✅ Config parameters (geolocation, queue, offline mode)
- ✅ Cron jobs (process logs, retry failed)
- ✅ Demo data (4 locations: Hà Nội, HCM, Đà Nẵng, Remote)

#### Documentation
- ✅ README.md - Full documentation
- ✅ QUICKSTART.md - Quick start guide
- ✅ INSTALL.md - Chi tiết cài đặt
- ✅ SUMMARY.txt - Module summary
- ✅ CHANGELOG.md - This file

### Technical Details

#### Frontend
- **Framework:** OWL (Odoo Web Library)
- **Pattern:** Patch existing components (không override)
- **State Management:** useState hook
- **Lifecycle:** onMounted hook
- **Services:** orm, rpc, notification

#### Backend
- **Python:** 3.10+
- **Dependencies:** geopy>=2.3.0
- **API:** JSON-RPC 2.0
- **Queue:** Cron-based processing
- **GPS:** Haversine distance calculation

#### Database
- **3 new models:** hr.attendance.log
- **Extended models:** hr.work.location, hr.attendance, hr.employee
- **SQL constraints:** Unique log per employee/time/action

### Performance
- ✅ Async processing (không block UI)
- ✅ Debounce (2 seconds)
- ✅ Batch processing (100 logs/cron run)
- ✅ Index on: employee_id, timestamp, state
- ✅ localStorage for offline queue

### Compatibility
- **Odoo Version:** 18.0
- **Dependencies:** hr_attendance (core), hdi_hr
- **Browser:** Chrome 90+, Firefox 88+, Safari 14+, Edge 90+
- **Mobile:** Android 8+, iOS 13+

### Known Limitations
- GPS chỉ hoạt động trên HTTPS hoặc localhost
- Reverse geocoding cần internet connection
- Offline queue giới hạn bởi localStorage (5-10MB)

### Future Roadmap
- [ ] Báo cáo chấm công theo địa điểm
- [ ] Dashboard thống kê GPS
- [ ] Export GPS to KML/GPX
- [ ] Tích hợp với payroll
- [ ] Mobile app native
- [ ] Face recognition
- [ ] QR code check-in
- [ ] Geofencing alerts
- [ ] Multi-language support
- [ ] Dark mode

### Credits
- **Based on:** NGSD ngs_attendance + NGSC ngs_hr_attendance_async
- **Developed by:** HDI Development Team
- **Date:** November 18, 2025
- **License:** LGPL-3

### Breaking Changes
None (first version)

### Migration Notes
If migrating from NGSD/NGSC:
1. Data migration: hr.work.location
2. Update employee default locations
3. Re-configure settings
4. Test GPS functionality

### Contributors
- HDI Dev Team

---

**Version:** 18.0.1.0.0  
**Release Date:** November 18, 2025  
**Status:** Stable ✅
