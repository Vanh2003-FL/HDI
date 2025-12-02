# 🧪 TESTING CHECKLIST - HDI SHIPPING MODULE

## 📋 Pre-Installation Tests

### 1. File Structure ✅
- [x] `__init__.py` imports models và wizards
- [x] `__manifest__.py` có đầy đủ dependencies (contacts, mail, stock)
- [x] All models có trong `models/__init__.py`
- [x] All wizards có trong `wizards/__init__.py`
- [x] Security file có đầy đủ access rights
- [x] Menu file có đúng sequence

### 2. Python Syntax ✅
- [x] No syntax errors in models
- [x] No syntax errors in wizards
- [x] All imports are correct
- [x] All dependencies exist

### 3. XML Syntax
- [ ] Validate all view XML files
- [ ] Check report template XML
- [ ] Check menu XML
- [ ] Check wizard views XML

---

## 🚀 Installation Tests

### 1. Module Installation
```bash
# Update module list
Apps → Update Apps List

# Install module
Search "HDI Shipping" → Install
```

**Expected Result:**
- ✅ Module installs without errors
- ✅ All models created in database
- ✅ All views loaded
- ✅ Menu items appear

### 2. Check Database
```sql
-- Check if tables exist
SELECT tablename FROM pg_tables WHERE tablename LIKE 'shipping_%';

-- Expected tables:
-- shipping_order
-- shipping_order_state_log
-- sender_address
-- shipping_service
-- shipment_item
```

### 3. Check Views
```
Settings → Technical → User Interface → Views
Search: "shipping"
```

**Expected:**
- shipping.order.search
- shipping.order.list
- shipping.order.form
- shipping.order.print.wizard.form
- sender.address views
- shipping.service views

---

## 🧪 Functional Tests

### Test 1: Tạo đơn hàng mới
**Steps:**
1. Vận chuyển HDI → Tạo đơn hàng
2. Chọn địa chỉ gửi (nếu chưa có, tạo mới)
3. Nhập thông tin người nhận
4. Thêm ít nhất 1 hàng hóa
5. Chọn dịch vụ vận chuyển
6. Lưu

**Expected:**
- ✅ Order number tự động generate (VD: SO/2025/0001)
- ✅ State = "Đơn nháp"
- ✅ Total weight và total value tự tính
- ✅ Shipping cost tự tính
- ✅ Tất cả fields có thể edit

### Test 2: Duyệt đơn hàng
**Steps:**
1. Mở đơn "Đơn nháp" từ Test 1
2. Nhấn "Duyệt đơn"
3. Xác nhận

**Expected:**
- ✅ State chuyển sang "Chờ lấy hàng"
- ✅ approved_date được ghi nhận
- ✅ approved_by = current user
- ✅ Tất cả fields trở thành readonly
- ✅ Button "Duyệt đơn" biến mất
- ✅ Button "Hủy đơn" vẫn còn
- ✅ Log được tạo trong tab "Lịch sử trạng thái"

### Test 3: Hủy đơn từ Draft
**Steps:**
1. Tạo đơn mới (State = Draft)
2. Nhấn "Hủy đơn"
3. Xác nhận

**Expected:**
- ✅ State = "Đã hủy"
- ✅ Log được tạo
- ✅ Không còn button action nào

### Test 4: Hủy đơn từ Waiting Pickup
**Steps:**
1. Tạo đơn mới → Duyệt đơn (State = Waiting Pickup)
2. Nhấn "Hủy đơn"
3. Xác nhận

**Expected:**
- ✅ State = "Đã hủy"
- ✅ Log được tạo

### Test 5: Workflow - Đã lấy hàng (Admin only)
**Steps:**
1. Login as admin/stock manager
2. Mở đơn "Chờ lấy hàng"
3. Nhấn "Đã lấy hàng"

**Expected:**
- ✅ State = "Đang vận chuyển"
- ✅ Log được tạo
- ✅ Hiện buttons: "Đã giao", "Yêu cầu duyệt hoàn"

### Test 6: Workflow - Đã giao (Admin only)
**Steps:**
1. Mở đơn "Đang vận chuyển"
2. Nhấn "Đã giao"

**Expected:**
- ✅ State = "Đã giao"
- ✅ Log được tạo
- ✅ Không còn action buttons

### Test 7: Workflow - Yêu cầu duyệt hoàn (Admin only)
**Steps:**
1. Mở đơn "Đang vận chuyển"
2. Nhấn "Yêu cầu duyệt hoàn"

**Expected:**
- ✅ State = "Chờ duyệt hoàn"
- ✅ Log được tạo
- ✅ Hiện buttons: "Duyệt hoàn", "Phát lại"

### Test 8: Duyệt hoàn
**Steps:**
1. Mở đơn "Chờ duyệt hoàn"
2. Nhấn "Duyệt hoàn"
3. Xác nhận

**Expected:**
- ✅ State = "Đã hoàn"
- ✅ Log được tạo
- ✅ Không còn action buttons

### Test 9: Phát lại
**Steps:**
1. Mở đơn "Chờ duyệt hoàn"
2. Nhấn "Phát lại"
3. Xác nhận

**Expected:**
- ✅ State = "Đang vận chuyển"
- ✅ Log được tạo
- ✅ Có thể giao lại hoặc yêu cầu hoàn tiếp

### Test 10: Không thể sửa đơn đã duyệt
**Steps:**
1. Tạo đơn → Duyệt
2. Thử sửa: Tên người nhận, SĐT, Hàng hóa, Dịch vụ

**Expected:**
- ✅ Tất cả fields đều readonly
- ✅ Không thể thêm/xóa hàng hóa
- ✅ can_edit = False

---

## 🔍 Search & Filter Tests

### Test 11: Tìm kiếm cơ bản
**Steps:**
1. Vận chuyển HDI → Quản lý đơn hàng gửi
2. Tìm theo:
   - Mã đơn hàng
   - Tên người nhận
   - SĐT người nhận

**Expected:**
- ✅ Kết quả chính xác
- ✅ Tìm partial match cho tên
- ✅ Tìm exact/partial cho SĐT

### Test 12: Filter theo trạng thái
**Steps:**
1. Quản lý đơn hàng gửi
2. Apply từng filter:
   - Đơn nháp
   - Chờ lấy hàng
   - Đang vận chuyển
   - Chờ duyệt hoàn
   - Đã giao
   - Đã hoàn
   - Đã hủy

**Expected:**
- ✅ Mỗi filter hiển thị đúng đơn theo state

### Test 13: Filter theo thời gian
**Steps:**
1. Tạo nhiều đơn ở các ngày khác nhau
2. Apply filters:
   - Hôm nay
   - Tuần này
   - Tháng này

**Expected:**
- ✅ Chỉ hiển thị đơn trong khoảng thời gian tương ứng

### Test 14: Filter theo địa chỉ gửi
**Steps:**
1. Tạo 2 địa chỉ gửi khác nhau
2. Tạo đơn cho mỗi địa chỉ
3. Filter theo từng địa chỉ

**Expected:**
- ✅ Chỉ hiển thị đơn của địa chỉ được chọn

### Test 15: Group By
**Steps:**
1. Tạo đơn với các trạng thái, dịch vụ khác nhau
2. Group by:
   - Trạng thái
   - Địa chỉ gửi
   - Dịch vụ
   - Ngày tạo

**Expected:**
- ✅ Dữ liệu được nhóm đúng
- ✅ Đếm số lượng đơn mỗi nhóm chính xác

---

## 🖨️ Print Tests

### Test 16: In từng đơn
**Steps:**
1. Mở form đơn hàng
2. Nhấn "In đơn"

**Expected:**
- ✅ PDF được tải xuống
- ✅ Tên file: "Phiếu gửi - SO/2025/0001.pdf"
- ✅ Nội dung đầy đủ:
  - Header: PHIẾU GỬI HÀNG
  - Mã đơn, ngày tạo, trạng thái
  - Thông tin người gửi đầy đủ
  - Thông tin người nhận đầy đủ
  - Bảng hàng hóa
  - Tổng cộng: số lượng, trọng lượng, giá trị
  - Cước phí, COD, người trả cước
  - Khu vực chữ ký

### Test 17: In nhiều đơn
**Steps:**
1. Quản lý đơn hàng gửi
2. Chọn 3-5 đơn
3. Nhấn "In đơn đã chọn"
4. Wizard hiện ra:
   - Kiểm tra số đơn đã chọn
   - Chọn "In gộp nhiều đơn"
5. Nhấn "In đơn"

**Expected:**
- ✅ Wizard hiển thị đúng số đơn
- ✅ PDF gộp được tải xuống
- ✅ Mỗi đơn trên 1 trang riêng
- ✅ Nội dung đầy đủ cho tất cả đơn

### Test 18: In đơn có nhiều hàng hóa
**Steps:**
1. Tạo đơn với 10+ items
2. In đơn

**Expected:**
- ✅ Bảng hàng hóa hiển thị đủ
- ✅ Tự động xuống trang nếu quá dài
- ✅ Tổng cộng chính xác

---

## 📊 Log & History Tests

### Test 19: Xem lịch sử trạng thái
**Steps:**
1. Tạo đơn mới (Draft)
2. Duyệt đơn (Waiting Pickup)
3. Đã lấy hàng (In Transit)
4. Yêu cầu duyệt hoàn (Pending Return)
5. Phát lại (In Transit)
6. Đã giao (Delivered)
7. Vào tab "Lịch sử trạng thái"

**Expected:**
- ✅ Có 5 log entries
- ✅ Mỗi log có:
  - Thời gian chính xác
  - Người thực hiện
  - Trạng thái cũ → mới
- ✅ Sắp xếp theo thời gian giảm dần

### Test 20: Log không thể xóa/sửa
**Steps:**
1. Vào tab "Lịch sử trạng thái"
2. Thử xóa/sửa log

**Expected:**
- ✅ Không có button create/edit/delete
- ✅ Tất cả readonly

---

## 🔐 Security Tests

### Test 21: User permissions
**Steps:**
1. Login as normal user (không phải admin)
2. Thử:
   - Tạo đơn ✅
   - Sửa đơn draft ✅
   - Duyệt đơn ✅
   - Hủy đơn ✅
   - Xem log ✅
   - Sửa log ❌
   - Xóa đơn ❌

**Expected:**
- ✅ User có thể làm việc với đơn của mình
- ✅ Không thể xóa đơn
- ✅ Không thể sửa log

### Test 22: Admin permissions
**Steps:**
1. Login as admin/stock manager
2. Thử:
   - Tất cả actions của user ✅
   - Đã lấy hàng ✅
   - Đã giao ✅
   - Yêu cầu duyệt hoàn ✅
   - Xóa đơn ✅

**Expected:**
- ✅ Admin có full quyền

---

## 🎨 UI/UX Tests

### Test 23: Màu sắc trạng thái
**Steps:**
1. Tạo đơn ở tất cả trạng thái
2. Xem list view

**Expected:**
- ✅ Draft: màu xanh dương (info)
- ✅ Waiting Pickup: màu xanh lam (primary)
- ✅ In Transit: không màu (default)
- ✅ Pending Return: màu vàng (warning)
- ✅ Delivered: màu xanh lá (success)
- ✅ Returned: màu xám (muted)
- ✅ Cancelled: màu xám (muted)

### Test 24: Button visibility
**Steps:**
1. Kiểm tra buttons trên mỗi trạng thái:

**Draft:**
- ✅ Hiện: Duyệt đơn, Hủy đơn, In đơn
- ✅ Ẩn: Tất cả buttons khác

**Waiting Pickup:**
- ✅ Hiện: Hủy đơn, In đơn, Đã lấy hàng (admin)
- ✅ Ẩn: Duyệt đơn

**In Transit:**
- ✅ Hiện: In đơn, Đã giao (admin), Yêu cầu duyệt hoàn (admin)
- ✅ Ẩn: Duyệt, Hủy

**Pending Return:**
- ✅ Hiện: In đơn, Duyệt hoàn, Phát lại
- ✅ Ẩn: Tất cả buttons khác

**Delivered/Returned/Cancelled:**
- ✅ Hiện: In đơn
- ✅ Ẩn: Tất cả buttons khác

### Test 25: Chatter
**Steps:**
1. Mở form đơn hàng
2. Kiểm tra chatter:
   - Gửi message
   - Tag user
   - Log note
   - Schedule activity

**Expected:**
- ✅ Chatter hoạt động bình thường
- ✅ Notifications được gửi
- ✅ Activities hiển thị

---

## 📱 Responsive Tests

### Test 26: Mobile view
**Steps:**
1. Mở trên mobile/tablet
2. Kiểm tra:
   - List view
   - Form view
   - Search filters
   - Print wizard

**Expected:**
- ✅ Layout responsive
- ✅ Buttons accessible
- ✅ Forms usable

---

## 🐛 Error Handling Tests

### Test 27: Validation errors
**Test các trường hợp lỗi:**

1. Tạo đơn không có hàng hóa → Duyệt
   - ❌ "Vui lòng thêm hàng hóa trước khi duyệt đơn!"

2. Hủy đơn đang In Transit
   - ❌ "Chỉ có thể hủy đơn ở trạng thái Đơn nháp hoặc Chờ lấy hàng!"

3. Duyệt đơn đã duyệt
   - ❌ "Chỉ đơn nháp mới có thể được duyệt!"

4. Duyệt hoàn đơn không phải Pending Return
   - ❌ "Chỉ đơn đang Chờ duyệt hoàn mới có thể duyệt hoàn!"

**Expected:**
- ✅ Tất cả validations hoạt động
- ✅ Messages rõ ràng
- ✅ Không crash

---

## 📈 Performance Tests

### Test 28: Large dataset
**Steps:**
1. Tạo 100+ đơn hàng
2. Mở list view
3. Apply filters
4. Group by
5. Print multiple orders (20+)

**Expected:**
- ✅ List view load < 3s
- ✅ Filters apply < 1s
- ✅ Print không quá chậm
- ✅ Không memory errors

---

## ✅ Final Checklist

### Pre-Production
- [ ] All tests passed
- [ ] No console errors
- [ ] No database errors
- [ ] Documentation complete
- [ ] User manual created
- [ ] Training materials ready

### Production Ready
- [ ] Backup database
- [ ] Install on staging
- [ ] User acceptance testing
- [ ] Performance benchmarks ok
- [ ] Security audit passed
- [ ] Ready for production deployment

---

## 📝 Test Results

| Test Category | Total Tests | Passed | Failed | Notes |
|---------------|-------------|--------|--------|-------|
| Installation  | 3 | - | - | |
| Functional    | 10 | - | - | |
| Search/Filter | 5 | - | - | |
| Print         | 3 | - | - | |
| Log/History   | 2 | - | - | |
| Security      | 2 | - | - | |
| UI/UX         | 3 | - | - | |
| Responsive    | 1 | - | - | |
| Error Handling| 1 | - | - | |
| Performance   | 1 | - | - | |
| **TOTAL**     | **31** | **-** | **-** | |

---

**Status**: 🟡 READY FOR TESTING
**Last Updated**: December 2, 2025
**Tested By**: [Tester Name]
**Environment**: Odoo 18.0
