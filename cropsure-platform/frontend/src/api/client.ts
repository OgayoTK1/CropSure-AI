import axios from 'axios';
import { API_BASE_URL } from '../config';
import { Farm, EnrollPayload, EnrollResponse, SimulateResponse } from '../types';

const http = axios.create({ baseURL: API_BASE_URL, timeout: 15000 });

export const api = {
  getFarms: async (): Promise<Farm[]> => {
    const { data } = await http.get<Farm[]>('/farms');
    return data;
  },

  getFarm: async (id: string): Promise<Farm> => {
    const { data } = await http.get<Farm>(`/farms/${id}`);
    return data;
  },

  enrollFarm: async (payload: EnrollPayload): Promise<EnrollResponse> => {
    const { data } = await http.post<EnrollResponse>('/farms/enroll', payload);
    return data;
  },

  simulateDrought: async (farmId: string): Promise<SimulateResponse> => {
    const { data } = await http.post<SimulateResponse>(
      `/trigger/simulate-drought/${farmId}`
    );
    return data;
  },
};