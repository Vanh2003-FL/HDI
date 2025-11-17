# HDI Attendance Management

Module quản lý chấm công nâng cao cho HDI được xây dựng trên nền tảng Odoo 18.

## Tính năng chính

### 🕐 Chấm công cơ bản
- Check-in/Check-out với GPS tracking
- Quản lý ca làm việc linh hoạt (sáng, chiều, tối, ngày, linh hoạt)
- Tính toán giờ làm việc và tăng ca tự động
- Hỗ trợ multiple địa điểm làm việc

### 📍 Quản lý địa điểm
- Cấu hình địa điểm làm việc với GPS coordinates
- Kiểm soát bán kính check-in/check-out
- Bản đồ tích hợp Google Maps
- Lịch làm việc theo địa điểm

### ⚠️ Ngoại lệ và giải trình
- Phát hiện tự động: đi muộn, về sớm, thiếu check-out
- Hệ thống giải trình với workflow phê duyệt
- Theo dõi ngoại lệ lặp lại
- Thông báo tự động cho quản lý

### 📊 Báo cáo và thống kê
- Dashboard chấm công cá nhân
- Báo cáo theo nhân viên, phòng ban, thời gian
- Thống kê vi phạm và compliance
- Xuất báo cáo PDF/Excel

### 🔧 Cấu hình linh hoạt
- Thiết lập dung sai thời gian
- Cấu hình bán kính GPS
- Quản lý thông báo
- Tùy chỉnh workflow phê duyệt

## Cài đặt

1. Copy module vào thư mục addons của Odoo
2. Restart Odoo server
3. Vào Apps và tìm "HDI Attendance Management"
4. Click Install

## Cấu hình ban đầu

1. **Thiết lập địa điểm làm việc**: Vào `Cấu hình > Địa điểm làm việc`
2. **Cấu hình settings**: Vào `Cấu hình > Cài đặt chấm công`
3. **Phân quyền**: Gán quyền cho các users tương ứng
4. **Thiết lập nhân viên**: Cấu hình địa điểm mặc định cho từng nhân viên

## Sử dụng

### Cho nhân viên:
- Sử dụng menu "Check-in/Check-out" để chấm công
- Xem lịch sử chấm công tại "Chấm công của tôi"  
- Gửi giải trình khi có ngoại lệ

### Cho quản lý:
- Xem và duyệt chấm công của team
- Phê duyệt giải trình
- Xem báo cáo thống kê

### Cho HR:
- Quản lý toàn bộ dữ liệu chấm công
- Cấu hình system settings
- Tạo báo cáo tổng hợp

## Tích hợp

Module được thiết kế để tích hợp với:
- HR core modules của Odoo
- Timesheet module
- Leave management
- Payroll (tùy chọn)

## Hỗ trợ

Để được hỗ trợ, vui lòng liên hệ:
- Email: support@hdi.com.vn
- Team phát triển: HDI Development Team

## Changelog

### Version 18.0.1.0.0
- Phiên bản đầu tiên
- Đầy đủ tính năng cơ bản
- Tích hợp GPS tracking
- Hệ thống giải trình
- Dashboard và báo cáo

## License
LGPL-3