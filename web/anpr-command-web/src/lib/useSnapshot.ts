"use client";
import { useEffect, useState } from "react";
import { Camera, CameraLink, Sighting, WatchlistEntry, Meta, VehicleRegistryRecord } from "./types";

export type SnapshotData = {
  meta: Meta;
  cameras: Camera[];
  camera_links: CameraLink[];
  sightings: Sighting[];
  watchlist: WatchlistEntry[];
  registry?: VehicleRegistryRecord[];
};

let cached: SnapshotData | null = null;
let inflight: Promise<SnapshotData> | null = null;

export function useSnapshot(enabled: boolean) {
  const [data, setData] = useState<SnapshotData | null>(cached);
  useEffect(() => {
    if (!enabled || cached) return;
    if (!inflight) {
      inflight = fetch("/snapshot.json", { cache: "force-cache" }).then((r) => r.json());
    }
    inflight.then((d) => {
      cached = d;
      setData(d);
    });
  }, [enabled]);
  return data;
}
