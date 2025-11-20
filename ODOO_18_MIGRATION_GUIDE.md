# Hướng dẫn Migration từ Odoo 15 lên Odoo 18

## Các thay đổi quan trọng cần lưu ý

### 1. Import statements - QUAN TRỌNG NHẤT
**❌ SAI:**
```python
from odoo import *
```

**✅ ĐÚNG:**
```python
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError
```

**Lý do:** `from odoo import *` là anti-pattern, gây khó khăn trong debug và có thể gây xung đột namespace.

---

### 2. API Decorators

#### 2.1. @api.multi và @api.one - ĐÃ BỊ XÓA
**❌ SAI:**
```python
@api.multi
def some_method(self):
    for record in self:
        pass

@api.one
def some_method(self):
    pass
```

**✅ ĐÚNG:**
```python
def some_method(self):
    for record in self:
        pass
```

**Lý do:** Từ Odoo 13+, tất cả methods mặc định hoạt động như `@api.multi`. Decorator này đã bị loại bỏ.

#### 2.2. @api.returns - HẠN CHẾ SỬ DỤNG
**❌ SAI (trong hầu hết trường hợp):**
```python
@api.returns('self', lambda value: value.id)
def some_method(self):
    return self
```

**✅ ĐÚNG:**
```python
def some_method(self):
    return self
```

**Lý do:** Odoo 18 tự động xử lý return values. Chỉ cần `@api.returns` trong các trường hợp đặc biệt.

#### 2.3. @api.cr_uid_* decorators - ĐÃ BỊ XÓA
Tất cả decorators kiểu `@api.cr_uid_ids_context`, `@api.cr_uid_context` đều đã bị xóa.

---

### 3. Views - attrs syntax

#### 3.1. invisible, readonly, required
**❌ SAI (Odoo 15):**
```xml
<field name="field_name" attrs="{'invisible': [('state', '=', 'done')]}"/>
<field name="field_name" attrs="{'readonly': [('state', '=', 'done')]}"/>
<field name="field_name" attrs="{'required': [('state', '=', 'draft')]}"/>
```

**✅ ĐÚNG (Odoo 18):**
```xml
<field name="field_name" invisible="state == 'done'"/>
<field name="field_name" readonly="state == 'done'"/>
<field name="field_name" required="state == 'draft'"/>
```

#### 3.2. Kết hợp nhiều điều kiện
**❌ SAI:**
```xml
attrs="{'invisible': ['|', ('state', '=', 'done'), ('active', '=', False)]}"
```

**✅ ĐÚNG:**
```xml
invisible="state == 'done' or not active"
```

**❌ SAI:**
```xml
attrs="{'invisible': [('state', '=', 'done'), ('active', '=', False)]}"
```

**✅ ĐÚNG:**
```xml
invisible="state == 'done' and not active"
```

#### 3.3. column_invisible
**❌ SAI:**
```xml
<field name="field_name" attrs="{'column_invisible': [('parent.type', '!=', 'car')]}"/>
```

**✅ ĐÚNG:**
```xml
<field name="field_name" column_invisible="parent.type != 'car'"/>
```

---

### 4. Exception Handling

#### 4.1. Raise ValidationError
**❌ SAI:**
```python
# Tạo ValidationError nhưng không raise
ValidationError("Message").with_traceback(None)
```

**✅ ĐÚNG:**
```python
# Nếu muốn raise
raise ValidationError("Message")

# Nếu muốn log lỗi nhưng không raise
import logging
_logger = logging.getLogger(__name__)
_logger.warning("Message")
self.env.user.notify_warning(message="Message")
```

#### 4.2. Try-except trong @api.constrains
**⚠️ LƯU Ý:** Nếu bạn catch exception trong `@api.constrains` mà không re-raise, transaction sẽ KHÔNG bị rollback.

**✅ ĐÚNG - Pattern xử lý email trong constraint:**
```python
@api.constrains("stage_id")
def _constrains_stage_id(self):
    for r in self:
        # Validation logic
        if condition:
            raise ValidationError("Error message")
        
        # Business logic (send email, etc.)
        if need_send_email:
            try:
                r._sent_email()
            except Exception as e:
                _logger.warning(f"Cannot send email: {e}")
                # Không raise lại - cho phép transaction tiếp tục
```

---

### 5. Context và Active Test

**✅ VẪN ĐÚNG - Không cần thay đổi:**
```python
# Pattern này vẫn hoạt động tốt trong Odoo 18
records = self.env['model.name'].with_context(active_test=False).search(domain)
```

---

### 6. Fields

#### 6.1. Selection field - Không còn tuple of tuples
**❌ SAI:**
```python
state = fields.Selection((
    ('draft', 'Draft'),
    ('done', 'Done'),
))
```

**✅ ĐÚNG:**
```python
state = fields.Selection([
    ('draft', 'Draft'),
    ('done', 'Done'),
], string='State')
```

---

### 7. Manifest File (__manifest__.py)

#### 7.1. Version
**❌ SAI:**
```python
'version': '15.0.1.0.0'
```

**✅ ĐÚNG:**
```python
'version': '18.0.1.0.0'
```

#### 7.2. Dependencies - Kiểm tra modules đã thay đổi
Một số modules đã được đổi tên hoặc merge:
- `website_sale` có thể đã thay đổi
- `website_form` đã được tích hợp vào `website`
- Kiểm tra từng dependency

---

### 8. ORM Methods

#### 8.1. write() và create() trả về gì?
**✅ KHÔNG THAY ĐỔI:**
```python
# create() trả về recordset
record = self.env['model'].create(vals)

# write() trả về True
result = record.write(vals)  # True
```

#### 8.2. search() với limit
**✅ KHÔNG THAY ĐỔI:**
```python
records = self.env['model'].search(domain, limit=1, order='id desc')
```

---

### 9. JavaScript/CSS Assets

#### 9.1. Assets bundles
**❌ SAI (có thể):**
```xml
<template id="assets_backend" inherit_id="web.assets_backend">
```

**⚠️ KIỂM TRA:** Odoo 18 có thể đã thay đổi cách organize assets. Cần kiểm tra documentation.

---

### 10. Quy trình Migration thực tế

1. **Sửa imports trước:**
   - Thay tất cả `from odoo import *` thành imports cụ thể
   
2. **Remove decorators cũ:**
   - Xóa `@api.multi`, `@api.one`
   - Xóa `@api.returns` (trừ trường hợp đặc biệt)
   
3. **Update views:**
   - Convert `attrs` sang syntax mới
   - Tìm kiếm: `attrs=.*invisible|attrs=.*readonly|attrs=.*required`
   
4. **Test từng module:**
   - Start Odoo và xem log
   - Test các chức năng chính
   
5. **Fix errors:**
   - Đọc error log carefully
   - Fix từng lỗi một

---

### 11. Tools hỗ trợ Migration

#### 11.1. Tìm kiếm các patterns cần fix
```bash
# Tìm from odoo import *
grep -r "from odoo import \*" --include="*.py"

# Tìm @api.multi/@api.one
grep -r "@api\.multi\|@api\.one" --include="*.py"

# Tìm attrs trong XML
grep -r "attrs=" --include="*.xml"

# Tìm @api.returns
grep -r "@api\.returns" --include="*.py"
```

---

### 12. Checklist Migration

- [ ] Sửa tất cả `from odoo import *`
- [ ] Xóa `@api.multi` và `@api.one`
- [ ] Xóa `@api.returns` không cần thiết
- [ ] Convert `attrs` trong XML views
- [ ] Update version trong `__manifest__.py`
- [ ] Kiểm tra dependencies
- [ ] Test chức năng chính
- [ ] Xem lại exception handling
- [ ] Check performance

---

## Ví dụ Migration một file hoàn chỉnh

### Before (Odoo 15):
```python
from odoo import *

class MyModel(models.Model):
    _name = 'my.model'
    
    state = fields.Selection((
        ('draft', 'Draft'),
        ('done', 'Done'),
    ))
    
    @api.multi
    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'done'})
    
    @api.one
    def action_cancel(self):
        self.state = 'draft'
```

### After (Odoo 18):
```python
from odoo import models, fields, api

class MyModel(models.Model):
    _name = 'my.model'
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'),
    ], default='draft')
    
    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'done'})
    
    def action_cancel(self):
        for rec in self:
            rec.state = 'draft'
```

### XML Before:
```xml
<field name="name" attrs="{'readonly': [('state', '=', 'done')]}"/>
<field name="amount" attrs="{'invisible': [('state', '!=', 'done')]}"/>
```

### XML After:
```xml
<field name="name" readonly="state == 'done'"/>
<field name="amount" invisible="state != 'done'"/>
```

---

## Tài nguyên tham khảo

- Odoo Official Documentation: https://www.odoo.com/documentation/18.0/
- Odoo GitHub: https://github.com/odoo/odoo
- Migration Guide: Tìm trong docs của từng phiên bản

