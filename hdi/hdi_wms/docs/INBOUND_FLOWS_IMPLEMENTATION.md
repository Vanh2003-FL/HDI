# Inbound Flows Implementation - NK_NV_01 to NK_NV_04

## Overview
This document describes the implementation of features to support the 4 inbound flows (NK_NV_01, NK_NV_02, NK_NV_03, NK_NV_04) in the HDI WMS module.

## Changes Summary

### 1. Import Document Traceability (NK_NV_03)

**Purpose**: Capture import document references (invoice, packing list, bill of lading) when creating batches from imported goods.

**Model Changes - `hdi.batch`**:
- Added field: `import_invoice_number` (Char) - Import invoice reference
- Added field: `import_packing_list` (Char) - Packing list reference  
- Added field: `import_bill_of_lading` (Char) - Bill of lading reference

**Wizard Changes - `hdi.batch.creation.wizard`**:
- Added same 3 fields to capture import docs during batch creation
- Modified `action_create_batch()` to copy these values to the created batch

**View Changes**:
- `batch_creation_wizard_views.xml`: Added "Chứng từ Nhập khẩu" group with 3 import doc fields
- `hdi_batch_views.xml`: Added notebook page "Chứng từ Nhập khẩu" to display import docs

### 2. Scan Detail Level Control (NK_NV_01 vs NK_NV_02)

**Purpose**: Control granularity of scanning - batch-only vs detailed product/item scanning.

**Model Changes - `stock.picking`**:
- Added field: `scan_detail_level` (Selection)
  - `batch_only`: Scan batch barcode only (NK_NV_01)
  - `batch_plus_products`: Scan batch and products (NK_NV_02)
  - `full_item`: Scan each item with serial/lot (NK_NV_02 detailed)

**View Changes - `stock_picking_views.xml`**:
- Added `scan_detail_level` field to picking form after `partner_id` group
- Field is visible only when `use_batch_management` is enabled

**Usage**:
- NK_NV_01 flow: Set `scan_detail_level = 'batch_only'`
- NK_NV_02 flow: Set `scan_detail_level = 'batch_plus_products'` or `'full_item'`

### 3. Handover Signature & Tracking (All Flows)

**Purpose**: Record production-to-warehouse handover with signature and timestamp.

**Model Changes - `stock.picking`**:
- Added field: `production_handover_signed_by` (Many2one res.users) - Who signed
- Added field: `production_handover_signature` (Binary) - Signature image/document
- Added field: `production_handover_date` (Datetime) - When handover occurred
- Added method: `action_confirm_handover()` - Records current user + timestamp

**View Changes - `stock_picking_views.xml`**:
- Added button "Xác nhận bàn giao" in header (before validate button)
  - Visible when picking is assigned/confirmed and not yet signed
- Added readonly fields to display handover info after signing

**Usage**:
1. Warehouse operator opens picking
2. Clicks "Xác nhận bàn giao" button
3. System records current user and timestamp
4. Button disappears, handover info displayed

## Flow Mapping

### NK_NV_01: Simple Batch Inbound (no detailed scanning)
1. Create receipt picking `WH/IN/xxxxx`
2. Enable `use_batch_management = True`
3. Set `scan_detail_level = 'batch_only'`
4. Click "Xác nhận bàn giao" to record handover
5. Click "Tạo Lô hàng" - fill import docs if applicable
6. Scan batch barcode only
7. Suggest putaway location
8. Confirm storage

### NK_NV_02: Detailed Item Scan Inbound
1. Same as NK_NV_01 steps 1-4
2. Set `scan_detail_level = 'batch_plus_products'` or `'full_item'`
3. Create batch - system requires scanning each product/item
4. Continue with putaway and storage

### NK_NV_03: Import Document Reference
1. Create receipt picking
2. Enable batch management
3. Click "Xác nhận bàn giao"
4. Click "Tạo Lô hàng" - **fill import document fields**:
   - Import Invoice Number
   - Import Packing List
   - Bill of Lading
5. Scan batch (level depends on requirement)
6. Complete putaway
7. View batch form - "Chứng từ Nhập khẩu" tab shows import docs

### NK_NV_04: Internal Transfer / Returns
- Uses same infrastructure
- Handover tracking works for internal department transfers
- Batch management optional (set `use_batch_management` as needed)

## Technical Notes

### Data Flow
1. **Wizard capture**: Import docs entered in `hdi.batch.creation.wizard`
2. **Batch creation**: `action_create_batch()` copies docs to `hdi.batch` record
3. **Display**: Batch form view shows docs in dedicated notebook page

### Future Enhancements
1. **Signature upload**: Currently stores binary field; add UI for signature pad or photo upload
2. **Document attachments**: Link actual PDF/image files of invoice/packing list
3. **Validation rules**: Check import doc formats, validate against supplier invoices
4. **Scanner enforcement**: Implement logic in `on_barcode_scanned()` to enforce `scan_detail_level`
5. **Audit trail**: Log all handover events in chatter/mail thread

## Testing Checklist

- [ ] Create receipt picking with batch management enabled
- [ ] Set scan detail level to each option (batch_only, batch_plus_products, full_item)
- [ ] Click "Xác nhận bàn giao" - verify user and timestamp recorded
- [ ] Create batch with import document references filled
- [ ] Verify import docs display in batch form "Chứng từ Nhập khẩu" page
- [ ] Complete putaway workflow with batch
- [ ] Verify batch state transitions correctly
- [ ] Test with real barcode scanner (if available)

## Related Files

### Models
- `models/hdi_batch.py` - Import doc fields
- `models/stock_picking.py` - Scan level + handover fields + action
- `wizard/batch_creation_wizard.py` - Import doc wizard fields

### Views
- `views/hdi_batch_views.xml` - Import docs page
- `views/stock_picking_views.xml` - Handover button + fields
- `wizard/batch_creation_wizard_views.xml` - Import docs input group

## Next Steps

1. **Restart Odoo** and upgrade module:
   ```bash
   # Stop Odoo
   pkill -f odoo
   
   # Upgrade module (adjust path to your odoo-bin and config)
   /path/to/odoo-bin -c /path/to/odoo.conf -u hdi_wms --stop-after-init
   
   # Restart Odoo normally
   /path/to/odoo-bin -c /path/to/odoo.conf
   ```

2. **Test in UI**: Follow testing checklist above

3. **Implement scanner logic**: Add enforcement of `scan_detail_level` in `on_barcode_scanned()` method

4. **Add signature UI**: Create web/mobile interface for capturing handover signature

5. **Document attachment**: Implement file upload for actual import documents

---
*Last updated: 2024 - HDI WMS Inbound Flows*
