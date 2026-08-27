import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = db();
  const [cameras, links, sightings, watchlist, meta, registry] = await Promise.all([
    supabase.from("cameras").select("*").order("id"),
    supabase.from("camera_links").select("*"),
    supabase.from("sightings").select("*").order("ts"),
    supabase.from("watchlist").select("*"),
    supabase.from("app_meta").select("*").eq("id", 1).single(),
    supabase.from("vehicle_registry").select("*"),
  ]);
  return NextResponse.json({
    schema_version: "1.0",
    generated_at: meta.data?.generated_at,
    meta: {
      source: "live",
      cameras_count: cameras.data?.length ?? 0,
      sightings_count: sightings.data?.length ?? 0,
      unique_plates: new Set((sightings.data ?? []).map((s: any) => s.plate_text).filter(Boolean)).size,
      ocr_model: meta.data?.ocr_model,
      footage_note: meta.data?.footage_note,
      hero_plates: meta.data?.hero_plates ?? [],
      clone_plate: meta.data?.clone_plate,
    },
    cameras: cameras.data,
    camera_links: links.data,
    sightings: sightings.data,
    watchlist: watchlist.data,
    registry: registry.data ?? [],
  });
}
