# WMS WORKFLOW DEMO - Quy trình hoàn chỉnh

## 1. NHẬP HÀNG (RECEIVING) - Workflow Hoàn chỉnh

### Bước 1: Tạo Phiếu Nhập Kho (Purchase Receipt)
```
Inventory → Operations → Receipts → Create
```

**Thông tin nhập:**
- Vendor: Nhà cung cấp
- Products: 
  * [ProductA] Laptop Dell - 10 cái
  * [ProductB] Mouse Logitech - 50 cái
- Scheduled Date: Ngày dự kiến nhận
- Location: WH/Input (receiving area)

✅ **Odoo tự động tạo**: Stock Picking với state = `draft`

---

### Bước 2: Xác nhận & Check Availability
```
Button: Check Availability (hoặc tự động nếu có PO)
```

✅ State chuyển: `draft` → `confirmed` → `assigned`

---

### Bước 3: **BẬT WMS** cho Receipt này
```
Tab: Other Info
☑ Use Batch Management = True
```

✅ WMS State: `none` → `batch_creation`  
✅ Xuất hiện button: **"Tạo Lô hàng"** (Create Batch)

---

### Bước 4: Tạo Batch/LPN khi hàng đến
```
Button: Tạo Lô hàng → Wizard mở ra
```

**Nhập thông tin thực tế:**

**Batch 1 - Pallet Laptop:**
- Loại lô: `Pallet`
- Sản phẩm: `Laptop Dell`
- Số lượng: `10`
- Vị trí hiện tại: `WH/Input`
- ☑ Tự động tạo mã vạch = True
- Trọng lượng: `150 kg`
- Thể tích: `2.5 m³`
- **LOT/Serial**: `LOT2025001` (tracking)
- **Expiration Date**: `2025-12-31` (FEFO)
- **Manufacturing Date**: `2025-01-01`

→ Click **Tạo**

✅ **Kết quả:**
- Batch `BATCH-000001` được tạo
- State = `in_receiving`
- Barcode = tự động (BATCH-000001)
- Liên kết với `stock.picking`
- **stock.move** tự động link `batch_id`

**Batch 2 - Container Chuột:**
- Loại lô: `Container`
- Sản phẩm: `Mouse Logitech`  
- Số lượng: `50`
- Vị trí: `WH/Input`
- Trọng lượng: `25 kg`
- Thể tích: `0.5 m³`
- LOT: `LOT2025002`

→ Tạo `BATCH-000002`

---

### Bước 5: Quét Barcode Xác nhận (Optional)
```
Button: Quét Mã vạch
Chế độ: Scan Batch
```

- Quét mã `BATCH-000001` → ✅ Confirmed
- Quét mã `BATCH-000002` → ✅ Confirmed

---

### Bước 6: Gợi ý Vị trí Đặt hàng (Putaway Suggestion)

**Mở Batch BATCH-000001:**
```
Button: Gợi ý Vị trí (Suggest Location)
```

✅ **WMS Engine tính toán:**

Tiêu chí đánh giá:
1. ✅ Capacity đủ không? (Volume/Weight)
2. ✅ Có sản phẩm giống đã ở đó? (Consolidation)
3. ✅ Moving class match? (A-A, B-B, C-C)
4. ✅ Khoảng cách từ receiving? (Tối ưu hóa đường đi)
5. ✅ FEFO rule? (Hạn sử dụng)

**Kết quả gợi ý (Top 5):**

| Vị trí | Tọa độ | Score | Lý do |
|--------|--------|-------|-------|
| WH/Stock/Shelf-A-01-03 | A-01-03 | 95 | Same product, A-class, 80% capacity left |
| WH/Stock/Shelf-A-02-01 | A-02-01 | 85 | Empty, A-class, close to input |
| WH/Stock/Shelf-B-01-02 | B-01-02 | 70 | Available capacity, farther |

→ **Chọn**: `Shelf-A-01-03` → Click **Select**

✅ **Cập nhật:**
- `batch.location_dest_id` = Shelf-A-01-03
- `batch.state` → `in_putaway`
- Suggestion state → `selected`

---

### Bước 7: Di chuyển vật lý & Xác nhận Lưu kho

**Nhân viên kho:**
1. Dùng xe nâng di chuyển Pallet BATCH-000001
2. Đặt vào vị trí `Shelf-A-01-03`
3. Quét mã vạch xác nhận

**Trong hệ thống:**
```
Batch BATCH-000001 → Button: Xác nhận Lưu kho (Confirm Storage)
```

✅ **Odoo thực hiện:**
```python
# Core operation - CẬP NHẬT STOCK.QUANT
for quant in batch.quant_ids:
    quant.location_id = batch.location_dest_id  # Shelf-A-01-03
```

✅ **Kết quả:**
- `batch.state` → `stored`
- `batch.location_id` → `Shelf-A-01-03`
- **stock.quant** location cập nhật → Tồn kho CHÍNH XÁC
- Inventory report hiển thị: 10 Laptop ở Shelf-A-01-03

---

### Bước 8: Lặp lại Putaway cho BATCH-000002

Tương tự cho Container chuột → Đặt vào `Shelf-B-02-05`

---

### Bước 9: Validate Receipt (Hoàn tất Nhập kho)

**Kiểm tra:**
- ✅ BATCH-000001: State = `stored`
- ✅ BATCH-000002: State = `stored`

```
Button: Validate (button_validate)
```

✅ **WMS Pre-validation:**
```python
if picking.use_batch_management:
    if pending_batches:  # Có batch chưa stored
        raise UserError("Please complete putaway first")
```

✅ **Core Odoo Logic (super()):**
- Stock moves xác nhận
- Quants cập nhật
- Picking state → `done`

✅ **WMS Post-update:**
- `picking.wms_state` → `wms_done`
- `picking.actual_end_time` = now()

---

## 2. XUẤT HÀNG (PICKING) - Workflow Hoàn chỉnh

### Bước 1: Tạo Đơn Giao hàng (Delivery Order)
```
Inventory → Operations → Delivery Orders → Create
```

- Customer: Khách hàng X
- Products:
  * Laptop Dell - 3 cái
  * Mouse Logitech - 20 cái

✅ State: `draft` → `confirmed` → `assigned`

---

### Bước 2: Bật WMS cho Delivery
```
☑ Use Batch Management = True
```

✅ `wms_state` = `picking_ready`

---

### Bước 3: Tạo Picking Wave (Optional - để lấy nhiều đơn cùng lúc)

Hoặc lấy từng đơn:

```
Button: Tạo Lô hàng
```

**Picking Batch (cho Picking):**
- Loại: `LPN` (License Plate Number - thùng chứa đơn)
- Sản phẩm: Mixed (để trống)
- Priority: `Urgent`

→ `BATCH-PICK-001` created
→ State: `in_picking`

---

### Bước 4: Quét Barcode Lấy hàng

**Nhân viên kho đến Shelf-A-01-03:**
```
Scan: BATCH-000001 (pallet Laptop)
→ Confirm: Lấy 3 cái
```

**Hệ thống:**
- Tạo `stock.move` từ Shelf-A-01-03 → WH/Output
- Link `batch_id` = BATCH-PICK-001
- Reserve quantity

**Đến Shelf-B-02-05:**
```
Scan: BATCH-000002 (container chuột)
→ Lấy 20 cái
```

---

### Bước 5: Đóng gói & Xác nhận Giao hàng

```
Button: Validate
```

✅ **Core Odoo:**
- Stock moves → done
- Quants giảm
- Product out → Customer location

✅ **WMS:**
- `batch.state` → `shipped`
- `picking.wms_state` → `wms_done`

---

## 3. CHUYỂN KHO NỘI BỘ (Internal Transfer)

### Use Case: Di chuyển Batch giữa các location

```
Inventory → Operations → Internal Transfers → Create
```

- From: `Shelf-A-01-03`
- To: `Shelf-C-05-10` (vị trí tốt hơn)
- Product: Laptop Dell
- Quantity: 5

✅ **Tích hợp WMS:**
- Batch `BATCH-000001` tự động update `location_id`
- stock.quant location thay đổi
- Traceability hoàn chỉnh

---

## 4. BÁO CÁO & TRUY VẾT

### Xem Tồn kho theo Batch
```
Inventory → Quản lý Kho → Lô hàng / Pallet
```

**Filter:**
- State = `stored`
- Location = `Shelf-A-*`

### Xem Location Capacity
```
Inventory → Configuration → Locations
```

**Metric hiển thị:**
- Current Weight: 150/500 kg (30%)
- Current Volume: 2.5/10 m³ (25%)
- Moving Class: A (Fast Moving)

### Truy vết Batch History
```
Batch BATCH-000001 → Tab: Chuyển kho (Moves)
```

**Timeline:**
1. 2025-01-15 09:00 - Created at WH/Input
2. 2025-01-15 09:15 - Putaway to Shelf-A-01-03
3. 2025-01-20 14:30 - Picked 3 units for Delivery/00005
4. 2025-01-25 10:00 - Remaining 7 units

---

## 5. CÁC TRƯỜNG HỢP ĐẶC BIỆT

### 5.1. Hàng Hỏng (Damaged Goods)
```
Batch → Reason Code = "Damaged Goods"
→ Putaway suggestion tự động gợi ý: WH/Quarantine/Damage
```

### 5.2. Hàng Trả lại (Return)
```
Receipt → Origin = "Return from Customer X"
Batch → Reason Code = "Customer Return"
→ Kiểm tra chất lượng trước khi putaway
```

### 5.3. Kiểm kê (Cycle Count)
```
Inventory → Operations → Inventory Adjustments
→ Quét Batch → So sánh system vs physical
→ Tạo adjustment nếu sai lệch
```

### 5.4. FEFO Logic (First Expired First Out)
```
Picking → Product = Laptop
→ WMS tự động chọn batch có expiration_date gần nhất
→ BATCH-000003 (expires 2025-06-30) picked trước BATCH-000001 (expires 2025-12-31)
```

---

## KẾT LUẬN

✅ **Core Odoo không thay đổi**:
- stock.picking workflow
- stock.move logic
- stock.quant inventory

✅ **WMS Extension thêm**:
- Batch tracking layer
- Putaway optimization
- Barcode scanning
- Location management
- Traceability nâng cao

✅ **Tích hợp hoàn hảo**: WMS state song song với Odoo state, không conflict
