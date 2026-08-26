import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { computeSummary } from "@/lib/analytics";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = db();
  const [{ data: sightings }, { count: openAlerts }, { count: openReview }] = await Promise.all([
    supabase.from("sightings").select("*"),
    supabase.from("alerts").select("*", { count: "exact", head: true }).eq("acknowledged", false),
    supabase.from("review_cases").select("*", { count: "exact", head: true }).eq("status", "open"),
  ]);
  const summary = computeSummary((sightings ?? []) as any, openAlerts ?? 0, openReview ?? 0);
  return NextResponse.json({ summary });
}
