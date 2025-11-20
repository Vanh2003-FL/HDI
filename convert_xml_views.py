#!/usr/bin/env python3
"""
Script để convert XML views từ Odoo 15 sang Odoo 18
Chuyển đổi attrs syntax sang syntax mới
"""

import os
import re
import sys

def convert_attrs_to_new_syntax(xml_content):
    """
    Convert attrs={'invisible': [...]} to invisible="..."
    """
    changes_made = 0
    
    # Pattern để tìm attrs với invisible
    # attrs="{'invisible': [('field', '=', 'value')]}"
    pattern_invisible = r'attrs="(\{[^}]*\'invisible\'[^}]*\})"'
    pattern_readonly = r'attrs="(\{[^}]*\'readonly\'[^}]*\})"'
    pattern_required = r'attrs="(\{[^}]*\'required\'[^}]*\})"'
    pattern_column_invisible = r'attrs="(\{[^}]*\'column_invisible\'[^}]*\})"'
    
    def convert_domain_to_python(domain_str):
        """Convert Odoo domain to Python expression"""
        # Remove outer brackets
        domain_str = domain_str.strip()
        if domain_str.startswith('[') and domain_str.endswith(']'):
            domain_str = domain_str[1:-1].strip()
        
        # Handle operators
        # ('field', '=', 'value') -> field == 'value'
        # ('field', '!=', 'value') -> field != 'value'
        # ('field', 'in', [...]) -> field in [...]
        # '|' -> or
        # '&' -> and
        
        # Simple cases first
        if not domain_str:
            return "True"
            
        # Replace Polish notation operators
        domain_str = domain_str.replace("'|'", " or ")
        domain_str = domain_str.replace("'&'", " and ")
        
        # Handle simple tuple: ('state', '=', 'done')
        simple_tuple_pattern = r"\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)"
        
        def replace_tuple(match):
            field = match.group(1)
            operator = match.group(2)
            value = match.group(3)
            
            # Convert operator
            if operator == '=':
                return f"{field} == '{value}'"
            elif operator == '!=':
                return f"{field} != '{value}'"
            elif operator == 'in':
                return f"{field} in {value}"
            elif operator == 'not in':
                return f"{field} not in {value}"
            else:
                return match.group(0)
        
        result = re.sub(simple_tuple_pattern, replace_tuple, domain_str)
        
        # Clean up
        result = result.replace(", or ,", " or ")
        result = result.replace(", and ,", " and ")
        result = result.strip(", ")
        
        return result
    
    # For now, just mark files that need manual conversion
    if 'attrs=' in xml_content:
        return xml_content, True
    
    return xml_content, False

def process_file(filepath):
    """Process a single XML file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        new_content, needs_manual = convert_attrs_to_new_syntax(content)
        
        if needs_manual:
            print(f"⚠️  NEEDS MANUAL REVIEW: {filepath}")
            return 'manual'
        elif new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"✓ Converted: {filepath}")
            return 'converted'
        else:
            return 'unchanged'
    except Exception as e:
        print(f"✗ Error processing {filepath}: {e}")
        return 'error'

def main():
    """Main function"""
    print("=" * 70)
    print("Odoo 15 to 18 XML Views Converter")
    print("=" * 70)
    print()
    print("⚠️  LƯU Ý: Script này chỉ đánh dấu các file cần convert thủ công")
    print("Bạn cần tự convert attrs sang syntax mới theo hướng dẫn")
    print()
    
    # Find all XML files in ngsd/
    xml_files = []
    for root, dirs, files in os.walk('ngsd'):
        for file in files:
            if file.endswith('.xml'):
                xml_files.append(os.path.join(root, file))
    
    print(f"Found {len(xml_files)} XML files")
    print()
    
    stats = {'converted': 0, 'manual': 0, 'unchanged': 0, 'error': 0}
    
    files_need_manual = []
    
    for filepath in xml_files:
        result = process_file(filepath)
        stats[result] += 1
        if result == 'manual':
            files_need_manual.append(filepath)
    
    print()
    print("=" * 70)
    print("Summary:")
    print(f"  Converted: {stats['converted']}")
    print(f"  Need manual review: {stats['manual']}")
    print(f"  Unchanged: {stats['unchanged']}")
    print(f"  Errors: {stats['error']}")
    print()
    
    if files_need_manual:
        print("Files needing manual conversion (sample - first 20):")
        for f in files_need_manual[:20]:
            print(f"  - {f}")
        if len(files_need_manual) > 20:
            print(f"  ... and {len(files_need_manual) - 20} more")
    
    print()
    print("Để convert XML, xem hướng dẫn trong ODOO_18_MIGRATION_GUIDE.md")

if __name__ == '__main__':
    main()
