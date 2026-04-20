# CropSure AI — Deployment Guide

## Prerequisites
- Railway account (free at railway.app)
- GitHub repository connected to Railway
- All environment variables ready from .env.example

---

## Step 1 — Create Railway Project

1. Go to https://railway.app and sign in with GitHub
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Select the CropSure-AI repository
5. Click "Deploy Now"

---

## Step 2 — Add PostgreSQL Database

1. Inside your Railway project click "New Service"
2. Select "Database" then "PostgreSQL"
3. Railway creates the database automatically
4. Click the database service and go to "Variables"
5. Copy the DATABASE_URL value — you will need it

---

## Step 3 — Deploy Backend

1. Click "New Service" then "GitHub Repo"
2. Select the repo and set root directory to "cropsure-platform/backend"
3. Railway detects FastAPI automatically via nixpacks
4. Go to "Variables" and add all variables from .env.example
5. Set DATABASE_URL to the value copied from Step 2
6. Set ML_SERVICE_URL to your ML service Railway URL
7. Click "Deploy"

---

## Step 4 — Deploy ML Service

1. Click "New Service" then "GitHub Repo"
2. Set root directory to "cropsure-platform/ml-service"
3. Add environment variables — especially SENTINEL_HUB_CLIENT_ID and SECRET
4. Click "Deploy"
5. Copy the ML service public URL
6. Go back to backend service and update ML_SERVICE_URL

---

## Step 5 — Deploy Frontend

1. Click "New Service" then "GitHub Repo"
2. Set root directory to "cropsure-platform/frontend"
3. Add VITE_API_URL pointing to your backend Railway URL
4. Click "Deploy"
5. Railway builds the React app and gives you a public URL

---

## Step 6 — Deploy WhatsApp Bot

1. Click "New Service" then "GitHub Repo"
2. Set root directory to "cropsure-platform/integration/whatsapp_bot"
3. Add all Twilio environment variables
4. Set BACKEND_URL to your backend Railway URL
5. Click "Deploy"
6. Copy the public URL
7. Go to Twilio console — Messaging — WhatsApp Sandbox Settings
8. Set webhook URL to: https://your-bot-url.railway.app/whatsapp

---

## Step 7 — Deploy USSD Handler

1. Click "New Service" then "GitHub Repo"
2. Set root directory to "cropsure-platform/integration/ussd"
3. Add Africa's Talking environment variables
4. Set BACKEND_URL to your backend Railway URL
5. Click "Deploy"
6. Copy the public URL
7. Go to Africa's Talking dashboard — USSD — set callback URL

---

## Step 8 — Load Demo Data

Once all services are running, load the demo data:

```bash
railway run psql $DATABASE_URL -f integration/demo/demo_data.sql
```

---

## Step 9 — Verify Everything Works

Check these URLs are all returning healthy responses:

- Backend: https://your-backend.railway.app/health
- ML Service: https://your-ml.railway.app/health
- WhatsApp Bot: https://your-bot.railway.app/health
- USSD Handler: https://your-ussd.railway.app/health
- Frontend: https://your-frontend.railway.app

---

## WARNING — Demo Day

NEVER run make reset-db on demo day.
NEVER push new code 1 hour before the pitch.
ALWAYS test the full demo flow the night before.
ALWAYS have the demo data pre-loaded and verified.
ALWAYS have a backup laptop with the app running locally.
