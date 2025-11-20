#!/bin/bash

echo "=== KIỂM TRA CÁC VẤN ĐỀ ODOO 18 MIGRATION ==="
echo ""

# 1. Kiểm tra version không đúng format
echo "1. Kiểm tra version trong __manifest__.py:"
python3 << 'PYTHON'
import os, ast
invalid = []
for root, dirs, files in os.walk('ngsd'):
    if '__manifest__.py' in files:
        path = os.path.join(root, '__manifest__.py')
        try:
            with open(path) as f:
                manifest = ast.literal_eval(f.read())
                version = manifest.get('version', '')
                if version:
                    parts = version.split('.')
                    if len(parts) < 4 or not version.startswith('18.0.'):
                        invalid.append(f"  {path}: {version}")
        except: pass
if invalid:
    print(f"❌ Tìm thấy {len(invalid)} version không hợp lệ:")
    for v in invalid: print(v)
else:
    print("✅ Tất cả version đã đúng format 18.0.x.y.z")
PYTHON

echo ""

# 2. Kiểm tra attrs trong XML
echo "2. Kiểm tra attrs trong XML (không tính comment):"
attrs_count=$(grep -r "attrs=" ngsd/ --include="*.xml" | grep -v "<!--" | wc -l)
if [ "$attrs_count" -gt 0 ]; then
    echo "❌ Còn $attrs_count attrs chưa convert"
    echo "   Top 10 file:"
    grep -r "attrs=" ngsd/ --include="*.xml" | grep -v "<!--" | cut -d: -f1 | sort | uniq -c | sort -rn | head -10
else
    echo "✅ Không còn attrs nào (hoặc chỉ trong comment)"
fi

echo ""

# 3. Kiểm tra import Domain từ odoo.fields
echo "3. Kiểm tra import Domain từ odoo.fields:"
domain_count=$(grep -r "from odoo.fields import.*Domain" ngsd/ --include="*.py" | wc -l)
if [ "$domain_count" -gt 0 ]; then
    echo "❌ Còn $domain_count file import Domain từ odoo.fields"
    grep -r "from odoo.fields import.*Domain" ngsd/ --include="*.py" -l
else
    echo "✅ Không còn import Domain từ odoo.fields"
fi

echo ""

# 4. Kiểm tra from odoo import *
echo "4. Kiểm tra 'from odoo import *':"
import_all=$(grep -r "from odoo import \*" ngsd/ --include="*.py" | wc -l)
if [ "$import_all" -gt 0 ]; then
    echo "❌ Còn $import_all file có 'from odoo import *'"
    grep -r "from odoo import \*" ngsd/ --include="*.py" -l | head -5
else
    echo "✅ Không còn 'from odoo import *'"
fi

echo ""
echo "=== HOÀN THÀNH KIỂM TRA ==="
