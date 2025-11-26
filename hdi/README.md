# HDI Modules - Odoo 18

## Overview

Thư mục này chứa tất cả custom modules cho hệ thống HDI, bao gồm:

### 1. Attendance Management (✅ Completed)
- **hdi_attendance** - Hệ thống chấm công và giải trình
- **hdi_hr** - HR extensions
- **hdi_hr_attendance_geolocation** - GPS tracking

### 2. Warehouse Management System (🚧 In Progress)

#### Phase 1: Core Foundation (✅ Completed)
- **wms_base** - Warehouse & Zone management
- **wms_product** - Product WMS settings  
- **wms_location** - Storage locations (Bins, Shelves, Racks)

#### Phase 2: Operations (⏳ Planned)
- **wms_inventory** - Stock tracking với lot/serial, FIFO/FEFO
- **wms_receipt** - Inbound operations (GRN, QC, Putaway)
- **wms_delivery** - Outbound operations (Picking, Packing, Shipping)
- **wms_transfer** - Internal transfers
- **wms_adjustment** - Inventory adjustments & cycle counting

#### Phase 3: Advanced (⏳ Planned)
- **wms_report** - Reporting & analytics
- **wms_dashboard** - Real-time dashboard
- **wms_integration** - External integrations (API, Barcode, EDI)

## WMS Architecture

### Database Structure
```
wms.warehouse (1) -----> (n) wms.zone (1) -----> (n) wms.location
                                                           |
                                                           v
                                                   wms.stock.quant
                                                           |
                                                           v
                                                   product.product
```

### Module Dependencies
```
wms_base (foundation)
  ├── wms_product (extends product.*)
  ├── wms_location (depends: wms_base, wms_product)
  └── wms_inventory (depends: wms_location)
        ├── wms_receipt (depends: wms_inventory)
        ├── wms_delivery (depends: wms_inventory)
        ├── wms_transfer (depends: wms_inventory)
        └── wms_adjustment (depends: wms_inventory)
              ├── wms_report (depends: all operation modules)
              ├── wms_dashboard (depends: all modules)
              └── wms_integration (depends: wms_inventory)
```

## Installation Order

### Attendance System
```bash
1. hdi_hr
2. hdi_hr_attendance_geolocation  
3. hdi_attendance
```

### WMS System
```bash
1. wms_base
2. wms_product
3. wms_location
4. wms_inventory (next)
5. wms_receipt
6. wms_delivery
7. wms_transfer
8. wms_adjustment
9. wms_report
10. wms_dashboard
11. wms_integration
```

## Current Status

### ✅ Completed Modules (5/14)
1. hdi_hr ✅
2. hdi_hr_attendance_geolocation ✅
3. hdi_attendance ✅
4. wms_base ✅
5. wms_product ✅
6. wms_location ✅

### 🚧 In Progress (1/14)
- wms_inventory (creating now)

### ⏳ Planned (8/14)
- wms_receipt
- wms_delivery
- wms_transfer
- wms_adjustment
- wms_report
- wms_dashboard
- wms_integration

## Quick Start

### WMS Setup
```bash
# 1. Install base modules
Apps -> Search "WMS Base" -> Install
Apps -> Search "WMS Product" -> Install
Apps -> Search "WMS Location" -> Install

# 2. Configure
WMS -> Configuration -> Settings
- Set default warehouse
- Enable barcode scanning
- Configure strategies (FIFO/FEFO)

# 3. Setup structure
WMS -> Configuration -> Warehouses
- Create/Edit warehouse
- Add zones
- Create locations (racks, shelves, bins)
```

## Documentation

- Attendance system: See `hdi_attendance/README.md`
- WMS system: See `WMS_README.md` (detailed docs)

## License
LGPL-3
