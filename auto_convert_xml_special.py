#!/usr/bin/env python3
"""
Script xử lý các patterns đặc biệt còn lại
"""
import re
import os

def convert_invisible_number(content):
    """Convert attrs với so sánh số: ('field', '=', 0), ('field', '&lt;', 33)"""
    # Pattern: ('field', '=', 0)
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'=',\s*(\d+)\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'invisible="{field} == {value}"'
    content = re.sub(pattern, replace, content)
    
    # Pattern: ('field', '&lt;', value) - less than
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'&lt;',\s*(\d+)\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'invisible="{field} &lt; {value}"'
    content = re.sub(pattern, replace, content)
    
    # Pattern: ('field', '&gt;', value) - greater than
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'&gt;',\s*(\d+)\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'invisible="{field} &gt; {value}"'
    content = re.sub(pattern, replace, content)
    
    # Pattern: ('field', '&gt;=', value)
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'&gt;=',\s*(\d+)\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'invisible="{field} &gt;= {value}"'
    return re.sub(pattern, replace, content)

def convert_invisible_not_in(content):
    """Convert attrs with 'not in' operator"""
    # Pattern: ('field', 'not in', ['a', 'b'])
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'not in',\s*\[([^\]]+)\]\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        values = m.group(3)
        return f'invisible="{field} not in [{values}]"'
    return re.sub(pattern, replace, content)

def convert_invisible_in(content):
    """Convert attrs with 'in' operator"""
    # Pattern: ('field', 'in', ['a', 'b'])
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'in',\s*\[([^\]]+)\]\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        values = m.group(3)
        return f'invisible="{field} in [{values}]"'
    return re.sub(pattern, replace, content)

def convert_invisible_special_eq(content):
    """Convert attrs với == operator sử dụng =="""
    # Pattern: ('field','==','value')
    pattern = r'''attrs=["'](\{'invisible':\s*\[\('([^']+)',\s*'==',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''invisible="{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_required_special(content):
    """Convert required với == operator"""
    # Pattern: ('field','==','value')
    pattern = r'''attrs=["'](\{'required':\s*\[\('([^']+)',\s*'==',\s*'([^']+)'\)\]\})["']'''
    def replace(m):
        field = m.group(2)
        value = m.group(3)
        return f'''required="{field} == '{value}'"'''
    return re.sub(pattern, replace, content)

def convert_readonly_special(content):
    """Convert readonly với complex patterns"""
    # Pattern: readonly with True constant
    pattern = r'''attrs=["']\{'readonly':\s*True\}["']'''
    content = re.sub(pattern, 'readonly="1"', content)
    
    return content

def convert_invisible_special(content):
    """Convert invisible với constant"""
    # Pattern: attrs="{'invisible': 1}"
    pattern = r'''attrs=["']\{'invisible':\s*1\}["']'''
    content = re.sub(pattern, 'invisible="1"', content)
    
    return content

def convert_multiple_attrs_simple(content):
    """Convert attrs có nhiều attributes đơn giản"""
    # Pattern: {'invisible': [...], 'required': [...]}
    # Tách thành 2 attributes riêng
    # Chỉ xử lý case đơn giản nhất
    return content

def convert_file(filepath):
    """Convert a single file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original = content
        
        # Apply conversions
        content = convert_invisible_number(content)
        content = convert_invisible_not_in(content)
        content = convert_invisible_in(content)
        content = convert_invisible_special_eq(content)
        content = convert_required_special(content)
        content = convert_readonly_special(content)
        content = convert_invisible_special(content)
        
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
