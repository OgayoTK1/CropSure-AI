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
  type ChartType,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import type { NdviReading } from '@/types';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Legend, Filler);

// Module augmentation so TypeScript accepts our custom plugin options
declare module 'chart.js' {
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  interface PluginOptionsByType<TType extends ChartType> {
    triggerLine?: { index?: number | null };
  }
}

// Draws a vertical dashed red line at the trigger point index
const triggerLinePlugin = {
  id: 'triggerLine',
  afterDraw(chart: ChartJS) {
    const opts = (chart.options.plugins as { triggerLine?: { index?: number | null } })?.triggerLine;
    if (opts?.index == null) return;
    const { ctx, chartArea, scales } = chart;
    if (!scales['x']) return;
    const xPx = scales['x'].getPixelForValue(opts.index);
    ctx.save();
    ctx.beginPath();
    ctx.moveTo(xPx, chartArea.top);
    ctx.lineTo(xPx, chartArea.bottom);
    ctx.strokeStyle = '#DC2626';
    ctx.lineWidth = 2;
    ctx.setLineDash([5, 5]);
    ctx.stroke();
    ctx.restore();
  },
};

ChartJS.register(triggerLinePlugin);

function computeBaseline(readings: NdviReading[]): number {
  if (readings.length === 0) return 0.6;
  return readings.reduce((s, r) => s + r.ndvi, 0) / readings.length;
}

export default function NdviChart({
  readings,
  triggerDate,
}: {
  readings: NdviReading[];
  triggerDate?: string | null;
}) {
  const sorted = useMemo(
    () => [...readings].sort((a, b) => a.date.localeCompare(b.date)),
    [readings],
  );

  const baseline = useMemo(() => computeBaseline(sorted), [sorted]);

  const triggerIdx = useMemo(() => {
    if (!triggerDate || sorted.length === 0) return null;
    const idx = sorted.findIndex((r) => r.date >= triggerDate);
    return idx >= 0 ? idx : sorted.length - 1;
  }, [sorted, triggerDate]);

  const data = useMemo(
    () => ({
      labels: sorted.map((r) => r.date.slice(0, 10)),
      datasets: [
        {
          label: 'Current Season',
          data: sorted.map((r) => r.ndvi),
          borderColor: '#1D9E75',
          backgroundColor: 'rgba(29,158,117,0.10)',
          tension: 0.3,
          fill: true,
          pointRadius: 2,
          borderWidth: 2,
        },
        {
          label: 'Historical Baseline',
          data: sorted.map(() => parseFloat(baseline.toFixed(3))),
          borderColor: '#94A3B8',
          backgroundColor: 'transparent',
          tension: 0,
          fill: false,
          pointRadius: 0,
          borderWidth: 1.5,
          borderDash: [5, 5],
        },
      ],
    }),
    [sorted, baseline],
  );

  const options = useMemo(
    () => ({
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: 'index' as const, intersect: false },
      plugins: {
        legend: {
          display: true,
          position: 'top' as const,
          labels: { boxWidth: 12, font: { size: 11 } },
        },
        tooltip: {
          callbacks: {
            label: (ctx: { dataset: { label?: string }; parsed: { y: number | null } }) =>
              `${ctx.dataset.label}: ${ctx.parsed.y?.toFixed(3) ?? '—'}`,
          },
        },
        triggerLine: triggerIdx != null ? { index: triggerIdx } : {},
      },
      scales: {
        y: {
          min: 0,
          max: 1,
          ticks: { stepSize: 0.2 },
          grid: { color: 'rgba(0,0,0,0.05)' },
        },
        x: {
          ticks: { maxTicksLimit: 6, font: { size: 10 } },
          grid: { display: false },
        },
      },
    }),
    [triggerIdx],
  );

  return (
    <div className="h-64">
      <Line data={data} options={options} />
    </div>
  );
}
