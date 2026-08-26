import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { searchPlates } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url);
  const q = searchParams.get("q") ?? "";
  if (!q.trim()) return NextResponse.json({ matches: [] });
  const { data, error } = await db().from("sightings").select("plate_text,camera_id");
  if (error) {
    return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  }
  const matches = searchPlates(
    (data ?? []).map((d: any) => ({ ...d, id: "", ts: "", plate_confidence: 0, track_id: 0, frame_count: 0, raw_reads: [], consensus_method: "", crop_url: "", video_offset_s: 0, flags: [], region_guess: null })),
    q
  );
  return NextResponse.json({ matches });
}
