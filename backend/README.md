# CropSure AI — Backend

FastAPI backend for a parametric crop micro-insurance platform. Automatically pays Kenyan smallholder farmers via M-Pesa when satellite data detects crop stress.

## Architecture

```
backend/
├── main.py               # FastAPI app, CORS, port 8000
├── database.py           # Async SQLAlchemy engine + session
├── models.py             # ORM: Farm, Policy, NdviReading, Payout, Baseline
├── mpesa.py              # Daraja STK Push + B2C
├── notifications.py      # Africa's Talking SMS + Twilio WhatsApp
├── trigger.py            # Monitoring cycle: ML → NDVI → payout pipeline
└── routers/
    ├── farms.py          # POST /farms/enroll, GET /farms, GET /farms/{id}
    ├── mpesa_webhooks.py # POST /mpesa/stk-callback, /b2c-callback, /b2c-timeout
    └── trigger_routes.py # POST /trigger/run, /trigger/simulate-drought/{farm_id}
```

## Quick Start

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env      # fill in your credentials
uvicorn main:app --reload --port 8000
```

Interactive docs: `http://localhost:8000/docs`

For M-Pesa callbacks in local dev, expose port 8000 with ngrok:
```bash
ngrok http 8000
# paste the https URL into MPESA_CALLBACK_URL etc. in .env
```

## Docker

```bash
docker build -t cropsure-backend .
docker run -p 8000:8000 --env-file .env cropsure-backend
```

---

## API Reference

### GET /
Returns service info and endpoint map.

### GET /health
Returns `{ "status": "ok", "database": "connected" }`.

---

### POST /farms/enroll
Register a farmer + farm. Calculates area, creates a Policy, fires STK Push for premium (KES 300/acre), queues ML baseline build.

**Request:**
```json
{
  "farmer_name": "Jane Wanjiku",
  "phone_number": "254712345678",
  "polygon_geojson": {
    "type": "Polygon",
    "coordinates": [[[36.8, -0.2], [36.82, -0.2], [36.82, -0.22], [36.8, -0.22], [36.8, -0.2]]]
  },
  "crop_type": "maize",
  "village": "Eldoret North"
}
```

**Response:**
```json
{
  "farm_id": "uuid",
  "policy_id": "uuid",
  "premium_amount": 900.0,
  "mpesa_stk_initiated": true,
  "stk_response": { "CheckoutRequestID": "...", "ResponseDescription": "..." }
}
```

```bash
curl -X POST http://localhost:8000/farms/enroll \
  -H "Content-Type: application/json" \
  -d '{"farmer_name":"Jane Wanjiku","phone_number":"254712345678","polygon_geojson":{"type":"Polygon","coordinates":[[[36.8,-0.2],[36.82,-0.2],[36.82,-0.22],[36.8,-0.22],[36.8,-0.2]]]},"crop_type":"maize","village":"Eldoret North"}'
```

---

### GET /farms/{farm_id}
Farm details + current policy + latest NDVI reading + payout history.

```bash
curl http://localhost:8000/farms/550e8400-e29b-41d4-a716-446655440000
```

---

### GET /farms
Admin list — all farms with current health status and policy status.

```bash
curl http://localhost:8000/farms
```

---

### POST /mpesa/stk-callback
Daraja webhook. On success → Policy activated. On failure → Policy marked `payment_failed`. Called by Safaricom, not directly.

---

### POST /mpesa/b2c-callback
Daraja webhook. On success → Payout marked `completed`. On failure → Payout marked `failed`. Called by Safaricom, not directly.

---

### POST /trigger/run
Manually trigger the monitoring cycle for all active policies.

```bash
curl -X POST http://localhost:8000/trigger/run
```

**Response:**
```json
{
  "policies_checked": 5,
  "payouts_triggered": 2,
  "results": [...]
}
```

---

### POST /trigger/simulate-drought/{farm_id}
**DEMO endpoint.** Forces a drought result for one farm and fires the full pipeline (real B2C payout + real SMS/WhatsApp). Used for the hackathon pitch.

```bash
curl -X POST http://localhost:8000/trigger/simulate-drought/550e8400-e29b-41d4-a716-446655440000
```

**Response:**
```json
{
  "farm_id": "...",
  "farmer_name": "Jane Wanjiku",
  "simulated_ndvi": 0.18,
  "payout_amount_kes": 4500.0,
  "conversation_id": "AG_...",
  "payout_status": "processing",
  "note": "Simulated drought — full pipeline executed"
}
```

---

## Database Schema

| Table | Key columns |
|-------|-------------|
| `farms` | id, farmer_name, phone_number, polygon_geojson, area_acres, crop_type, village |
| `policies` | id, farm_id, season_start/end, premium_paid_kes, coverage_amount_kes, status, mpesa_reference |
| `ndvi_readings` | id, farm_id, reading_date, ndvi_value, stress_type, confidence, cloud_contaminated |
| `payouts` | id, policy_id, farm_id, payout_amount_kes, stress_type, explanation_en/sw, mpesa_transaction_id, status |
| `baselines` | farm_id (PK), baseline_data (JSON), last_updated |

Policy statuses: `pending_payment` → `active` → `expired` (or `payment_failed`)  
Payout statuses: `pending` → `processing` → `completed` (or `failed`)

## ML Service Contract

The backend calls two endpoints on `ML_SERVICE_URL`:

**POST /build-baseline** (fire-and-forget on enrollment)
```json
{ "farm_id": "uuid", "polygon_geojson": {...} }
```

**POST /analyze** (called each monitoring cycle)
```json
{ "farm_id": "uuid", "polygon_geojson": {...} }
```
Expected response:
```json
{
  "ndvi_value": 0.32,
  "stress_type": "drought",
  "confidence": 0.87,
  "cloud_contaminated": false,
  "payout_recommended": true,
  "payout_amount_kes": 4500.0,
  "explanation_en": "NDVI dropped 28% below your March baseline.",
  "explanation_sw": "NDVI ilishuka asilimia 28 chini ya kiwango cha Machi."
}
```
