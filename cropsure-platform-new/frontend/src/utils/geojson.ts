import type { GeoJSONPolygon } from '@/types';

export type LatLng = { lat: number; lng: number };

export function pointsToPolygon(points: LatLng[]): GeoJSONPolygon | null {
  if (points.length < 3) return null;
  const ring = [...points, points[0]].map((p) => [p.lng, p.lat]);
  return {
    type: 'Polygon',
    coordinates: [ring],
  };
}

export function polygonToLatLngs(polygon: GeoJSONPolygon): LatLng[] {
  const ring = polygon.coordinates?.[0] ?? [];
  // GeoJSON is [lng,lat]
  return ring.map((c) => ({ lng: c[0], lat: c[1] }));
}

export function formatAcreage(acres: number | null | undefined): string {
  if (acres == null || Number.isNaN(acres)) return '-';
  return `${acres.toFixed(2)}`;
}
