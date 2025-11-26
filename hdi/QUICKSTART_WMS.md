# HDI WMS Quick Start Guide

## ⚡ Cài đặt nhanh trong 5 phút

### Bước 1: Restart Odoo với modules mới
```bash
cd /path/to/odoo
./odoo-bin -c odoo.conf --addons-path=/workspaces/HDI/hdi -u all -d your_database
```

### Bước 2: Cài đặt modules trong Odoo UI

1. Đăng nhập Odoo với admin
2. Vào **Apps** → Click **Update Apps List**
3. Tìm và cài đặt theo thứ tự:

```
✅ HDI Stock Batch Flow
✅ HDI Stock Putaway Map  
✅ HDI Stock Receipt Extension
✅ HDI Stock Dispatch Extension
✅ HDI Stock Inventory Extension
✅ HDI Stock Odd Items
✅ HDI Barcode Workflow
✅ HDI API Map Connector
✅ HDI Logistics Partner
✅ HDI Fleet Assignment
✅ HDI Stock Reporting
```

### Bước 3: Cấu hình cơ bản

#### 3.1 Thiết lập vị trí kho 3D
```
Inventory → Configuration → Warehouse 3D Map
```
- Chọn location → Nhập Floor/Aisle/Rack/Shelf
- Set coordinates X/Y/Z
- Chọn ABC classification (A/B/C)

#### 3.2 Tạo Putaway Rules
```
Inventory → Configuration → Putaway Rules → Create
```
- Name: "High Turnover - Zone A"
- Strategy: ABC
- ABC Class: A - High Turnover

#### 3.3 Cấu hình QC cho Receipt
```
Inventory → Receipt Management → Stock Receipts
```
- Enable QC Required
- Assign QC Inspector

### Bước 4: Test workflow đầu tiên

#### Workflow: Nhập kho → QC → Putaway
```python
# 1. Tạo Receipt
receipt = env['stock.receipt'].create({
    'picking_id': picking.id,
    'container_no': 'CONT-001',
    'qc_required': True,
})

# 2. Start QC
receipt.action_start_qc()
receipt.action_qc_pass()

# 3. Get putaway suggestion
location = env['putaway.suggestion'].get_suggested_location(
    product_id=product.id,
    quantity=100,
)
```

## 🎯 Demo Data

### Tạo demo locations với tọa độ
```python
locations = env['stock.location']
for aisle in ['A', 'B', 'C']:
    for rack in range(1, 6):
        for level in range(1, 4):
            locations.create({
                'name': f'{aisle}-{rack:02d}-{level}',
                'location_id': warehouse.lot_stock_id.id,
                'aisle': aisle,
                'rack': f'{rack:02d}',
                'floor_level': level,
                'coordinate_x': ord(aisle) - ord('A') + 1,
                'coordinate_y': rack,
                'coordinate_z': level,
                'abc_classification': 'a' if aisle == 'A' else 'b',
            })
```

## 🚀 Production Checklist

- [ ] Đã cài đặt tất cả 11 modules
- [ ] Đã setup tọa độ cho ít nhất 10 locations
- [ ] Đã tạo ít nhất 2 putaway rules
- [ ] Đã test 1 workflow nhập kho hoàn chỉnh
- [ ] Đã train user về QC process
- [ ] Đã cấu hình sequence numbers
- [ ] Đã setup backup tự động

## 📊 KPI Dashboard

Sau khi cài đặt, bạn có thể tracking:

- **Receipt Performance**: Thời gian nhập kho trung bình
- **Putaway Efficiency**: % sử dụng AI suggestion
- **QC Pass Rate**: % hàng pass QC
- **Picking Speed**: Lines picked per hour
- **Inventory Accuracy**: % chênh lệch kiểm kê

## 🆘 Quick Fixes

**Q: Module không hiện trong Apps list?**
```bash
# Restart Odoo và update apps list
./odoo-bin -c odoo.conf --addons-path=/workspaces/HDI/hdi -u all
```

**Q: Import error khi cài module?**
```python
# Check dependencies installed
pip install -r requirements.txt
```

**Q: Menu không hiện?**
```
Settings → Technical → Menu Items → Reload
```

---
**⏱️ Setup time: 5 phút | 📦 Modules: 11 | 🎯 Ready to use!**
