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
| `SHOPWARE_BASE_URL` | Shop-Ware API base URL. Missing until docs are provided. |
| `SHOPWARE_MODE` | `mock` for local development or `live` for real Shop-Ware API calls. |
| `SHOPWARE_API_TOKEN` | Bearer token if Shop-Ware uses token auth. |
| `SHOPWARE_AUTH_HEADER_NAME` | Header used for token auth. Defaults to `Authorization`. |
| `SHOPWARE_AUTH_SCHEME` | Auth scheme prefix. Defaults to `Bearer`; leave blank if the token should be sent directly. |
| `SHOPWARE_CLIENT_ID` | Client ID if Shop-Ware uses OAuth/client credentials. |
| `SHOPWARE_CLIENT_SECRET` | Client secret if Shop-Ware uses OAuth/client credentials. |
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
SHOPWARE_BASE_URL=https://example.shop-ware-api.test
SHOPWARE_API_TOKEN=replace-me
SHOPWARE_APPOINTMENT_CREATE_PATH=/replace/with/official/create/path
SHOPWARE_APPOINTMENT_UPDATE_PATH=/replace/with/official/update/path/{appointment_id}
SHOPWARE_APPOINTMENT_CANCEL_PATH=/replace/with/official/cancel/path/{appointment_id}
SHOPWARE_APPOINTMENT_ID_FIELD=id
```

The endpoint paths above are placeholders by design. Replace them only after official Shop-Ware API documentation confirms the paths and payload shape.

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

## Missing Shop-Ware Details

Phase 2 needs:

- Official base URL and environment strategy.
- Authentication method: bearer token, OAuth, API key, or something else.
- Appointment create/update/cancel endpoint paths.
- Required appointment payload fields and response shape.
- Customer, vehicle, and repair order search endpoint support.
- Error format, rate limits, pagination, and webhook availability.

Until those details are provided, the Shop-Ware client stores appointments locally and logs that remote calls are skipped.

## Extension Points

- Quo calls/texts and AI intake can attach to `app/integrations` and call `app/services`.
- Route optimization can extend appointment metadata with travel windows, technician assignment, working hours, and geocoding.
- Estimate automation can add repair-order, inspection, and recommendation services.
- ScanTool.ai support can add diagnostic session models and ingestion endpoints without changing appointment contracts.
