# HƯỚNG DẪN SỬ DỤNG - XUẤT KHO (OUTBOUND / PICKING)

## 🎯 DEMO XUẤT KHO - 10 PHÚT

### Tổng quan quy trình
```
1. Nhận yêu cầu xuất kho
2. Tạo Delivery Order
3. ⚡ HỆ THỐNG GỢI Ý VỊ TRÍ LẤY HÀNG (FIFO/FEFO)
4. Tạo Pick Tasks (công việc lấy hàng)
5. Gán nhân viên
6. Nhân viên lấy hàng từ vị trí được gợi ý
7. Quét barcode xác nhận
8. Validate phiếu xuất kho
9. ✅ HOÀN TẤT
```

**Thời gian:** 5-7 phút/phiếu xuất (sau khi quen)

---

## PHASE 1: TẠO PHIẾU XUẤT KHO

### Bước 1: Tạo Delivery Order
```
Tồn kho (Inventory) → Vận hành (Operations) → Delivery Orders → Tạo (Create)
```

**Điền thông tin:**
- Customer: Chọn khách hàng
- Scheduled Date: Ngày xuất
- Products → Add a line:
  * Product: [Chọn sản phẩm cần xuất]
  * Demand: 100 (ví dụ)

→ Click **Save**

---

### Bước 2: Check Availability
```
Button: Check Availability
```

✅ State chuyển: Draft → Ready

---

## PHASE 2: GỢI Ý VỊ TRÍ LẤY HÀNG (FIFO)

### Bước 3: Chọn chiến lược lấy hàng

```
Tab: Other Info → hoặc cuộn xuống
```

**Chọn Pick Strategy:**
- ☑ **FIFO** = First In First Out (Hàng nhập trước → lấy trước) ✅ MẶC ĐỊNH
- ☐ FEFO = First Expire First Out (Hàng hết hạn sớm → lấy trước)
- ☐ Manual = Tự chọn vị trí

---

### Bước 4: Tạo gợi ý lấy hàng

#### Cách 1: Từ Header (Nhanh)
```
Button: "Gợi ý Lấy hàng (FIFO)" (màu xanh, ở header)
```

#### Cách 2: Từ Tab Pick Tasks
```
Tab: Pick Tasks → Button: "1️⃣ Tạo Gợi ý Lấy hàng"
```

**Hệ thống tự động:**
1. Tìm tất cả vị trí có sản phẩm cần xuất
2. Sắp xếp theo FIFO (ngày nhập cũ → mới)
3. Chia số lượng ra nhiều batch/vị trí nếu cần
4. Tính điểm ưu tiên (priority score)

✅ **Kết quả - Danh sách gợi ý xuất hiện:**

**Ví dụ: Cần xuất 100 sản phẩm A**

| STT | Vị trí | Tọa độ | Batch | Số lượng lấy | Ngày nhập | Lý do |
|-----|--------|--------|-------|--------------|-----------|-------|
| 1 | **Shelf-A-01-03** | 1-1-3 | BATCH-001 | 50 | 01/12/2025 | FIFO: Nhập 01/12/2025<br/>Vị trí ưu tiên 10<br/>Batch BATCH-001 |
| 2 | **Shelf-A-02-05** | 1-2-5 | BATCH-005 | 30 | 03/12/2025 | FIFO: Nhập 03/12/2025<br/>Vị trí ưu tiên 15 |
| 3 | **Shelf-B-01-01** | 2-1-1 | BATCH-008 | 20 | 05/12/2025 | FIFO: Nhập 05/12/2025<br/>Vị trí ưu tiên 20 |

**💡 Chú ý:**
- Thứ tự = thứ tự đi lấy (1 → 2 → 3)
- Hàng cũ nhất được gợi ý lấy trước (FIFO)
- Nếu 1 vị trí không đủ hàng → Hệ thống tự động chia ra nhiều vị trí

---

## PHASE 3: TẠO PICK TASKS (CÔNG VIỆC LẤY HÀNG)

### Bước 5: Tạo Pick Tasks từ gợi ý

```
Tab: Pick Tasks → Button: "2️⃣ Tạo Pick Tasks"
```

**Hệ thống tự động tạo:**
- 1 Pick Task = 1 công việc lấy hàng từ 1 vị trí cụ thể
- Mỗi task có:
  * Vị trí cần đến: Shelf-A-01-03
  * Tọa độ: 1-1-3
  * Sản phẩm: Product A
  * Batch: BATCH-001
  * Số lượng cần lấy: 50
  * Trạng thái: Chờ lấy hàng

✅ **Kết quả:**
- 3 Pick Tasks được tạo (PICK-000001, PICK-000002, PICK-000003)
- Thứ tự đã được sắp xếp sẵn
- Sẵn sàng gán cho nhân viên

---

### Bước 6: Gán nhân viên (Tùy chọn)

**Cách 1: Gán từ danh sách Pick Tasks**
```
Tab: Pick Tasks → Click vào task → Nhân viên được gán: [Chọn nhân viên]
```

**Cách 2: Nhân viên tự nhận trên Mobile**
- Nhân viên mở app trên iPad/Mobile
- Xem danh sách task chưa gán
- Click "Nhận task"

**Cách 3: Hệ thống tự động gán**
- Dựa trên khu vực (zone) nhân viên phụ trách
- Hoặc round-robin

---

## PHASE 4: LẤY HÀNG TẠI KHO

### Bước 7: Nhân viên bắt đầu lấy hàng

**Nhân viên mở Mobile/iPad:**

```
Menu: Inventory → Quản lý Kho → Pick Tasks → Click vào PICK-000001
```

**Hoặc quét QR code của task (nếu có in sẵn)**

**Màn hình hiển thị:**
```
╔═══════════════════════════════════════╗
║        PICK-000001                     ║
╠═══════════════════════════════════════╣
║ 📍 Vị trí: Shelf-A-01-03              ║
║ 📐 Tọa độ: 1-1-3                      ║
║ 📦 Sản phẩm: Product A                 ║
║ 🏷️  Batch: BATCH-001                  ║
║                                        ║
║ Cần lấy: 50                            ║
║ Đã lấy:  0                             ║
║                                        ║
║  [▶ BẮT ĐẦU]                          ║
╚═══════════════════════════════════════╝
```

**Click button: "▶ BẮT ĐẦU"**

✅ **Kết quả:**
- State chuyển: Chờ lấy hàng → **Đang lấy hàng**
- Ghi lại thời gian bắt đầu
- Nhân viên được gán (nếu chưa có)

---

### Bước 8: Đi đến vị trí và lấy hàng

**Nhân viên:**
1. Nhìn màn hình: Vị trí **Shelf-A-01-03** (Tọa độ 1-1-3)
2. Đi đến vị trí đó
3. Tìm Batch **BATCH-001** (có QR code)

**Có 3 cách xác nhận:**

#### CÁCH 1: Quét QR Batch (Nhanh nhất - Batch chuẩn)
```
Quét QR code của BATCH-001
→ ✅ Hệ thống tự động confirm Batch khớp
→ Nhập số lượng lấy: 50
→ Click "✓ HOÀN THÀNH"
```

#### CÁCH 2: Quét từng Barcode sản phẩm (Batch đã phân rã)
```
Quét barcode sản phẩm thứ 1 → Đã lấy: 1/50
Quét barcode sản phẩm thứ 2 → Đã lấy: 2/50
...
Quét barcode sản phẩm thứ 50 → Đã lấy: 50/50 ✅
→ Click "✓ HOÀN THÀNH"
```

#### CÁCH 3: Nhập thủ công (Khẩn cấp)
```
Nhập số lượng đã lấy: 50
→ Click "✓ HOÀN THÀNH"
```

---

### Bước 9: Xác nhận hoàn thành task

```
Button: "✓ HOÀN THÀNH"
```

✅ **Hệ thống thực hiện:**
- State task → **Đã hoàn thành**
- Ghi lại thời gian hoàn thành
- Cập nhật `stock.move.line`:
  * `qty_done` = 50
  * `location_id` = Shelf-A-01-03
  * `batch_id` = BATCH-001
- **Batch state** → In Picking (nếu chưa shipped)

**Thông báo:**
> ✅ Hoàn thành: Đã lấy 50 Product A

---

### Bước 10-12: Lặp lại cho các task còn lại

**Nhân viên tiếp tục:**
- PICK-000002 → Lấy 30 từ Shelf-A-02-05
- PICK-000003 → Lấy 20 từ Shelf-B-01-01

**Khi hoàn thành hết:**
- Tất cả Pick Tasks → State = **Đã hoàn thành**
- Hàng được đưa về **Khu vực chờ xuất** (Staging Area)

---

## PHASE 5: QUÉT BARCODE XUẤT KHO (XÁC NHẬN CUỐI)

### Bước 13: Mở chế độ Quét xuất kho

```
Header → Button: "Quét Lấy hàng" (màu xanh, icon scanner)
```

**Màn hình Scanner xuất hiện:**
```
╔═══════════════════════════════════════╗
║  📦 DELIVERY ORDER: WH/OUT/00001      ║
║  👤 Customer: ABC Company              ║
║  📊 WMS State: Picking Progress        ║
╠═══════════════════════════════════════╣
║  Pick Tasks:                           ║
║  ✅ PICK-000001 (Đã hoàn thành)        ║
║  ✅ PICK-000002 (Đã hoàn thành)        ║
║  ✅ PICK-000003 (Đã hoàn thành)        ║
╚═══════════════════════════════════════╝
```

---

### Bước 14: Quét xác nhận từng sản phẩm (tùy theo scan_detail_level)

**Nếu scan_detail_level = "Chỉ quét Lô":**
```
Quét QR BATCH-001 → ✅ Confirmed
Quét QR BATCH-005 → ✅ Confirmed
Quét QR BATCH-008 → ✅ Confirmed
→ XONG
```

**Nếu scan_detail_level = "Quét Chi tiết từng Kiện":**
```
Quét barcode sản phẩm 1 → ✅ 1/100
Quét barcode sản phẩm 2 → ✅ 2/100
...
Quét barcode sản phẩm 100 → ✅ 100/100 DONE
```

---

## PHASE 6: HOÀN TẤT XUẤT KHO

### Bước 15: Validate Delivery Order

```
Quay lại form Delivery Order → Button: "Validate" (màu xanh lá)
```

✅ **Hệ thống kiểm tra:**
- Tất cả Pick Tasks đã hoàn thành? → ✅ YES
- Số lượng quét đủ? → ✅ YES
- Cho phép validate

✅ **Odoo Core thực hiện:**
- Stock moves confirmed
- Inventory updated (trừ tồn kho từ Shelf-A-01-03, Shelf-A-02-05, Shelf-B-01-01)
- State → **Done**

✅ **WMS State:**
- `wms_state` → **WMS Complete**
- Các Batch → State = **Shipped** (đã xuất kho)

---

### Bước 16: Kiểm tra kết quả

**Xem tồn kho sau khi xuất:**
```
Tồn kho → Báo cáo → Inventory Report
Filter: Product = "Product A"
```

**Kết quả:**
| Location | Batch | Before | After | Change |
|----------|-------|--------|-------|--------|
| Shelf-A-01-03 | BATCH-001 | 50 | 0 | -50 ✅ |
| Shelf-A-02-05 | BATCH-005 | 50 | 20 | -30 ✅ |
| Shelf-B-01-01 | BATCH-008 | 40 | 20 | -20 ✅ |

**Xem Pick Tasks đã hoàn thành:**
```
Menu: Inventory → Quản lý Kho → Pick Tasks
Filter: Picking = WH/OUT/00001
```

**Timeline:**
| Task | Location | Qty | Nhân viên | Thời gian | Duration |
|------|----------|-----|-----------|-----------|----------|
| PICK-000001 | Shelf-A-01-03 | 50 | John | 10:00-10:03 | 3 phút |
| PICK-000002 | Shelf-A-02-05 | 30 | John | 10:03-10:05 | 2 phút |
| PICK-000003 | Shelf-B-01-01 | 20 | John | 10:05-10:07 | 2 phút |

---

## 🎓 CÁC TÍNH NĂNG NÂNG CAO

### A. FEFO (First Expire First Out)
```
Delivery Order → Pick Strategy: FEFO
→ Hệ thống ưu tiên lấy hàng có HSD sớm trước
```

**Ví dụ:**
| Vị trí | Batch | Số lượng | HSD | Thứ tự lấy |
|--------|-------|----------|-----|------------|
| Shelf-A | BATCH-001 | 50 | 31/12/2025 | 🥇 1 (sớm nhất) |
| Shelf-B | BATCH-005 | 30 | 15/01/2026 | 2 |
| Shelf-C | BATCH-008 | 20 | 28/02/2026 | 3 |

---

### B. Báo cáo vấn đề khi lấy hàng

**Nếu không tìm thấy hàng tại vị trí:**
```
Pick Task → Button: "Báo cáo vấn đề"
→ Chọn:
  - ☐ Không tìm thấy hàng
  - ☐ Hàng bị hư hỏng
  - ☐ Thiếu hàng (số lượng < kế hoạch)
  - ☐ Khác
→ Nhập chi tiết vấn đề
→ Save
```

**Hệ thống:**
- Thông báo quản lý kho
- Gợi ý vị trí thay thế (nếu có)
- Tạo phiếu điều chỉnh tồn kho (nếu cần)

---

### C. Lấy một phần (Partial Pick)

**Nếu chỉ lấy được 45/50:**
```
Pick Task → Đã lấy: 45 (thay vì 50)
→ Click "✓ HOÀN THÀNH"
→ Hệ thống cảnh báo: "Thiếu 5"
→ Quản lý quyết định:
  - Tạo task bổ sung (lấy thêm 5 từ vị trí khác)
  - Hoặc chấp nhận thiếu (tạo backorder)
```

---

### D. Gán nhiều nhân viên song song

**Khi có nhiều Pick Tasks:**
```
Gán task 1-5 → Nhân viên A (khu vực A)
Gán task 6-10 → Nhân viên B (khu vực B)
→ Cả 2 làm song song → Nhanh hơn
```

---

## ❌ XỬ LÝ LỖI THƯỜNG GẶP

### Lỗi 1: "No suitable locations found"
**Nguyên nhân:** Không có tồn kho hoặc tồn kho không đủ

**Giải pháp:**
```
1. Kiểm tra tồn kho: Inventory → Inventory Report
2. Nếu hàng ở vị trí khác → Điều chuyển về vị trí picking
3. Nếu thiếu hàng → Nhập kho bổ sung
```

---

### Lỗi 2: "Cannot validate picking: X pick tasks are not yet completed"
**Nguyên nhân:** Đúng theo design! Phải hoàn thành hết pick tasks

**Giải pháp:**
```
1. Xem tab Pick Tasks
2. Kiểm tra task nào State != "Đã hoàn thành"
3. Hoàn thành từng task
4. Sau đó mới Validate
```

---

### Lỗi 3: Quét barcode không khớp
**Nguyên nhân:** 
- Quét sai batch
- Batch không thuộc pick task này
- Barcode bị hỏng

**Giải pháp:**
```
1. Kiểm tra lại QR code Batch
2. Xác nhận Batch thuộc task này (xem trên màn hình)
3. Nếu barcode hỏng → Nhập thủ công (manager override)
```

---

### Lỗi 4: Pick suggestion không theo FIFO
**Nguyên nhân:** 
- Ngày nhập kho (in_date) trong stock.quant chưa đúng
- Hoặc chọn sai strategy

**Giải pháp:**
```
1. Kiểm tra Pick Strategy = FIFO
2. Xem lại ngày nhập kho của các Batch
3. Nếu sai → Cập nhật lại in_date
4. Tạo lại gợi ý
```

---

## 📊 BÁO CÁO & KPI

### A. Thống kê Pick Tasks
```
Menu: Inventory → Quản lý Kho → Pick Tasks
Group by: Nhân viên
```

**KPI:**
| Nhân viên | Tasks hoàn thành | Thời gian TB | Hiệu suất |
|-----------|------------------|--------------|-----------|
| John | 25 | 3.2 phút | ⭐⭐⭐⭐⭐ |
| Mary | 20 | 4.1 phút | ⭐⭐⭐⭐ |

---

### B. Báo cáo FIFO compliance
```
Inventory → Quản lý Kho → Gợi ý Lấy hàng
Filter: State = Picked
```

**Kiểm tra:**
- Có lấy đúng thứ tự FIFO không?
- Có batch nào bị bỏ qua?

---

## 🚀 TỔNG KẾT QUY TRÌNH XUẤT KHO

```
1. Tạo Delivery Order
2. Check Availability
3. ⚡ Chọn Pick Strategy (FIFO/FEFO)
4. ⚡ Tạo Gợi ý Lấy hàng (Hệ thống tự động)
5. ⚡ Tạo Pick Tasks
6. Gán nhân viên (tùy chọn)
7. Nhân viên bắt đầu lấy hàng (Mobile)
8. Đi đến vị trí → Lấy hàng
9. Quét QR Batch hoặc barcode sản phẩm
10. Xác nhận hoàn thành từng task
11. (Tùy chọn) Quét tổng thể trước xuất
12. Validate Delivery Order
13. ✅ DONE - Hàng đã xuất, tồn kho cập nhật
```

**Thời gian:** 5-7 phút/phiếu xuất (sau khi quen)

**Lợi ích:**
- ✅ FIFO/FEFO tự động → Tuân thủ quy định
- ✅ Biết chính xác lấy hàng từ đâu → Không tìm mò
- ✅ Tracking chính xác nhân viên/thời gian
- ✅ Giảm sai sót nhờ quét barcode
- ✅ Báo cáo đầy đủ, KPI rõ ràng
- ✅ Tích hợp chặt chẽ với core Odoo

---

## 📱 MOBILE WORKFLOW (TÓM TẮT)

**Nhân viên kho chỉ cần:**
1. Mở iPad/Tablet
2. Menu → Pick Tasks → Xem danh sách task của mình
3. Click task đầu tiên
4. Nhìn màn hình: Vị trí Shelf-A-01-03 (Tọa độ 1-1-3)
5. Đi đến đó
6. Click "▶ BẮT ĐẦU"
7. Quét QR Batch hoặc barcode sản phẩm
8. Click "✓ HOÀN THÀNH"
9. Lặp lại cho task tiếp theo
10. ✅ XONG

**Không cần:**
- ❌ Nhớ vị trí nào có hàng gì
- ❌ Tính toán FIFO thủ công
- ❌ Nhập số lượng thủ công (nếu quét đủ)
- ❌ Báo cáo riêng (hệ thống tự động)
