import { Coordinate } from '../types';

/** Shoelace formula on a local equirectangular projection → acres */
export function computeAreaAcres(coords: Coordinate[]): number {
  if (coords.length < 3) return 0;

  const R = 6371000; // Earth radius in metres
  const toRad = (deg: number) => (deg * Math.PI) / 180;
  const lat0 = coords[0].lat;
  const lng0 = coords[0].lng;

  const pts = coords.map((c) => ({
    x: R * toRad(c.lng - lng0) * Math.cos(toRad(lat0)),
    y: R * toRad(c.lat - lat0),
  }));

  let area = 0;
  for (let i = 0; i < pts.length; i++) {
    const j = (i + 1) % pts.length;
    area += pts[i].x * pts[j].y - pts[j].x * pts[i].y;
  }

  return Math.abs(area) / 2 / 4047; // sq metres → acres
}

export function getCentroid(coords: Coordinate[]): Coordinate {
  const lat = coords.reduce((s, c) => s + c.lat, 0) / coords.length;
  const lng = coords.reduce((s, c) => s + c.lng, 0) / coords.length;
  return { lat, lng };
}