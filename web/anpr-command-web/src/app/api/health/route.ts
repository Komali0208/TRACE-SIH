import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    const { data, error } = await db().from("app_meta").select("generated_at").eq("id", 1).single();
    if (error) throw error;
    return NextResponse.json({
      status: "ok",
      schema_version: "1.0",
      generated_at: data?.generated_at ?? new Date().toISOString(),
      mode: "live",
    });
  } catch (e) {
    return NextResponse.json(
      { error: { code: "DB_UNAVAILABLE", message: "Database not reachable" } },
      { status: 503 }
    );
  }
}
