# CropSure AI — Backend 
## By Ngugi James

Parametric crop micro-insurance for Kenyan smallholder farmers.  
Automatically detects crop stress via satellite NDVI and pays out via M-Pesa.

```
FastAPI  ──►  PostgreSQL (asyncpg)
         ──►  ML microservice (NDVI analysis)
         ──►  M-Pesa Daraja (STK Push + B2C)
         ──►  Africa's Talking (SMS)
         ──►  Twilio (WhatsApp)
```

---

## Quick start

```bash
# 1. Clone and install
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env — fill in DB, M-Pesa, AT, Twilio credentials

# 3. Start Postgres (Docker shortcut)
docker run -d --name cropsure-pg \
  -e POSTGRES_DB=cropsure -e POSTGRES_PASSWORD=password \
  -p 5432:5432 postgres:16

# 4. Run
uvicorn main:app --reload --port 8000
```

Or with Docker Compose (if you have one):
```bash
docker build -t cropsure-backend .
docker run --env-file .env -p 8000:8000 cropsure-backend
```

API docs: http://localhost:8000/docs

---

## Environment variables

See `.env.example` for the full list. Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | asyncpg PostgreSQL URL |
| `ML_SERVICE_URL` | ML microservice base URL |
| `MPESA_CONSUMER_KEY` / `MPESA_CONSUMER_SECRET` | Daraja app credentials |
| `MPESA_CALLBACK_BASE_URL` | Public URL for M-Pesa callbacks (use ngrok in dev) |
| `AT_API_KEY` / `AT_USERNAME` | Africa's Talking SMS |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` | Twilio WhatsApp |

---

## Endpoints

### Meta

| Method | Path | Description |
|---|---|---|
| GET | `/` | API info |
| GET | `/health` | Status + DB connection check |

```bash
curl http://localhost:8000/health
```

---

### Farms

#### Enroll a farm
`POST /farms/enroll`

```bash
curl -X POST http://localhost:8000/farms/enroll \
  -H "Content-Type: application/json" \
  -d '{
    "farmer_name": "Jane Wanjiku",
    "phone_number": "254712345678",
    "crop_type": "maize",
    "village": "Kiambu",
    "polygon_geojson": {
      "type": "Feature",
      "geometry": {
        "type": "Polygon",
        "coordinates": [[[36.8, -1.2],[36.81, -1.2],[36.81, -1.21],[36.8, -1.21],[36.8, -1.2]]]
      },
      "properties": {}
    }
  }'
```

**Response:**
```json
{
  "farm_id": "uuid",
  "policy_id": "uuid",
  "area_acres": 27.4,
  "premium_amount_kes": 8220,
  "coverage_amount_kes": 41100,
  "mpesa_stk_initiated": true,
  "mpesa_checkout_request_id": "ws_CO_..."
}
```

#### Get farm details
`GET /farms/{farm_id}`

```bash
curl http://localhost:8000/farms/YOUR_FARM_ID
```

Returns farm info, current policy status, latest NDVI reading, and full payout history.

#### List all farms (admin)
`GET /farms/`

```bash
curl http://localhost:8000/farms/
```

Returns all farms with current health status (`healthy` / `moderate_stress` / `severe_stress`).

---

### M-Pesa Webhooks

These are called by Safaricom's servers — not by your frontend.

#### STK Push result (premium payment)
`POST /mpesa/stk-callback`

Safaricom POSTs here after the farmer completes (or cancels) the STK prompt.  
On success (`ResultCode: 0`): policy status → `active`.  
On failure: policy status → `payment_failed`.

#### B2C result (payout)
`POST /mpesa/b2c-callback`

Safaricom POSTs here after a B2C payout is processed.  
On success: payout status → `completed`, `completed_at` timestamp recorded.  
On failure: payout status → `failed`.

> **Local development:** Use [ngrok](https://ngrok.com) to expose port 8000 and set  
> `MPESA_CALLBACK_BASE_URL=https://your-subdomain.ngrok.io` in `.env`.

---

### Trigger / Monitoring

#### Run monitoring cycle (manual)
`POST /trigger/run`

```bash
curl -X POST http://localhost:8000/trigger/run
```

Fetches every active policy, calls the ML service `/analyze` for each farm, stores NDVI readings, and fires payouts where warranted (subject to 30-day cooldown).

**Response:**
```json
{
  "status": "completed",
  "summary": {
    "farms_checked": 12,
    "payouts_triggered": 2,
    "payouts_skipped_cooldown": 1,
    "ml_errors": 0,
    "timestamp": "2025-06-01T10:00:00"
  }
}
```

#### Simulate drought (DEMO)
`POST /trigger/simulate-drought/{farm_id}`

```bash
curl -X POST http://localhost:8000/trigger/simulate-drought/YOUR_FARM_ID
```

**DEMO ONLY** — forces a drought stress result for the given farm and fires the full payout pipeline immediately. Use during hackathon pitches.

**Response:**
```json
{
  "simulated": true,
  "farm_id": "uuid",
  "payout_id": "uuid",
  "payout_amount_kes": 41100,
  "payout_status": "processing",
  "mpesa_conversation_id": "AG_..."
}
```

---

## Data models

### farms
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| farmer_name | varchar | |
| phone_number | varchar | M-Pesa format: 2547XXXXXXXX |
| polygon_geojson | JSON | Valid GeoJSON Feature or geometry |
| area_acres | float | Auto-calculated via Shapely |
| crop_type | varchar | |
| village | varchar | |
| created_at | timestamp | |

### policies
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| farm_id | UUID | FK → farms |
| status | enum | `pending_payment` / `active` / `expired` / `payment_failed` |
| premium_paid_kes | float | KES 300 × area_acres |
| coverage_amount_kes | float | premium × coverage_multiplier (default 5×) |
| mpesa_reference | varchar | M-Pesa receipt number |
| mpesa_checkout_id | varchar | STK CheckoutRequestID |

### ndvi_readings
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| farm_id | UUID | FK → farms |
| reading_date | timestamp | |
| ndvi_value | float | 0.0 – 1.0 |
| stress_type | varchar | e.g. `drought`, `flood`, `pest` |
| confidence | float | ML confidence 0.0 – 1.0 |
| cloud_contaminated | bool | |

### payouts
| Column | Type | Notes |
|---|---|---|
| id | UUID | PK |
| policy_id | UUID | FK → policies |
| farm_id | UUID | FK → farms |
| payout_amount_kes | float | |
| status | enum | `pending` / `processing` / `completed` / `failed` |
| mpesa_transaction_id | varchar | Final M-Pesa TxID (set by B2C callback) |
| mpesa_conversation_id | varchar | Daraja ConversationID |
| triggered_at | timestamp | |
| completed_at | timestamp | Set on B2C success callback |

---

## Architecture notes

- All endpoints are **async** (asyncpg + SQLAlchemy 2.0 async).
- ML baseline build is **fire-and-forget** (`asyncio.create_task`) — enrollment doesn't block on it.
- Monitoring cycle is designed to be called by a **cron job** (e.g. daily via `POST /trigger/run`) or a task scheduler in production.
- B2C retry logic is logged on failure; a production system should wire `PayoutStatus.FAILED` records to a Celery/ARQ retry queue.
- M-Pesa sandbox credentials: [Daraja portal](https://developer.safaricom.co.ke).
