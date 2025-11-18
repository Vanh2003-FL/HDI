# Hướng dẫn Cài đặt Chi tiết

## Bước 1: Chuẩn bị môi trường

### 1.1. Install Python dependencies

```bash
# Vào thư mục Odoo
cd /workspaces/HDI/ngsd

# Install geopy cho reverse geocoding
pip install geopy

# Hoặc nếu dùng requirements.txt
echo "geopy>=2.3.0" >> requirements.txt
pip install -r requirements.txt
```

### 1.2. Kiểm tra module đã tồn tại

```bash
ls -la /workspaces/HDI/hdi/hdi_hr_attendance_enhanced/
```

Kết quả mong đợi:
```
__init__.py
__manifest__.py
README.md
QUICKSTART.md
SUMMARY.txt
models/
controllers/
views/
static/
wizard/
security/
data/
```

## Bước 2: Restart Odoo Server

### 2.1. Stop Odoo hiện tại

```bash
# Tìm process Odoo đang chạy
ps aux | grep odoo

# Kill process
kill -9 <PID>

# Hoặc dùng
pkill -f odoo-bin
```

### 2.2. Start Odoo với update module list

```bash
cd /workspaces/HDI/ngsd

# Start với update module list
./odoo-bin -c ngsd.conf -u all --stop-after-init

# Sau đó start bình thường
./odoo-bin -c ngsd.conf
```

## Bước 3: Install Module trong Odoo

### 3.1. Truy cập Odoo

```
URL: http://172.16.101.51:8089
User: Administrator
Password: admin
```

### 3.2. Update Apps List

```
Settings > Apps > Update Apps List
```

Click "Update" trong dialog

### 3.3. Tìm và Install Module

```
1. Vào Apps
2. Xóa filter "Apps" 
3. Search: "HDI HR Attendance Enhanced"
4. Click "Install"
```

Đợi 30-60 giây để install hoàn tất.

## Bước 4: Cấu hình Module

### 4.1. Thiết lập Settings

```
Settings > HR > Attendance
```

Kéo xuống phần "Attendance Enhanced", bật:

- ☑️ **Bật định vị GPS** (Geolocation Enabled)
- ☐ **Bắt buộc GPS** (không bắt buộc, nếu bật thì PHẢI có GPS mới chấm được)
- ☑️ **Bật Queue System**
- ☑️ **Cho phép Offline**
- ☑️ **Kiểm tra bán kính**
- **Bán kính mặc định:** 500 (mét)

Click "Save"

### 4.2. Tạo Địa điểm Làm việc

```
HR > Chấm công Enhanced > Địa điểm làm việc > Create
```

#### Ví dụ: Chi nhánh Hà Nội

```
Tên: Chi nhánh Hà Nội
Địa chỉ: 48 Tô Hiệu, Hà Đông, Hà Nội
Vĩ độ: 21.0285
Kinh độ: 105.8542
Bán kính cho phép: 500 (mét)
☑️ Địa điểm mặc định
☑️ Active
```

Click "Save"

#### Tip: Lấy tọa độ GPS

1. Vào Google Maps: https://maps.google.com
2. Click chuột phải vào địa điểm
3. Chọn tọa độ đầu tiên (vd: 21.0285, 105.8542)
4. Copy và paste vào form

### 4.3. Set địa điểm mặc định cho Employee

```
HR > Employees > Chọn nhân viên > Edit
```

Tìm field:
- **Địa điểm mặc định:** Chi nhánh Hà Nội
- ☑️ **Cho phép checkout khác địa điểm**

Click "Save"

## Bước 5: Test Chấm công

### 5.1. Truy cập My Attendances

```
HR > Attendance > My Attendances
```

### 5.2. Kiểm tra giao diện

Bạn sẽ thấy:
- ✅ "Xin chào!" ở trên
- ✅ Avatar của bạn
- ✅ **Dropdown "Địa điểm làm việc"** (GIỐNG ẢNH)
- ✅ Icon lớn "Check in"

### 5.3. Thực hiện Check-in

1. **Chọn địa điểm** từ dropdown: "Chi nhánh Hà Nội"
2. Click icon **"Check in"**
3. Trình duyệt sẽ hỏi "Allow location?" → Click **Allow**
4. Đợi 2-3 giây
5. Thấy thông báo: **"Đã ghi nhận chấm công của bạn!"**

### 5.4. Xem kết quả

```
HR > Attendance > Attendances
```

Bạn sẽ thấy bản ghi chấm công với:
- Employee: Tên bạn
- Work Location: Chi nhánh Hà Nội
- Check-in: Thời gian
- GPS: Tọa độ (nếu bật GPS)
- Address: Địa chỉ (nếu có GPS)

## Bước 6: Kiểm tra Queue Logs

### 6.1. Xem Attendance Logs

```
HR > Chấm công Enhanced > Attendance Logs (Queue)
```

Filter "Chờ xử lý" → Sẽ thấy các log đang pending

### 6.2. Kiểm tra Cron Jobs

```
Settings > Technical > Automation > Scheduled Actions
```

Tìm 2 cron jobs:
1. **Attendance: Process Pending Logs** (chạy mỗi 1 phút)
2. **Attendance: Retry Failed Logs** (chạy mỗi 5 phút)

Đảm bảo cả 2 đều **Active = True**

### 6.3. Test Manual Process

Nếu log không tự động xử lý:

```
HR > Chấm công Enhanced > Attendance Logs
Chọn 1 log "Pending"
Click button "Xử lý ngay"
```

## Bước 7: Test Offline Mode

### 7.1. Mở Chrome DevTools

```
F12 > Network tab
```

### 7.2. Set Offline

```
Network tab > Throttling dropdown > Offline
```

### 7.3. Thử Check-in

Click "Check in" → Sẽ thấy:
- ⚠️ "Không có kết nối. Đã lưu tạm và sẽ gửi khi online."
- Log được lưu vào `localStorage`

### 7.4. Check localStorage

```
F12 > Console tab
localStorage.getItem('attendance_offline_queue')
```

Sẽ thấy JSON array chứa logs offline.

### 7.5. Set Online lại

```
Network tab > Throttling dropdown > Online
```

Đợi 2-3 giây → Logs sẽ tự động sync!

## Bước 8: Test Check-out

```
HR > Attendance > My Attendances
```

1. Chọn địa điểm (có thể khác địa điểm check-in)
2. Click icon **"Check out"**
3. Đợi → Thông báo thành công
4. Xem worked_hours đã được tính

## Troubleshooting

### GPS không hoạt động?

**Nguyên nhân:** Browser không hỗ trợ GPS trên HTTP

**Giải pháp:**
1. Dùng HTTPS thay vì HTTP
2. Hoặc test trên localhost
3. Hoặc test trên mobile (luôn support GPS)

### Log không được xử lý?

**Kiểm tra:**
```sql
-- Vào psql
SELECT * FROM hr_attendance_log WHERE state = 'pending';

-- Check cron
SELECT * FROM ir_cron WHERE model = 'hr.attendance.log';
```

**Fix:**
- Chạy cron manually
- Check error_message trong log

### Module không tìm thấy?

**Kiểm tra:**
```bash
# Check module path
ls -la /workspaces/HDI/hdi/hdi_hr_attendance_enhanced/__manifest__.py

# Check addons_path trong config
grep addons_path /workspaces/HDI/ngsd/ngsd.conf
```

**Fix:**
- Update apps list lại
- Restart Odoo

### Lỗi "geopy not found"?

```bash
pip install geopy
# Restart Odoo
```

## Tips

### 1. Xem logs real-time

```bash
tail -f /workspaces/HDI/ngsd/odoo.log | grep attendance
```

### 2. Debug JavaScript

```javascript
// Browser console
localStorage.getItem('attendance_offline_queue')
```

### 3. Clear cache

```bash
# Clear browser cache
Ctrl + Shift + Delete

# Clear Odoo cache
rm -rf /workspaces/HDI/ngsd/.odoo_cache
```

### 4. Check API

```javascript
// Test API trong console
fetch('/hr_attendance/check_settings', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({jsonrpc: '2.0', method: 'call', params: {}})
})
.then(r => r.json())
.then(console.log)
```

## Success Criteria

✅ Dropdown địa điểm hiển thị
✅ GPS lấy được tọa độ
✅ Chấm công thành công
✅ Log được tạo trong hr.attendance.log
✅ Cron xử lý log → tạo hr.attendance
✅ Offline mode lưu vào localStorage
✅ Online lại → auto sync

## Next Steps

1. **Customize:** Thêm validation rules
2. **Report:** Tạo báo cáo chấm công theo địa điểm
3. **Mobile:** Test trên Odoo Mobile app
4. **Integration:** Tích hợp với payroll

---

**Hoàn tất!** Module đã sẵn sàng sử dụng.
