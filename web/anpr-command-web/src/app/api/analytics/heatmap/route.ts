import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { computeHeatmap } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = db();
  const [{ data: sightings }, { data: cameras }] = await Promise.all([
    supabase.from("sightings").select("*"),
    supabase.from("cameras").select("*"),
  ]);
  const result = computeHeatmap((sightings ?? []) as any, (cameras ?? []) as any);
  return NextResponse.json(result);
}
