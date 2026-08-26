import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { buildLegs, fuzzyMergedFrom } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export async function GET(_req: Request, props: { params: Promise<{ plate: string }> | { plate: string } }) {
  const params = await props.params;
  const plate = decodeURIComponent(params.plate).toUpperCase();
  const supabase = db();
  const [{ data: sightings, error }, { data: cameras }, { data: links }, { data: watchEntry }] =
    await Promise.all([
      supabase.from("sightings").select("*").eq("plate_text", plate).order("ts"),
      supabase.from("cameras").select("*"),
      supabase.from("camera_links").select("*"),
      supabase.from("watchlist").select("*").eq("plate_text", plate).maybeSingle(),
    ]);

  if (error) {
    return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  }
  if (!sightings || sightings.length === 0) {
    return NextResponse.json(
      { error: { code: "PLATE_NOT_FOUND", message: `No sightings for plate ${plate}.` } },
      { status: 404 }
    );
  }

  const legs = buildLegs(sightings as any, (links ?? []) as any, (cameras ?? []) as any);
  const merged = fuzzyMergedFrom(sightings as any, plate);

  return NextResponse.json({
    plate_text: plate,
    sightings,
    legs,
    fuzzy_merged_from: merged,
    watchlist_status: watchEntry?.status ?? null,
  });
}
