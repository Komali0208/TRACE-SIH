"use client";
import { useEffect, useMemo, useState } from "react";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { PlateChip } from "@/components/PlateChip";
import { CropThumb } from "@/components/CropThumb";
import { ConsensusVote } from "@/components/ConsensusVote";
import { FlagChip, Skeleton } from "@/components/Chips";
import { isValidPlate, voteConsensus, fmtTime } from "@/lib/utils";
import { ReviewCase } from "@/lib/types";

function ReviewCard({
  c,
  cached,
  onDone,
}: {
  c: ReviewCase;
  cached: boolean;
  onDone: (id: string) => void;
}) {
  const [correcting, setCorrecting] = useState(false);
  const [value, setValue] = useState(c.sighting?.plate_text ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);

  const reads = c.sighting?.raw_reads ?? [];
  const derived = useMemo(() => voteConsensus(reads), [reads]);
  const consensus = c.sighting?.plate_text ?? derived;

  async function act(action: "accepted" | "corrected" | "rejected") {
    if (cached) return;
    if (action === "corrected" && !isValidPlate(value)) {
      setError("Must match plate format, e.g. KA05MH1234");
      return;
    }
    setBusy(true);
    setError(null);
    const res = await fetch(`/api/review/${c.id}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, corrected_plate: action === "corrected" ? value : undefined }),
    });
    setBusy(false);
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setError(j?.error?.message ?? "Action failed");
      return;
    }
    setStatus(action);
    setTimeout(() => onDone(c.id), 550);
  }

  return (
    <div className={`card p-4 flex flex-col gap-3 transition-all ${status ? "opacity-0 scale-[0.98]" : "animate-rise"}`}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <FlagChip flag={c.flag_type} />
          <span className="font-data text-[10px] text-[var(--muted)]">{c.sighting && fmtTime(c.sighting.ts)}</span>
        </div>
        <span className="font-data text-[10px] text-[var(--muted)]">{c.sighting_id}</span>
      </div>

      <div className="flex gap-3">
        <CropThumb cameraLabel={c.sighting?.camera_id ?? ""} offset={c.sighting?.video_offset_s ?? 0} className="h-24 w-28 shrink-0" />
        <div className="flex-1 min-w-0">
          <ConsensusVote
            reads={reads}
            consensus={consensus}
            frameCount={c.sighting?.frame_count}
            method={c.sighting?.consensus_method}
          />
        </div>
      </div>

      {status ? (
        <div className="text-xs eyebrow" style={{ color: status === "rejected" ? "var(--danger)" : "var(--ok)" }}>
          {status}
        </div>
      ) : correcting ? (
        <div className="flex flex-col gap-2 border-t border-[var(--border)] pt-3">
          <input
            value={value}
            onChange={(e) => setValue(e.target.value.toUpperCase())}
            className="font-data uppercase bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--signal)]"
            placeholder="KA05MH1234"
          />
          {error && <div className="text-[11px] text-[var(--danger)]">{error}</div>}
          <div className="flex gap-2">
            <button
              disabled={busy}
              onClick={() => act("corrected")}
              className="flex-1 rounded-lg bg-[var(--signal)] text-[#FBF8F1] text-xs font-semibold py-2 disabled:opacity-50"
            >
              Save correction
            </button>
            <button onClick={() => setCorrecting(false)} className="rounded-lg border border-[var(--border)] text-xs px-3">
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <div className="flex gap-2 border-t border-[var(--border)] pt-3" title={cached ? "Live backend unavailable — showing cached review cases." : undefined}>
          <button
            disabled={cached || busy}
            onClick={() => act("accepted")}
            className="flex-1 rounded-lg border border-[var(--ok)]/40 text-[var(--ok)] text-xs font-semibold py-2 hover:bg-[var(--ok)]/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Accept
          </button>
          <button
            disabled={cached || busy}
            onClick={() => setCorrecting(true)}
            className="flex-1 rounded-lg border border-[var(--signal)]/40 text-[var(--signal)] text-xs font-semibold py-2 hover:bg-[var(--signal)]/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Correct
          </button>
          <button
            disabled={cached || busy}
            onClick={() => act("rejected")}
            className="flex-1 rounded-lg border border-[var(--danger)]/40 text-[var(--danger)] text-xs font-semibold py-2 hover:bg-[var(--danger)]/10 disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Reject
          </button>
        </div>
      )}
    </div>
  );
}

export default function ReviewPage() {
  const { mode } = useDataMode();
  const snap = useSnapshot(mode === "cached");
  const [cases, setCases] = useState<ReviewCase[] | null>(null);

  useEffect(() => {
    if (mode === "live") {
      fetch("/api/review?status=open&limit=50").then((r) => r.json()).then((d) => setCases(d.cases));
    } else if (mode === "cached" && snap) {
      // Cached fallback: recompute the flagged set from the snapshot directly.
      const flagged = snap.sightings.filter((s) => s.flags.length > 0);
      setCases(
        flagged.map((s) => ({
          id: `RVW_${s.id}`,
          sighting_id: s.id,
          flag_type: s.flags[0],
          status: "open" as const,
          corrected_plate: null,
          reviewed_at: null,
          sighting: s,
        }))
      );
    }
  }, [mode, snap]);

  function remove(id: string) {
    setCases((prev) => (prev ? prev.filter((c) => c.id !== id) : prev));
  }

  const loading = !cases;

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
      <div className="mb-5">
        <div className="eyebrow mb-1">Review queue</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">Multi-frame OCR, made auditable</h1>
        <p className="text-sm text-[var(--muted)] mt-1 max-w-2xl">
          Every flagged sighting shows its raw per-frame reads converging into one consensus plate — character-vote
          across frames, not a single guess. Accept, correct, or reject each case.
        </p>
      </div>

      {mode === "cached" && (
        <div className="card p-3 mb-4 border-[var(--warn)]/40 text-xs text-[var(--warn)]" style={{ borderColor: "rgba(232,148,46,0.4)" }}>
          Live backend unavailable — showing cached review cases. Actions are visible but disabled.
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {loading
          ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-64" />)
          : cases!.map((c) => <ReviewCard key={c.id} c={c} cached={mode === "cached"} onDone={remove} />)}
      </div>

      {!loading && cases!.length === 0 && (
        <div className="card p-10 text-center mt-4">
          <div className="font-display text-lg mb-1">Queue clear</div>
          <p className="text-sm text-[var(--muted)]">No open review cases right now.</p>
        </div>
      )}
    </div>
  );
}
