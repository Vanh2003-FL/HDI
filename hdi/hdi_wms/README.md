# HDI WMS Module

Advanced Warehouse Management System for Odoo 18

## Architecture

✅ **Kế thừa đúng cách (Inherit Core)**:
- `stock.picking` - Thêm batch management, WMS workflow, **PICK TASKS & FIFO SUGGESTION**
- `stock.move` - Thêm batch_id linking
- `stock.location` - Thêm coordinates X-Y-Z, capacity, attributes
- `stock.quant` - Sync batch với inventory

❌ **Tạo mới (Custom Models)**:
- `hdi.batch` - Batch/LPN/Pallet management
- `hdi.putaway.suggestion` - Putaway location engine (INBOUND)
- `hdi.pick.suggestion` - Pick location engine with FIFO/FEFO (OUTBOUND) ⭐ NEW
- `hdi.pick.task` - Work orders for warehouse picking (OUTBOUND) ⭐ NEW
- `hdi.loose.line` - Loose items tracking

## Key Features

### 1. **Batch/LPN Management** (INBOUND)
   - Pallet, LPN, Container tracking
   - Link với stock.quant (core inventory)
   - Barcode scanning support

### 2. **Putaway Suggestion Engine** (INBOUND)
   - ABC classification
   - Capacity checking
   - Smart location recommendation

### 3. **Pick Suggestion Engine** (OUTBOUND) ⭐ NEW
   - **FIFO (First In First Out)** - Hàng nhập trước lấy trước
   - **FEFO (First Expire First Out)** - Hàng hết hạn sớm lấy trước
   - Automatic location and batch suggestion
   - Split quantity across multiple locations
   - Priority scoring based on:
     * Inbound date (FIFO)
     * Expiration date (FEFO)
     * Location priority
     * Batch availability

### 4. **Pick Task Management** (OUTBOUND) ⭐ NEW
   - Work order system for warehouse picking
   - Task assignment to warehouse staff
   - Mobile-friendly interface
   - Barcode scanning integration
   - Track picking time and performance
   - Issue reporting (not found, damaged, short pick)
   - Real-time progress tracking

### 5. **WMS Workflow States**
   - **INBOUND**: Receiving → Putaway → Storage
   - **OUTBOUND**: Picking Ready → Picking Progress → WMS Complete ⭐ NEW
   - Parallel với Odoo core states

### 6. **Location Extensions**
   - X-Y-Z coordinates
   - Capacity management
   - Temperature zones
   - Moving class

## Installation

1. Copy module to addons folder
2. Update apps list
3. Install "HDI WMS"
4. Configure locations with WMS attributes

## Workflow

### INBOUND (Nhập kho)
```
1. Create Receipt
2. Check Availability
3. ☑ Enable Batch Management
4. Create Batches (with QR codes)
5. System suggests putaway locations
6. Confirm storage
7. Validate receipt
→ ✅ Inventory updated, batch stored
```

### OUTBOUND (Xuất kho) ⭐ NEW
```
1. Create Delivery Order
2. Check Availability
3. Select Pick Strategy (FIFO/FEFO)
4. Generate Pick Suggestions
   → System analyzes stock.quant
   → Sorts by inbound date or expiration
   → Splits across locations if needed
5. Create Pick Tasks from suggestions
6. Assign to warehouse staff
7. Staff picks items using mobile scanner
   → Scan batch QR or product barcodes
   → Confirm quantities
8. Complete all pick tasks
9. Validate delivery
→ ✅ Inventory updated, goods shipped
```

## Nguyên tắc thiết kế

✅ **ĐÚNG**: Màn hình core → inherit và extend
✅ **ĐÚNG**: Logic tồn kho → 100% từ stock.quant
✅ **ĐÚNG**: Model mới → link chặt với core models
✅ **ĐÚNG**: FIFO/FEFO → Query từ stock.quant.in_date, lot.expiration_date
❌ **SAI**: Tạo bảng tồn kho riêng
❌ **SAI**: Fork logic core ra ngoài

## Documentation

- **Inbound workflow**: See `HUONG_DAN_SU_DUNG.md`
- **Outbound workflow**: See `HUONG_DAN_XUAT_KHO.md` ⭐ NEW

## Technical Details

### Models Structure

#### hdi.pick.suggestion (NEW)
```python
Fields:
- picking_id: Link to delivery order
- product_id: Product to pick
- location_id: Source location
- batch_id: Specific batch to pick
- quantity_to_pick: Quantity from this location
- sequence: Pick order (1 = first)
- priority: Calculated score
- inbound_date: When stock arrived (FIFO)
- expiration_date: Lot expiration (FEFO)
- pick_reason: Explanation of why this location

Methods:
- generate_pick_suggestions(picking, strategy='fifo')
  → Queries stock.quant
  → Sorts by strategy
  → Allocates quantities
  → Returns ordered suggestions
```

#### hdi.pick.task (NEW)
```python
Fields:
- name: Task number (PICK-000001)
- picking_id: Link to delivery order
- location_id: Where to pick from
- product_id: What to pick
- batch_id: Specific batch
- planned_qty: Target quantity
- picked_qty: Actual quantity picked
- state: todo/in_progress/done/cancel
- assigned_user_id: Staff member
- start_time, end_time: Performance tracking

Methods:
- action_start_picking(): Begin task
- action_confirm_picked(): Complete task & update move lines
- on_barcode_scanned(barcode): Handle scanning
```

### Key Algorithms

#### FIFO Pick Suggestion
```python
# In hdi.pick.suggestion._find_available_quants()
quants = env['stock.quant'].search([
    ('product_id', '=', product.id),
    ('location_id', 'child_of', warehouse_location.id),
    ('quantity', '>', 0),
], order='in_date ASC, location_id.location_priority ASC')

# Allocate quantities in FIFO order
for quant in quants:
    if qty_remaining > 0:
        qty_to_pick = min(quant.available_qty, qty_remaining)
        create_suggestion(quant.location, batch, qty_to_pick)
        qty_remaining -= qty_to_pick
```

#### FEFO Pick Suggestion
```python
# Similar but order by expiration date
quants = env['stock.quant'].search([...],
    order='lot_id.expiration_date ASC NULLS LAST, in_date ASC'
)
```

### Integration Points

1. **stock.picking**: Extended with pick_task_ids, pick_suggestion_ids, pick_strategy
2. **stock.move.line**: Updated by pick tasks via `_update_picking_move_lines()`
3. **stock.quant**: Source of truth for FIFO/FEFO calculations
4. **hdi.batch**: Tracked through pick process, state updated to 'shipped'

## Security

Access rights defined in `security/ir.model.access.csv`:
- `group_wms_user`: Read/Write pick tasks and suggestions
- `group_wms_manager`: Full access including delete
- `group_wms_scanner`: Mobile scanning access

## Future Enhancements

- [ ] Wave picking (batch multiple orders)
- [ ] Route optimization (shortest path)
- [ ] Packing station integration
- [ ] Carrier integration & label printing
- [ ] Advanced analytics & KPI dashboard
- [ ] Multi-warehouse transfer optimization
