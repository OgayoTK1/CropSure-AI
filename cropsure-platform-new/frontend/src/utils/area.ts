import type { GeoJSONPolygon } from '@/types';

const EARTH_RADIUS_M = 6371008.8;

function toRadians(deg: number): number {
  return (deg * Math.PI) / 180;
}

// Approximate spherical polygon area based on l'Huilier / Chamberlain–Duquette style approach.
// Good enough for UI estimates; backend remains the source of truth.
export function polygonAreaMeters2(polygon: GeoJSONPolygon): number {
  const ring = polygon.coordinates?.[0];
  if (!ring || ring.length < 4) return 0;

  // ring is [lng, lat] and expected to be closed.
  let sum = 0;
  for (let i = 0; i < ring.length - 1; i++) {
    const [lng1, lat1] = ring[i];
    const [lng2, lat2] = ring[i + 1];
    const phi1 = toRadians(lat1);
    const phi2 = toRadians(lat2);
    const lambda1 = toRadians(lng1);
    const lambda2 = toRadians(lng2);
    sum += (lambda2 - lambda1) * (2 + Math.sin(phi1) + Math.sin(phi2));
  }

  const area = Math.abs((sum * EARTH_RADIUS_M * EARTH_RADIUS_M) / 2);
  return Number.isFinite(area) ? area : 0;
}

export function meters2ToAcres(m2: number): number {
  return m2 / 4046.8564224;
}
