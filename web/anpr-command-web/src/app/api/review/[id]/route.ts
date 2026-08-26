import { NextResponse } from "next/server";
import { db } from "@/lib/supabase";
import { isValidPlate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export async function POST(req: Request, props: { params: Promise<{ id: string }> | { id: string } }) {
  const params = await props.params;
  const body = await req.json().catch(() => ({}));
  const action = body.action as "accepted" | "corrected" | "rejected";
  const correctedPlate = (body.corrected_plate as string | undefined)?.trim().toUpperCase();

  if (!["accepted", "corrected", "rejected"].includes(action)) {
    return NextResponse.json(
      { error: { code: "INVALID_ACTION", message: "action must be accepted, corrected, or rejected" } },
      { status: 400 }
    );
  }
  if (action === "corrected") {
    if (!correctedPlate || !isValidPlate(correctedPlate)) {
      return NextResponse.json(
        { error: { code: "INVALID_PLATE_FORMAT", message: "Corrected plate must match XX##[X..XXX]#### format" } },
        { status: 400 }
      );
    }
  }

  const supabase = db();
  const { data: existing, error: fetchErr } = await supabase
    .from("review_cases")
    .select("*")
    .eq("id", params.id)
    .single();
  if (fetchErr || !existing) {
    return NextResponse.json({ error: { code: "NOT_FOUND", message: "Review case not found" } }, { status: 404 });
  }

  const { data: updated, error } = await supabase
    .from("review_cases")
    .update({
      status: action,
      corrected_plate: action === "corrected" ? correctedPlate : null,
      reviewed_at: new Date().toISOString(),
    })
    .eq("id", params.id)
    .select()
    .single();

  if (error) {
    return NextResponse.json({ error: { code: "UPDATE_FAILED", message: error.message } }, { status: 500 });
  }

  if (action === "corrected" && correctedPlate) {
    await supabase
      .from("sightings")
      .update({ plate_text: correctedPlate, flags: [] })
      .eq("id", existing.sighting_id);
  }

  return NextResponse.json({ case: updated });
}
