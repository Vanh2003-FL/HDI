#!/usr/bin/env python3
"""
Script convert các pattern phức tạp hơn - OR, AND conditions
"""
import re
import os

def convert_or_invisible(content):
    """Convert attrs="{'invisible': ['|', ('a', '=', False), ('b', '=', False)]}" """
    # OR with 2 False conditions
    pattern = r'''attrs=["'](\{'invisible':\s*\['\|',\s*\('([^']+)',\s*'=',\s*False\),\s*\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        field2 = m.group(3)
        return f'invisible="not {field1} or not {field2}"'
    content = re.sub(pattern, replace, content)
    
    # OR with 2 True conditions
    pattern = r'''attrs=["'](\{'invisible':\s*\['\|',\s*\('([^']+)',\s*'=',\s*True\),\s*\('([^']+)',\s*'=',\s*True\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        field2 = m.group(3)
        return f'invisible="{field1} or {field2}"'
    content = re.sub(pattern, replace, content)
    
    # OR với string values - pattern 1: ('a', '!=', 'x'), ('b', '=', False)
    pattern = r'''attrs=["'](\{'invisible':\s*\['\|',\s*\('([^']+)',\s*'!=',\s*'([^']+)'\),\s*\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        value1 = m.group(3)
        field2 = m.group(4)
        return f'''invisible="{field1} != '{value1}' or not {field2}"'''
    content = re.sub(pattern, replace, content)
    
    # OR pattern: ('a', '!=', 'x'), ('b', '=', 'y')
    pattern = r'''attrs=["'](\{'invisible':\s*\['\|',\s*\('([^']+)',\s*'!=',\s*'([^']+)'\),\s*\('([^']+)',\s*'=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        value1 = m.group(3)
        field2 = m.group(4)
        value2 = m.group(5)
        return f'''invisible="{field1} != '{value1}' or {field2} == '{value2}'"'''
    content = re.sub(pattern, replace, content)
    
    return content

def convert_and_invisible(content):
    """Convert attrs="{'invisible': [('a', '=', False), ('b', '=', False)]}" (AND is default) """
    # AND with 2 False conditions
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*False\),\s*\('([^']+)',\s*'=',\s*False\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        field2 = m.group(3)
        return f'invisible="not {field1} and not {field2}"'
    content = re.sub(pattern, replace, content)
    
    # AND with 2 True conditions
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*True\),\s*\('([^']+)',\s*'=',\s*True\)\]\})["']'''
    def replace(m):
        field1 = m.group(2)
        field2 = m.group(3)
        return f'invisible="{field1} and {field2}"'
    content = re.sub(pattern, replace, content)
    
    return content

def convert_column_invisible(content):
    """Convert column_invisible"""
    # column_invisible with !=
    pattern = r'''attrs=["'](\{'column_invisible':\s*\[\('parent\.([^']+)',\s*'!=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''column_invisible="parent.{field} != '{value}'"'''
    content = re.sub(pattern, replace, content)
    
    # column_invisible with =
    pattern = r'''attrs=["'](\{'column_invisible':\s*\[\('parent\.([^']+)',\s*'=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''column_invisible="parent.{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_required_eq(content):
    """Convert required with == operator"""
    pattern = r'''attrs=["'](\{'required':\s*\[\('([^']+)',\s*'=',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''required="{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_file(filepath):
    """Convert a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Apply conversions
        content = convert_or_invisible(content)
        content = convert_and_invisible(content)
        content = convert_column_invisible(content)
        content = convert_required_eq(content)
        
        if content != original:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        return False
    except Exception as e:
        print(f"Error: {filepath}: {e}")
        return False

def main():
    xml_files = []
    for root, dirs, files in os.walk('ngsd'):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    print(f"Processing {len(xml_files)} files...")
    converted = 0
    for filepath in xml_files:
        if convert_file(filepath):
            converted += 1
            print(f"✓ {filepath}")
    
    print(f"\nConverted {converted} files")

if __name__ == '__main__':
    main()
