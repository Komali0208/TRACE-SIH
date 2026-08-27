"use client";
import { useEffect, useState } from "react";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { Skeleton } from "@/components/Chips";
import { VehicleRegistryRecord } from "@/lib/types";

const BANNER =
  "This is simulated registry data for demonstration. Live deployment would query VAHAN directly, pending authorised access.";

const SOURCE_NOTE_FALLBACK =
  "Mock registry. Real VAHAN access requires authorised government\n  credentials.";

function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (s === "active") return "var(--ok)";
  if (s === "suspended") return "var(--warn)";
  if (s === "expired") return "var(--danger)";
  return "var(--muted)";
}

function isPast(isoDate: string): boolean {
  if (!isoDate) return false;
  const d = new Date(isoDate.length === 10 ? `${isoDate}T23:59:59Z` : isoDate);
  return !Number.isNaN(+d) && +d < Date.now();
}

function ValidityRow({ label, value }: { label: string; value: string }) {
  const expired = isPast(value);
  return (
    <div className="flex items-center justify-between gap-3 py-1.5 border-b border-[var(--border)]/60 last:border-0">
      <span className="text-xs text-[var(--muted)]">{label}</span>
      <span
        className="font-data text-xs flex items-center gap-1.5"
        style={{ color: expired ? "var(--warn)" : "var(--text)" }}
      >
        {expired && (
          <span aria-hidden className="text-[var(--warn)]" title="Expired">
            ⚠
          </span>
        )}
        {value}
      </span>
    </div>
  );
}

export function RegistryPanel({ plate, onClose }: { plate: string; onClose: () => void }) {
  const { mode } = useDataMode();
  const snap = useSnapshot(true);
  const [record, setRecord] = useState<VehicleRegistryRecord | null | undefined>(undefined);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setRecord(undefined);
    setErrorMsg(null);

    async function load() {
      if (mode === "checking") return;

      if (mode === "cached") {
        if (!snap) return;
        const rows = snap.registry ?? [];
        const hit = rows.find((r) => r.plate_text.toUpperCase() === plate) ?? null;
        if (!cancelled) {
          setRecord(hit);
          if (!hit) setErrorMsg("No registry record for this plate in our mock dataset");
        }
        return;
      }

      try {
        const res = await fetch(`/api/registry/${encodeURIComponent(plate)}`);
        if (cancelled) return;
        if (res.status === 404) {
          setRecord(null);
          setErrorMsg("No registry record for this plate in our mock dataset");
          return;
        }
        if (!res.ok) {
          if (!snap) return;
          const fromSnap = (snap.registry ?? []).find((r) => r.plate_text.toUpperCase() === plate) ?? null;
          setRecord(fromSnap);
          if (!fromSnap) setErrorMsg("No registry record for this plate in our mock dataset");
          return;
        }
        const data = (await res.json()) as VehicleRegistryRecord;
        setRecord(data);
      } catch {
        if (cancelled) return;
        if (!snap) return;
        const fromSnap = (snap.registry ?? []).find((r) => r.plate_text.toUpperCase() === plate) ?? null;
        setRecord(fromSnap);
        if (!fromSnap) setErrorMsg("No registry record for this plate in our mock dataset");
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, [plate, mode, snap]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const loading = record === undefined && !errorMsg;

  return (
    <div className="fixed inset-0 z-[600] flex justify-end" role="dialog" aria-modal="true" aria-label="Vehicle registry">
      <button
        type="button"
        className="absolute inset-0 bg-black/35 border-0 cursor-default"
        aria-label="Close registry panel"
        onClick={onClose}
      />
      <aside className="relative h-full w-full max-w-md flex flex-col bg-[var(--surface)] border-l border-[var(--border)] shadow-panel animate-rise">
        <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-[var(--border)]">
          <div>
            <div className="eyebrow mb-1">Vehicle registry</div>
            <span
              className="inline-flex items-center justify-center h-6 min-w-[92px] text-[11px] px-1.5 shrink-0 rounded-[3px] border-2 border-black font-data font-bold tracking-wider text-[var(--plate-ink)]"
              style={{ background: "var(--plate-white)", boxShadow: "0 1px 3px rgba(0,0,0,0.5)" }}
            >
              {plate}
            </span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-[var(--muted)] hover:text-[var(--text)] px-2 py-1 rounded-md hover:bg-black/5"
          >
            Close
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {loading && (
            <div className="space-y-3">
              <Skeleton className="h-8 w-2/3" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-16 w-full" />
            </div>
          )}

          {!loading && !record && (
            <div className="card p-5 text-center">
              <div className="font-display text-base mb-1">No registry record</div>
              <p className="text-sm text-[var(--muted)]">
                {errorMsg ?? "No registry record for this plate in our mock dataset"}
              </p>
            </div>
          )}

          {!loading && record && (
            <div className="space-y-4">
              <div className="card p-4">
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div>
                    <div className="eyebrow mb-1">Owner</div>
                    <div className="font-display text-xl leading-tight">{record.owner_name}</div>
                  </div>
                  <span
                    className="eyebrow inline-flex items-center rounded-full px-2 py-0.5 border shrink-0"
                    style={{
                      color: statusColor(record.registration_status),
                      borderColor: `${statusColor(record.registration_status)}55`,
                      background: `${statusColor(record.registration_status)}18`,
                    }}
                  >
                    {record.registration_status}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <div className="eyebrow mb-0.5">Class</div>
                    <div>{record.vehicle_class}</div>
                  </div>
                  <div>
                    <div className="eyebrow mb-0.5">Fuel</div>
                    <div>{record.fuel_type}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="eyebrow mb-0.5">Make / model</div>
                    <div>{record.make_model}</div>
                  </div>
                  <div className="col-span-2">
                    <div className="eyebrow mb-0.5">Registering authority</div>
                    <div>{record.registering_authority}</div>
                  </div>
                  <div>
                    <div className="eyebrow mb-0.5">Registered</div>
                    <div className="font-data text-xs">{record.registration_date}</div>
                  </div>
                </div>
              </div>

              <div className="card p-4">
                <div className="eyebrow mb-2">Validity</div>
                <ValidityRow label="Fitness valid until" value={record.fitness_valid_until} />
                <ValidityRow label="Insurance valid until" value={record.insurance_valid_until} />
                <ValidityRow label="PUC valid until" value={record.puc_valid_until} />
              </div>

              <p className="text-[11px] text-[var(--muted)] font-data whitespace-pre-line">
                {record.source_note ?? SOURCE_NOTE_FALLBACK}
              </p>
            </div>
          )}
        </div>

        <div
          className="shrink-0 px-4 py-3 border-t text-xs leading-snug"
          style={{
            borderColor: "rgba(196,132,42,0.45)",
            background: "rgba(196,132,42,0.12)",
            color: "var(--warn)",
          }}
        >
          {BANNER}
        </div>
      </aside>
    </div>
  );
}
