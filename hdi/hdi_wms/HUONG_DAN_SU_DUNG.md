# HƯỚNG DẪN SỬ DỤNG WMS - Từng bước chi tiết

## 🎯 DEMO NHẬP HÀNG - 5 PHÚT

### Bước 1: Tạo Phiếu Nhập Kho
```
Tồn kho (Inventory) → Vận hành (Operations) → Receipts → Tạo (Create)
```

**Điền thông tin:**
- Contact: Chọn nhà cung cấp (hoặc để trống)
- Scheduled Date: Ngày hôm nay
- Products → Add a line:
  * Product: [Chọn 1 sản phẩm bất kỳ]
  * Demand: 10
  * Done: Để trống (sẽ điền sau)

→ Click **Save**

---

### Bước 2: Xác nhận sẵn sàng nhận hàng
```
Button: Check Availability
```

✅ State chuyển: Waiting → Ready

---

### Bước 3: BẬT CHẾ ĐỘ WMS
```
Tab: Other Info (hoặc cuộn xuống)
```

**Tích chọn:**
- ☑ **Use Batch Management** = Bật

✅ **Kết quả:** 
- Xuất hiện button "Tạo Lô hàng" màu xanh ở header
- Xuất hiện tab "Lô hàng" trong form

---

### Bước 4: Tạo Batch (Lô hàng/Pallet)

#### Cách 1: Từ Header (Nhanh)
```
Button: Tạo Lô hàng (ở header, bên trái button Validate)
```

#### Cách 2: Từ Tab Lô hàng
```
Tab: Lô hàng → Click vào khoảng trắng bên dưới
```

**Popup mở ra - Điền thông tin:**

| Trường | Giá trị ví dụ | Bắt buộc |
|--------|---------------|----------|
| Loại lô | Pallet | ✅ |
| Sản phẩm | [Chọn sản phẩm vừa nhập] | ✅ |
| Số lượng | 10 | ✅ |
| Vị trí | WH/Input | ✅ (tự động) |
| ☑ Tự động tạo mã vạch | Bật | |
| Trọng lượng (kg) | 50 | |
| Thể tích (m³) | 2 | |

→ Click **Tạo**

✅ **Kết quả:**
- Batch `BATCH-000001` xuất hiện trong tab Lô hàng
- State = In Receiving (Đang nhập hàng)
- Có icon 💡 **"Gợi ý"** bên cạnh

---

### Bước 5: GỢI Ý VỊ TRÍ ĐẶT HÀNG

#### Cách 1: Từ Tab Lô hàng (Đề xuất - Dễ nhất)
```
Tab: Lô hàng → Dòng BATCH-000001 → Click icon 💡 "Gợi ý"
```

#### Cách 2: Mở chi tiết Batch
```
Tab: Lô hàng → Click vào tên "BATCH-000001" → Tab "Gợi ý Vị trí Đặt hàng"
→ Button: Gợi ý Vị trí (ở header)
```

**Popup Wizard mở ra:**
- Product: [Đã tự động điền]
- Quantity: [Đã tự động điền]

→ Click **Generate Suggestions** (Tạo gợi ý)

✅ **Kết quả - Danh sách gợi ý xuất hiện:**

Ví dụ:

| Vị trí | Tọa độ | Điểm | Lý do | Action |
|--------|--------|------|-------|--------|
| **Shelf-A-01-03** | 1-1-3 | 95% ████████▓ | ✅ Capacity ok, Same product nearby, A-class | [Chọn vị trí này] ✅ |
| Shelf-A-01-01 | 1-1-1 | 85% ████████░ | ✅ Empty, A-class, Close to input | [Chọn vị trí này] |
| Shelf-B-02-05 | 2-2-5 | 70% ███████░░ | ✅ Available capacity | [Chọn vị trí này] |

---

### Bước 6: CHỌN VỊ TRÍ

```
Click button: [Chọn vị trí này] ở dòng "Shelf-A-01-03"
```

✅ **Kết quả:**
- Popup đóng lại
- Batch BATCH-000001:
  * `Destination Location` = **Shelf-A-01-03**
  * `State` = **In Putaway** (Đang đặt hàng)
- Icon ✅ **"Xác nhận"** xuất hiện

**Thông báo màu xanh:**
> ✅ Location Selected: Putaway location set to WH/Stock/Shelf-A-01-03

---

### Bước 7: XÁC NHẬN ĐÃ ĐẶT HÀNG VÀO VỊ TRÍ

**Tình huống thực tế:**
> Nhân viên kho đã dùng xe nâng di chuyển pallet BATCH-000001 đến vị trí Shelf-A-01-03

**Trong hệ thống:**

#### Cách 1: Từ Tab Lô hàng (Nhanh nhất)
```
Tab: Lô hàng → Dòng BATCH-000001 → Click icon ✅ "Xác nhận"
```

#### Cách 2: Từ Form Batch
```
Mở BATCH-000001 → Button: Xác nhận Lưu kho (header, màu xanh lá)
```

✅ **Kết quả CỰC KỲ QUAN TRỌNG:**
- Batch state → **Stored** (Đã lưu kho)
- **stock.quant** (tồn kho core) được cập nhật:
  * Product: [Sản phẩm của bạn]
  * Location: **Shelf-A-01-03**
  * Quantity: 10
  * Batch: BATCH-000001

---

### Bước 8: HOÀN TẤT NHẬP KHO

```
Quay lại form Receipt → Button: Validate (màu xanh lá)
```

✅ **WMS Kiểm tra tự động:**
- Có batch nào chưa stored không? → KHÔNG (BATCH-000001 đã stored)
- ✅ Cho phép validate

✅ **Odoo Core thực hiện:**
- Stock moves confirmed
- Inventory updated
- State → Done

✅ **WMS State:**
- picking.wms_state → **WMS Complete**
- picking.actual_end_time = [Giờ hiện tại]

---

## ✅ KIỂM TRA KẾT QUẢ

### 1. Xem Tồn kho theo Vị trí
```
Tồn kho → Báo cáo → Inventory Report
Filter: Location = "Shelf-A-01-03"
```

**Kết quả:**
| Product | Location | Batch | Quantity |
|---------|----------|-------|----------|
| [Sản phẩm] | Shelf-A-01-03 | BATCH-000001 | 10 |

### 2. Xem Batch đã tạo
```
Tồn kho → Quản lý Kho → Lô hàng / Pallet
```

**Kết quả:**
- BATCH-000001
- State: Stored ✅
- Location: Shelf-A-01-03
- Product: [Sản phẩm]
- Quantity: 10

### 3. Xem Timeline Batch
```
Mở BATCH-000001 → Tab Chuyển kho (Stock Moves)
```

**History:**
1. 2025-12-03 10:00 - Created at WH/Input
2. 2025-12-03 10:05 - Putaway to Shelf-A-01-03
3. 2025-12-03 10:06 - Stored

---

## 🎓 CÁC TÍNH NĂNG NÂNG CAO

### A. Quét Barcode (Nếu có máy quét)
```
Button: Quét Mã vạch → Chọn chế độ "Scan Batch"
→ Quét mã BATCH-000001
→ ✅ Confirmed
```

### B. Gợi ý cho Nhiều Batch cùng lúc
```
Header → Button: Gợi ý Vị trí Tất cả
→ Hệ thống gợi ý cho tất cả batch chưa có destination
```

### C. Theo dõi LOT/Serial Number
```
Khi tạo Batch → Điền thêm:
- Lot/Serial Number: LOT2025001
- Expiration Date: 2025-12-31
- Manufacturing Date: 2025-01-01
```

### D. Priority (Ưu tiên)
```
Receipt form → WMS Priority: Urgent
→ Batch này sẽ được ưu tiên xử lý
```

---

## ❌ XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi 1: Không thấy button "Tạo Lô hàng"
**Nguyên nhân:** Chưa bật Use Batch Management  
**Giải pháp:** 
```
Receipt → Other Info → ☑ Use Batch Management = Bật
```

### Lỗi 2: Không thấy Tab "Lô hàng"
**Nguyên nhân:** Tương tự lỗi 1  
**Giải pháp:** Bật Use Batch Management

### Lỗi 3: Button "Gợi ý" không hoạt động
**Nguyên nhân:** Batch chưa có Product  
**Giải pháp:** 
```
Edit Batch → Điền Product → Save
```

### Lỗi 4: "No suitable locations found"
**Nguyên nhân:** 
- Không có location nào đủ capacity
- Hoặc không có location nào có `is_putable = True`

**Giải pháp:**
```
Tồn kho → Configuration → Locations
→ Tạo location mới hoặc Edit location cũ:
  - ☑ Is Putable = True
  - Max Weight: 500
  - Max Volume: 10
  - Coordinate X-Y-Z: điền giá trị
```

### Lỗi 5: Validate bị chặn "batches not stored"
**Nguyên nhân:** Đúng theo design! Phải hoàn tất putaway trước  
**Giải pháp:**
```
1. Xem tab Lô hàng
2. Kiểm tra batch nào State != Stored
3. Click "Gợi ý" → Chọn location → "Xác nhận"
4. Lặp lại cho tất cả batch
5. Sau đó mới Validate
```

---

## 📊 CÁC TRƯỜNG HỢP SỬ DỤNG KHÁC

### 1. Hàng Hỏng
```
Batch → Reason Code = "Damaged Goods"
→ Gợi ý sẽ tự động chọn: WH/Quarantine-Damage
```

### 2. Hàng Trả lại
```
Receipt → Origin = "Return/XXXXX"
Batch → Reason Code = "Customer Return"
```

### 3. Mixed Products (Nhiều sản phẩm trong 1 pallet)
```
Tạo Batch → Product = [Để trống]
→ Batch type = "Mixed"
```

---

## 🚀 TỔNG KẾT QUY TRÌNH

```
1. Tạo Receipt
2. Check Availability
3. ☑ Use Batch Management
4. Tạo Lô hàng (BATCH-000001)
5. 💡 Gợi ý Vị trí
6. ✅ Chọn Shelf-A-01-03
7. ✅ Xác nhận Lưu kho
8. Validate Receipt
9. ✅ DONE - Hàng đã vào Shelf-A-01-03
```

**Thời gian:** 2-3 phút/receipt (sau khi quen)

**Lợi ích:**
- ✅ Tồn kho chính xác 100%
- ✅ Biết hàng ở đâu (Shelf-A-01-03)
- ✅ Trace được batch/lot
- ✅ Optimize vị trí đặt hàng
- ✅ Barcode scanning
- ✅ Báo cáo đầy đủ
