import axios, { AxiosError } from 'axios';
import { API_BASE_URL } from '../config';
import type { EnrollRequest, EnrollResponse, Farm } from '../types';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor
apiClient.interceptors.request.use(
  (config) => {
    return config;
  },
  (error: AxiosError) => {
    console.error('[API] Request error:', error.message);
    return Promise.reject(error);
  }
);

// Response interceptor — log errors
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      console.error(
        `[API] Response error ${error.response.status}:`,
        error.response.data
      );
    } else if (error.request) {
      console.error('[API] No response received:', error.message);
    } else {
      console.error('[API] Request setup error:', error.message);
    }
    return Promise.reject(error);
  }
);

export async function enrollFarm(data: EnrollRequest): Promise<EnrollResponse> {
  const response = await apiClient.post<EnrollResponse>('/farms/enroll', data);
  return response.data;
}

export async function listFarms(): Promise<Farm[]> {
  const response = await apiClient.get<Farm[]>('/farms');
  return response.data;
}

export async function getFarm(id: string): Promise<Farm> {
  const response = await apiClient.get<Farm>(`/farms/${id}`);
  return response.data;
}

export async function simulateDrought(farmId: string): Promise<unknown> {
  const response = await apiClient.post(`/trigger/simulate-drought/${farmId}`);
  return response.data;
}

export async function runMonitoring(): Promise<unknown> {
  const response = await apiClient.post('/trigger/run');
  return response.data;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const response = await apiClient.get('/health');
    return response.status === 200;
  } catch {
    return false;
  }
}

export default apiClient;
