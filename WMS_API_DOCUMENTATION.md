# WMS REST API Documentation

## Base URL
```
http://your-odoo-server.com
```

## Authentication
All API requests require an API key in the header:
```
X-API-Key: wms_your_api_key_here
```

---

## API Endpoints

### 1. Query Stock
**Endpoint**: `/api/wms/stock/query`  
**Method**: `POST`  
**Permission**: `can_query`

**Request Body**:
```json
{
  "product_code": "PRD001",
  "location_code": "A-01-01"
}
```

**Response**:
```json
{
  "success": true,
  "data": [
    {
      "product_code": "PRD001",
      "product_name": "Product Name",
      "location_code": "A-01-01",
      "location_name": "Aisle A - Row 1 - Shelf 1",
      "quantity": 100.0,
      "available_quantity": 80.0,
      "reserved_quantity": 20.0,
      "uom": "Unit(s)"
    }
  ]
}
```

### 2. Create Receipt
**Endpoint**: `/api/wms/receipt/create`  
**Method**: `POST`  
**Permission**: `can_create_receipt`

**Request Body**:
```json
{
  "warehouse_code": "WH01",
  "origin": "PO12345",
  "notes": "Supplier delivery",
  "lines": [
    {
      "product_code": "PRD001",
      "quantity": 100,
      "notes": "Good condition"
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "receipt_id": 1,
    "receipt_number": "RCV/2024/0001",
    "state": "draft"
  }
}
```

### 3. Create Delivery
**Endpoint**: `/api/wms/delivery/create`  
**Method**: `POST`  
**Permission**: `can_create_delivery`

**Request Body**:
```json
{
  "warehouse_code": "WH01",
  "origin": "SO67890",
  "customer_name": "Customer ABC",
  "delivery_address": "123 Main St, City",
  "notes": "Urgent delivery",
  "lines": [
    {
      "product_code": "PRD001",
      "quantity": 50,
      "notes": ""
    }
  ]
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "delivery_id": 1,
    "delivery_number": "DEL/2024/0001",
    "state": "draft"
  }
}
```

### 4. Reserve Stock
**Endpoint**: `/api/wms/stock/reserve`  
**Method**: `POST`  
**Permission**: `can_reserve`

**Request Body**:
```json
{
  "product_code": "PRD001",
  "location_code": "A-01-01",
  "quantity": 20,
  "origin": "SO67890"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "product_code": "PRD001",
    "reserved_quantity": 20
  }
}
```

### 5. Move Stock
**Endpoint**: `/api/wms/stock/move`  
**Method**: `POST`  
**Permission**: `can_move`

**Request Body**:
```json
{
  "product_code": "PRD001",
  "location_from_code": "A-01-01",
  "location_to_code": "B-02-03",
  "quantity": 30,
  "origin": "Transfer #123"
}
```

**Response**:
```json
{
  "success": true,
  "data": {
    "move_id": 1,
    "product_code": "PRD001",
    "quantity": 30,
    "location_from": "A-01-01",
    "location_to": "B-02-03"
  }
}
```

### 6. Barcode Scan
**Endpoint**: `/api/wms/barcode/scan`  
**Method**: `POST`  
**Permission**: `can_query` (minimum)

**Request Body**:
```json
{
  "barcode": "PRD001",
  "operation_type": "query",
  "warehouse_code": "WH01"
}
```

**Response**:
```json
{
  "scan_id": 1,
  "scan_type": "product",
  "success": true,
  "message": "Product: Product Name\nTotal: 100.0",
  "data": {
    "product": "Product Name",
    "total_quantity": 100.0,
    "locations": [
      {
        "location": "A-01-01",
        "quantity": 80.0,
        "available": 60.0
      }
    ]
  }
}
```

---

## Error Responses

### 401 Unauthorized
```json
{
  "error": "API key missing",
  "code": 401
}
```

### 403 Forbidden
```json
{
  "error": "Permission denied"
}
```

### 404 Not Found
```json
{
  "error": "Warehouse not found"
}
```

### 500 Server Error
```json
{
  "error": "Error message details"
}
```

---

## Usage Examples

### Python
```python
import requests
import json

API_URL = "http://your-odoo-server.com"
API_KEY = "wms_your_api_key_here"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

# Query stock
data = {
    "product_code": "PRD001"
}

response = requests.post(
    f"{API_URL}/api/wms/stock/query",
    headers=headers,
    data=json.dumps(data)
)

print(response.json())
```

### cURL
```bash
curl -X POST \
  http://your-odoo-server.com/api/wms/stock/query \
  -H 'X-API-Key: wms_your_api_key_here' \
  -H 'Content-Type: application/json' \
  -d '{
    "product_code": "PRD001"
  }'
```

### JavaScript
```javascript
const API_URL = "http://your-odoo-server.com";
const API_KEY = "wms_your_api_key_here";

const queryStock = async (productCode) => {
  const response = await fetch(`${API_URL}/api/wms/stock/query`, {
    method: 'POST',
    headers: {
      'X-API-Key': API_KEY,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      product_code: productCode
    })
  });
  
  return await response.json();
};

queryStock('PRD001').then(data => console.log(data));
```

---

## API Key Management

### Create API Key
1. Login to Odoo as WMS Manager
2. Go to: WMS → Integration → API Keys
3. Click "Create"
4. Fill in:
   - Name: Description of API key
   - User: Select user
   - Warehouse: (optional) Limit to specific warehouse
   - Expires On: Set expiration date
   - IP Whitelist: (optional) Comma-separated IPs
5. Configure Permissions:
   - Can Query Stock
   - Can Create Receipt
   - Can Create Delivery
   - Can Reserve Stock
   - Can Move Stock
6. Save → Copy the generated API key

### Security Best Practices
- Use separate API keys for different applications
- Set expiration dates
- Use IP whitelist for production
- Rotate keys regularly
- Monitor API logs for suspicious activity
- Disable unused API keys

---

## Rate Limiting & Performance

- No built-in rate limiting (implement at nginx/load balancer level)
- API logs stored for 90 days (auto-cleanup)
- Response times logged for monitoring
- Use pagination for large datasets (implement in custom queries)

---

## Webhooks

Configure webhooks to receive notifications on events:

### Available Events
- `receipt_done`: Receipt completed
- `delivery_shipped`: Delivery shipped
- `transfer_done`: Transfer completed
- `adjustment_done`: Adjustment completed
- `stock_low`: Stock below minimum threshold
- `product_expired`: Product expired

### Webhook Payload
```json
{
  "event": "receipt_done",
  "timestamp": "2024-01-15T10:30:00",
  "data": {
    "receipt_id": 1,
    "receipt_number": "RCV/2024/0001",
    "warehouse": "Main Warehouse",
    "state": "done"
  }
}
```

### Configure Webhook
1. WMS → Integration → Webhooks → Create
2. Enter webhook URL
3. Select events to trigger
4. Configure authentication (if needed)
5. Set retry settings
6. Test webhook

---

## Support
For API support, check:
- API Logs: WMS → Integration → API Logs
- Error messages in response body
- Server logs: /var/log/odoo/odoo-server.log
