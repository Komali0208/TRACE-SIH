import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import path from "path";
import { db } from "@/lib/supabase";

export const dynamic = "force-dynamic";

const SOURCE_NOTE =
  "Mock registry. Real VAHAN access requires authorised government\n  credentials.";

async function fromSnapshot(plate: string) {
  const file = path.join(process.cwd(), "public", "snapshot.json");
  const raw = await readFile(file, "utf-8");
  const data = JSON.parse(raw) as { registry?: Array<Record<string, unknown>> };
  const row = (data.registry ?? []).find(
    (r) => String(r.plate_text ?? "").toUpperCase() === plate
  );
  return row ?? null;
}

export async function GET(
  _req: Request,
  props: { params: Promise<{ plate: string }> | { plate: string } }
) {
  const params = await props.params;
  const plate = decodeURIComponent(params.plate).trim().toUpperCase();
  if (!plate) {
    return NextResponse.json(
      { error: { code: "INVALID_INPUT", message: "plate is required" } },
      { status: 400 }
    );
  }

  try {
    const { data, error } = await db()
      .from("vehicle_registry")
      .select("*")
      .eq("plate_text", plate)
      .maybeSingle();

    if (!error && data) {
      return NextResponse.json({ ...data, is_mock_data: true, source_note: SOURCE_NOTE });
    }
  } catch {
    // Table missing or unreachable — fall through to snapshot.
  }

  try {
    const row = await fromSnapshot(plate);
    if (row) {
      return NextResponse.json({ ...row, is_mock_data: true, source_note: SOURCE_NOTE });
    }
  } catch {
    // Snapshot unreadable
  }

  return NextResponse.json(
    {
      error: {
        code: "REGISTRY_NOT_FOUND",
        message: `No registry record for plate ${plate} in our mock dataset.`,
      },
    },
    { status: 404 }
  );
}
