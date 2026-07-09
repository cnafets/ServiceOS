# Your New Mechanic Automation Backend

FastAPI backend foundation for Your New Mechanic, LLC. Phase 1 focuses on a Shop-Ware scheduling integration boundary, local appointment metadata, double-booking prevention, and internal REST endpoints for future Quo, ChatGPT/OpenAI, website, and ScanTool.ai workflows.

## Architecture

- `app/api/routes`: internal REST endpoints.
- `app/core`: settings, logging, and shared exceptions.
- `app/db`: SQLAlchemy engine, sessions, and base metadata.
- `app/models`: database models.
- `app/schemas`: Pydantic request and response models.
- `app/services`: business rules such as double-booking prevention.
- `app/integrations/shopware`: Shop-Ware API client boundary.
- `tests`: focused tests for scheduling behavior.

The system defaults to SQLite for local development and can use PostgreSQL through `DATABASE_URL`.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

API docs will be available at `http://127.0.0.1:8000/docs`.

## Local Developer Setup on Windows

If `python.exe` fails with `The file cannot be accessed by the system`, PowerShell is probably resolving Python to the Microsoft Store app alias instead of a real interpreter. Check with:

```powershell
Get-Command python -All
```

If it points to `C:\Users\<you>\AppData\Local\Microsoft\WindowsApps\python.exe`, install a real Python build from [python.org](https://www.python.org/downloads/windows/). During install, enable:

- `Add python.exe to PATH`
- `pip`
- `venv`
- `py launcher`

This project was verified locally with Python 3.12.10. If the current PowerShell session still sees the Store alias after install, either open a new PowerShell window or use the full interpreter path:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" --version
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m pip --version
```

Create the virtual environment:

```powershell
& "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe" -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, allow scripts for the current user, then retry activation:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Install dependencies:

```powershell
python -m pip install -e ".[dev]"
```

Confirm pip and run tests:

```powershell
python -m pip --version
python -m pytest
```

Run the API locally:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open Swagger UI at `http://127.0.0.1:8000/docs`.

Quick curl test:

```powershell
curl.exe http://127.0.0.1:8000/health
```

Create an appointment:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/appointments `
  -H "Content-Type: application/json" `
  -d "{\"customer_name\":\"Jane Driver\",\"customer_phone\":\"555-0100\",\"customer_address\":\"123 Main St, Charlotte, NC\",\"vehicle_year\":2018,\"vehicle_make\":\"Toyota\",\"vehicle_model\":\"Camry\",\"service_description\":\"No-start diagnostic\",\"start_time\":\"2026-07-10T14:00:00Z\",\"end_time\":\"2026-07-10T16:00:00Z\",\"priority\":\"standard\",\"required_tools\":\"scan tool, battery tester\",\"parts_status\":\"not_checked\",\"communication_status\":\"awaiting_confirmation\"}"
```

List appointments:

```powershell
curl.exe http://127.0.0.1:8000/api/v1/appointments
```

## Appointment Workflow Test

Start the API in one PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Then run the end-to-end workflow script in a second PowerShell window:

```powershell
.\.venv\Scripts\Activate.ps1
python scripts/appointment_workflow.py
```

To point the script at a different local port:

```powershell
$env:BASE_URL = "http://127.0.0.1:8124"
python scripts/appointment_workflow.py
Remove-Item Env:BASE_URL
```

The script performs this sequence:

- Creates an appointment.
- Retrieves the created appointment.
- Attempts an overlapping appointment and expects `409 Conflict`.
- Updates the original appointment.
- Cancels the appointment.
- Lists appointments and confirms the final status is `cancelled`.

Equivalent PowerShell curl workflow:

```powershell
$base = "http://127.0.0.1:8000"

$createBody = @{
  customer_name = "Jane Driver"
  customer_phone = "555-0100"
  customer_address = "123 Main St, Charlotte, NC"
  vehicle_year = 2018
  vehicle_make = "Toyota"
  vehicle_model = "Camry"
  service_description = "No-start diagnostic"
  start_time = "2026-07-10T14:00:00Z"
  end_time = "2026-07-10T16:00:00Z"
  priority = "standard"
  required_tools = "scan tool, battery tester"
  parts_status = "not_checked"
  communication_status = "awaiting_confirmation"
} | ConvertTo-Json

$created = curl.exe -s -X POST "$base/api/v1/appointments" `
  -H "Content-Type: application/json" `
  -d $createBody | ConvertFrom-Json

curl.exe -s "$base/api/v1/appointments/$($created.id)"

$overlapBody = @{
  customer_name = "Overlap Test"
  customer_phone = "555-0101"
  customer_address = "456 Oak St, Charlotte, NC"
  vehicle_year = 2020
  vehicle_make = "Honda"
  vehicle_model = "Accord"
  service_description = "Overlapping diagnostic"
  start_time = "2026-07-10T15:00:00Z"
  end_time = "2026-07-10T17:00:00Z"
  priority = "standard"
} | ConvertTo-Json

curl.exe -i -X POST "$base/api/v1/appointments" `
  -H "Content-Type: application/json" `
  -d $overlapBody

$updateBody = @{
  service_description = "Updated no-start diagnostic and battery test"
  start_time = "2026-07-10T17:00:00Z"
  end_time = "2026-07-10T19:00:00Z"
  parts_status = "not_needed"
  communication_status = "confirmed"
  notes = "Customer confirmed later arrival window."
} | ConvertTo-Json

curl.exe -s -X PATCH "$base/api/v1/appointments/$($created.id)" `
  -H "Content-Type: application/json" `
  -d $updateBody

curl.exe -s -X DELETE "$base/api/v1/appointments/$($created.id)"

curl.exe -s "$base/api/v1/appointments"
```

## Environment Variables

| Variable | Purpose |
| --- | --- |
| `APP_NAME` | FastAPI application name. |
| `APP_ENV` | Environment label such as `local`, `staging`, or `production`. |
| `LOG_LEVEL` | Python logging level. |
| `DATABASE_URL` | SQLAlchemy connection string. Defaults to local SQLite. |
| `SHOPWARE_BASE_URL` | Shop-Ware API base URL. Defaults to `https://api.shop-ware.com`. |
| `SHOPWARE_MODE` | `mock` for local development or `live` for real Shop-Ware API calls. |
| `SHOPWARE_API_PARTNER_ID` | Sent as official `X-Api-Partner-Id` header. |
| `SHOPWARE_API_SECRET` | Sent as official `X-Api-Secret` header. |
| `SHOPWARE_TENANT_ID` | Tenant ID for tenant-scoped API paths. |
| `SHOPWARE_DEFAULT_SHOP_ID` | Required to create appointments because Shop-Ware requires `shop_id`. |
| `SHOPWARE_DEFAULT_STAFF_ID` | Optional technician/staff assignment for synced appointments. |
| `SHOPWARE_TIMEOUT_SECONDS` | HTTP timeout for Shop-Ware calls. |
| `SHOPWARE_RETRY_ATTEMPTS` | Number of API request attempts before marking sync pending. |
| `SHOPWARE_RETRY_BACKOFF_SECONDS` | Base delay between retry attempts. |
| `SHOPWARE_APPOINTMENT_CREATE_PATH` | Live-mode create appointment path. |
| `SHOPWARE_APPOINTMENT_UPDATE_PATH` | Live-mode update appointment path. Use `{appointment_id}` where the remote ID belongs. |
| `SHOPWARE_APPOINTMENT_CANCEL_PATH` | Live-mode cancel appointment path. Use `{appointment_id}` where the remote ID belongs. |
| `SHOPWARE_CUSTOMER_SEARCH_PATH` | Live-mode customer search path. |
| `SHOPWARE_VEHICLE_SEARCH_PATH` | Live-mode vehicle search path. |
| `SHOPWARE_REPAIR_ORDER_SEARCH_PATH` | Live-mode repair order search path. |
| `SHOPWARE_APPOINTMENT_ID_FIELD` | Dot-path for the appointment ID in Shop-Ware responses. Defaults to `id`. |

## API Usage

Create an appointment:

```http
POST /api/v1/appointments
Content-Type: application/json

{
  "customer_name": "Jane Driver",
  "customer_phone": "555-0100",
  "customer_address": "123 Main St, Charlotte, NC",
  "vehicle_year": 2018,
  "vehicle_make": "Toyota",
  "vehicle_model": "Camry",
  "service_description": "No-start diagnostic",
  "start_time": "2026-07-10T14:00:00Z",
  "end_time": "2026-07-10T16:00:00Z",
  "priority": "standard",
  "required_tools": "scan tool, battery tester",
  "parts_status": "not_checked",
  "communication_status": "awaiting_confirmation"
}
```

Other Phase 1 endpoints:

- `GET /health`
- `GET /api/v1/appointments`
- `GET /api/v1/appointments/{appointment_id}`
- `PATCH /api/v1/appointments/{appointment_id}`
- `DELETE /api/v1/appointments/{appointment_id}`
- `POST /api/v1/appointments/{appointment_id}/sync`
- `GET /api/v1/shopware/customers/search?q=Jane`
- `GET /api/v1/shopware/vehicles/search?q=Camry`
- `GET /api/v1/shopware/repair-orders/search?q=RO-123`

Overlapping active appointments return `409 Conflict`.

## Shop-Ware Sync

Shop-Ware integration is split into two layers:

- `ShopWareClient`: reusable HTTP client with configurable auth, timeout handling, retries, and request/response logging.
- `ShopWareAppointmentAdapter`: appointment-specific adapter that translates scheduling actions into configured Shop-Ware calls.

The scheduling service depends on the adapter, not the raw client. Future customer, vehicle, repair order, and inspection adapters can reuse the same client without pushing Shop-Ware details into scheduling logic.

Local development defaults to mock mode:

```env
SHOPWARE_MODE=mock
```

Mock mode returns deterministic remote IDs such as `mock-sw-1`, stores them in `shopware_appointment_id`, and marks records as `synced`.

Live mode is enabled with:

```env
SHOPWARE_MODE=live
SHOPWARE_BASE_URL=https://api.shop-ware.com
SHOPWARE_API_PARTNER_ID=replace-me
SHOPWARE_API_SECRET=replace-me
SHOPWARE_TENANT_ID=replace-me
SHOPWARE_DEFAULT_SHOP_ID=replace-me
SHOPWARE_DEFAULT_STAFF_ID=
SHOPWARE_APPOINTMENT_CREATE_PATH=/api/v1/tenants/{tenant_id}/appointments
SHOPWARE_APPOINTMENT_UPDATE_PATH=/api/v1/tenants/{tenant_id}/appointments/{appointment_id}
SHOPWARE_APPOINTMENT_CANCEL_PATH=/api/v1/tenants/{tenant_id}/appointments/{appointment_id}
SHOPWARE_APPOINTMENT_ID_FIELD=id
```

The official API uses header authentication:

- `X-Api-Partner-Id`
- `X-Api-Secret`

There is no separate OAuth/token authentication endpoint in the OpenAPI file provided.

Official endpoints used or prepared:

| Entity | Methods | Path |
| --- | --- | --- |
| Authorizations | `GET` | `/api/v1/partners/{partner_id}/authorizations` |
| Tenants | `GET` | `/api/v1/tenants`, `/api/v1/tenants/{id}` |
| Appointments | `GET`, `POST` | `/api/v1/tenants/{tenant_id}/appointments` |
| Appointments | `GET`, `PUT`, `DELETE` | `/api/v1/tenants/{tenant_id}/appointments/{id}` |
| Customers | `GET`, `POST` | `/api/v1/tenants/{tenant_id}/customers` |
| Customers | `GET`, `PUT` | `/api/v1/tenants/{tenant_id}/customers/{id}` |
| Vehicles | `GET`, `POST` | `/api/v1/tenants/{tenant_id}/vehicles` |
| Vehicles | `GET`, `PUT` | `/api/v1/tenants/{tenant_id}/vehicles/{id}` |
| Repair Orders | `GET`, `POST` | `/api/v1/tenants/{tenant_id}/repair_orders` |
| Repair Orders | `GET`, `PUT` | `/api/v1/tenants/{tenant_id}/repair_orders/{id}` |
| Repair Order Actions | `POST` | `/api/v1/tenants/{tenant_id}/repair_orders/{id}/start`, `/api/v1/tenants/{tenant_id}/repair_orders/{id}/share` |
| Recommendations | `GET`, `POST` | `/api/v1/tenants/{tenant_id}/recommendations` |
| Recommendations | `GET`, `PUT` | `/api/v1/tenants/{tenant_id}/recommendations/{id}` |
| Past Recommendations | `GET` | `/api/v1/tenants/{tenant_id}/past_recommendations`, `/api/v1/tenants/{tenant_id}/past_recommendations/{id}` |
| Webhooks | `GET`, `POST` | `/api/v1/webhooks` |
| Webhooks | `GET`, `PUT`, `DELETE` | `/api/v1/webhooks/{id}` |

Documented appointment payload fields:

```json
{
  "shop_id": 1,
  "staff_id": 2,
  "repair_order_id": 1,
  "title": "My Appointment Title",
  "description": "My Appointment Description",
  "start_at": "2026-03-10T11:19:19Z",
  "end_at": "2026-03-11T07:59:59Z"
}
```

`shop_id` and `start_at` are required by Shop-Ware. The docs also note that either `repair_order_id` or `title` must be set. The adapter maps local appointment data into `title`, `description`, `start_at`, and `end_at`, and uses `SHOPWARE_DEFAULT_SHOP_ID` plus optional `SHOPWARE_DEFAULT_STAFF_ID`.

If Shop-Ware synchronization fails, the local appointment is still saved. The API response includes:

- `sync_status`: `pending_sync` or `synced`
- `sync_error`: latest sync failure message
- `sync_attempts`: total sync attempts
- `last_sync_at`: latest sync attempt timestamp
- `shopware_appointment_id`: remote appointment ID when available

Manually retry synchronization:

```powershell
curl.exe -X POST http://127.0.0.1:8000/api/v1/appointments/1/sync
```

## Docker

```powershell
Copy-Item .env.example .env
docker compose up --build
```

The compose file includes PostgreSQL and points the API at it.

## Tests

```powershell
pytest
```

Current tests cover local appointment persistence, double-booking prevention, and cancellation freeing a time slot.

## Shop-Ware API Limitations and Blockers

Known blockers for full scheduling integration:

- The API creates appointments against a `shop_id`, but Your New Mechanic is mobile. We need a production convention for which Shop-Ware shop represents mobile work.
- Appointment records do not directly include customer, vehicle, address, travel time, route, or required tool fields. Those must remain local metadata or be connected through repair orders.
- Appointment creation does not automatically update `repair_order.due_in_at` or `repair_order.due_out_at`, according to the docs.
- The public docs do not expose a dedicated availability/free-busy endpoint, so double-booking prevention remains local unless Shop-Ware calendar conflicts must be fetched and reconciled.
- Customer search is filter-based (`last_name`, `email`, `phone_number`), not a single full-text query.
- Vehicle search is VIN/customer-id based. Make/model search is not documented.
- Repair order search supports filters like `number`, `customer_id`, `vehicle_id`, `status`, and `shop_id`, not broad text search.
- Webhooks are available for object/action events such as `appointment.created`, `appointment.updated`, and `appointment.deleted`, but webhook signature verification details were not present in the extracted endpoint summary.
- The OpenAPI file does not document rate limits.

## Extension Points

- Quo calls/texts and AI intake can attach to `app/integrations` and call `app/services`.
- Route optimization can extend appointment metadata with travel windows, technician assignment, working hours, and geocoding.
- Estimate automation can add repair-order, inspection, and recommendation services.
- ScanTool.ai support can add diagnostic session models and ingestion endpoints without changing appointment contracts.
