#!/bin/bash
# Script để tìm và report các vấn đề cần fix khi migrate lên Odoo 18

echo "=== KIỂM TRA CÁC VẤN ĐỀ CẦN FIX TRONG NGSD ==="
echo ""

echo "1. Tìm các file còn dùng 'from odoo import *':"
grep -r "from odoo import \*" ngsd/ --include="*.py" | wc -l
echo ""

echo "2. Tìm các file dùng @api.multi hoặc @api.one:"
grep -r "@api\.multi\|@api\.one" ngsd/ --include="*.py" | wc -l
echo ""

echo "3. Tìm các file dùng @api.returns:"
grep -r "@api\.returns" ngsd/ --include="*.py"
echo ""

echo "4. Tìm các view XML dùng attrs với invisible/readonly/required:"
grep -r 'attrs=.*invisible\|attrs=.*readonly\|attrs=.*required' ngsd/ --include="*.xml" | wc -l
echo ""

echo "5. Tìm các Selection field dùng tuple thay vì list:"
grep -rn "= fields.Selection((" ngsd/ --include="*.py" | head -20
echo ""

echo "=== HOÀN THÀNH KIỂM TRA ==="
