#!/usr/bin/env python3
"""
Script hỗ trợ convert XML attrs syntax từ Odoo 15 sang Odoo 18
Xử lý các pattern phổ biến
"""

import re
import sys

# Các pattern để convert
CONVERSION_PATTERNS = {
    # Simple invisible
    r'''attrs=["'](\{[^}]*'invisible':\s*\[\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)\][^}]*\})["']''': 
        lambda m: convert_simple_condition('invisible', m.group(2), m.group(3), m.group(4)),
    
    # Simple readonly
    r'''attrs=["'](\{[^}]*'readonly':\s*\[\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)\][^}]*\})["']''':
        lambda m: convert_simple_condition('readonly', m.group(2), m.group(3), m.group(4)),
    
    # Simple required
    r'''attrs=["'](\{[^}]*'required':\s*\[\('([^']+)',\s*'([^']+)',\s*'([^']+)'\)\][^}]*\})["']''':
        lambda m: convert_simple_condition('required', m.group(2), m.group(3), m.group(4)),
}

def convert_simple_condition(attr_type, field, operator, value):
    """Convert simple condition like ('state', '=', 'done')"""
    # Remove quotes from value if it's a string
    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]
        value = f"'{value}'"
    
    # Convert operator
    op_map = {
        '=': '==',
        '!=': '!=',
        'in': 'in',
        'not in': 'not in',
    }
    
    python_op = op_map.get(operator, operator)
    
    # Special case for False/True
    if value in ['False', 'True']:
        if operator == '=':
            if value == 'False':
                return f'{attr_type}="not {field}"'
            else:
                return f'{attr_type}="{field}"'
        elif operator == '!=':
            if value == 'False':
                return f'{attr_type}="{field}"'
            else:
                return f'{attr_type}="not {field}"'
    
    return f'{attr_type}="{field} {python_op} {value}"'

def show_examples():
    """Show conversion examples"""
    examples = [
        # Example 1
        {
            'before': '''<field name="name" attrs="{'invisible': [('state', '=', 'done')]}"/>''',
            'after': '''<field name="name" invisible="state == 'done'"/>''',
        },
        # Example 2
        {
            'before': '''<field name="amount" attrs="{'readonly': [('state', '!=', 'draft')]}"/>''',
            'after': '''<field name="amount" readonly="state != 'draft'"/>''',
        },
        # Example 3
        {
            'before': '''<field name="description" attrs="{'required': [('type', '=', 'manual')]}"/>''',
            'after': '''<field name="description" required="type == 'manual'"/>''',
        },
        # Example 4 - Boolean
        {
            'before': '''<field name="note" attrs="{'invisible': [('active', '=', False)]}"/>''',
            'after': '''<field name="note" invisible="not active"/>''',
        },
        # Example 5 - OR condition
        {
            'before': '''<field name="x" attrs="{'invisible': ['|', ('a', '=', 'b'), ('c', '=', 'd')]}"/>''',
            'after': '''<field name="x" invisible="a == 'b' or c == 'd'"/>''',
        },
        # Example 6 - AND condition
        {
            'before': '''<field name="y" attrs="{'invisible': [('a', '=', 'b'), ('c', '=', 'd')]}"/>''',
            'after': '''<field name="y" invisible="a == 'b' and c == 'd'"/>''',
        },
        # Example 7 - column_invisible
        {
            'before': '''<field name="col" attrs="{'column_invisible': [('parent.type', '!=', 'car')]}"/>''',
            'after': '''<field name="col" column_invisible="parent.type != 'car'"/>''',
        },
    ]
    
    print("=" * 80)
    print("VÍ DỤ CONVERSION TỪ ODOO 15 SANG ODOO 18")
    print("=" * 80)
    print()
    
    for i, example in enumerate(examples, 1):
        print(f"Ví dụ {i}:")
        print(f"  BEFORE: {example['before']}")
        print(f"  AFTER:  {example['after']}")
        print()
    
    print("=" * 80)
    print()

def show_common_patterns():
    """Show common patterns that need conversion"""
    print("=" * 80)
    print("CÁC PATTERN PHỔ BIẾN CẦN CONVERT")
    print("=" * 80)
    print()
    
    patterns = [
        {
            'name': 'Simple invisible',
            'pattern': '''attrs="{'invisible': [('field', 'op', 'value')]}"''',
            'becomes': '''invisible="field op value"''',
        },
        {
            'name': 'Boolean False',
            'pattern': '''attrs="{'invisible': [('active', '=', False)]}"''',
            'becomes': '''invisible="not active"''',
        },
        {
            'name': 'Boolean True',
            'pattern': '''attrs="{'invisible': [('active', '=', True)]}"''',
            'becomes': '''invisible="active"''',
        },
        {
            'name': 'OR condition',
            'pattern': '''attrs="{'invisible': ['|', ('a', '=', 'x'), ('b', '=', 'y')]}"''',
            'becomes': '''invisible="a == 'x' or b == 'y'"''',
        },
        {
            'name': 'AND condition (default)',
            'pattern': '''attrs="{'invisible': [('a', '=', 'x'), ('b', '=', 'y')]}"''',
            'becomes': '''invisible="a == 'x' and b == 'y'"''',
        },
        {
            'name': 'Multiple attrs',
            'pattern': '''attrs="{'invisible': [...], 'readonly': [...]}"''',
            'becomes': '''invisible="..." readonly="..."''' + ' (tách thành 2 attributes)',
        },
    ]
    
    for pattern in patterns:
        print(f"📌 {pattern['name']}:")
        print(f"   Pattern:  {pattern['pattern']}")
        print(f"   Becomes:  {pattern['becomes']}")
        print()
    
    print("=" * 80)
    print()

def show_regex_help():
    """Show useful regex for find & replace"""
    print("=" * 80)
    print("REGEX HỮU ÍCH CHO FIND & REPLACE (VS CODE)")
    print("=" * 80)
    print()
    
    regexes = [
        {
            'find': r"attrs=\"\{'invisible': \[\('([^']+)', '=', False\)\]\}\"",
            'replace': r'invisible="not $1"',
            'description': 'Convert invisible with False value',
        },
        {
            'find': r"attrs=\"\{'invisible': \[\('([^']+)', '=', True\)\]\}\"",
            'replace': r'invisible="$1"',
            'description': 'Convert invisible with True value',
        },
        {
            'find': r"attrs=\"\{'invisible': \[\('([^']+)', '=', '([^']+)'\)\]\}\"",
            'replace': r"invisible=\"$1 == '$2'\"",
            'description': 'Convert simple invisible with = operator',
        },
        {
            'find': r"attrs=\"\{'invisible': \[\('([^']+)', '!=', '([^']+)'\)\]\}\"",
            'replace': r"invisible=\"$1 != '$2'\"",
            'description': 'Convert simple invisible with != operator',
        },
    ]
    
    print("Cách sử dụng trong VS Code:")
    print("1. Mở Find & Replace (Ctrl+H)")
    print("2. Bật 'Use Regular Expression' (.*)")
    print("3. Copy regex từ 'Find' vào ô tìm kiếm")
    print("4. Copy từ 'Replace' vào ô thay thế")
    print("5. Test trên một file trước, sau đó Replace All")
    print()
    
    for i, regex in enumerate(regexes, 1):
        print(f"{i}. {regex['description']}")
        print(f"   Find:    {regex['find']}")
        print(f"   Replace: {regex['replace']}")
        print()
    
    print("⚠️  LƯU Ý: Luôn backup hoặc commit code trước khi replace!")
    print()
    print("=" * 80)
    print()

def main():
    """Main function"""
    print()
    show_examples()
    show_common_patterns()
    show_regex_help()
    
    print("📚 Để xem hướng dẫn chi tiết, đọc file: ODOO_18_MIGRATION_GUIDE.md")
    print()

if __name__ == '__main__':
    main()
