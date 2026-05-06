export interface Farm {
  id: string;
  farmer_name: string;
  phone_number: string;
  village: string;
  crop_type: string;
  area_acres: number;
  polygon_geojson: GeoJSONPolygon;
  health_status?: 'healthy' | 'mild_stress' | 'stress';
  current_ndvi?: number;
  stress_type?: string;
  policy_status?: string;
  created_at: string;
  policy?: FarmPolicy;
  ndvi_history?: NdviReading[];
  payouts?: Payout[];
}

export interface GeoJSONPolygon {
  type: 'Polygon';
  coordinates: number[][][];
}

export interface FarmPolicy {
  id: string;
  status: 'pending_payment' | 'active' | 'expired' | 'payment_failed';
  premium_paid_kes: number;
  coverage_amount_kes: number;
  season_start: string;
  season_end: string;
}

export interface NdviReading {
  date: string;
  ndvi: number;
  stress_type?: string;
  confidence?: number;
}

export interface Payout {
  id: string;
  amount_kes: number;
  stress_type: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  explanation_en?: string;
  explanation_sw?: string;
  triggered_at: string;
  completed_at?: string;
}

export interface EnrollRequest {
  farmer_name: string;
  phone_number: string;
  village: string;
  crop_type: string;
  polygon_geojson: GeoJSONPolygon;
}

export interface EnrollResponse {
  farm_id: string;
  policy_id: string;
  farmer_name: string;
  area_acres: number;
  premium_amount_kes: number;
  coverage_amount_kes: number;
  season_start: string;
  season_end: string;
  mpesa_stk_initiated: boolean;
  policy_status: string;
}
