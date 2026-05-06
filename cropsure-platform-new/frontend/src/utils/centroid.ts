import type { GeoJSONPolygon } from '@/types';

export function polygonCentroid(polygon: GeoJSONPolygon): { lat: number; lng: number } | null {
  const ring = polygon.coordinates?.[0];
  if (!ring || ring.length < 3) return null;

  // Use simple centroid on projected plane (good enough for map centering at small scale).
  let x = 0;
  let y = 0;
  let n = 0;
  for (const [lng, lat] of ring) {
    x += lng;
    y += lat;
    n += 1;
  }
  if (n === 0) return null;
  return { lng: x / n, lat: y / n };
}
