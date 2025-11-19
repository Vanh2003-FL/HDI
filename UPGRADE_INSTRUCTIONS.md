# Hướng dẫn Upgrade Module sau khi sửa lỗi

## Đã sửa các lỗi sau:

### 1. Lỗi "Private methods cannot be called remotely"
- **File**: `/workspaces/HDI/hdi/hdi_hr_attendance_geolocation/models/hr_employee.py`
- **Sửa**: Thêm method public `attendance_action_change()` để wrapper cho method private `_attendance_action_change()`

### 2. Lỗi duplicate method trong hdi_attendance
- **File**: `/workspaces/HDI/hdi/hdi_attendance/models/hr_employee.py`
- **Sửa**: Xóa method duplicate `attendance_action_change()` vì module `hdi_hr_attendance_geolocation` đã kế thừa và implement

## Cách Upgrade Module:

### Phương án 1: Qua giao diện Odoo (Khuyến nghị)
1. Vào Odoo: Settings > Apps
2. Tìm module "HDI Attendance Management" hoặc "hdi_attendance"
3. Click nút "Upgrade"
4. Đợi quá trình upgrade hoàn tất
5. Refresh trang và thử lại chức năng Check In

### Phương án 2: Qua Command Line (Nếu có quyền truy cập)
```bash
# Upgrade module hdi_hr_attendance_geolocation trước
odoo-bin -c /path/to/odoo.conf -u hdi_hr_attendance_geolocation --stop-after-init

# Sau đó upgrade hdi_attendance
odoo-bin -c /path/to/odoo.conf -u hdi_attendance --stop-after-init

# Restart Odoo
systemctl restart odoo
# hoặc
service odoo restart
```

### Phương án 3: Qua Odoo Shell (Developer mode)
1. Bật Developer Mode trong Odoo
2. Vào Settings > Technical > Database Structure > Modules
3. Xóa filter "Installed"
4. Tìm module "hdi_attendance" và "hdi_hr_attendance_geolocation"
5. Click "Upgrade" cho từng module

## Kiểm tra sau khi upgrade:

1. Vào trang Chấm công (Attendance Dashboard)
2. Mở Console trình duyệt (F12)
3. Thử click nút "CHECK IN"
4. Cho phép truy cập GPS khi được hỏi
5. Kiểm tra Console không còn lỗi "Private methods cannot be called remotely"
6. Kiểm tra chấm công thành công

## Nếu vẫn còn lỗi:

1. Clear cache trình duyệt (Ctrl + Shift + Delete)
2. Restart Odoo server
3. Kiểm tra file log của Odoo: `/var/log/odoo/odoo.log`
4. Đảm bảo module dependencies đã được cài đặt:
   - hr_attendance
   - hdi_hr
   - hdi_hr_attendance_geolocation

## Các thay đổi chi tiết:

### File: hdi_hr_attendance_geolocation/models/hr_employee.py
```python
# TRƯỚC:
def _attendance_action_change(self, geo_ip_response=None):
    """Override để lưu thông tin GPS khi check-in/check-out"""
    ...

# SAU:
def attendance_action_change(self):
    """Public method to handle attendance check-in/out with GPS"""
    return self._attendance_action_change()

def _attendance_action_change(self, geo_ip_response=None):
    """Override để lưu thông tin GPS khi check-in/check-out"""
    ...
```

### File: hdi_attendance/models/hr_employee.py
```python
# TRƯỚC:
def attendance_action_change(self):
    """Public wrapper for _attendance_action_change to be called from JS"""
    self.ensure_one()
    return self._attendance_action_change()

# SAU: (ĐÃ XÓA - không cần thiết vì module geolocation đã có)
```

---

**Lưu ý**: Module `hdi_hr_attendance_geolocation` được kế thừa bởi `hdi_attendance` nên phải upgrade theo thứ tự đúng.
