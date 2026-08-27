"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { PlateChip } from "@/components/PlateChip";
import { CropThumb } from "@/components/CropThumb";
import { StatusBadge, Skeleton } from "@/components/Chips";
import { fmtTime, relTime, isValidPlate } from "@/lib/utils";
import { Alert, WatchlistEntry } from "@/lib/types";

export default function AlertsPage() {
  const { mode } = useDataMode();
  const snap = useSnapshot(mode === "cached");
  const [alerts, setAlerts] = useState<Alert[] | null>(null);
  const [watchlist, setWatchlist] = useState<WatchlistEntry[] | null>(null);

  const [plate, setPlate] = useState("");
  const [status, setStatus] = useState<"stolen" | "blacklisted" | "flagged">("flagged");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  function loadLive() {
    fetch("/api/alerts").then((r) => r.json()).then((d) => setAlerts(d.alerts));
    fetch("/api/watchlist").then((r) => r.json()).then((d) => setWatchlist(d.watchlist));
  }

  useEffect(() => {
    if (mode === "live") {
      loadLive();
    } else if (mode === "cached" && snap) {
      const camMap = new Map(snap.cameras.map((c) => [c.id, c]));
      const wl = new Map(snap.watchlist.map((w) => [w.plate_text, w]));
      const cachedAlerts: Alert[] = snap.sightings
        .filter((s) => s.plate_text && wl.has(s.plate_text))
        .map((s) => ({
          id: `A_${s.id}`,
          sighting_id: s.id,
          plate_text: s.plate_text!,
          watchlist_status: wl.get(s.plate_text!)!.status,
          ts: s.ts,
          acknowledged: false,
          sighting: s,
        }))
        .sort((a, b) => +new Date(b.ts) - +new Date(a.ts));
      setAlerts(cachedAlerts);
      setWatchlist(snap.watchlist);
    }
  }, [mode, snap]);

  async function acknowledge(id: string) {
    if (mode !== "live") return;
    await fetch(`/api/alerts/${id}/acknowledge`, { method: "POST" });
    loadLive();
  }

  async function addToWatchlist() {
    setError(null);
    const p = plate.trim().toUpperCase();
    if (!isValidPlate(p)) {
      setError("Enter a valid plate, e.g. KA05MH1234");
      return;
    }
    if (mode !== "live") {
      setError("Live backend unavailable — watchlist changes require a live connection.");
      return;
    }
    setBusy(true);
    const res = await fetch("/api/watchlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plate_text: p, status, reason }),
    });
    setBusy(false);
    if (!res.ok) {
      const j = await res.json().catch(() => ({}));
      setError(j?.error?.message ?? "Failed to add plate");
      return;
    }
    const d = await res.json();
    setToast(`${p} added — ${d.alerts_generated} alert${d.alerts_generated === 1 ? "" : "s"} generated from existing sightings`);
    setPlate("");
    setReason("");
    loadLive();
    setTimeout(() => setToast(null), 4500);
  }

  async function removeFromWatchlist(p: string) {
    if (mode !== "live") return;
    await fetch(`/api/watchlist?plate=${p}`, { method: "DELETE" });
    loadLive();
  }

  const loading = !alerts || !watchlist;
  const cameraName = (id?: string) => snap?.cameras.find((c) => c.id === id)?.name ?? id;

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
      <div className="mb-5">
        <div className="eyebrow mb-1">Alerts</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">Watchlist hits</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Every sighting cross-referenced against the watchlist in real time. Add a plate below and any existing
          sighting immediately generates an alert.
        </p>
      </div>

      {toast && (
        <div className="card p-3 mb-4 border-[var(--ok)]/40 text-xs text-[var(--ok)]" style={{ borderColor: "rgba(79,169,107,0.4)" }}>
          {toast}
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        <div className="flex flex-col gap-3">
          {loading
            ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-24" />)
            : alerts!.map((a) => (
                <div key={a.id} className="card p-3 flex items-center gap-3 animate-rise">
                  <CropThumb
                    cameraLabel={a.sighting?.camera_id ?? ""}
                    offset={a.sighting?.video_offset_s ?? 0}
                    className="h-16 w-20 shrink-0"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <PlateChip plate={a.plate_text} size="sm" />
                      <StatusBadge status={a.watchlist_status} />
                    </div>
                    <div className="text-xs font-medium truncate">{cameraName(a.sighting?.camera_id)}</div>
                    <div className="font-data text-[10px] text-[var(--muted)] mt-0.5">{fmtTime(a.ts)} · {relTime(a.ts)}</div>
                  </div>
                  <div className="flex flex-col gap-1.5 items-end shrink-0">
                    <Link href={`/trajectory?plate=${a.plate_text}`} className="text-[11px] text-[var(--signal)] hover:underline">
                      View trajectory →
                    </Link>
                    {!a.acknowledged && mode === "live" && (
                      <button
                        onClick={() => acknowledge(a.id)}
                        className="text-[11px] text-[var(--muted)] hover:text-[var(--text)] border border-[var(--border)] rounded px-2 py-0.5"
                      >
                        Acknowledge
                      </button>
                    )}
                    {a.acknowledged && <span className="eyebrow text-[var(--ok)]">Acknowledged</span>}
                  </div>
                </div>
              ))}
          {!loading && alerts!.length === 0 && (
            <div className="card p-10 text-center">
              <div className="font-display text-lg mb-1">No alerts</div>
              <p className="text-sm text-[var(--muted)]">No watchlisted plates have been sighted.</p>
            </div>
          )}
        </div>

        <div className="flex flex-col gap-4">
          <div className="card p-4">
            <div className="eyebrow mb-3">Add to watchlist</div>
            <div className="flex flex-col gap-2">
              <input
                value={plate}
                onChange={(e) => setPlate(e.target.value.toUpperCase())}
                placeholder="KA05MH1234"
                className="font-data uppercase bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--signal)]"
              />
              <select
                value={status}
                onChange={(e) => setStatus(e.target.value as any)}
                className="bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--signal)]"
              >
                <option value="flagged">Flagged</option>
                <option value="blacklisted">Blacklisted</option>
                <option value="stolen">Stolen</option>
              </select>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason (e.g. FIR 442/2026)"
                className="bg-[var(--surface-2)] border border-[var(--border)] rounded-lg px-3 py-2 text-sm outline-none focus:border-[var(--signal)]"
              />
              {error && <div className="text-[11px] text-[var(--danger)]">{error}</div>}
              <button
                disabled={busy}
                onClick={addToWatchlist}
                title={mode !== "live" ? "Live backend unavailable — showing cached data." : undefined}
                className="rounded-lg bg-[var(--signal)] text-[#FBF8F1] text-sm font-semibold py-2 disabled:opacity-50"
              >
                Add plate
              </button>
            </div>
          </div>

          <div className="card p-4">
            <div className="eyebrow mb-3">Watchlist ({watchlist?.length ?? 0})</div>
            <div className="flex flex-col divide-y divide-[var(--border)]">
              {loading
                ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-12 my-1" />)
                : watchlist!.map((w) => (
                    <div key={w.plate_text} className="py-2.5 flex items-center justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <PlateChip plate={w.plate_text} size="sm" />
                          <StatusBadge status={w.status} />
                        </div>
                        <div className="text-[11px] text-[var(--muted)] truncate">{w.reason}</div>
                      </div>
                      {mode === "live" && (
                        <button
                          onClick={() => removeFromWatchlist(w.plate_text)}
                          className="text-[11px] text-[var(--muted)] hover:text-[var(--danger)] shrink-0"
                        >
                          Remove
                        </button>
                      )}
                    </div>
                  ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
