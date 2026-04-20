export type CropType = 'Maize' | 'Beans' | 'Tea' | 'Wheat' | 'Sorghum';

export type FarmStatus = 'healthy' | 'mild_stress' | 'severe_stress';

export interface Coordinate {
  lat: number;
  lng: number;
}

export interface FarmerDetails {
  fullName: string;
  phone: string;
  village: string;
  cropType: CropType;
}

export interface NDVIPoint {
  week: number;
  ndvi: number;
  baseline: number;
}

export interface Payout {
  id: string;
  amount: number;
  triggeredAt: string;
  reason: string;
  reasonSw: string;
}

export interface Farm {
  id: string;
  farmerName: string;
  phone: string;
  village: string;
  cropType: CropType;
  boundary: Coordinate[];
  areaAcres: number;
  premium: number;
  coverage: number;
  coverageStart: string;
  coverageEnd: string;
  status: FarmStatus;
  currentNDVI: number;
  ndviHistory: NDVIPoint[];
  payouts: Payout[];
  policyId: string;
  enrolledAt: string;
}

export interface ActivityEvent {
  id: string;
  type: 'enrollment' | 'ndvi_reading' | 'payout';
  farmName: string;
  description: string;
  timestamp: string;
}

export interface EnrollPayload {
  farmerDetails: FarmerDetails;
  boundary: Coordinate[];
  areaAcres: number;
}

export interface EnrollResponse {
  id: string;
  policyId: string;
  message: string;
}

export interface SimulateResponse {
  payout: number;
  phone: string;
  farmId: string;
}

export interface DashboardStats {
  totalFarms: number;
  activePolicies: number;
  totalPayoutsKes: number;
  farmsUnderStress: number;
}