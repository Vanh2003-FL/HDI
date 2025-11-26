# HDI Warehouse Management System (WMS) for Odoo 18

Hệ thống quản lý kho hoàn chỉnh cho Odoo 18 với 11 module tích hợp.

## 🏗️ Kiến Trúc Hệ Thống

```
ODOO 18 CORE (stock, barcode, sale, purchase, fleet)
                    │
    ┌───────────────┴───────────────┐
    │   HDI WMS MODULE LAYER (11)    │
    └───────────────┬───────────────┘
                    │
    ┌───────────────┴───────────────┐
    │  BATCH  │ PUTAWAY │ RECEIPT   │
    │ DISPATCH│INVENTORY│ ODD ITEMS │
    │ BARCODE │   API   │ LOGISTICS │
    │  FLEET  │ REPORTING│          │
    └───────────────────────────────┘
```

## 📦 Danh Sách 11 Module

### 1. **hdi_stock_batch_flow** - Quản lý Batch/Lô
- ✅ Tách lô lớn thành lô nhỏ (Batch Split)
- ✅ Gộp lô nhỏ thành lô lớn (Batch Merge)  
- ✅ QR Code tracking
- ✅ Models: `StockBatchSplit`, `StockBatchMerge`

### 2. **hdi_stock_putaway_map** - Bản đồ kho 3D
- ✅ Tọa độ X/Y/Z cho vị trí kho
- ✅ Cấu trúc: Tầng → Dãy → Kệ → Ô
- ✅ Engine gợi ý vị trí (ABC, FIFO, khoảng cách)
- ✅ Models: `stock.location (inherit)`, `PutawaySuggestion`

### 3. **hdi_stock_receipt_extension** - Nhập kho nâng cao
- ✅ Container, Bill of Lading, Tờ khai HQ
- ✅ QC nhập kho (Pass/Fail)
- ✅ Batch line chi tiết
- ✅ Models: `StockReceipt`, `ReceiptBatchLine`

### 4. **hdi_stock_dispatch_extension** - Xuất kho chuyên nghiệp
- ✅ Picklist cho nhân viên lấy hàng
- ✅ Staging location
- ✅ Tracking tiến độ picking
- ✅ Models: `PickingPicklist`, `PicklistLine`

### 5. **hdi_stock_inventory_extension** - Kiểm kê nâng cao
- ✅ Cycle count
- ✅ Kiểm kê theo vị trí/lô/sản phẩm
- ✅ Tracking chênh lệch
- ✅ Models: `stock.inventory (inherit)`, `InventoryResultLine`

### 6. **hdi_stock_odd_items** - Hàng lẻ/Thiếu lô
- ✅ Quản lý hàng damaged, sample, return
- ✅ Đánh dấu odd item trong quant
- ✅ Models: `OddItem`, `stock.quant (inherit)`

### 7. **hdi_barcode_workflow** - Quy trình Barcode
- ✅ Quy trình quét nhiều bước
- ✅ Scan location → product → lot → qty
- ✅ Models: `BarcodeWorkflow`, `BarcodeWorkflowStep`

### 8. **hdi_api_map_connector** - Kết nối 3D Map
- ✅ Sync dữ liệu với Digital Layout 3D
- ✅ Queue system cho sync
- ✅ Models: `MapSyncQueue`

### 9. **hdi_logistics_partner** - Đối tác 3PL
- ✅ Quản lý vận đơn 3PL
- ✅ API integration
- ✅ Tính phí vận chuyển
- ✅ Models: `LogisticsPartner`, `LogisticsRate`

### 10. **hdi_fleet_assignment** - Phân công xe
- ✅ Gán xe + tài xế cho đơn hàng
- ✅ Quản lý lộ trình
- ✅ Models: `PickingVehicleAssign`

### 11. **hdi_stock_reporting** - Báo cáo WMS
- ✅ Báo cáo nhập/xuất/tồn/kiểm kê
- ✅ Dashboard metrics
- ✅ Models: `StockReportEntry`

## 🚀 Cài Đặt

### Yêu cầu
- Odoo 18.0
- Python 3.10+
- PostgreSQL 13+

### Bước 1: Copy modules vào addons path
```bash
cp -r hdi/hdi_stock_* /path/to/odoo/addons/
```

### Bước 2: Update apps list
```bash
# Vào Odoo, Settings → Apps → Update Apps List
```

### Bước 3: Cài đặt modules theo thứ tự
1. `hdi_stock_batch_flow` (cơ sở)
2. `hdi_stock_putaway_map` (cơ sở)
3. Các module còn lại có thể cài đặt theo bất kỳ thứ tự

### Dependencies giữa các modules
```
hdi_stock_receipt_extension → depends → hdi_stock_batch_flow
hdi_stock_dispatch_extension → depends → hdi_stock_batch_flow
hdi_api_map_connector → depends → hdi_stock_putaway_map
hdi_stock_reporting → depends → hdi_stock_batch_flow, hdi_stock_putaway_map
```

## 📊 ERD - Quan hệ Model

```
┌─────────────────────────────────────────────────┐
│              ODOO CORE MODELS                   │
│  stock.picking, stock.move, stock.lot,          │
│  stock.location, stock.quant, res.partner       │
└────────────────┬────────────────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼──────────┐    ┌────────▼─────────┐
│ BATCH FLOW   │    │  PUTAWAY MAP     │
│ - Split      │    │ - Location(XYZ)  │
│ - Merge      │    │ - Suggestion     │
└───┬──────────┘    └────────┬─────────┘
    │                        │
    │  ┌─────────────────────┘
    │  │
┌───▼──▼───────┐  ┌──────────────┐  ┌──────────────┐
│  RECEIPT     │  │  DISPATCH    │  │  INVENTORY   │
│  Extension   │  │  Picklist    │  │  Extension   │
└──────────────┘  └──────────────┘  └──────────────┘
    │                  │                   │
    └──────────────────┴───────────────────┘
                       │
              ┌────────┴────────┐
              │                 │
    ┌─────────▼────┐   ┌───────▼────────┐
    │ BARCODE      │   │  ODD ITEMS     │
    │ WORKFLOW     │   │                │
    └──────────────┘   └────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────────┐  ┌──────▼──────┐  ┌──────────────┐
│ LOGISTICS  │  │   FLEET     │  │  REPORTING   │
│ 3PL        │  │  ASSIGNMENT │  │              │
└────────────┘  └─────────────┘  └──────────────┘
         │             │                 │
         └─────────────┴─────────────────┘
                       │
              ┌────────▼────────┐
              │   MAP CONNECTOR │
              │   (API to 3D)   │
              └─────────────────┘
```

## 🎯 Use Cases

### UC1: Nhập hàng Container
1. Tạo **Receipt** với thông tin container, tờ khai HQ
2. QC kiểm tra → Pass/Fail
3. Hệ thống **Putaway** gợi ý vị trí đặt hàng (ABC rule)
4. **Batch Split** nếu cần chia nhỏ lô
5. Sync sang **3D Map** để visualize

### UC2: Xuất hàng
1. Tạo **Picklist** từ Delivery Order
2. **Barcode Workflow**: Quét location → product → lot → qty
3. Đưa hàng ra **Staging location**
4. **Fleet Assignment**: Gán xe + tài xế
5. **3PL Integration**: Tạo vận đơn

### UC3: Kiểm kê
1. Chọn **Inventory Mode**: Full/Cycle/Location
2. Nhập số lượng thực tế
3. Hệ thống tạo **InventoryResultLine** với chênh lệch
4. Đánh dấu **Odd Items** nếu có hàng lẻ

## 🔧 Cấu hình

### Cấu hình Bản đồ kho 3D
```
Inventory → Configuration → Warehouse 3D Map
- Nhập tọa độ X/Y/Z cho từng vị trí
- Set ABC classification
- Cấu hình Accessibility Score
```

### Cấu hình Putaway Rules
```
Inventory → Configuration → Putaway Rules
- Strategy: FIFO / ABC / Nearest / Capacity
- Priority: 1-100
- Điều kiện áp dụng
```

### Cấu hình 3PL
```
Inventory → 3PL Logistics → Partners
- API Endpoint
- API Key
- Coverage Areas
- Rate Configuration
```

## 📱 Menu Structure

```
Inventory
├── Operations
│   ├── Receipts
│   ├── Deliveries
│   └── Returns
├── Batch Management ⭐ NEW
│   ├── Batch Split
│   └── Batch Merge
├── Putaway Strategy ⭐ NEW
│   ├── Warehouse 3D Map
│   └── Putaway Rules
├── Receipt Management ⭐ NEW
│   └── Stock Receipts (Extended)
├── Dispatch Management ⭐ NEW
│   └── Picklists
├── Odd Items ⭐ NEW
│   └── Odd Item Management
├── Barcode Workflows ⭐ NEW
│   └── Workflow List
├── 3PL Logistics ⭐ NEW
│   ├── Partners
│   └── Rates
├── Fleet Assignment ⭐ NEW
│   └── Vehicle Assignments
├── Configuration
│   └── 3D Map Sync ⭐ NEW
└── Reporting
    └── WMS Reports ⭐ NEW
        ├── Receipt Reports
        ├── Dispatch Reports
        ├── Inventory Reports
        └── Movement Reports
```

## 🧪 Testing

### Test Module 1: Batch Flow
```python
# Test split batch
batch_split = env['stock.batch.split'].create({
    'source_lot_id': lot_id,
    'source_quantity': 100,
})
batch_split.split_line_ids.create({
    'split_id': batch_split.id,
    'new_lot_name': 'LOT001-A',
    'quantity': 50,
})
batch_split.action_confirm()
batch_split.action_done()
```

### Test Module 2: Putaway Suggestion
```python
# Get suggested location
suggestion = env['putaway.suggestion'].get_suggested_location(
    product_id=product.id,
    quantity=10,
    warehouse_id=warehouse.id
)
```

## 📖 API Documentation

### REST API Endpoints (Module 8: Map Connector)

#### Sync Location to 3D Map
```http
POST /api/wms/map/sync/location
Content-Type: application/json

{
    "location_id": 123,
    "x": 10.5,
    "y": 20.3,
    "z": 5.0
}
```

#### Get Inventory Status
```http
GET /api/wms/inventory/status?warehouse_id=1
```

## 🐛 Troubleshooting

### Lỗi: "Putaway suggestion không hoạt động"
- Kiểm tra coordinate X/Y/Z đã được set cho locations
- Verify putaway rules đã được activate

### Lỗi: "QC status không update"
- Check qc_required = True trong Receipt
- Verify user có quyền stock.group_stock_manager

## 📝 Changelog

### Version 18.0.1.0.0 (2025-11-26)
- ✅ Hoàn thành 11 modules WMS
- ✅ Tích hợp Odoo 18
- ✅ Full CRUD operations
- ✅ Multi-company support

## 👥 Credits

**Developer**: HDI Team  
**Version**: 18.0.1.0.0  
**License**: LGPL-3  
**Odoo Version**: 18.0

## 📧 Support

- Documentation: https://docs.hdi.com/wms
- Issues: https://github.com/hdi/wms/issues
- Email: support@hdi.com

---

**🎉 Hệ thống WMS hoàn chỉnh cho Odoo 18 - Sẵn sàng sử dụng!**
