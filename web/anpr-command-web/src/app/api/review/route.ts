import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const status = searchParams.get("status") ?? "open";
  const limit = Math.min(100, Number(searchParams.get("limit") ?? 50));

  const supabase = db();
  const { data: cases, error, count } = await supabase
    .from("review_cases")
    .select("*", { count: "exact" })
    .eq("status", status)
    .order("id")
    .limit(limit);

  if (error) {
    return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  }

  const sightingIds = (cases ?? []).map((c) => c.sighting_id);
  const { data: sightings } = await supabase.from("sightings").select("*").in("id", sightingIds);
  const byId = new Map((sightings ?? []).map((s: any) => [s.id, s]));

  const withSighting = (cases ?? []).map((c) => ({ ...c, sighting: byId.get(c.sighting_id) }));
  return NextResponse.json({ cases: withSighting, total: count ?? 0 });
}
