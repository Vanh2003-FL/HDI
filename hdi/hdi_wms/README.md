# HDI WMS Module

Advanced Warehouse Management System for Odoo 18

## Architecture

✅ **Kế thừa đúng cách (Inherit Core)**:
- `stock.picking` - Thêm batch management, WMS workflow
- `stock.move` - Thêm batch_id linking
- `stock.location` - Thêm coordinates X-Y-Z, capacity, attributes
- `stock.quant` - Sync batch với inventory

❌ **Tạo mới (Custom Models)**:
- `hdi.batch` - Batch/LPN/Pallet management
- `hdi.putaway.suggestion` - Putaway location engine
- `hdi.loose.line` - Loose items tracking

## Key Features

1. **Batch/LPN Management**
   - Pallet, LPN, Container tracking
   - Link với stock.quant (core inventory)
   - Barcode scanning support

2. **Putaway Suggestion Engine**
   - ABC classification
   - Capacity checking
   - Smart location recommendation

3. **WMS Workflow States**
   - Parallel với Odoo core states
   - Receiving → Putaway → Storage → Picking

4. **Location Extensions**
   - X-Y-Z coordinates
   - Capacity management
   - Temperature zones
   - Moving class

## Installation

1. Copy module to addons folder
2. Update apps list
3. Install "HDI WMS"
4. Configure locations with WMS attributes

## Nguyên tắc thiết kế

✅ **ĐÚNG**: Màn hình core → inherit và extend
✅ **ĐÚNG**: Logic tồn kho → 100% từ stock.quant
✅ **ĐÚNG**: Model mới → link chặt với core models
❌ **SAI**: Tạo bảng tồn kho riêng
❌ **SAI**: Fork logic core ra ngoài
