import { useMemo } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

import type { NdviReading } from '@/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

export default function NdviChart({ readings }: { readings: NdviReading[] }) {
  const sorted = useMemo(() => {
    return [...readings].sort((a, b) => a.date.localeCompare(b.date));
  }, [readings]);

  const data = useMemo(() => {
    return {
      labels: sorted.map((r) => r.date),
      datasets: [
        {
          label: 'NDVI',
          data: sorted.map((r) => r.ndvi),
          borderColor: '#1D9E75',
          backgroundColor: 'rgba(29, 158, 117, 0.12)',
          tension: 0.25,
          fill: true,
          pointRadius: 2,
        },
      ],
    };
  }, [sorted]);

  const options = useMemo(() => {
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
      },
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: { stepSize: 0.2 },
        },
      },
    } as const;
  }, []);

  return (
    <div className="h-64">
      <Line data={data} options={options} />
    </div>
  );
}
