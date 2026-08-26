import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function GET() {
  const supabase = db();
  const [cameras, links] = await Promise.all([
    supabase.from("cameras").select("*").order("id"),
    supabase.from("camera_links").select("*"),
  ]);
  return NextResponse.json({ cameras: cameras.data ?? [], camera_links: links.data ?? [] });
}
