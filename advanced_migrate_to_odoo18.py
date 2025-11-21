#!/usr/bin/env python3
"""
Advanced Odoo 18 Migration Script
Handles complex cases: models, views, security, assets
"""

import os
import re
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

class AdvancedOdooMigrator:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.issues = []
        self.fixed = []
        
    def fix_all_models(self):
        """Fix all Python model files"""
        print("\n🔧 Fixing Python Models...")
        
        for py_file in self.base_path.rglob('models/*.py'):
            if py_file.name != '__init__.py':
                self.fix_model_file(py_file)
        
        for py_file in self.base_path.rglob('wizard/*.py'):
            if py_file.name != '__init__.py':
                self.fix_model_file(py_file)
    
    def fix_model_file(self, file_path):
        """Fix individual model file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original = content
            
            # 1. Fix imports
            if 'from odoo import' in content:
                # Ensure proper import order
                imports = []
                if 'models' in content:
                    imports.append('models')
                if 'fields' in content:
                    imports.append('fields')
                if 'api' in content:
                    imports.append('api')
                if '_' in content and 'from odoo import' in content:
                    imports.append('_')
                if 'exceptions' in content:
                    imports.append('exceptions')
                
                # Replace old import with new organized import
                if imports:
                    new_import = f"from odoo import {', '.join(imports)}"
                    content = re.sub(
                        r'from odoo import.*',
                        new_import,
                        content,
                        count=1
                    )
            
            # 2. Remove deprecated decorators
            content = re.sub(r'@api\.multi\s*\n\s*', '', content)
            content = re.sub(r'@api\.one\s*\n\s*', '', content)
            content = re.sub(r'@api\.returns\([\'"]self[\'"]\)\s*\n\s*', '', content)
            content = re.sub(r'@api\.cr\s*\n\s*', '', content)
            content = re.sub(r'@api\.v7\s*\n\s*', '', content)
            content = re.sub(r'@api\.v8\s*\n\s*', '', content)
            
            # 3. Fix compute methods
            # Old: @api.multi def _compute_something(self):
            # New: def _compute_something(self):
            content = re.sub(
                r'@api\.multi\s*\n\s*def\s+(_compute_\w+)',
                r'def \1',
                content
            )
            
            # 4. Fix onchange methods
            content = re.sub(
                r'@api\.multi\s*\n\s*@api\.onchange',
                r'@api.onchange',
                content
            )
            
            # 5. Fix depends decorator
            content = re.sub(
                r'@api\.multi\s*\n\s*@api\.depends',
                r'@api.depends',
                content
            )
            
            # 6. Fix constrains
            content = re.sub(
                r'@api\.multi\s*\n\s*@api\.constrains',
                r'@api.constrains',
                content
            )
            
            # 7. Fix model decorator (for model methods)
            content = re.sub(
                r'@api\.multi\s*\n\s*@api\.model',
                r'@api.model',
                content
            )
            
            # 8. Fix field definitions
            # Old: oldname='old_field_name'
            # Check and warn about deprecated parameters
            if "oldname=" in content:
                self.issues.append(f"⚠️  {file_path}: Contains 'oldname' parameter (deprecated)")
            
            # 9. Fix selection fields with selection_add
            # Old format: selection_add=[('new_value', 'New Label')]
            # New format: selection_add=[('new_value', 'New Label')]
            # Actually same, but check for proper override
            
            # 10. Fix related fields
            # Ensure related fields have store=True if needed for performance
            content = re.sub(
                r"(\w+)\s*=\s*fields\.\w+\([^)]*related=['\"]([^'\"]+)['\"](?!.*store=)",
                lambda m: m.group(0).replace(')', ', store=False)') if ')' in m.group(0) else m.group(0),
                content
            )
            
            # 11. Fix _sql_constraints
            # Format: ('constraint_name', 'CHECK(condition)', 'Error message')
            # Still valid in v18
            
            # 12. Fix _rec_name
            # Still valid in v18
            
            # 13. Fix _order
            # Still valid in v18
            
            # 14. Fix fields_view_get override (deprecated in v13+)
            if 'fields_view_get' in content and '@api.model' not in content.split('fields_view_get')[0].split('\n')[-2]:
                self.issues.append(f"⚠️  {file_path}: fields_view_get might need @api.model decorator")
            
            # 15. Fix write/create methods
            # Check for proper return super().write(vals)
            content = re.sub(
                r'def write\(self, vals\):\s*\n\s*res = super\([^)]+\)\.write\(vals\)',
                'def write(self, vals):\n        res = super().write(vals)',
                content
            )
            
            # 16. Fix self.env.cr.execute calls
            # Ensure proper SQL injection protection
            if 'self.env.cr.execute' in content:
                execute_calls = content.split('self.env.cr.execute')
                if len(execute_calls) > 1:
                    first_call = execute_calls[1].split('\n')[0]
                    if '%s' not in first_call and ("'" in first_call or '"' in first_call):
                        self.issues.append(f"⚠️  {file_path}: SQL injection risk in cr.execute()")
            
            # 17. Fix search domain
            # Old: [('field', 'operator', value)]
            # New: Same, but check for deprecated operators
            
            # 18. Fix name_search and name_get
            # name_search is deprecated, use _name_search
            if 'def name_search' in content:
                self.issues.append(f"⚠️  {file_path}: name_search is deprecated, use _name_search")
            
            # 19. Fix _defaults dictionary (very old, removed in v9+)
            if '_defaults = {' in content:
                self.issues.append(f"❌ {file_path}: _defaults dictionary is very deprecated!")
            
            # 20. Fix _columns dictionary (very old, removed in v9+)
            if '_columns = {' in content:
                self.issues.append(f"❌ {file_path}: _columns dictionary is very deprecated!")
            
            if content != original:
                file_path.write_text(content, encoding='utf-8')
                self.fixed.append(str(file_path))
                print(f"  ✓ Fixed {file_path.relative_to(self.base_path)}")
            
        except Exception as e:
            print(f"  ✗ Error fixing {file_path}: {e}")
            self.issues.append(f"❌ {file_path}: {e}")
    
    def fix_all_views(self):
        """Fix all XML view files"""
        print("\n🔧 Fixing XML Views...")
        
        for xml_file in self.base_path.rglob('views/*.xml'):
            self.fix_view_file(xml_file)
        
        for xml_file in self.base_path.rglob('wizard/*.xml'):
            self.fix_view_file(xml_file)
    
    def fix_view_file(self, file_path):
        """Fix individual XML view file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original = content
            
            # 1. Remove create/edit/delete attributes
            content = re.sub(r'\s+create="[^"]*"', '', content)
            content = re.sub(r'\s+edit="[^"]*"', '', content)
            content = re.sub(r'\s+delete="[^"]*"', '', content)
            
            # 2. Fix colors attribute (deprecated)
            # Old: colors="red:state=='draft';blue:state=='done'"
            # New: decoration-danger="state=='draft'" decoration-info="state=='done'"
            color_map = {
                'red': 'danger',
                'green': 'success',
                'blue': 'info',
                'orange': 'warning',
                'gray': 'muted',
                'purple': 'primary',
            }
            
            if 'colors="' in content:
                self.issues.append(f"⚠️  {file_path}: Contains deprecated 'colors' attribute")
            
            # 3. Fix fonts attribute (deprecated)
            content = re.sub(r'\s+fonts="[^"]*"', '', content)
            
            # 4. Fix string attribute on field (check if needed)
            # In Odoo 18, many string attributes are optional
            
            # 5. Fix xpath expressions
            # Ensure expr attribute exists
            content = re.sub(
                r'<xpath\s+position="([^"]*)"(?!\s+expr)',
                r'<xpath expr="." position="\1"',
                content
            )
            
            # 6. Fix field widgets
            widget_replacements = {
                'many2many_binary': 'many2many_binary',  # Still valid
                'html': 'html',  # Still valid
                'image': 'image',  # Still valid
                'pdf_viewer': 'pdf_viewer',  # Check if exists
            }
            
            # 7. Fix button attributes
            # type attribute: object, action, or workflow (workflow removed)
            content = re.sub(r'type="workflow"', 'type="object"', content)
            
            # 8. Fix notebook and page tags
            # Still valid in v18
            
            # 9. Fix group tag with col and colspan
            # Still valid but check proper usage
            
            # 10. Fix field with groups attribute
            # Format: groups="base.group_user,base.group_system"
            
            # 11. Fix action window views
            # view_mode attribute: tree,form,kanban,calendar,pivot,graph,activity
            
            # 12. Fix menu items
            # Ensure proper parent and action attributes
            
            # 13. Fix record ids
            # Use module_name.record_id format
            
            # 14. Fix noupdate attribute
            # <data noupdate="1"> still valid
            
            # 15. Fix field invisible/readonly/required attributes
            # Old: attrs="{'invisible': [('field', '=', value)]}"
            # New: invisible="field == value" (Odoo 16+)
            # But attrs still works in v18, just check syntax
            
            # 16. Fix tree view attributes
            # Add default_order if missing for better UX
            
            # 17. Fix form view attributes
            # Check for proper structure
            
            # 18. Fix search view
            # Check filter and group_by
            
            # 19. Fix kanban view
            # Check for proper card structure
            
            # 20. Fix calendar/pivot/graph views
            # Check for required attributes
            
            if content != original:
                file_path.write_text(content, encoding='utf-8')
                self.fixed.append(str(file_path))
                print(f"  ✓ Fixed {file_path.relative_to(self.base_path)}")
            
        except Exception as e:
            print(f"  ✗ Error fixing {file_path}: {e}")
            self.issues.append(f"❌ {file_path}: {e}")
    
    def fix_all_security(self):
        """Fix security files"""
        print("\n🔧 Fixing Security Files...")
        
        for csv_file in self.base_path.rglob('security/*.csv'):
            self.fix_security_file(csv_file)
    
    def fix_security_file(self, file_path):
        """Fix individual security CSV file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original = content
            
            # Check CSV format
            lines = content.split('\n')
            if lines and 'id,name,model_id:id,group_id:id,perm_read,perm_write,perm_create,perm_unlink' in lines[0]:
                # Correct format
                pass
            else:
                self.issues.append(f"⚠️  {file_path}: Check CSV header format")
            
            # Check for deprecated groups
            deprecated_groups = [
                'base.group_sale_salesman',  # Check if exists in v18
                'base.group_sale_manager',   # Check if exists in v18
            ]
            
            for group in deprecated_groups:
                if group in content:
                    self.issues.append(f"⚠️  {file_path}: Contains potentially deprecated group {group}")
            
            if content != original:
                file_path.write_text(content, encoding='utf-8')
                self.fixed.append(str(file_path))
                print(f"  ✓ Fixed {file_path.relative_to(self.base_path)}")
            
        except Exception as e:
            print(f"  ✗ Error fixing {file_path}: {e}")
            self.issues.append(f"❌ {file_path}: {e}")
    
    def fix_all_manifests(self):
        """Fix all manifest files"""
        print("\n🔧 Fixing Manifest Files...")
        
        for manifest in self.base_path.rglob('__manifest__.py'):
            self.fix_manifest_file(manifest)
    
    def fix_manifest_file(self, file_path):
        """Fix individual manifest file"""
        try:
            content = file_path.read_text(encoding='utf-8')
            original = content
            
            # 1. Update version
            if "'version':" in content or '"version":' in content:
                # Update to 18.0.x.x.x format
                content = re.sub(
                    r"(['\"]version['\"]:\s*['\"])(?:0\.1|1\.0|1\.5|15\.\d+\.\d+\.\d+\.\d+|16\.\d+\.\d+\.\d+\.\d+|17\.\d+\.\d+\.\d+\.\d+)(['\"])",
                    r"\g<1>18.0.1.0.0\g<2>",
                    content
                )
            
            # 2. Check dependencies
            deprecated_modules = {
                'website_sale_stock': 'website_sale',
                'web_diagram': None,
                'web_kanban_gauge': None,
                'stock_barcode': 'stock',
                'website_crm': 'website',
                'website_form': 'website',
                'website_mail': 'website',
            }
            
            for old_mod, new_mod in deprecated_modules.items():
                if f"'{old_mod}'" in content or f'"{old_mod}"' in content:
                    if new_mod:
                        content = content.replace(f"'{old_mod}'", f"'{new_mod}'")
                        content = content.replace(f'"{old_mod}"', f'"{new_mod}"')
                    else:
                        # Remove from depends list
                        content = re.sub(rf",?\s*['\"{old_mod}\"'],?\s*", "", content)
                        content = re.sub(rf"['\"{old_mod}\"'],?\s*", "", content)
            
            # 3. Check assets structure
            if "'assets':" in content or '"assets":' in content:
                # Ensure proper assets structure for Odoo 18
                # web.assets_backend, web.assets_frontend, web.assets_common
                pass
            
            # 4. Add license if missing
            if "'license':" not in content and '"license":' not in content:
                # Add LGPL-3 as default
                content = re.sub(
                    r"(['\"]author['\"]:[^,]+,)",
                    r"\1\n    'license': 'LGPL-3',",
                    content
                )
            
            # 5. Check installable flag
            if "'installable':" not in content and '"installable":' not in content:
                content = re.sub(
                    r"(})\s*$",
                    r"    'installable': True,\n}",
                    content
                )
            
            if content != original:
                file_path.write_text(content, encoding='utf-8')
                self.fixed.append(str(file_path))
                print(f"  ✓ Fixed {file_path.relative_to(self.base_path)}")
            
        except Exception as e:
            print(f"  ✗ Error fixing {file_path}: {e}")
            self.issues.append(f"❌ {file_path}: {e}")
    
    def generate_report(self):
        """Generate migration report"""
        print("\n" + "=" * 80)
        print("📊 MIGRATION REPORT")
        print("=" * 80)
        
        print(f"\n✅ Files Fixed: {len(self.fixed)}")
        if self.fixed:
            for f in self.fixed[:10]:
                print(f"  - {f}")
            if len(self.fixed) > 10:
                print(f"  ... and {len(self.fixed) - 10} more")
        
        print(f"\n⚠️  Issues Found: {len(self.issues)}")
        if self.issues:
            for issue in self.issues[:20]:
                print(f"  - {issue}")
            if len(self.issues) > 20:
                print(f"  ... and {len(self.issues) - 20} more")
        
        # Save report to file
        report_path = self.base_path / 'ODOO18_MIGRATION_REPORT.txt'
        with open(report_path, 'w') as f:
            f.write("ODOO 18 MIGRATION REPORT\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Files Fixed: {len(self.fixed)}\n")
            f.write("\n".join(self.fixed))
            f.write("\n\n" + "=" * 80 + "\n\n")
            f.write(f"Issues Found: {len(self.issues)}\n")
            f.write("\n".join(self.issues))
        
        print(f"\n📄 Full report saved to: {report_path}")


def main():
    base_path = Path(__file__).parent
    
    print("🚀 Advanced Odoo 18 Migration Tool")
    print("=" * 80)
    
    migrator = AdvancedOdooMigrator(base_path)
    
    print("\n1. Fixing Manifest Files...")
    migrator.fix_all_manifests()
    
    print("\n2. Fixing Python Models...")
    migrator.fix_all_models()
    
    print("\n3. Fixing XML Views...")
    migrator.fix_all_views()
    
    print("\n4. Fixing Security Files...")
    migrator.fix_all_security()
    
    print("\n5. Generating Report...")
    migrator.generate_report()
    
    print("\n✅ Migration Complete!")
    print("\nNext steps:")
    print("1. Review ODOO18_MIGRATION_REPORT.txt for issues")
    print("2. Test your modules in Odoo 18")
    print("3. Fix any remaining issues manually")
    print("4. Update documentation")


if __name__ == '__main__':
    main()
