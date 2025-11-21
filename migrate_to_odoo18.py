#!/usr/bin/env python3
"""
Script to migrate Odoo 15 modules to Odoo 18
Handles manifest updates, XML view changes, Python code updates
"""

import os
import re
import sys
from pathlib import Path

class OdooMigrator:
    def __init__(self, base_path):
        self.base_path = Path(base_path)
        self.changes_made = []
        
    def migrate_all(self):
        """Main migration function"""
        print("=" * 80)
        print("Starting Odoo 15 -> 18 Migration")
        print("=" * 80)
        
        # Process both ngsd and ngsc directories
        for folder in ['ngsd', 'ngsc']:
            folder_path = self.base_path / folder
            if folder_path.exists():
                print(f"\n📁 Processing {folder}/")
                self.process_directory(folder_path)
        
        print("\n" + "=" * 80)
        print(f"Migration complete! {len(self.changes_made)} changes made.")
        print("=" * 80)
        
        return self.changes_made
    
    def process_directory(self, directory):
        """Process all modules in a directory"""
        for module_dir in directory.iterdir():
            if module_dir.is_dir() and not module_dir.name.startswith('.'):
                self.process_module(module_dir)
    
    def process_module(self, module_path):
        """Process a single module"""
        module_name = module_path.name
        print(f"\n  📦 Module: {module_name}")
        
        # Update __manifest__.py
        manifest = module_path / '__manifest__.py'
        if manifest.exists():
            self.update_manifest(manifest)
        
        # Update Python files
        for py_file in module_path.rglob('*.py'):
            if py_file.name != '__manifest__.py':
                self.update_python_file(py_file)
        
        # Update XML files
        for xml_file in module_path.rglob('*.xml'):
            self.update_xml_file(xml_file)
        
        # Update JavaScript files
        for js_file in module_path.rglob('*.js'):
            self.update_js_file(js_file)
    
    def update_manifest(self, manifest_path):
        """Update __manifest__.py for Odoo 18"""
        try:
            content = manifest_path.read_text(encoding='utf-8')
            original = content
            
            # Update version to 18.0.x.x.x format
            if "'version':" in content or '"version":' in content:
                # If version is like '0.1' or '1.0', change to 18.0.1.0.0
                content = re.sub(
                    r"['\"]version['\"]:\s*['\"](?:0\.1|1\.0|1\.5)['\"]",
                    "'version': '18.0.1.0.0'",
                    content
                )
                # Update existing 15.0 or 16.0 versions
                content = re.sub(
                    r"['\"]version['\"]:\s*['\"](?:15|16|17)\.\d+\.\d+\.\d+\.\d+['\"]",
                    "'version': '18.0.1.0.0'",
                    content
                )
            
            # Update deprecated modules in dependencies
            deprecated_modules = {
                'website_sale_stock': 'website_sale',  # Merged into website_sale
                'web_diagram': None,  # Removed
                'web_kanban_gauge': None,  # Removed
                'stock_barcode': 'stock',  # Now part of stock
            }
            
            for old_module, new_module in deprecated_modules.items():
                if f"'{old_module}'" in content or f'"{old_module}"' in content:
                    if new_module:
                        content = content.replace(f"'{old_module}'", f"'{new_module}'")
                        content = content.replace(f'"{old_module}"', f'"{new_module}"')
                        print(f"    ⚠️  Replaced deprecated module: {old_module} -> {new_module}")
                    else:
                        # Remove from list
                        content = re.sub(rf",?\s*['\"{old_module}\"'],?\s*", "", content)
                        print(f"    ⚠️  Removed deprecated module: {old_module}")
            
            if content != original:
                manifest_path.write_text(content, encoding='utf-8')
                self.changes_made.append(f"Updated manifest: {manifest_path}")
                print(f"    ✓ Updated __manifest__.py")
                
        except Exception as e:
            print(f"    ✗ Error updating manifest: {e}")
    
    def update_python_file(self, py_file):
        """Update Python files for Odoo 18 compatibility"""
        try:
            content = py_file.read_text(encoding='utf-8')
            original = content
            
            # Update deprecated decorators
            # @api.multi is removed in Odoo 13+
            content = re.sub(r'@api\.multi\s*\n', '', content)
            
            # @api.one is removed
            content = re.sub(r'@api\.one\s*\n', '', content)
            
            # @api.returns decorator changes
            content = re.sub(
                r"@api\.returns\(['\"]self['\"]\)",
                "@api.model",
                content
            )
            
            # Update field definitions
            # selection_add format changed
            content = re.sub(
                r"selection_add=\[",
                "selection_add=[",
                content
            )
            
            # Update old-style compute methods
            if '@api.multi' in original or '@api.one' in original:
                print(f"    ⚠️  Found deprecated decorators in {py_file.name}")
            
            # Update deprecated methods
            deprecated_methods = {
                'sudo()': 'with_user(SUPERUSER_ID)',  # Changed usage pattern
                '.search_count(': '.search_count(',  # Still valid but check usage
            }
            
            # Update odoo imports
            content = re.sub(
                r'from odoo import fields, models, api, _',
                'from odoo import fields, models, api, _',
                content
            )
            
            if content != original:
                py_file.write_text(content, encoding='utf-8')
                self.changes_made.append(f"Updated Python: {py_file}")
                print(f"    ✓ Updated {py_file.name}")
                
        except Exception as e:
            print(f"    ✗ Error updating {py_file.name}: {e}")
    
    def update_xml_file(self, xml_file):
        """Update XML files for Odoo 18 compatibility"""
        try:
            content = xml_file.read_text(encoding='utf-8')
            original = content
            
            # Remove deprecated attributes
            # create, edit, delete attributes are removed in Odoo 13+
            content = re.sub(r'\s+create="(?:true|false)"', '', content)
            content = re.sub(r'\s+edit="(?:true|false)"', '', content)
            content = re.sub(r'\s+delete="(?:true|false)"', '', content)
            
            # Update colors attribute format (Odoo 18 uses different color system)
            content = re.sub(
                r'colors="([^"]*)"',
                lambda m: f'decoration-{m.group(1).split(":")[0].lower()}="{m.group(1).split(":")[1]}"' if ':' in m.group(1) else m.group(0),
                content
            )
            
            # Update string attribute on fields (some are now label)
            # But this needs context, so we skip automatic replacement
            
            # Update groups attribute format
            # Ensure proper XML entity escaping
            content = re.sub(r'groups="([^"]*)"', lambda m: f'groups="{m.group(1)}"', content)
            
            # Update xpath expressions
            # expr attribute is now required
            content = re.sub(
                r'<xpath\s+position="([^"]*)"(?!\s+expr)',
                r'<xpath expr="." position="\1"',
                content
            )
            
            # Update field widget attributes for new widgets
            widget_mappings = {
                'many2many_tags': 'many2many_tags',  # Still valid
                'statusbar': 'statusbar',  # Still valid
                'monetary': 'monetary',  # Still valid
            }
            
            # Update deprecated widgets
            deprecated_widgets = {
                'one2many_list': 'one2many',
                'reference': 'reference',
            }
            
            for old_widget, new_widget in deprecated_widgets.items():
                if f'widget="{old_widget}"' in content:
                    content = content.replace(f'widget="{old_widget}"', f'widget="{new_widget}"')
                    print(f"    ⚠️  Updated widget: {old_widget} -> {new_widget}")
            
            # Update tree view (list view)
            # default_order is now default_order in tree tag
            content = re.sub(
                r'<tree([^>]*)>',
                lambda m: m.group(0),
                content
            )
            
            if content != original:
                xml_file.write_text(content, encoding='utf-8')
                self.changes_made.append(f"Updated XML: {xml_file}")
                print(f"    ✓ Updated {xml_file.name}")
                
        except Exception as e:
            print(f"    ✗ Error updating {xml_file.name}: {e}")
    
    def update_js_file(self, js_file):
        """Update JavaScript files for Odoo 18 compatibility"""
        try:
            content = js_file.read_text(encoding='utf-8')
            original = content
            
            # Update module system
            # Old: odoo.define
            # New: @odoo/module system (Odoo 18)
            
            # Update require statements
            content = re.sub(
                r"var\s+(\w+)\s+=\s+require\(['\"]([^'\"]+)['\"]\);",
                r"import { \1 } from '\2';",
                content
            )
            
            # Update Class.include syntax
            content = re.sub(
                r"(\w+)\.include\({",
                r"\1.include({",
                content
            )
            
            # Update ajax calls
            # Old: this._rpc
            # Still valid but check for deprecated patterns
            
            if 'odoo.define' in content:
                print(f"    ⚠️  Found old odoo.define in {js_file.name} - manual review needed")
            
            if content != original:
                js_file.write_text(content, encoding='utf-8')
                self.changes_made.append(f"Updated JS: {js_file}")
                print(f"    ✓ Updated {js_file.name}")
                
        except Exception as e:
            print(f"    ✗ Error updating {js_file.name}: {e}")


def main():
    """Main entry point"""
    base_path = Path(__file__).parent
    
    print(f"\n🚀 Odoo Migration Tool")
    print(f"📂 Base path: {base_path}")
    print(f"\nThis will modify files in place. Make sure you have backups!")
    
    response = input("\nContinue? (yes/no): ")
    if response.lower() not in ['yes', 'y']:
        print("Migration cancelled.")
        return
    
    migrator = OdooMigrator(base_path)
    changes = migrator.migrate_all()
    
    print(f"\n📝 Summary:")
    print(f"   Total files modified: {len(changes)}")
    
    if changes:
        print(f"\n   First 10 changes:")
        for change in changes[:10]:
            print(f"   - {change}")
        
        if len(changes) > 10:
            print(f"   ... and {len(changes) - 10} more")


if __name__ == '__main__':
    main()
