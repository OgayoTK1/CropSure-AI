# CropSure AI — Backend

FastAPI backend for an index-based crop insurance platform targeting smallholder farmers in Kenya.

## Architecture

```
backend/
├── main.py              # FastAPI app, port 8000
├── database.py          # Async SQLAlchemy engine + session
├── models.py            # ORM tables: Farmer, Farm, MpesaTransaction, MonitoringCycle, Notification
├── mpesa.py             # Daraja STK Push (premium collection) + B2C (drought payouts)
├── notifications.py     # SMS via Africa's Talking + WhatsApp via Meta Business Cloud
├── trigger.py           # Monitoring cycle pipeline (NDVI + rainfall → drought detection)
├── routers/
│   ├── farms.py         # POST /farms/enroll, GET /farms, GET /farms/{id}
│   ├── mpesa_webhooks.py# POST /webhooks/stk-callback, /b2c-result, /b2c-timeout
│   └── trigger_routes.py# POST /trigger/run, /trigger/simulate-drought/{farm_id}
├── requirements.txt
└── Dockerfile
```

## Quick Start

### 1. Install dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure environment
Create a `.env` file:
```env
DATABASE_URL=sqlite+aiosqlite:///./cropsure.db   # or postgresql+asyncpg://user:pass@host/db

# M-Pesa Daraja
MPESA_CONSUMER_KEY=your_key
MPESA_CONSUMER_SECRET=your_secret
MPESA_SHORTCODE=174379
MPESA_PASSKEY=your_passkey
MPESA_B2C_INITIATOR_NAME=testapi
MPESA_B2C_SECURITY_CREDENTIAL=your_credential
MPESA_CALLBACK_URL=https://your-domain.com/webhooks/stk-callback
MPESA_B2C_RESULT_URL=https://your-domain.com/webhooks/b2c-result
MPESA_B2C_TIMEOUT_URL=https://your-domain.com/webhooks/b2c-timeout
MPESA_ENVIRONMENT=sandbox   # sandbox | production

# Notifications
AT_API_KEY=your_at_key
AT_USERNAME=sandbox
WHATSAPP_TOKEN=your_meta_token
WHATSAPP_PHONE_ID=your_phone_id

# Weather (OpenWeatherMap free tier)
OWM_API_KEY=your_owm_key

# Drought thresholds (optional)
NDVI_DROUGHT_THRESHOLD=0.35
RAINFALL_DROUGHT_MM=50.0
```

### 3. Run
```bash
uvicorn main:app --reload --port 8000
```

Visit `http://localhost:8000/docs` for the interactive API docs.

## API Overview

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/farms/enroll` | Register farmer + farm, trigger STK premium push |
| `GET` | `/farms` | List all farms |
| `GET` | `/farms/{farm_id}` | Get a single farm |
| `POST` | `/webhooks/stk-callback` | Daraja STK result callback |
| `POST` | `/webhooks/b2c-result` | Daraja B2C payout result |
| `POST` | `/webhooks/b2c-timeout` | Daraja B2C timeout callback |
| `POST` | `/trigger/run` | Run full monitoring cycle for all active farms |
| `POST` | `/trigger/simulate-drought/{farm_id}` | Simulate drought on one farm (no real payout) |
| `GET` | `/health` | Health check |

## Docker

```bash
docker build -t cropsure-backend .
docker run -p 8000:8000 --env-file .env cropsure-backend
```

## Monitoring Pipeline

`POST /trigger/run` executes:
1. Queries all active farms
2. Fetches rainfall from OpenWeatherMap (per farm GPS coordinates)
3. Computes NDVI (simulated — swap `_fetch_ndvi()` in `trigger.py` with Sentinel Hub or Planet)
4. If `ndvi < 0.35` OR `rainfall < 50mm` → drought detected
5. Sends SMS + WhatsApp alert to farmer
6. Initiates M-Pesa B2C payout (`payout_amount` from farm enrollment)

Use `/trigger/simulate-drought/{farm_id}` to test the full alert flow without a real payout.
