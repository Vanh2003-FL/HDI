# HƯỚNG DẪN SỬ DỤNG - HDI ATTENDANCE

## 🚀 CÀI ĐẶT & KHỞI ĐỘNG

### Bước 1: Nâng cấp module
```bash
cd /workspaces/HDI
./odoo-bin -u hdi_attendance -d your_database_name
```

### Bước 2: Khởi động lại Odoo
```bash
./odoo-bin -d your_database_name
```

### Bước 3: Kiểm tra menu
Vào menu: **Chấm công HDI** → **Chấm công của tôi**

---

## 📖 HƯỚNG DẪN SỬ DỤNG CHO NHÂN VIÊN

### 1. Xem chấm công của mình
- Menu: **Chấm công HDI** → **Chấm công của tôi**
- Chọn view: **Calendar** (xem theo lịch với màu sắc)
  - 🟢 Màu xanh: Chấm công bình thường
  - 🟠 Màu cam: Đi muộn hoặc về sớm
  - 🔴 Màu đỏ: Quên chấm công
  - 🟡 Màu vàng: Chưa checkout
  - 🟣 Màu tím: Giờ làm không đủ (< 7.75h)

### 2. Tạo giải trình chấm công
#### Cách 1: Từ bản ghi chấm công
1. Vào **Chấm công của tôi**
2. Mở bản ghi cần giải trình
3. Click nút **Giải trình** (ở header)
4. Form giải trình mở ra với thông tin tự động điền

#### Cách 2: Tạo mới trực tiếp
1. Menu: **Chấm công HDI** → **Giải trình chấm công** → **Giải trình của tôi**
2. Click nút **Tạo**
3. Chọn loại giải trình:
   - **Quên chấm công (MA)**: Tạo bản ghi mới
   - **Điều chỉnh Check in (DCC)**: Sửa giờ vào
   - **Điều chỉnh Check out (DCO)**: Sửa giờ ra
   - **Đi muộn (LATE)**: Giải trình đi muộn
   - **Về sớm (EARLY)**: Giải trình về sớm
   - **WFH/Công tác/Khác**: Các lý do khác

### 3. Điền thông tin giải trình
1. **Tab "Chi tiết giờ giấc"**:
   - Thêm dòng check in: Chọn type = Check in, nhập ngày và giờ (VD: 8.5 = 8h30)
   - Thêm dòng check out: Chọn type = Check out, nhập ngày và giờ (VD: 17.5 = 17h30)
   
2. **Tab "Giải trình"**:
   - Nhập lý do chi tiết
   - Đính kèm tài liệu (nếu có)

3. Click nút **Gửi phê duyệt**

### 4. Theo dõi trạng thái
- **Mới tạo**: Chưa gửi phê duyệt
- **Chờ duyệt**: Đã gửi, đang chờ manager phê duyệt
- **Đã duyệt**: Manager đã duyệt, thay đổi đã áp dụng vào chấm công
- **Từ chối**: Manager từ chối, cần sửa lại

### 5. Lưu ý quan trọng
- ⚠️ **Hạn mức**: Chỉ được giải trình tối đa **3 lần/tháng** (các loại tính hạn mức: MA, DCC, DCO, LATE, EARLY, OTHER)
- ⚠️ **Chu kỳ tháng**: Từ ngày 25 tháng trước đến ngày 24 tháng sau
- ⚠️ **Loại TSDA/TSNDA**: Dành cho timesheet, không tính vào hạn mức

---

## 👨‍💼 HƯỚNG DẪN CHO QUẢN LÝ (MANAGER)

### 1. Xem giải trình cần phê duyệt
- Menu: **Chấm công HDI** → **Giải trình chấm công** → **Cần phê duyệt**
- Danh sách hiển thị các giải trình đang chờ bạn duyệt

### 2. Phê duyệt giải trình
#### Phê duyệt từng cái
1. Mở giải trình cần duyệt
2. Kiểm tra:
   - Lý do giải trình
   - Chi tiết giờ giấc (tab "Chi tiết giờ giấc")
   - Tài liệu đính kèm
   - Quy trình phê duyệt (tab "Quy trình phê duyệt")
3. Click **Phê duyệt** hoặc **Từ chối**
4. Nếu từ chối, nhập lý do

#### Phê duyệt hàng loạt
1. Vào danh sách **Cần phê duyệt**
2. Chọn nhiều giải trình (checkbox)
3. Click **Action** → **Duyệt hàng loạt** hoặc **Từ chối hàng loạt**

### 3. Xem tất cả giải trình
- Menu: **Chấm công HDI** → **Giải trình chấm công** → **Tất cả giải trình**
- Filters:
  - Mới tạo
  - Chờ duyệt
  - Đã duyệt
  - Từ chối
  - Tháng này
- Group by:
  - Nhân viên
  - Trạng thái
  - Loại giải trình
  - Ngày

### 4. Khi phê duyệt, hệ thống tự động:
- **Loại MA (Quên chấm công)**:
  - Tạo bản ghi chấm công mới với giờ trong "Chi tiết giờ giấc"
  - Link bản ghi mới vào giải trình

- **Loại DCC (Điều chỉnh Check in)**:
  - Cập nhật giờ check_in của bản ghi chấm công hiện tại
  - Tính lại: en_late, color, warning_message

- **Loại DCO (Điều chỉnh Check out)**:
  - Cập nhật giờ check_out của bản ghi chấm công hiện tại
  - Tính lại: en_soon, worked_hours, color

- **Loại khác (LATE, EARLY, WFH, etc.)**:
  - Ghi nhận lý do
  - Không thay đổi giờ chấm công

---

## 🔧 CẤU HÌNH HỆ THỐNG (ADMIN)

### 1. Thay đổi hạn mức giải trình
**Settings** → **Technical** → **System Parameters**

- `en_max_attendance_request_count`: Số lần tối đa (mặc định: 3)
- `en_attendance_request_start`: Ngày bắt đầu chu kỳ (mặc định: 25)

### 2. Thay đổi tolerance (dung sai)
- `en_late_tolerance_minutes`: Phút cho đi muộn (mặc định: 15)
- `en_early_tolerance_minutes`: Phút cho về sớm (mặc định: 15)
- `en_min_working_hours`: Giờ làm tối thiểu (mặc định: 7.75)

### 3. Cấu hình GPS
- `en_max_gps_distance`: Khoảng cách tối đa (km, mặc định: 0.5)

### 4. Cấu hình auto logout
- `en_auto_logout_time`: Giờ tự động checkout (mặc định: 23:59)
- `en_enable_auto_logout`: Bật/tắt (mặc định: True)

### 5. Quản lý loại giải trình
Menu: **Chấm công HDI** → **Cấu hình** → **Loại giải trình**

Mỗi loại có 2 thuộc tính:
- **Tính vào hạn mức**: Có đếm vào 3 lần/tháng không
- **Dùng ngày giải trình**: Dùng trường ngày thay vì chọn bản ghi chấm công

---

## 🎨 MÀU SẮC CALENDAR VIEW

| Màu | Ý nghĩa | Color Code |
|-----|---------|------------|
| 🟢 Green | Bình thường | 10 |
| 🟠 Orange | Đi muộn hoặc về sớm | 1 |
| 🔴 Red | Quên chấm công | 2 |
| 🟡 Yellow | Chưa checkout | 3 |
| 🟣 Purple | Giờ làm không đủ | 4 |

---

## ⏰ CRON JOBS (Tự động chạy)

### 1. Auto Logout (23:59 hàng ngày)
- Tự động checkout cho những bản ghi chưa checkout
- Check out time = 23:59 cùng ngày

### 2. Process Attendance Log (5 phút 1 lần)
- Xử lý queue chấm công bất đồng bộ
- Tránh lỗi khi nhiều người chấm công cùng lúc

---

## 🐛 XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi: "Bạn đã vượt quá số lần giải trình cho phép trong tháng"
- **Nguyên nhân**: Đã giải trình >= 3 lần trong chu kỳ (từ 25 tháng trước đến 24 tháng này)
- **Giải pháp**: 
  - Đợi sang chu kỳ mới (từ ngày 25)
  - Hoặc admin tăng hạn mức trong System Parameters

### Lỗi: "This type of explanation requires attendance_id"
- **Nguyên nhân**: Loại DCC/DCO cần chọn bản ghi chấm công, không dùng ngày
- **Giải pháp**: Chọn bản ghi trong field "Attendance"

### Lỗi: "This type of explanation requires explanation_date"
- **Nguyên nhân**: Loại MA/TSDA/TSNDA cần nhập ngày giải trình
- **Giải pháp**: Điền ngày vào field "Explanation Date"

### Lỗi: "Only one check_in/check_out allowed per explanation"
- **Nguyên nhân**: Thêm nhiều hơn 1 dòng check_in hoặc check_out
- **Giải pháp**: Mỗi giải trình chỉ 1 dòng check_in và 1 dòng check_out

---

## 📞 HỖ TRỢ

Nếu gặp vấn đề, liên hệ:
- **IT Support**: support@hdi.com.vn
- **Hotline**: 1900-xxxx

---

**Phiên bản:** 1.0.0
**Ngày cập nhật:** 2024
**Module:** hdi_attendance
**Odoo Version:** 18.0
