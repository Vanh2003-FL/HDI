#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra xem method attendance_action_change có tồn tại không
Chạy trong Odoo shell: odoo-bin shell -c odoo.conf -d <database_name>
"""

import sys

def test_method():
    try:
        # Import Odoo environment
        import odoo
        from odoo import api, SUPERUSER_ID
        
        # Lấy database name từ command line hoặc dùng default
        db_name = sys.argv[1] if len(sys.argv) > 1 else 'vanh_odoo'
        
        # Kết nối database
        registry = odoo.registry(db_name)
        
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            
            # Kiểm tra model hr.employee
            HrEmployee = env['hr.employee']
            
            print("=" * 60)
            print("KIỂM TRA METHOD TRONG HR.EMPLOYEE")
            print("=" * 60)
            
            # Lấy tất cả methods của model
            methods = [m for m in dir(HrEmployee) if not m.startswith('_') and callable(getattr(HrEmployee, m, None))]
            
            # Kiểm tra method attendance_action_change
            if 'attendance_action_change' in methods:
                print("✅ Method 'attendance_action_change' TỒN TẠI")
                method = getattr(HrEmployee, 'attendance_action_change')
                print(f"   Type: {type(method)}")
                print(f"   Doc: {method.__doc__}")
            else:
                print("❌ Method 'attendance_action_change' KHÔNG TỒN TẠI")
                print("\n📋 Các methods public có sẵn:")
                attendance_methods = [m for m in methods if 'attendance' in m.lower()]
                for m in sorted(attendance_methods):
                    print(f"   - {m}")
            
            # Kiểm tra module có được load không
            print("\n" + "=" * 60)
            print("KIỂM TRA MODULE")
            print("=" * 60)
            
            modules = env['ir.module.module'].search([
                ('name', 'in', ['hdi_hr_attendance_geolocation', 'hdi_attendance']),
            ])
            
            for module in modules:
                status = "✅" if module.state == 'installed' else "❌"
                print(f"{status} {module.name}: {module.state}")
            
            print("\n" + "=" * 60)
            
    except Exception as e:
        print(f"❌ LỖI: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_method()
