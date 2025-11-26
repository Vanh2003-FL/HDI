#!/bin/bash

# Module 4: hdi_stock_dispatch_extension
mkdir -p hdi_stock_dispatch_extension/{models,views,security,data,wizard}
cat > hdi_stock_dispatch_extension/__init__.py << 'EOF'
from . import models
from . import wizard
EOF

cat > hdi_stock_dispatch_extension/__manifest__.py << 'EOF'
{
    'name': 'HDI Stock Dispatch Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quy trình xuất kho chuyên nghiệp (Picklist – Pack – Staging)',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_batch_flow'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/picking_picklist_views.xml',
        'views/menu_views.xml',
        'wizard/generate_picklist_wizard_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 5: hdi_stock_inventory_extension  
mkdir -p hdi_stock_inventory_extension/{models,views,security,data}
cat > hdi_stock_inventory_extension/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_stock_inventory_extension/__manifest__.py << 'EOF'
{
    'name': 'HDI Stock Inventory Extension',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Kiểm kê nâng cao (cycle count, batch count)',
    'author': 'HDI',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_inventory_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 6: hdi_stock_odd_items
mkdir -p hdi_stock_odd_items/{models,views,security}
cat > hdi_stock_odd_items/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_stock_odd_items/__manifest__.py << 'EOF'
{
    'name': 'HDI Stock Odd Items',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quản lý hàng lẻ / thiếu lô',
    'author': 'HDI',
    'depends': ['stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/odd_item_views.xml',
        'views/stock_quant_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 7: hdi_barcode_workflow
mkdir -p hdi_barcode_workflow/{models,views,security,data}
cat > hdi_barcode_workflow/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_barcode_workflow/__manifest__.py << 'EOF'
{
    'name': 'HDI Barcode Workflow',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Quy trình quét barcode nhiều bước',
    'author': 'HDI',
    'depends': ['stock', 'barcodes'],
    'data': [
        'data/ir_sequence_data.xml',
        'security/ir.model.access.csv',
        'views/barcode_workflow_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 8: hdi_api_map_connector
mkdir -p hdi_api_map_connector/{models,views,security,controllers}
cat > hdi_api_map_connector/__init__.py << 'EOF'
from . import models
from . import controllers
EOF

cat > hdi_api_map_connector/__manifest__.py << 'EOF'
{
    'name': 'HDI API Map Connector',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Kết nối Odoo WMS ↔ Digital Layout 3D',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_putaway_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/map_sync_queue_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 9: hdi_logistics_partner
mkdir -p hdi_logistics_partner/{models,views,security,data}
cat > hdi_logistics_partner/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_logistics_partner/__manifest__.py << 'EOF'
{
    'name': 'HDI Logistics Partner',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Quản lý đối tác vận chuyển (3PL)',
    'author': 'HDI',
    'depends': ['stock', 'delivery'],
    'data': [
        'security/ir.model.access.csv',
        'views/logistics_partner_views.xml',
        'views/logistics_rate_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 10: hdi_fleet_assignment
mkdir -p hdi_fleet_assignment/{models,views,security}
cat > hdi_fleet_assignment/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_fleet_assignment/__manifest__.py << 'EOF'
{
    'name': 'HDI Fleet Assignment',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Delivery',
    'summary': 'Quản lý đội xe + phân công giao hàng',
    'author': 'HDI',
    'depends': ['stock', 'fleet'],
    'data': [
        'security/ir.model.access.csv',
        'views/picking_vehicle_assign_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

# Module 11: hdi_stock_reporting
mkdir -p hdi_stock_reporting/{models,views,security,report}
cat > hdi_stock_reporting/__init__.py << 'EOF'
from . import models
EOF

cat > hdi_stock_reporting/__manifest__.py << 'EOF'
{
    'name': 'HDI Stock Reporting',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Báo cáo WMS (nhập – xuất – tồn – kiểm kê)',
    'author': 'HDI',
    'depends': ['stock', 'hdi_stock_batch_flow', 'hdi_stock_putaway_map'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_report_entry_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}
EOF

echo "✅ Created all WMS module structures"
