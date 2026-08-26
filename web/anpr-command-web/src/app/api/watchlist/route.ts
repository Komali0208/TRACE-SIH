import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  const { data, error } = await db().from("watchlist").select("*").order("added_at", { ascending: false });
  if (error) return NextResponse.json({ error: { code: "QUERY_FAILED", message: error.message } }, { status: 500 });
  return NextResponse.json({ watchlist: data ?? [] });
}

export async function POST(req: Request) {
  const body = await req.json().catch(() => ({}));
  const plate_text = (body.plate_text as string | undefined)?.trim().toUpperCase();
  const status = body.status as "stolen" | "blacklisted" | "flagged";
  const reason = (body.reason as string | undefined) ?? "";

  if (!plate_text || !["stolen", "blacklisted", "flagged"].includes(status)) {
    return NextResponse.json(
      { error: { code: "INVALID_INPUT", message: "plate_text and a valid status are required" } },
      { status: 400 }
    );
  }

  const supabase = db();
  const { data: entry, error } = await supabase
    .from("watchlist")
    .upsert({ plate_text, status, reason, added_at: new Date().toISOString() })
    .select()
    .single();
  if (error) return NextResponse.json({ error: { code: "INSERT_FAILED", message: error.message } }, { status: 500 });

  // Live scan: generate alerts for every existing sighting of this plate,
  // so adding a plate here makes the Alerts screen react immediately.
  const { data: matches } = await supabase.from("sightings").select("*").eq("plate_text", plate_text);
  const newAlerts = (matches ?? []).map((s: any) => ({
    id: `ALT_${s.id.replace("SGT_", "")}_${Date.now().toString(36)}`,
    sighting_id: s.id,
    plate_text,
    watchlist_status: status,
    ts: s.ts,
    acknowledged: false,
  }));
  if (newAlerts.length) {
    await supabase.from("alerts").upsert(newAlerts, { onConflict: "id", ignoreDuplicates: true });
  }

  return NextResponse.json({ entry, alerts_generated: newAlerts.length });
}

export async function DELETE(req: Request) {
  const { searchParams } = new URL(req.url);
  const plate = searchParams.get("plate")?.toUpperCase();
  if (!plate) {
    return NextResponse.json({ error: { code: "INVALID_INPUT", message: "plate query param required" } }, { status: 400 });
  }
  const { error } = await db().from("watchlist").delete().eq("plate_text", plate);
  if (error) return NextResponse.json({ error: { code: "DELETE_FAILED", message: error.message } }, { status: 500 });
  return NextResponse.json({ ok: true });
}
