import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const from = searchParams.get("from");
  const to = searchParams.get("to");
  const cameraId = searchParams.get("camera_id");
  const plate = searchParams.get("plate");
  const flagged = searchParams.get("flagged");
  const limit = Math.min(500, Number(searchParams.get("limit") ?? 100));
  const offset = Number(searchParams.get("offset") ?? 0);

  let q = db().from("sightings").select("*", { count: "exact" }).order("ts", { ascending: false });
  if (from) q = q.gte("ts", from);
  if (to) q = q.lte("ts", to);
  if (cameraId) q = q.eq("camera_id", cameraId);
  if (plate) q = q.ilike("plate_text", `%${plate}%`);
  if (flagged === "true") q = q.not("flags", "eq", "{}");
  q = q.range(offset, offset + limit - 1);

  const { data, error, count } = await q;
  if (error) {
    return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  }
  return NextResponse.json({ sightings: data ?? [], total: count ?? 0, limit, offset });
}
