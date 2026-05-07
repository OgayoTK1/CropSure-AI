import axios from 'axios';
import { API_BASE_URL } from '../config';
import { Farm, EnrollPayload, EnrollResponse, SimulateResponse, FarmStatus } from '../types';

const http = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });

// ── Response transformers ─────────────────────────────────────────────────────

function healthToStatus(healthStatus: string | null): FarmStatus {
  if (healthStatus === 'drought' || healthStatus === 'pest') return 'severe_stress';
  if (healthStatus === 'flood') return 'mild_stress';
  return 'healthy';
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function transformFarmList(raw: any): Farm {
  return {
    id: raw.id,
    farmerName: raw.farmer_name,
    phone: raw.phone_number,
    village: raw.village,
    cropType: raw.crop_type.charAt(0).toUpperCase() + raw.crop_type.slice(1) as Farm['cropType'],
    boundary: raw.polygon_geojson?.coordinates?.[0]?.map(([lng, lat]: [number, number]) => ({ lat, lng })) ?? [],
    areaAcres: raw.area_acres,
    premium: raw.policy?.premium_paid_kes ?? Math.round(raw.area_acres * 300),
    coverage: raw.policy?.coverage_amount_kes ?? Math.round(raw.area_acres * 300) * 10,
    coverageStart: raw.policy?.season_start ?? raw.created_at,
    coverageEnd: raw.policy?.season_end ?? raw.created_at,
    status: healthToStatus(raw.health_status ?? raw.latest_ndvi?.stress_type ?? null),
    currentNDVI: raw.latest_ndvi?.ndvi_value ?? 0,
    ndviHistory: [],
    payouts: (raw.payout_history ?? []).map((p: any) => ({
      id: p.id,
      amount: p.payout_amount_kes,
      triggeredAt: p.triggered_at,
      reason: p.explanation_en ?? '',
      reasonSw: p.explanation_sw ?? '',
    })),
    policyId: raw.policy_id ?? raw.policy?.id ?? '',
    enrolledAt: raw.created_at,
  };
}

// ── Request transformer ───────────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildEnrollRequest(payload: EnrollPayload): any {
  const { farmerDetails, boundary } = payload;

  // Convert 07XXXXXXXX → 2547XXXXXXXX
  const phone = farmerDetails.phone.startsWith('07')
    ? '254' + farmerDetails.phone.slice(1)
    : farmerDetails.phone;

  // Convert [{lat, lng}] → GeoJSON Polygon (close the ring)
  const coords = boundary.map(({ lat, lng }) => [lng, lat]);
  if (coords.length > 0) coords.push(coords[0]);

  return {
    farmer_name: farmerDetails.fullName,
    phone_number: phone,
    polygon_geojson: { type: 'Polygon', coordinates: [coords] },
    crop_type: farmerDetails.cropType.toLowerCase(),
    village: farmerDetails.village,
  };
}

// ── API client ────────────────────────────────────────────────────────────────

export const api = {
  getFarms: async (): Promise<Farm[]> => {
    const { data } = await http.get<any[]>('/farms');
    return data.map(transformFarmList);
  },

  getFarm: async (id: string): Promise<Farm> => {
    const { data } = await http.get<any>(`/farms/${id}`);
    return transformFarmList(data);
  },

  enrollFarm: async (payload: EnrollPayload): Promise<EnrollResponse> => {
    const { data } = await http.post<any>('/farms/enroll', buildEnrollRequest(payload));
    return {
      id: data.farm_id,
      policyId: data.policy_id,
      message: data.mpesa_stk_initiated ? 'STK Push sent — check your phone.' : 'Enrolled successfully.',
    };
  },

  simulateDrought: async (farmId: string): Promise<SimulateResponse> => {
    const { data } = await http.post<any>(`/trigger/simulate-drought/${farmId}`);
    return {
      payout: data.payout_amount_kes,
      phone: data.phone_number ?? data.farmer_name,
      farmId: data.farm_id,
    };
  },
};