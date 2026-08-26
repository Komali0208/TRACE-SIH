import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const acknowledged = searchParams.get("acknowledged");
  const supabase = db();
  let q = supabase.from("alerts").select("*").order("ts", { ascending: false });
  if (acknowledged !== null) q = q.eq("acknowledged", acknowledged === "true");
  const { data: alerts, error } = await q;
  if (error) {
    return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  }
  const ids = (alerts ?? []).map((a) => a.sighting_id);
  const { data: sightings } = await supabase.from("sightings").select("*").in("id", ids);
  const byId = new Map((sightings ?? []).map((s: any) => [s.id, s]));
  const withSighting = (alerts ?? []).map((a) => ({ ...a, sighting: byId.get(a.sighting_id) }));
  return NextResponse.json({ alerts: withSighting });
}
