# HDI SHIPPING - QUẢN LÝ ĐƠN HÀNG GỬI

## 📋 Tổng quan

Module **hdi_shipping** cung cấp chức năng quản lý đơn hàng vận chuyển hoàn chỉnh cho Odoo 18, bao gồm:
- **Tạo phiếu gửi hàng**: Tạo đơn hàng mới với thông tin người gửi, người nhận, hàng hóa, dịch vụ
- **Quản lý đơn hàng gửi**: Theo dõi, tìm kiếm, lọc, in và xử lý trạng thái đơn hàng

## 🎯 Mục đích chức năng

### 1. Tạo phiếu gửi hàng (Đã có sẵn)
Cho phép khách hàng tạo đơn hàng mới với đầy đủ thông tin.

### 2. Quản lý đơn hàng gửi (Mới triển khai)
Chức năng Quản lý đơn hàng gửi cho phép khách hàng:
- ✅ Theo dõi tất cả các đơn hàng đã tạo
- ✅ Tìm kiếm – lọc – xem – in – xử lý trạng thái theo từng đơn
- ✅ Quản lý toàn bộ lịch sử gửi hàng theo từng địa chỉ gửi
- ✅ In đơn hàng (từng đơn hoặc nhiều đơn cùng lúc)
- ✅ Điều chỉnh trạng thái phiếu gửi theo workflow

## 👥 Đối tượng sử dụng

- Chủ shop, cửa hàng
- Nhân viên kho của khách (nếu cấp quyền)
- Nhân viên tạo đơn hàng từ Web khách hàng

## 🔄 Workflow trạng thái đơn hàng

```
┌─────────────┐
│ Đơn nháp    │ ──[Duyệt đơn]──▶ ┌──────────────────┐
│  (Draft)    │                   │ Chờ lấy hàng     │
└─────────────┘                   │ (Waiting Pickup) │
      │                           └──────────────────┘
      │                                     │
  [Hủy đơn]                         [FUTA lấy hàng]
      │                                     │
      ▼                                     ▼
┌─────────────┐                   ┌──────────────────┐
│  Đã hủy     │                   │ Đang vận chuyển  │
│ (Cancelled) │                   │  (In Transit)    │
└─────────────┘                   └──────────────────┘
                                           │
                        ┌──────────────────┼──────────────────┐
                        │                  │                  │
                 [Giao thành công]  [Giao thất bại]  [Khách yêu cầu]
                        │                  │                  │
                        ▼                  ▼                  ▼
                  ┌──────────┐    ┌─────────────────┐  ┌──────────┐
                  │ Đã giao  │    │ Chờ duyệt hoàn  │  │ Đã hoàn  │
                  │Delivered │    │Pending Return   │  │ Returned │
                  └──────────┘    └─────────────────┘  └──────────┘
                                           │
                                    ┌──────┴──────┐
                                    │             │
                              [Duyệt hoàn]  [Phát lại]
                                    │             │
                                    ▼             ▼
                              ┌──────────┐  ┌──────────────┐
                              │ Đã hoàn  │  │ Đang vận     │
                              │ Returned │  │ chuyển lại   │
                              └──────────┘  └──────────────┘
```

## 📊 Các trạng thái đơn hàng

| Trạng thái | Mã | Mô tả | Hành động được phép |
|------------|-----|-------|---------------------|
| **Đơn nháp** | `draft` | Đơn mới tạo, chưa được FUTA nhận | • Duyệt đơn<br>• Hủy đơn<br>• Chỉnh sửa nội dung |
| **Chờ lấy hàng** | `waiting_pickup` | Đã duyệt, chờ FUTA đến lấy hàng | • Hủy đơn<br>• FUTA xác nhận đã lấy hàng |
| **Đang vận chuyển** | `in_transit` | FUTA đã lấy hàng, đang giao | • Xác nhận đã giao<br>• Yêu cầu duyệt hoàn |
| **Chờ duyệt hoàn** | `pending_return_approval` | Giao thất bại, chờ khách quyết định | • Duyệt hoàn<br>• Phát lại |
| **Đã giao** | `delivered` | Giao hàng thành công | _Kết thúc_ |
| **Đã hoàn** | `returned` | Hàng đã trả về người gửi | _Kết thúc_ |
| **Đã hủy** | `cancelled` | Đơn đã bị hủy | _Kết thúc_ |

## 🔍 Tính năng tìm kiếm và lọc

### Bộ lọc cơ bản:
- **Địa chỉ gửi hàng**: Chọn kho/địa chỉ gửi mà khách muốn xem đơn
- **Khoảng thời gian**: Lấy danh sách đơn theo ngày tạo (Hôm nay / Tuần này / Tháng này)
- **SĐT người nhận**: Tìm nhanh theo số điện thoại người nhận

### Bộ lọc theo trạng thái:
- Đơn nháp
- Chờ lấy hàng
- Đang vận chuyển
- Chờ duyệt hoàn
- Đã giao
- Đã hoàn
- Đã hủy

### Nhóm theo (Group by):
- Trạng thái
- Địa chỉ gửi
- Dịch vụ vận chuyển
- Ngày tạo

## 📝 Danh sách đơn hàng

Thông tin hiển thị trên danh sách:
- ✅ Mã phiếu gửi (mã đơn)
- ✅ Tên người nhận
- ✅ SĐT người nhận
- ✅ Địa chỉ nhận
- ✅ Ngày tạo
- ✅ Dịch vụ vận chuyển
- ✅ COD (nếu có)
- ✅ Người thanh toán cước (người gửi / người nhận)
- ✅ Trạng thái đơn hàng
- ✅ Cước phí

## 🖨️ In đơn hàng

### Cách 1: In từng đơn
- Mở form đơn hàng → Nhấn nút "In đơn"
- Hệ thống xuất PDF cho đơn hàng đó

### Cách 2: In nhiều đơn cùng lúc
1. Vào màn "Quản lý đơn hàng gửi"
2. Tích chọn nhiều dòng đơn hàng
3. Nhấn nút "In đơn đã chọn"
4. Chọn kiểu in (từng đơn riêng / gộp nhiều đơn)
5. Nhấn "In đơn"
6. Hệ thống xuất PDF gộp tất cả các đơn đã chọn

### Nội dung phiếu in gồm:
- Tiêu đề: **PHIẾU GỬI HÀNG**
- Thông tin đơn hàng: Mã đơn, Ngày tạo, Trạng thái, Dịch vụ
- Thông tin người gửi: Tên, SĐT, Địa chỉ
- Thông tin người nhận: Tên, SĐT, Địa chỉ, Khung giờ nhận
- Bảng hàng hóa: STT, Tên hàng, Loại, Số lượng, Trọng lượng, Giá trị
- Thông tin cước phí: Cước phí, COD, Người thanh toán, Tổng cước
- Chữ ký: Người gửi, Người nhận

## ⚙️ Quy tắc nghiệp vụ quan trọng

### 1. Duyệt đơn
- ❗ **Chỉ đơn Draft mới được "Duyệt đơn"**
- Sau khi duyệt → chuyển sang trạng thái "Chờ lấy hàng"
- Ghi nhận thông tin: Người duyệt, Ngày giờ duyệt
- **Đơn đã duyệt → KHÔNG được chỉnh nội dung nữa** (người nhận, hàng hóa, COD...)

### 2. Hủy đơn
- ❗ **Hủy đơn chỉ được thực hiện ở trạng thái:**
  - Draft (Đơn nháp)
  - Waiting Pickup (Chờ lấy hàng)
- Sau khi hủy → không thể khôi phục

### 3. Chờ duyệt hoàn
- Khi đơn ở trạng thái "Chờ duyệt hoàn", khách có 2 lựa chọn:
  - **Duyệt hoàn**: Đơn sẽ trả về cho người gửi → trạng thái "Đã hoàn"
  - **Phát tiếp**: Yêu cầu giao lại cho người nhận → trạng thái "Đang vận chuyển"

### 4. Ghi log trạng thái
- ✅ Mọi thay đổi trạng thái đều được ghi log tự động:
  - Ai làm
  - Khi nào
  - Từ trạng thái nào → sang trạng thái nào
- Xem log tại tab "Lịch sử trạng thái" trong form đơn hàng

### 5. Phân quyền
- ✅ Chỉ chủ tài khoản hoặc nhân viên được phân quyền mới được xem địa chỉ gửi tương ứng
- User thường: Đọc, Tạo, Sửa (không xóa)
- Stock Manager: Đọc, Tạo, Sửa, Xóa
- Admin: Full quyền

## 📁 Cấu trúc module

```
hdi_shipping/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── shipping_order.py              # Model chính
│   ├── shipping_order_state_log.py    # Log thay đổi trạng thái
│   ├── sender_address.py              # Địa chỉ gửi hàng
│   ├── shipping_service.py            # Dịch vụ vận chuyển
│   └── shipment_item.py               # Chi tiết hàng hóa
├── wizards/
│   ├── __init__.py
│   ├── shipping_order_print_wizard.py           # Wizard in đơn
│   └── shipping_order_print_wizard_views.xml    # View wizard
├── views/
│   ├── shipping_order_views.xml       # View quản lý đơn hàng (NEW)
│   ├── sender_address_views.xml
│   ├── shipping_service_views.xml
│   └── menu.xml                       # Menu (UPDATED)
├── reports/
│   └── shipping_order_report.xml      # Template in đơn (NEW)
├── data/
│   └── sequence_data.xml
└── security/
    └── ir.model.access.csv            # Phân quyền (UPDATED)
```

## 🔧 Models & Fields

### 1. shipping.order (Đã cập nhật)

**Thêm mới:**
- `approved_date`: Ngày duyệt đơn
- `approved_by`: Người duyệt đơn
- `currency_id`: Tiền tệ (VNĐ)
- `state_log_ids`: One2many → Lịch sử trạng thái
- `can_edit`: Computed field - Có thể chỉnh sửa hay không
- `is_draft`, `is_waiting_pickup`, `is_pending_return`: Computed fields

**Trạng thái (đã cập nhật):**
```python
state = fields.Selection([
    ('draft', 'Đơn nháp'),
    ('waiting_pickup', 'Chờ lấy hàng'),
    ('in_transit', 'Đang vận chuyển'),
    ('pending_return_approval', 'Chờ duyệt hoàn'),
    ('delivered', 'Đã giao'),
    ('returned', 'Đã hoàn'),
    ('cancelled', 'Đã hủy'),
])
```

**Methods:**
- `action_approve()`: Duyệt đơn (draft → waiting_pickup)
- `action_cancel()`: Hủy đơn
- `action_approve_return()`: Duyệt hoàn (pending_return_approval → returned)
- `action_redeliver()`: Phát lại (pending_return_approval → in_transit)
- `action_set_in_transit()`: Đã lấy hàng (waiting_pickup → in_transit)
- `action_set_delivered()`: Đã giao (in_transit → delivered)
- `action_request_return_approval()`: Yêu cầu duyệt hoàn (in_transit → pending_return_approval)
- `action_print_order()`: In đơn hàng
- `_log_state_change()`: Ghi log thay đổi trạng thái

### 2. shipping.order.state.log (Mới)

```python
_name = 'shipping.order.state.log'
```

**Fields:**
- `order_id`: Many2one → shipping.order
- `user_id`: Người thực hiện
- `old_state`: Trạng thái cũ
- `new_state`: Trạng thái mới
- `change_date`: Thời gian thay đổi
- `note`: Ghi chú
- `old_state_display`, `new_state_display`: Computed fields

### 3. shipping.order.print.wizard (Mới)

```python
_name = 'shipping.order.print.wizard'
```

**Fields:**
- `order_ids`: Many2many → Các đơn hàng cần in
- `order_count`: Số lượng đơn
- `print_type`: Kiểu in (single/batch)

**Methods:**
- `action_print()`: In đơn hàng
- `action_print_and_close()`: In và đóng wizard

## 📱 Menu Structure

```
Vận chuyển HDI
├── Tạo đơn hàng (action_shipping_order_create)
├── Quản lý đơn hàng gửi (action_shipping_order_manage) ⭐ MỚI
└── Cấu hình
    ├── Dịch vụ vận chuyển
    └── Địa chỉ gửi hàng
```

## 🔐 Security (ir.model.access.csv)

| Model | User | Manager |
|-------|------|---------|
| shipping.order | RWC | RWCD |
| shipping.order.state.log | R | RWCD |
| sender.address | RWC | RWCD |
| shipping.service | R | RWCD |
| shipment.item | RWC | - |
| shipping.order.print.wizard | RWCD | RWCD |

**Chú thích:** R=Read, W=Write, C=Create, D=Delete

## 🎨 UI/UX

### Tree View
- Màu sắc theo trạng thái:
  - Xanh dương (info): Đơn nháp
  - Xanh lam (primary): Chờ lấy hàng
  - Vàng (warning): Chờ duyệt hoàn
  - Xanh lá (success): Đã giao
  - Xám (muted): Đã hủy, Đã hoàn

- Button "In đơn đã chọn" trên header của list view

### Form View
- Các nút action hiển thị tùy theo trạng thái
- Readonly fields khi đơn đã duyệt (`can_edit = False`)
- Tab "Lịch sử trạng thái" hiển thị tất cả log
- Chatter để theo dõi comments và activities

### Search View
- Quick filters: Draft, Waiting Pickup, In Transit, Pending Return, Delivered, Returned, Cancelled
- Date filters: Hôm nay, Tuần này, Tháng này
- Group by: Trạng thái, Địa chỉ gửi, Dịch vụ, Ngày tạo

## 📋 Hướng dẫn sử dụng

### 1. Tạo đơn hàng mới
1. Vào menu **Vận chuyển HDI → Tạo đơn hàng**
2. Điền thông tin người gửi, người nhận
3. Thêm hàng hóa
4. Chọn dịch vụ vận chuyển
5. Nhấn **Lưu**
6. Đơn ở trạng thái "Đơn nháp"

### 2. Duyệt đơn hàng
1. Mở đơn hàng ở trạng thái "Đơn nháp"
2. Kiểm tra thông tin
3. Nhấn nút **"Duyệt đơn"**
4. Xác nhận → Đơn chuyển sang "Chờ lấy hàng"
5. Sau khi duyệt, không thể sửa nội dung

### 3. Quản lý đơn hàng
1. Vào menu **Vận chuyển HDI → Quản lý đơn hàng gửi**
2. Sử dụng bộ lọc để tìm đơn:
   - Chọn địa chỉ gửi
   - Chọn khoảng thời gian
   - Nhập SĐT người nhận
3. Xem danh sách đơn hàng
4. Click vào đơn để xem chi tiết

### 4. In đơn hàng

**Cách 1: In từng đơn**
1. Mở form đơn hàng
2. Nhấn nút **"In đơn"** trên header
3. PDF sẽ được tải xuống

**Cách 2: In nhiều đơn**
1. Vào **Quản lý đơn hàng gửi**
2. Tích chọn các đơn cần in
3. Nhấn **"In đơn đã chọn"**
4. Wizard hiện ra:
   - Xem số lượng đơn đã chọn
   - Chọn kiểu in
5. Nhấn **"In đơn"**
6. PDF gộp sẽ được tải xuống

### 5. Xử lý đơn hoàn
Khi nhận thông báo đơn "Chờ duyệt hoàn":
1. Mở đơn hàng
2. Xem lý do giao thất bại (nếu có)
3. Chọn một trong hai:
   - **Duyệt hoàn**: Đơn sẽ trả về
   - **Phát lại**: Yêu cầu giao lại

### 6. Hủy đơn hàng
1. Chỉ hủy được đơn ở trạng thái "Đơn nháp" hoặc "Chờ lấy hàng"
2. Mở đơn hàng
3. Nhấn nút **"Hủy đơn"**
4. Xác nhận → Đơn chuyển sang "Đã hủy"

### 7. Xem lịch sử trạng thái
1. Mở form đơn hàng
2. Chuyển sang tab **"Lịch sử trạng thái"**
3. Xem toàn bộ log thay đổi:
   - Thời gian
   - Người thực hiện
   - Trạng thái cũ → Trạng thái mới

## 🚀 Installation & Setup

### Yêu cầu
- Odoo 18.0
- Python 3.10+
- Dependencies: `contacts`, `mail`, `stock`

### Cài đặt
1. Copy module vào thư mục `addons`
2. Restart Odoo server
3. Vào Apps → Update Apps List
4. Tìm "HDI Shipping"
5. Nhấn Install

### Cấu hình ban đầu
1. **Tạo dịch vụ vận chuyển:**
   - Vào **Vận chuyển HDI → Cấu hình → Dịch vụ vận chuyển**
   - Tạo dịch vụ mới (VD: FUTA Express, FUTA Standard...)
   
2. **Tạo địa chỉ gửi hàng:**
   - Vào **Vận chuyển HDI → Cấu hình → Địa chỉ gửi hàng**
   - Thêm địa chỉ kho/cửa hàng của bạn

3. **Phân quyền:**
   - Vào Settings → Users & Companies → Users
   - Cấp quyền "Stock Manager" cho user cần quản lý đơn hàng

## 🔄 Upgrade từ version cũ

Nếu đã có module `hdi_shipping` cũ:
1. Backup database
2. Update code mới
3. Restart Odoo
4. Vào Apps → tìm "HDI Shipping" → Upgrade
5. Dữ liệu cũ sẽ được migrate tự động:
   - Trạng thái `submitted` → `waiting_pickup`
   - Các đơn cũ sẽ tự động có log trạng thái

## ⚠️ Lưu ý khi sử dụng

1. **Không thể sửa đơn đã duyệt**: Sau khi duyệt đơn, tất cả thông tin bị khóa
2. **Chỉ hủy được đơn Draft/Waiting Pickup**: Đơn đang vận chuyển không thể hủy
3. **Workflow phải tuân thủ đúng**: Không thể nhảy trạng thái tùy tiện
4. **Log trạng thái không thể xóa**: Đảm bảo tính toàn vẹn dữ liệu
5. **In PDF có thể chậm**: Khi in nhiều đơn cùng lúc (>50 đơn)

## 📞 Support

- Email: support@hdi.vn
- Hotline: 1900-xxxx
- Documentation: http://docs.hdi.vn/shipping

## 📝 Changelog

### Version 18.0.1.0.0 (2025-12-02)
- ✅ Thêm chức năng "Quản lý đơn hàng gửi"
- ✅ Cập nhật workflow trạng thái (7 trạng thái)
- ✅ Thêm log lịch sử trạng thái
- ✅ Thêm wizard in đơn hàng (single/batch)
- ✅ Thêm report template PDF
- ✅ Thêm search view với filters nâng cao
- ✅ Cập nhật form view với workflow buttons
- ✅ Thêm mail.thread integration (chatter)
- ✅ Cập nhật menu structure
- ✅ Cập nhật security (access rights)

## 📄 License
LGPL-3

---

**Developed by HDI Development Team**
© 2025 HDI Company
