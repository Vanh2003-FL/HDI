# 🚀 QUICK START GUIDE - HDI SHIPPING

## 📦 Cài đặt nhanh (5 phút)

### 1. Cài đặt module
```bash
# Restart Odoo server
sudo systemctl restart odoo

# Hoặc nếu chạy manual:
./odoo-bin -c odoo.conf
```

Sau đó:
1. Vào Odoo → **Apps**
2. Nhấn **Update Apps List**
3. Tìm **"HDI Shipping"**
4. Nhấn **Install** ✅

---

## ⚙️ Cấu hình ban đầu (5 phút)

### Bước 1: Tạo dịch vụ vận chuyển
1. **Vận chuyển HDI** → **Cấu hình** → **Dịch vụ vận chuyển**
2. Nhấn **Create**
3. Điền thông tin:
   - **Tên dịch vụ**: FUTA Express
   - **Mô tả**: Giao hàng nhanh trong 24h
   - **Giá cơ bản**: 30000 (VNĐ)
4. **Save**

Lặp lại cho các dịch vụ khác (FUTA Standard, FUTA Economy...)

### Bước 2: Tạo địa chỉ gửi hàng
1. **Vận chuyển HDI** → **Cấu hình** → **Địa chỉ gửi hàng**
2. Nhấn **Create**
3. Điền thông tin:
   - **Tên người gửi**: Công ty ABC
   - **Điện thoại**: 0901234567
   - **Đường**: 123 Nguyễn Văn Linh
   - **Thành phố**: Hồ Chí Minh
   - **Tỉnh/Thành**: Chọn "Hồ Chí Minh"
   - ✅ **Địa chỉ mặc định**: Tích chọn
4. **Save**

---

## 🎯 Sử dụng cơ bản

### ✅ Tạo đơn hàng mới

**Bước 1-5 phút:**
1. **Vận chuyển HDI** → **Tạo đơn hàng**
2. Nhấn **Create**
3. **Thông tin người gửi:**
   - Chọn **Địa chỉ gửi** (đã tạo ở trên)
4. **Thông tin người nhận:**
   - Tên: Nguyễn Văn A
   - SĐT: 0912345678
   - Địa chỉ: 456 Lê Lợi, Quận 1, TP.HCM
5. **Thêm hàng hóa:**
   - Nhấn **Add a line**
   - Tên hàng: Quần áo
   - Loại: Hàng thời trang
   - Số lượng: 5
   - Trọng lượng: 2.5 kg
   - Giá trị: 500000 VNĐ
6. **Chọn dịch vụ:**
   - Dịch vụ: FUTA Express
7. **Thông tin cước phí:**
   - ⬜ Người nhận trả cước (bỏ trống = người gửi trả)
   - COD: 0 (hoặc nhập nếu có)
8. **Save**

➡️ Đơn được tạo với trạng thái **"Đơn nháp"** ✅

---

### ✅ Duyệt đơn hàng

**Sau khi tạo đơn:**
1. Kiểm tra lại thông tin
2. Nhấn nút **"Duyệt đơn"** (màu xanh)
3. Xác nhận: **OK**

➡️ Đơn chuyển sang **"Chờ lấy hàng"** ✅
➡️ ⚠️ **Không thể sửa nội dung nữa!**

---

### ✅ Quản lý đơn hàng

1. **Vận chuyển HDI** → **Quản lý đơn hàng gửi**
2. Xem danh sách tất cả đơn

**Tìm kiếm nhanh:**
- Nhập mã đơn vào ô search
- Hoặc nhập SĐT người nhận

**Lọc đơn:**
- Nhấn **Filters** → Chọn:
  - **Đơn nháp** (chưa duyệt)
  - **Chờ lấy hàng** (đã duyệt, chờ FUTA)
  - **Hôm nay** (đơn tạo hôm nay)

---

### ✅ In đơn hàng

**Cách 1: In 1 đơn**
1. Mở form đơn hàng
2. Nhấn nút **"In đơn"** (icon máy in)
3. PDF tự động tải xuống ✅

**Cách 2: In nhiều đơn**
1. **Quản lý đơn hàng gửi**
2. **Tích chọn** các đơn cần in (☑️)
3. Nhấn **"In đơn đã chọn"** (button màu xanh ở trên)
4. Wizard hiện ra → Nhấn **"In đơn"**
5. PDF gộp tự động tải xuống ✅

---

### ✅ Hủy đơn hàng

**Chỉ hủy được đơn Draft hoặc Waiting Pickup:**
1. Mở đơn hàng
2. Nhấn nút **"Hủy đơn"**
3. Xác nhận: **OK**

➡️ Đơn chuyển sang **"Đã hủy"** ✅

---

## 🔄 Workflow đơn hàng

```
1️⃣ TẠO ĐƠN → Trạng thái: "Đơn nháp"
   ↓ (Nhấn "Duyệt đơn")
   
2️⃣ DUYỆT → Trạng thái: "Chờ lấy hàng"
   ↓ (FUTA đến lấy hàng - Admin)
   
3️⃣ LẤY HÀNG → Trạng thái: "Đang vận chuyển"
   ↓ (FUTA giao hàng)
   
4️⃣ GIAO THÀNH CÔNG → Trạng thái: "Đã giao" ✅ XONG
   
   HOẶC
   
4️⃣ GIAO THẤT BẠI → Trạng thái: "Chờ duyệt hoàn"
   ├─ Chọn "Duyệt hoàn" → "Đã hoàn" ✅ XONG
   └─ Chọn "Phát lại" → "Đang vận chuyển" (quay lại bước 3)
```

---

## 🎨 Màu sắc trạng thái

| Trạng thái | Màu | Ý nghĩa |
|------------|-----|---------|
| 🔵 Đơn nháp | Xanh dương | Mới tạo, chưa duyệt |
| 🟦 Chờ lấy hàng | Xanh lam | Đã duyệt, chờ FUTA |
| ⚪ Đang vận chuyển | Trắng | FUTA đang giao |
| 🟡 Chờ duyệt hoàn | Vàng | Giao thất bại, chờ quyết định |
| 🟢 Đã giao | Xanh lá | Thành công |
| ⚫ Đã hoàn | Xám | Đã trả về |
| ⚫ Đã hủy | Xám | Đã hủy |

---

## ⚠️ Lưu ý quan trọng

### 🚫 SAU KHI DUYỆT ĐƠN:
- ❌ **KHÔNG thể sửa** thông tin người nhận
- ❌ **KHÔNG thể sửa** hàng hóa
- ❌ **KHÔNG thể sửa** dịch vụ
- ❌ **KHÔNG thể sửa** COD
- ✅ **CHỈ có thể xem** và in

### ✅ TRƯỚC KHI DUYỆT:
- ✅ Kiểm tra kỹ SĐT người nhận
- ✅ Kiểm tra kỹ địa chỉ
- ✅ Kiểm tra kỹ hàng hóa
- ✅ Kiểm tra kỹ COD

### 🔐 HỦY ĐƠN:
- ✅ Chỉ hủy được ở: **Đơn nháp**, **Chờ lấy hàng**
- ❌ Không hủy được khi: **Đang vận chuyển**, **Đã giao**, v.v.

---

## 📊 Dashboard nhanh

### Xem tất cả đơn hôm nay:
**Quản lý đơn hàng gửi** → **Filters** → **Hôm nay**

### Xem đơn chờ duyệt:
**Quản lý đơn hàng gửi** → **Filters** → **Đơn nháp**

### Xem đơn đã duyệt chờ lấy:
**Quản lý đơn hàng gửi** → **Filters** → **Chờ lấy hàng**

### Xem đơn có vấn đề:
**Quản lý đơn hàng gửi** → **Filters** → **Chờ duyệt hoàn**

---

## 🎯 Kịch bản thực tế

### Kịch bản 1: Shop gửi 10 đơn/ngày
**Buổi sáng (9h):**
1. Tạo 10 đơn hàng mới (mỗi đơn 2-3 phút)
2. Kiểm tra kỹ thông tin
3. Duyệt tất cả 10 đơn

**Buổi trưa (12h):**
4. In tất cả 10 đơn (chọn nhiều đơn → In gộp)
5. Dán phiếu lên hàng

**Buổi chiều (14h):**
6. FUTA đến lấy hàng
7. Admin đánh dấu "Đã lấy hàng"

**Ngày hôm sau:**
8. Kiểm tra trạng thái giao hàng
9. Xử lý đơn hoàn (nếu có)

### Kịch bản 2: Xử lý đơn hoàn
**Nhận thông báo:**
1. Đơn SO/2025/0123 giao thất bại
2. Lý do: Người nhận không nghe máy

**Xử lý:**
3. Mở đơn → Trạng thái "Chờ duyệt hoàn"
4. Gọi lại người nhận
5. Nếu OK → Nhấn **"Phát lại"**
6. Nếu không OK → Nhấn **"Duyệt hoàn"**

---

## 📱 Tips & Tricks

### 💡 Tip 1: Tạo đơn nhanh
- Sao chép đơn cũ: Mở đơn → Action → Duplicate
- Chỉ cần sửa thông tin người nhận

### 💡 Tip 2: Tìm đơn nhanh
- Nhập **SĐT** vào search → Enter
- Tất cả đơn của khách đó sẽ hiện ra

### 💡 Tip 3: In đơn nhanh
- Filter: Hôm nay + Chờ lấy hàng
- Chọn tất cả (Ctrl+A)
- In đơn đã chọn

### 💡 Tip 4: Theo dõi đơn
- Vào form đơn
- Tab "Lịch sử trạng thái"
- Xem toàn bộ quá trình

### 💡 Tip 5: Nhắc việc
- Vào form đơn
- Nhấn "Schedule Activity"
- Đặt nhắc nhở: "Gọi khách xác nhận" vào ngày mai

---

## ❓ FAQ - Câu hỏi thường gặp

**Q: Tôi duyệt nhầm đơn, làm sao sửa?**
A: Sau khi duyệt không thể sửa. Chỉ có thể Hủy → Tạo lại đơn mới.

**Q: Tôi muốn in logo công ty lên phiếu?**
A: Settings → Companies → Upload logo. Logo sẽ tự động hiện trên phiếu.

**Q: Làm sao biết ai đã duyệt đơn?**
A: Mở form đơn → Xem field "Người duyệt" và "Ngày duyệt".

**Q: Tôi có thể in đơn nhiều lần không?**
A: Có! Không giới hạn số lần in.

**Q: Làm sao xem tất cả đơn của 1 địa chỉ gửi?**
A: Quản lý đơn hàng → Search box → Chọn địa chỉ gửi → Apply.

**Q: Có thể xóa đơn không?**
A: Chỉ Admin mới được xóa. User thường chỉ Hủy đơn.

---

## 📞 Liên hệ hỗ trợ

- 📧 Email: support@hdi.vn
- 📱 Hotline: 1900-xxxx
- 🌐 Website: https://hdi.vn
- 📖 Docs: https://docs.hdi.vn/shipping

---

## ✅ Checklist bắt đầu

- [ ] Đã cài đặt module
- [ ] Đã tạo ít nhất 1 dịch vụ vận chuyển
- [ ] Đã tạo ít nhất 1 địa chỉ gửi hàng
- [ ] Đã tạo thử 1 đơn hàng
- [ ] Đã duyệt thử 1 đơn hàng
- [ ] Đã in thử 1 đơn hàng
- [ ] Đã hủy thử 1 đơn hàng
- [ ] Đã xem lịch sử trạng thái
- [ ] Đã tìm kiếm/lọc đơn hàng
- [ ] Đã đọc hết Quick Start Guide này

➡️ **Bạn đã sẵn sàng sử dụng HDI Shipping!** 🎉

---

**Version:** 18.0.1.0.0  
**Last Updated:** December 2, 2025  
**Author:** HDI Development Team
