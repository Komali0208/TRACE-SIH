export type Camera = {
  id: string;
  name: string;
  lat: number;
  lon: number;
  road_name: string;
  direction: string;
  clip_url?: string | null;
};

export type CameraLink = {
  from_camera: string;
  to_camera: string;
  road_distance_m: number;
};

export type RawRead = { frame: number; text: string; conf: number };

export type Sighting = {
  id: string;
  plate_text: string | null;
  plate_confidence: number;
  camera_id: string;
  ts: string;
  track_id: number;
  frame_count: number;
  raw_reads: RawRead[];
  consensus_method: string;
  crop_url: string;
  video_offset_s: number;
  flags: string[];
  region_guess: string | null;
};

export type WatchlistEntry = {
  plate_text: string;
  status: "stolen" | "blacklisted" | "flagged";
  reason: string;
  added_at: string;
};

export type VehicleRegistryRecord = {
  plate_text: string;
  owner_name: string;
  registration_date: string;
  registering_authority: string;
  vehicle_class: string;
  make_model: string;
  fuel_type: string;
  registration_status: string;
  fitness_valid_until: string;
  insurance_valid_until: string;
  puc_valid_until: string;
  is_mock_data: boolean;
  source_note?: string;
};

export type Alert = {
  id: string;
  sighting_id: string;
  plate_text: string;
  watchlist_status: string;
  ts: string;
  acknowledged: boolean;
  sighting?: Sighting;
};

export type ReviewCase = {
  id: string;
  sighting_id: string;
  flag_type: string;
  status: "open" | "accepted" | "corrected" | "rejected";
  corrected_plate: string | null;
  reviewed_at: string | null;
  sighting?: Sighting;
};

export type TrajectoryLeg = {
  from_sighting_id: string;
  to_sighting_id: string;
  from_camera: string;
  to_camera: string;
  road_distance_m: number;
  elapsed_seconds: number;
  implied_speed_kmh: number;
  anomaly: boolean;
  anomaly_reason: string | null;
};

export type Meta = {
  hero_plates: string[];
  clone_plate: string;
  generated_at: string;
  ocr_model: string;
  footage_note: string;
};

export const FLAG_LABEL: Record<string, string> = {
  FORMAT_MISMATCH: "Format mismatch",
  UNREADABLE: "Unreadable",
  LOW_CONF_ALL_FRAMES: "Low confidence",
  FUZZY_MERGE: "Fuzzy merge",
  SPEED_ANOMALY: "Speed anomaly",
};
