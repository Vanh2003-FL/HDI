#!/usr/bin/env python3
"""
Script tự động convert XML attrs syntax từ Odoo 15 sang Odoo 18
"""
import re
import os
import sys

def convert_simple_invisible_false(content):
    """Convert attrs="{'invisible': [('field', '=', False)]}" to invisible="not field" """
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'invisible="not {field}"'
    return re.sub(pattern, replace, content)

def convert_simple_invisible_true(content):
    """Convert attrs="{'invisible': [('field', '=', True)]}" to invisible="field" """
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*True\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'invisible="{field}"'
    return re.sub(pattern, replace, content)

def convert_simple_invisible_eq(content):
    """Convert attrs="{'invisible': [('field', '=', 'value')]}" to invisible="field == 'value'" """
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''invisible="{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_simple_invisible_neq(content):
    """Convert attrs="{'invisible': [('field', '!=', 'value')]}" to invisible="field != 'value'" """
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'!=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''invisible="{field} != '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_simple_required_true(content):
    """Convert attrs="{'required': [('field', '=', True)]}" to required="field" """
    pattern = r'''attrs=["'](\{'required':\s*\[\('([^']+)',\s*'=',\s*True\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'required="{field}"'
    return re.sub(pattern, replace, content)

def convert_simple_required_false(content):
    """Convert attrs="{'required': [('field', '=', False)]}" to required="not field" """
    pattern = r'''attrs=["'](\{'required':\s*\[\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'required="not {field}"'
    return re.sub(pattern, replace, content)

def convert_simple_readonly_true(content):
    """Convert attrs="{'readonly': [('field', '=', True)]}" to readonly="field" """
    pattern = r'''attrs=["'](\{'readonly':\s*\[\('([^']+)',\s*'=',\s*True\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'readonly="{field}"'
    return re.sub(pattern, replace, content)

def convert_simple_readonly_false(content):
    """Convert attrs="{'readonly': [('field', '=', False)]}" to readonly="not field" """
    pattern = r'''attrs=["'](\{'readonly':\s*\[\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        return f'readonly="not {field}"'
    return re.sub(pattern, replace, content)

def convert_simple_readonly_neq(content):
    """Convert attrs="{'readonly': [('field', '!=', 'value')]}" to readonly="field != 'value'" """
    pattern = r'''attrs=["'](\{'readonly':\s*\[\('([^']+)',\s*'!=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''readonly="{field} != '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_simple_readonly_eq(content):
    """Convert attrs="{'readonly': [('field', '=', 'value')]}" to readonly="field == 'value'" """
    pattern = r'''attrs=["'](\{'readonly':\s*\[\('([^']+)',\s*'=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''readonly="{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_file(filepath):
    """Convert a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Apply all conversions
        content = convert_simple_invisible_false(content)
        content = convert_simple_invisible_true(content)
        content = convert_simple_invisible_eq(content)
        content = convert_simple_invisible_neq(content)
        content = convert_simple_required_true(content)
        content = convert_simple_required_false(content)
        content = convert_simple_readonly_true(content)
        content = convert_simple_readonly_false(content)
        content = convert_simple_readonly_eq(content)
        content = convert_simple_readonly_neq(content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {filepath}: {e}")
        return False

def main():
    """Main function"""
    # Find all XML files
    xml_files = []
    for root, dirs, files in os.walk('ngsd'):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    print(f"Found {len(xml_files)} XML files")
    
    converted = 0
    for filepath in xml_files:
        if convert_file(filepath):
            converted += 1
            print(f"✓ {filepath}")
    
    print(f"\nConverted {converted} files")
    print(f"Run './check_migration_issues.sh' to check remaining attrs")

if __name__ == '__main__':
    main()
