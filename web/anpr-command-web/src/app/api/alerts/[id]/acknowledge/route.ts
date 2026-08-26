import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

export async function POST(_req: Request, props: { params: Promise<{ id: string }> | { id: string } }) {
  const params = await props.params;
  const { data, error } = await db()
    .from("alerts")
    .update({ acknowledged: true })
    .eq("id", params.id)
    .select()
    .single();
  if (error) {
    return NextResponse.json({ error: { code: "UPDATE_FAILED", message: error.message } }, { status: 500 });
  }
  return NextResponse.json({ alert: data });
}
