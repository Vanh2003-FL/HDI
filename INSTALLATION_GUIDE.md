# WMS Installation & Configuration Guide

## Table of Contents
1. [System Requirements](#system-requirements)
2. [Installation Steps](#installation-steps)
3. [Initial Configuration](#initial-configuration)
4. [Module-by-Module Setup](#module-by-module-setup)
5. [Testing & Validation](#testing--validation)
6. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Software Requirements
- **Odoo**: Version 18.0 or higher
- **Python**: 3.10 or higher
- **PostgreSQL**: 12.0 or higher
- **Operating System**: Linux (Ubuntu 20.04+ recommended) / macOS / Windows

### Python Dependencies
```bash
pip install xlsxwriter>=3.0.0
pip install requests>=2.28.0
pip install pillow>=9.0.0  # For barcode generation
```

### Hardware Requirements (Minimum)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Storage**: 20 GB free space
- **Network**: 100 Mbps

### Hardware Requirements (Recommended for Production)
- **CPU**: 4+ cores
- **RAM**: 8+ GB
- **Storage**: 50+ GB SSD
- **Network**: 1 Gbps

---

## Installation Steps

### Step 1: Prepare Odoo Environment

#### 1.1 Install Odoo 18
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y git python3-pip python3-dev libxml2-dev libxslt1-dev \
    libldap2-dev libsasl2-dev libtiff5-dev libjpeg8-dev libopenjp2-7-dev \
    zlib1g-dev libfreetype6-dev liblcms2-dev libwebp-dev libharfbuzz-dev \
    libfribidi-dev libxcb1-dev libpq-dev python3-venv

# Create Odoo user
sudo useradd -m -d /opt/odoo -U -r -s /bin/bash odoo

# Clone Odoo 18
sudo su - odoo
git clone https://github.com/odoo/odoo.git --depth 1 --branch 18.0 odoo18
cd odoo18

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Odoo requirements
pip install -r requirements.txt
```

#### 1.2 Install WMS Dependencies
```bash
# While in virtual environment
pip install xlsxwriter requests pillow
```

### Step 2: Copy WMS Modules

```bash
# Create custom addons directory
mkdir -p /opt/odoo/custom-addons

# Copy WMS modules (adjust source path)
cp -r /workspaces/HDI/hdi/wms_* /opt/odoo/custom-addons/

# Set permissions
sudo chown -R odoo:odoo /opt/odoo/custom-addons
```

### Step 3: Configure Odoo

#### 3.1 Create odoo.conf
```bash
sudo nano /etc/odoo.conf
```

Add the following configuration:
```ini
[options]
admin_passwd = admin_password_change_me
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo_db_password
addons_path = /opt/odoo/odoo18/addons,/opt/odoo/custom-addons
logfile = /var/log/odoo/odoo-server.log
log_level = info
workers = 4
max_cron_threads = 2
```

#### 3.2 Create systemd service
```bash
sudo nano /etc/systemd/system/odoo.service
```

Add:
```ini
[Unit]
Description=Odoo 18
After=network.target postgresql.service

[Service]
Type=simple
User=odoo
Group=odoo
ExecStart=/opt/odoo/odoo18/venv/bin/python3 /opt/odoo/odoo18/odoo-bin -c /etc/odoo.conf
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 3.3 Start Odoo
```bash
sudo systemctl daemon-reload
sudo systemctl enable odoo
sudo systemctl start odoo
sudo systemctl status odoo
```

### Step 4: Install WMS Modules

#### 4.1 Via Command Line (All modules at once)
```bash
/opt/odoo/odoo18/venv/bin/python3 /opt/odoo/odoo18/odoo-bin \
    -c /etc/odoo.conf \
    -d your_database_name \
    -i wms_base,wms_product,wms_location,wms_inventory,wms_receipt,wms_delivery,wms_transfer,wms_adjustment,wms_report,wms_dashboard,wms_integration \
    --stop-after-init
```

#### 4.2 Via Odoo Web Interface (Step by step)
1. Open browser: `http://localhost:8069`
2. Create or select database
3. Go to: **Apps** menu
4. Click: **Update Apps List**
5. Search: "WMS"
6. Install modules in order:
   - wms_base
   - wms_product
   - wms_location
   - wms_inventory
   - wms_receipt
   - wms_delivery
   - wms_transfer
   - wms_adjustment
   - wms_report
   - wms_dashboard
   - wms_integration

---

## Initial Configuration

### 1. Create Warehouse

**Path**: WMS → Configuration → Warehouses → Create

**Required Fields**:
- **Name**: Main Warehouse
- **Code**: WH01
- **Address**: Full warehouse address

**Optional Fields**:
- **Capacity Total**: 10000 (units)
- **Temperature Range**: -5°C to 25°C
- **Notes**: Any additional info

**Click**: Save

### 2. Create Zones

**Path**: WMS → Configuration → Zones → Create

Create the following zones:

#### Zone 1: Receiving
- **Name**: Receiving Area
- **Code**: RCV
- **Warehouse**: Main Warehouse
- **Zone Type**: receiving
- **Capacity**: 500
- **Sequence**: 10

#### Zone 2: Storage
- **Name**: Main Storage
- **Code**: STG
- **Warehouse**: Main Warehouse
- **Zone Type**: storage
- **Capacity**: 8000
- **Sequence**: 20

#### Zone 3: Picking
- **Name**: Picking Zone
- **Code**: PCK
- **Warehouse**: Main Warehouse
- **Zone Type**: picking
- **Capacity**: 1000
- **Sequence**: 30

#### Zone 4: Packing
- **Name**: Packing Station
- **Code**: PAK
- **Warehouse**: Main Warehouse
- **Zone Type**: packing
- **Capacity**: 300
- **Sequence**: 40

#### Zone 5: Shipping
- **Name**: Shipping Dock
- **Code**: SHP
- **Warehouse**: Main Warehouse
- **Zone Type**: shipping
- **Capacity**: 200
- **Sequence**: 50

#### Zone 6: Quarantine
- **Name**: Quarantine
- **Code**: QRT
- **Warehouse**: Main Warehouse
- **Zone Type**: quarantine
- **Capacity**: 100
- **Sequence**: 60

### 3. Create Locations

**Path**: WMS → Configuration → Locations → Create

#### Sample Hierarchical Structure:

**Main Storage (8000 capacity)**

**Aisle A**:
```
A-01-01 (Aisle A, Row 1, Shelf 1) - Bin - Capacity: 100
A-01-02 (Aisle A, Row 1, Shelf 2) - Bin - Capacity: 100
A-02-01 (Aisle A, Row 2, Shelf 1) - Bin - Capacity: 100
...
```

**Aisle B**:
```
B-01-01 (Aisle B, Row 1, Shelf 1) - Bin - Capacity: 100
B-01-02 (Aisle B, Row 1, Shelf 2) - Bin - Capacity: 100
...
```

**Quick Create Script** (via Developer Mode → Python Code):
```python
# Run this in Odoo shell or create via script
zone_storage = env['wms.zone'].search([('code', '=', 'STG')], limit=1)
warehouse = zone_storage.warehouse_id

# Create 10 aisles (A-J), 10 rows per aisle, 10 shelves per row
for aisle in ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J']:
    for row in range(1, 11):
        for shelf in range(1, 11):
            code = f"{aisle}-{row:02d}-{shelf:02d}"
            name = f"Aisle {aisle}, Row {row}, Shelf {shelf}"
            
            env['wms.location'].create({
                'name': name,
                'code': code,
                'warehouse_id': warehouse.id,
                'zone_id': zone_storage.id,
                'location_type': 'bin',
                'capacity': 100,
                'can_stock': True,
            })
```

This creates **1,000 storage locations** (10×10×10).

### 4. Configure Products

**Path**: Inventory → Products → Select Product → Edit

Enable WMS features for each product:

**General Tab**:
- **Product Type**: Storable Product
- **Tracking**: By Unique Serial Number / By Lots

**WMS Tab** (new tab added by wms_product):
- **Track Stock**: ✓ Enable
- **ABC Classification**: A / B / C
- **Min Stock Level**: 10
- **Max Stock Level**: 1000
- **Reorder Point**: 20
- **Costing Method**: FIFO / FEFO / LIFO

**Inventory Tab**:
- **Barcode**: Generate or enter barcode
- **Internal Reference**: PRD001, PRD002, etc.

### 5. Create User Groups

**Path**: Settings → Users & Companies → Groups

Assign users to groups:
- **WMS User**: Warehouse operators
- **WMS Manager**: Warehouse supervisors

**Path**: Settings → Users & Companies → Users → Select User → Access Rights

Enable:
- **Warehouse Management / User** (for operators)
- **Warehouse Management / Manager** (for supervisors)

### 6. Configure API (Optional)

**Path**: WMS → Integration → API Keys → Create

**If using REST API**:
- **Name**: Mobile App API
- **User**: Select technical user
- **Warehouse**: Main Warehouse (optional)
- **Expires On**: 2025-12-31

**Permissions** (check boxes):
- ✓ Can Query Stock
- ✓ Can Create Receipt
- ✓ Can Create Delivery
- ✓ Can Reserve Stock
- ✓ Can Move Stock

**Security**:
- **IP Whitelist**: 192.168.1.100, 192.168.1.101 (optional)

**Click**: Save → **Copy the generated API key**

---

## Module-by-Module Setup

### Module 1-4: Foundation & Inventory
✅ Already configured via Warehouse/Zone/Location/Product setup above.

### Module 5: Receipt (Inbound)
**Test First Receipt**:
1. WMS → Operations → Receipts → Create
2. **Warehouse**: Main Warehouse
3. **Origin**: PO12345
4. **Add Line**: Product PRD001, Quantity 100
5. **Confirm** → State: Receiving
6. **Complete Receiving** → Enter received: 100
7. **Complete QC** → All pass
8. **Complete Putaway** → Location: A-01-01
9. **Verify**: Check Stock → Product PRD001 should have 100 units in A-01-01

### Module 6: Delivery (Outbound)
**Test First Delivery**:
1. WMS → Operations → Deliveries → Create
2. **Warehouse**: Main Warehouse
3. **Customer**: ABC Company
4. **Add Line**: Product PRD001, Quantity 10
5. **Confirm** → Auto-reserve stock from A-01-01
6. **Complete Picking** → Picked: 10
7. **Complete Packing** → Package: PKG001
8. **Complete Shipping** → Carrier: FedEx
9. **Verify**: Stock should decrease to 90 units

### Module 7: Transfer
**Test Internal Transfer**:
1. WMS → Operations → Transfers → Create
2. **Warehouse**: Main Warehouse
3. **Add Line**: PRD001, From: A-01-01, To: B-02-02, Qty: 20
4. **Submit for Approval**
5. **Manager Approves**: Approve button
6. **Execute Transfer**
7. **Verify**: 70 in A-01-01, 20 in B-02-02

### Module 8: Adjustment
**Test Cycle Count**:
1. WMS → Operations → Adjustments → Create
2. **Location**: A-01-01
3. **Adjustment Reason**: Cycle Count
4. **Add Line**: PRD001, System: 70, Actual: 68
5. **Variance**: -2 (system calculates)
6. **Complete** (if variance < threshold) or **Submit for Approval**
7. **Verify**: Stock adjusted to 68

### Module 9: Reports
**Generate Stock Aging Report**:
1. WMS → Reports → Stock Aging Report
2. **Date**: Today
3. **Aging Method**: FIFO (by in_date)
4. **Aging Period**: 30-60-90 days
5. **Generate Report**
6. **Download Excel**: Check formatting, colors, formulas

### Module 10: Dashboard
**View Dashboard**:
1. WMS → Dashboard
2. **Warehouse Selector**: Select Main Warehouse
3. **Verify Data**:
   - Total Stock: Should show current stock (e.g., 88 units)
   - Capacity: Calculate % used
   - Charts: Should display movement trends
   - Alerts: Check if any low stock alerts

### Module 11: Integration

#### Test API:
```bash
# Get API key from WMS → Integration → API Keys
export API_KEY="wms_your_generated_key"

# Query stock
curl -X POST \
  http://localhost:8069/api/wms/stock/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"product_code": "PRD001"}'

# Expected response: Stock levels in JSON format
```

#### Test Barcode Scanner:
1. WMS → Integration → Barcode Scanner → Scans
2. Click mobile-friendly kanban view
3. Scan product barcode (or manually enter PRD001)
4. **Operation**: Query Stock
5. **Result**: Should show locations and quantities

#### Test EDI Import:
1. Create CSV file `products.csv`:
```csv
default_code,name,list_price,standard_price
PRD010,Test Product 10,100,80
PRD011,Test Product 11,150,120
```

2. WMS → Integration → EDI → Import Data
3. **Import Type**: Product
4. **File Format**: CSV
5. **Warehouse**: Main Warehouse
6. **Upload File**: products.csv
7. **Import**
8. **Verify**: Check Products list for PRD010, PRD011

#### Configure Webhook:
1. WMS → Integration → Webhooks → Create
2. **Name**: Notify External System
3. **URL**: https://your-system.com/webhook
4. **Method**: POST
5. **Events**: Check "Receipt Done", "Delivery Shipped"
6. **Authentication**: Bearer Token (if needed)
7. **Save** → **Test Webhook**

---

## Testing & Validation

### Functional Tests

#### Test 1: Complete Inbound Flow
```
✓ Create Receipt
✓ Receive Products (scan barcodes)
✓ Quality Check (pass/fail)
✓ Putaway to Storage
✓ Verify Stock Levels
✓ Check Dashboard Updates
```

#### Test 2: Complete Outbound Flow
```
✓ Create Delivery
✓ Reserve Stock
✓ Pick Products (scan barcodes)
✓ Pack Items
✓ Ship Order
✓ Verify Stock Deduction
```

#### Test 3: Internal Operations
```
✓ Create Transfer
✓ Approve Transfer
✓ Execute Move
✓ Verify Stock Redistribution
```

#### Test 4: Reporting
```
✓ Generate all 5 reports
✓ Verify data accuracy
✓ Check Excel formatting
✓ Validate calculations
```

#### Test 5: Integration
```
✓ API authentication
✓ Stock query endpoint
✓ Receipt creation endpoint
✓ Barcode scanning
✓ EDI import/export
✓ Webhook delivery
```

### Performance Tests

#### Load Test: 10,000 Products
```python
# Create test data
for i in range(1, 10001):
    env['product.product'].create({
        'name': f'Test Product {i}',
        'default_code': f'TEST{i:05d}',
        'type': 'product',
        'track_stock': True,
    })
```

#### Load Test: 1,000 Stock Moves
```python
# Create test stock moves
for i in range(1000):
    env['wms.stock.move'].create({
        'product_id': product.id,
        'quantity': 10,
        'location_from_id': loc_from.id,
        'location_to_id': loc_to.id,
        'move_type': 'transfer',
    }).action_done()
```

#### Dashboard Load Time
- Target: < 2 seconds for 10,000 products
- Monitor: Response time in API logs

---

## Troubleshooting

### Issue: Modules not visible in Apps
**Solution**:
```bash
# Update apps list
./odoo-bin -c odoo.conf -d your_db -u all --stop-after-init

# Or via UI: Apps → Update Apps List
```

### Issue: ImportError: No module named 'xlsxwriter'
**Solution**:
```bash
# Install in Odoo's virtual environment
source /opt/odoo/odoo18/venv/bin/activate
pip install xlsxwriter requests
```

### Issue: Permission denied on /var/log/odoo
**Solution**:
```bash
sudo mkdir -p /var/log/odoo
sudo chown odoo:odoo /var/log/odoo
```

### Issue: Database connection error
**Solution**:
```bash
# Check PostgreSQL running
sudo systemctl status postgresql

# Create Odoo database user
sudo -u postgres createuser -s odoo
sudo -u postgres psql -c "ALTER USER odoo WITH PASSWORD 'odoo_password';"
```

### Issue: API returns 401 Unauthorized
**Solution**:
- Verify API key is active
- Check expiration date
- Verify IP whitelist (if configured)
- Check header: `X-API-Key` (case-sensitive)

### Issue: Dashboard charts not displaying
**Solution**:
```bash
# Check browser console for JavaScript errors
# Verify Chart.js loaded: /web/static/lib/Chart/Chart.js
# Clear browser cache
# Check Odoo logs for errors
```

### Issue: Stock not updating after receipt
**Solution**:
- Verify receipt state is "Done"
- Check putaway completed
- Verify product.track_stock = True
- Check location.can_stock = True
- Review Odoo logs for errors

### Issue: Excel reports not generating
**Solution**:
```bash
# Verify xlsxwriter installed
python3 -c "import xlsxwriter; print(xlsxwriter.__version__)"

# Check Odoo logs for errors
tail -f /var/log/odoo/odoo-server.log

# Verify write permissions
sudo chown -R odoo:odoo /opt/odoo
```

---

## Post-Installation Checklist

### System Health
- [ ] All 11 modules installed successfully
- [ ] No errors in Odoo log
- [ ] Database size reasonable (< 1GB for test data)
- [ ] Odoo service auto-starts on boot

### Configuration
- [ ] At least 1 warehouse created
- [ ] At least 5 zones created (receiving, storage, picking, packing, shipping)
- [ ] At least 100 locations created
- [ ] Sample products configured with WMS attributes
- [ ] User groups assigned correctly

### Functionality
- [ ] Can create and complete receipts
- [ ] Can create and complete deliveries
- [ ] Can create and execute transfers
- [ ] Can perform cycle counting
- [ ] Dashboard loads and displays data
- [ ] All 5 reports generate Excel files
- [ ] API endpoints respond correctly
- [ ] Barcode scanning works
- [ ] EDI import/export functions

### Performance
- [ ] Dashboard loads in < 3 seconds
- [ ] Reports generate in < 10 seconds
- [ ] API response time < 500ms
- [ ] No memory leaks after 24h operation

### Security
- [ ] Admin password changed from default
- [ ] API keys configured with appropriate permissions
- [ ] User access rights verified
- [ ] IP whitelist configured (if applicable)

---

## Next Steps

1. **Training**: Train warehouse staff on system usage
2. **Data Migration**: Import existing products, locations, stock
3. **Integration**: Connect external systems via API
4. **Customization**: Extend modules for specific business needs
5. **Monitoring**: Set up monitoring for system health
6. **Backup**: Configure daily database backups
7. **Optimization**: Tune performance based on usage patterns

---

## Support Resources

- **Documentation**: See WMS_COMPLETE_DOCUMENTATION.md
- **API Reference**: See WMS_API_DOCUMENTATION.md
- **Odoo Forums**: https://www.odoo.com/forum
- **GitHub Issues**: [Create an issue](/)

---

**Installation Complete! 🎉**

Your WMS system is now ready for production use.
