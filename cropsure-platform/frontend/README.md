# CropSure AI – Frontend

Parametric crop micro-insurance app for African smallholder farmers.  
React 18 + Vite + Tailwind CSS + Leaflet.js + Chart.js.

## Quick start

```bash
cd cropsure-platform/frontend
npm install
npm run dev
```

App runs at **http://localhost:3000**.

## Environment

Create `.env.local` to point at your backend:

```
VITE_API_URL=http://localhost:8000
```

Defaults to `http://localhost:8000` if not set. The dashboard falls back to built-in demo data when the backend is unreachable.

## Pages

| Route | Description |
|---|---|
| `/` | Farmer enrollment wizard (3 steps) |
| `/dashboard` | Admin dashboard – map, stats, NDVI chart, drought simulator |
| `/farm/:farmId` | Farm detail – map, full NDVI history, payout records |

## Build

```bash
npm run build    # outputs to dist/
npm run preview  # serve the built app
```

## Structure

```
src/
├── api/          # Axios API client
├── components/   # Shared UI (Header, Spinner, Error, Toast, EmptyState)
├── context/      # Toast notification context
├── data/         # Mock farm data (demo fallback)
├── enrollment/   # Step components (Farmer Details, GPS Boundary, Payment)
├── i18n/         # English + Swahili translations (en.json, sw.json)
├── pages/        # Route-level pages (Enrollment, Dashboard, FarmDetail)
├── utils/        # Geo utilities (Shoelace area formula, centroid)
└── types.ts      # All TypeScript interfaces
```

## Language

Toggle between **English** and **Swahili** using the button in the header. All UI strings are translated.