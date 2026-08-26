import { Camera, CameraLink, Sighting, TrajectoryLeg } from "./types";

function haversineM(a: Camera, b: Camera) {
  const R = 6371000;
  const dLat = ((b.lat - a.lat) * Math.PI) / 180;
  const dLon = ((b.lon - a.lon) * Math.PI) / 180;
  const la1 = (a.lat * Math.PI) / 180;
  const la2 = (b.lat * Math.PI) / 180;
  const h =
    Math.sin(dLat / 2) ** 2 + Math.cos(la1) * Math.cos(la2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

export function linkDistance(
  fromId: string,
  toId: string,
  links: CameraLink[],
  cameras: Camera[]
): number {
  if (fromId === toId) return 0;
  const direct = links.find(
    (l) =>
      (l.from_camera === fromId && l.to_camera === toId) ||
      (l.from_camera === toId && l.to_camera === fromId)
  );
  if (direct) return direct.road_distance_m;
  const a = cameras.find((c) => c.id === fromId);
  const b = cameras.find((c) => c.id === toId);
  if (a && b) return Math.round(haversineM(a, b) * 1.35); // road-factor estimate
  return 0;
}

export function buildLegs(
  sightings: Sighting[],
  links: CameraLink[],
  cameras: Camera[]
): TrajectoryLeg[] {
  const ordered = [...sightings].sort((a, b) => +new Date(a.ts) - +new Date(b.ts));
  const legs: TrajectoryLeg[] = [];
  for (let i = 0; i < ordered.length - 1; i++) {
    const from = ordered[i];
    const to = ordered[i + 1];
    const elapsed = Math.max(1, (+new Date(to.ts) - +new Date(from.ts)) / 1000);
    const distance = linkDistance(from.camera_id, to.camera_id, links, cameras);
    const speed = (distance / 1000) / (elapsed / 3600);
    const flaggedAnomaly = to.flags.includes("SPEED_ANOMALY") || from.flags.includes("SPEED_ANOMALY");
    const anomaly = speed > 150 || flaggedAnomaly;
    legs.push({
      from_sighting_id: from.id,
      to_sighting_id: to.id,
      from_camera: from.camera_id,
      to_camera: to.camera_id,
      road_distance_m: distance,
      elapsed_seconds: Math.round(elapsed),
      implied_speed_kmh: Math.round(speed * 10) / 10,
      anomaly,
      anomaly_reason: anomaly
        ? `Implied speed ${Math.round(speed)} km/h exceeds 150 km/h threshold — possible plate cloning or misread merge`
        : null,
    });
  }
  return legs;
}

export function fuzzyMergedFrom(sightings: Sighting[], plate: string): string[] {
  const out = new Set<string>();
  for (const s of sightings) {
    if (!s.flags.includes("FUZZY_MERGE") && !s.flags.includes("FORMAT_MISMATCH")) continue;
    for (const r of s.raw_reads || []) {
      if (r.text && r.text !== plate && !r.text.includes("_")) out.add(r.text);
    }
  }
  return Array.from(out);
}

export function computeSummary(
  sightings: Sighting[],
  openAlerts: number,
  openReview: number
) {
  const withConf = sightings.filter((s) => typeof s.plate_confidence === "number");
  const mean =
    withConf.reduce((a, s) => a + s.plate_confidence, 0) / (withConf.length || 1);
  const unique = new Set(sightings.map((s) => s.plate_text).filter(Boolean)).size;
  const times = sightings.map((s) => +new Date(s.ts)).sort((a, b) => a - b);
  return {
    total_sightings: sightings.length,
    unique_plates: unique,
    mean_confidence: Math.round(mean * 1000) / 1000,
    open_alerts: openAlerts,
    open_review_cases: openReview,
    time_range: {
      from: times.length ? new Date(times[0]).toISOString() : null,
      to: times.length ? new Date(times[times.length - 1]).toISOString() : null,
    },
  };
}

export function computeHeatmap(sightings: Sighting[], cameras: Camera[]) {
  const perCamera = cameras.map((c) => {
    const rows = sightings.filter((s) => s.camera_id === c.id);
    const mean =
      rows.reduce((a, s) => a + s.plate_confidence, 0) / (rows.length || 1);
    return { camera_id: c.id, count: rows.length, mean_confidence: Math.round(mean * 1000) / 1000 };
  });
  const byHour = new Map<string, number>();
  for (const s of sightings) {
    const d = new Date(s.ts);
    d.setMinutes(0, 0, 0);
    const key = d.toISOString();
    byHour.set(key, (byHour.get(key) || 0) + 1);
  }
  const hourly = Array.from(byHour.entries())
    .sort((a, b) => +new Date(a[0]) - +new Date(b[0]))
    .map(([hour, count]) => ({ hour, count }));

  const odMap = new Map<string, number>();
  const byTrack = new Map<string, Sighting[]>();
  for (const s of sightings) {
    const key = s.plate_text || `t${s.track_id}`;
    if (!byTrack.has(key)) byTrack.set(key, []);
    byTrack.get(key)!.push(s);
  }
  for (const list of byTrack.values()) {
    const ordered = [...list].sort((a, b) => +new Date(a.ts) - +new Date(b.ts));
    for (let i = 0; i < ordered.length - 1; i++) {
      const key = `${ordered[i].camera_id}|${ordered[i + 1].camera_id}`;
      odMap.set(key, (odMap.get(key) || 0) + 1);
    }
  }
  const od_matrix = Array.from(odMap.entries()).map(([k, count]) => {
    const [from_camera, to_camera] = k.split("|");
    return { from_camera, to_camera, count };
  });

  return { per_camera: perCamera, hourly, od_matrix };
}

export function computeTravelTimes(sightings: Sighting[], links: CameraLink[]) {
  const byTrack = new Map<string, Sighting[]>();
  for (const s of sightings) {
    const key = s.plate_text || `t${s.track_id}`;
    if (!byTrack.has(key)) byTrack.set(key, []);
    byTrack.get(key)!.push(s);
  }
  const samples = new Map<string, number[]>();
  for (const list of byTrack.values()) {
    const ordered = [...list].sort((a, b) => +new Date(a.ts) - +new Date(b.ts));
    for (let i = 0; i < ordered.length - 1; i++) {
      const a = ordered[i];
      const b = ordered[i + 1];
      if (a.camera_id === b.camera_id) continue;
      const key = [a.camera_id, b.camera_id].sort().join("|");
      const secs = (+new Date(b.ts) - +new Date(a.ts)) / 1000;
      if (secs <= 0 || secs > 4000) continue;
      if (!samples.has(key)) samples.set(key, []);
      samples.get(key)!.push(secs);
    }
  }
  const rows = links.map((link) => {
    const key = [link.from_camera, link.to_camera].sort().join("|");
    const arr = (samples.get(key) || []).sort((a, b) => a - b);
    const median = arr.length ? arr[Math.floor(arr.length / 2)] : link.road_distance_m / 11.1;
    const current = arr.length ? arr[arr.length - 1] : median;
    const delay = current / median;
    return {
      from_camera: link.from_camera,
      to_camera: link.to_camera,
      road_distance_m: link.road_distance_m,
      sample_count: arr.length,
      median_seconds: Math.round(median),
      current_seconds: Math.round(current),
      delay_ratio: Math.round(delay * 100) / 100,
      congested: delay > 1.3,
    };
  });
  return rows.sort((a, b) => b.delay_ratio - a.delay_ratio);
}

export function searchPlates(sightings: Sighting[], q: string) {
  const query = q.trim().toUpperCase();
  if (!query) return [];
  const byPlate = new Map<string, { cameras: Set<string>; count: number }>();
  for (const s of sightings) {
    if (!s.plate_text) continue;
    if (!s.plate_text.includes(query)) continue;
    if (!byPlate.has(s.plate_text)) byPlate.set(s.plate_text, { cameras: new Set(), count: 0 });
    const e = byPlate.get(s.plate_text)!;
    e.cameras.add(s.camera_id);
    e.count++;
  }
  return Array.from(byPlate.entries())
    .map(([plate_text, v]) => ({ plate_text, sighting_count: v.count, cameras: Array.from(v.cameras) }))
    .sort((a, b) => b.sighting_count - a.sighting_count)
    .slice(0, 20);
}
