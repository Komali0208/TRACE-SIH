import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { computeTravelTimes } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = db();
  const [{ data: sightings }, { data: links }] = await Promise.all([
    supabase.from("sightings").select("*"),
    supabase.from("camera_links").select("*"),
  ]);
  const rows = computeTravelTimes((sightings ?? []) as any, (links ?? []) as any);
  return NextResponse.json({ travel_times: rows });
}
