# CHANGES.md - HDI Attendance Module Refactoring

## Tổng quan

Module đã được chuyển đổi từ **standalone model** sang **inherit hr.attendance** để phù hợp với architecture của Odoo 18 và ngsc/ngsd.

## Thay đổi chính

### 1. Architecture Changes

**Trước đây:**
```python
class HdiAttendance(models.Model):
    _name = 'hdi.attendance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    employee_id = fields.Many2one('hr.employee')
    check_in = fields.Datetime()
    check_out = fields.Datetime()
    # ... tất cả fields được define lại
```

**Bây giờ:**
```python
class HrAttendance(models.Model):
    _inherit = 'hr.attendance'
    
    # Chỉ thêm HDI-specific fields
    work_location_id = fields.Many2one('hdi.work.location')
    checkin_latitude = fields.Float()
    checkin_longitude = fields.Float()
    checkout_latitude = fields.Float()
    checkout_longitude = fields.Float()
    color = fields.Integer(compute='_compute_color')
    warning_message = fields.Text(compute='_compute_color')
```

**Lợi ích:**
- Tận dụng toàn bộ logic của hr_attendance (validation, sequence, workflow)
- Tương thích với các module khác extend hr_attendance
- Giảm code duplication
- Dễ maintain và upgrade

### 2. Dependencies Changes

**__manifest__.py**

Trước:
```python
'depends': ['base', 'hr', 'mail']
```

Sau:
```python
'depends': ['hr_attendance', 'mail']
```

Thêm assets section:
```python
'assets': {
    'web.assets_backend': [
        'hdi_attendance_clean/static/src/js/**/*',
        'hdi_attendance_clean/static/src/xml/**/*',
    ],
}
```

### 3. Model References Updates

Tất cả references từ `hdi.attendance` → `hr.attendance`:

**Files affected:**
- `views/attendance_views.xml`: 15 occurrences
- `views/menu_views.xml`: 1 occurrence
- `security/ir.model.access.csv`: 2 lines
- `models/employee.py`: 2 methods

### 4. Removed Files/Sections

**Removed:**
- `data/sequence_data.xml`: hr.attendance có sequence riêng
- Validation methods trong attendance.py:
  - `_check_validity()`: hr.attendance có sẵn
  - `action_checkout()`: hr.attendance có sẵn

### 5. New JavaScript Implementation

**Created:** `static/src/js/hdi_attendance.js`

```javascript
/** @odoo-module **/
import { MyAttendances } from "@hr_attendance/components/my_attendances/my_attendances";
import { patch } from "@web/core/utils/patch";

patch(MyAttendances.prototype, {
    async willStart() {
        await super.willStart(...arguments);
        // Load working locations
    },
    
    async _manual_attendance(next_action) {
        // Get GPS coordinates
        // Pass to backend via context
        return super._manual_attendance(...arguments);
    }
});
```

**Created:** `static/src/xml/hdi_attendance.xml`

```xml
<templates xml:space="preserve">
    <t t-name="hdi_attendance_clean.MyAttendances" t-inherit="hr_attendance.MyAttendances" t-inherit-mode="extension">
        <xpath expr="//div[@class='o_hr_attendance_kiosk_mode']//h4[@class='mt0']" position="before">
            <!-- Location dropdown -->
        </xpath>
    </t>
</templates>
```

### 6. Employee Model Extensions

**models/employee.py - Added methods:**

```python
def get_working_locations(self):
    """Return list of locations for dropdown"""
    # Format: [{'id': 1, 'name': 'Office', 'default_value': 1}]

def get_en_checked_diff_ok(self):
    """Check if employee can checkout at different location"""
    
def attendance_manual(self, next_action, entered_pin=None):
    """Override to capture GPS and location from context"""
```

### 7. Security Updates

**ir.model.access.csv**

Trước:
```csv
access_hdi_attendance_user,access.hdi.attendance.user,model_hdi_attendance,...
```

Sau:
```csv
access_hr_attendance_user,access.hr.attendance.user,hr_attendance.model_hr_attendance,...
```

## Migration Path

### Nếu đã cài hdi_attendance_clean version cũ:

1. **Backup database:**
```bash
pg_dump hdi_odoo > backup_before_migration.sql
```

2. **Uninstall old module:**
```bash
python odoo-bin -d hdi_odoo -u hdi_attendance_clean --stop-after-init
# Hoặc qua UI: Apps > HDI Attendance > Uninstall
```

3. **Migrate data (if needed):**
```sql
-- Copy attendance records from hdi.attendance to hr.attendance
INSERT INTO hr_attendance (
    employee_id, check_in, check_out, worked_hours,
    checkin_latitude, checkin_longitude, 
    checkout_latitude, checkout_longitude,
    work_location_id, create_date, write_date, create_uid, write_uid
)
SELECT 
    employee_id, check_in, check_out, worked_hours,
    checkin_latitude, checkin_longitude,
    checkout_latitude, checkout_longitude,
    work_location_id, create_date, write_date, create_uid, write_uid
FROM hdi_attendance;

-- Drop old table
DROP TABLE hdi_attendance CASCADE;
```

4. **Install new module:**
```bash
python odoo-bin -d hdi_odoo -i hdi_attendance_clean --stop-after-init
```

### Nếu fresh installation:

Chỉ cần install trực tiếp:
```bash
python odoo-bin -d hdi_odoo -i hdi_attendance_clean --stop-after-init
```

## Testing Checklist

- [ ] Module installs without errors
- [ ] Work locations can be created
- [ ] MyAttendances widget shows location dropdown
- [ ] Check-in captures GPS coordinates and location
- [ ] Check-out captures GPS coordinates
- [ ] Calendar view shows color coding
- [ ] List view decorations work (red/green)
- [ ] Form view shows GPS coordinates in notebook
- [ ] Manager can view all attendances
- [ ] Access rights work correctly
- [ ] Kiosk mode works with location selector

## Known Issues & Limitations

1. **GPS Tracking**
   - Chỉ hoạt động trên HTTPS hoặc localhost
   - Requires browser permission
   - May not work trên các browser cũ

2. **Location Dropdown**
   - Load tất cả locations - có thể chậm nếu có quá nhiều
   - Consider pagination hoặc search nếu >100 locations

3. **Calendar Color**
   - Computed field - không store
   - Có thể chậm với dataset lớn
   - Consider store=True với cron job update

## Rollback Plan

Nếu gặp vấn đề:

1. **Restore database:**
```bash
dropdb hdi_odoo
createdb hdi_odoo
psql hdi_odoo < backup_before_migration.sql
```

2. **Checkout old version:**
```bash
git checkout <old-commit-hash>
```

3. **Restart Odoo:**
```bash
python odoo-bin -d hdi_odoo
```

## Next Steps

1. **Test thoroughly** trên development environment
2. **Performance testing** với large dataset
3. **User acceptance testing** với actual users
4. **Documentation** cho end users
5. **Training** cho managers và HR team

## Contact

For issues or questions, contact: HDI Team
