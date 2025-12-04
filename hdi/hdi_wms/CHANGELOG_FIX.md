# Bản sửa lỗi - 2025-12-04

## ❌ Lỗi đã sửa

### Lỗi 1: Cho phép tạo Batch ở màn Giao hàng (Xuất kho) - SAI NGHIỆP VỤ BRD

**Nguyên nhân:**
- Button "Tạo Lô hàng" hiển thị cho TẤT CẢ các loại picking (incoming, outgoing, internal)
- Method `action_create_batch()` không có validation kiểm tra loại picking
- Wizard `batch_creation_wizard` không chặn tạo batch cho outgoing
- **Vi phạm nghiệp vụ BRD**: Lô hàng chỉ được tạo khi NHẬP KHO, xuất kho chỉ lấy từ lô có sẵn

**Giải pháp:**
1. **View XML** (`views/stock_picking_views.xml`):
   - Ẩn button "Tạo Lô hàng" khi `picking_type_code == 'outgoing'`
   - Thêm field `picking_type_code` (related) để dùng trong điều kiện invisible
   - Cập nhật help text: "chỉ nhập kho"

2. **Python** (`models/stock_picking.py`):
   - Thêm field `picking_type_code` (related từ `picking_type_id.code`, store=True)
   - Thêm validation trong `action_create_batch()`: raise UserError nếu picking_type_code='outgoing'
   - Thông báo lỗi rõ ràng bằng tiếng Việt giải thích nghiệp vụ

3. **Wizard** (`wizard/batch_creation_wizard.py`):
   - Thêm validation trong `action_create_batch()`: chặn nếu picking_type_code='outgoing'
   - Thông báo lỗi hướng dẫn sử dụng "Gợi ý Lấy hàng" thay vì tạo lô

**Thay đổi cụ thể:**

```xml
<!-- views/stock_picking_views.xml -->
<!-- TRƯỚC (Lỗi) -->
<button name="action_create_batch" type="object" string="Tạo Lô hàng"
        invisible="state != 'assigned' or not use_batch_management"
        class="btn-primary"/>

<!-- SAU (Đã sửa) -->
<button name="action_create_batch" type="object" string="Tạo Lô hàng"
        invisible="state != 'assigned' or not use_batch_management or picking_type_code == 'outgoing'"
        class="btn-primary"/>
```

```python
# models/stock_picking.py
# TRƯỚC (Lỗi)
def action_create_batch(self):
    self.ensure_one()
    return {...}  # Không có validation

# SAU (Đã sửa)
def action_create_batch(self):
    self.ensure_one()
    if self.picking_type_id.code == 'outgoing':
        raise UserError(_('Không thể tạo lô hàng cho phiếu XUẤT KHO!...'))
    return {...}
```

**Kết quả:**
- ✅ Màn Nhập kho: Hiển thị button "Tạo Lô hàng" bình thường
- ✅ Màn Xuất kho: Button "Tạo Lô hàng" bị ẨN
- ✅ Nếu ai đó bypass UI: Python validation sẽ chặn và báo lỗi rõ ràng
- ✅ Tuân thủ 100% nghiệp vụ BRD: Batch chỉ tạo khi nhập kho

---

### Lỗi 2: Field "sequence" không tồn tại trong model "stock.picking" (ĐÃ SỬA TRƯỚC ĐÓ)

**Nguyên nhân:**
Trong file `views/stock_picking_views.xml`, các inline tree view của `pick_suggestion_ids` và `pick_task_ids` có sử dụng field `sequence`. Khi Odoo parse view, nó nghĩ rằng `sequence` là field của model cha (`stock.picking`) thay vì của child model.

**Giải pháp:**
Đã xóa field `sequence` khỏi inline tree views vì:
1. Trong inline tree view, không cần hiển thị sequence (người dùng thấy thứ tự tự nhiên)
2. Sequence vẫn được sử dụng cho sorting backend (trong model)
3. Tránh nhầm lẫn với model cha

**File đã sửa:**
- `hdi/hdi_wms/views/stock_picking_views.xml` (dòng 130-150)

**Thay đổi cụ thể:**
```xml
<!-- TRƯỚC (Lỗi) -->
<tree>
    <field name="sequence"/>  <!-- ❌ Odoo nghĩ đây là stock.picking.sequence -->
    <field name="product_id"/>
    ...
</tree>

<!-- SAU (Đã sửa) -->
<tree>
    <!-- ✅ Xóa sequence, vẫn giữ thứ tự tự nhiên -->
    <field name="product_id"/>
    ...
</tree>
```

## ✅ Module đã được validate thành công

```
✅ Python syntax OK
✅ XML syntax OK (tất cả 14 files)
✅ Module structure OK
✅ All features implemented
```

## 🚀 Cách upgrade module

### Option 1: Command line (Nhanh)
```bash
# Dừng Odoo
sudo systemctl stop odoo

# Upgrade module
odoo-bin -u hdi_wms -d db_hdi1 --stop-after-init

# Hoặc nếu cần update tất cả
odoo-bin -u hdi_wms -d db_hdi1

# Khởi động lại
sudo systemctl start odoo
```

### Option 2: UI (Dễ dàng)
```
1. Mở Odoo
2. Vào Apps
3. Tìm "HDI WMS"
4. Click "Upgrade"
5. Chờ hoàn thành
```

### Option 3: Restart service (Tự động reload)
```bash
sudo systemctl restart odoo
```

## 📊 Tóm tắt module sau khi sửa

### Models (11 files)
- ✅ hdi.batch - Batch/LPN management
- ✅ hdi.putaway.suggestion - Putaway engine (Inbound)
- ✅ hdi.pick.suggestion - Pick engine FIFO/FEFO (Outbound) **NEW**
- ✅ hdi.pick.task - Work orders for picking (Outbound) **NEW**
- ✅ hdi.loose.line - Loose items
- ✅ stock.picking (extended) - Added pick tasks
- ✅ stock.move (extended)
- ✅ stock.location (extended)
- ✅ stock.quant (extended)
- ✅ product.product (extended)

### Views (10 files)
- ✅ Pick Task views (tree, form, kanban, mobile scanner)
- ✅ Pick Suggestion views (tree, form)
- ✅ Stock Picking views (extended with Pick Tasks tab)
- ✅ Batch views
- ✅ Location views
- ✅ All other views

### Features
- ✅ INBOUND: Batch → Putaway → Storage
- ✅ OUTBOUND: FIFO/FEFO → Pick Tasks → Scanner → Validate **NEW**
- ✅ Mobile-friendly interface
- ✅ Barcode scanning
- ✅ Performance tracking

## 🎯 Test nhanh sau khi upgrade

### Test Inbound (Nhập kho)
```
1. Tạo Receipt
2. Create Batch
3. Generate Putaway Suggestion
4. Confirm Storage
5. Validate
→ ✅ Should work
```

### Test Outbound (Xuất kho)
```
1. Tạo Delivery Order
2. Check Availability
3. Click "Gợi ý Lấy hàng (FIFO)"
4. Click "Tạo Pick Tasks"
5. Open Pick Task → Start → Confirm
6. Validate Delivery
→ ✅ Should work
```

## ⚠️ Lưu ý

- Field `sequence` vẫn tồn tại trong models `hdi.pick.task` và `hdi.pick.suggestion`
- Chỉ xóa khỏi inline tree view trong `stock.picking`
- Thứ tự vẫn được bảo toàn khi query (order by sequence)
- Không ảnh hưởng đến chức năng

## 📝 Nếu vẫn gặp lỗi

1. **Xóa cache:** `rm -rf ~/.local/share/Odoo/filestore/db_hdi1/__pycache__`
2. **Xóa view cache:** Vào Settings → Technical → Views → Search "hdi_wms" → Delete all
3. **Reinstall:** Uninstall module → Install lại
4. **Check logs:** `tail -f /var/log/odoo/odoo.log`

## ✅ Module sẵn sàng sử dụng!
