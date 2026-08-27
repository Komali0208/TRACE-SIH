"use client";
import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { useDataMode } from "@/lib/mode";
import { useSnapshot } from "@/lib/useSnapshot";
import { Skeleton } from "@/components/Chips";
import { computeHeatmap, computeTravelTimes } from "@/lib/analytics";
import { fmtTime } from "@/lib/utils";
import { Camera } from "@/lib/types";

const MapView = dynamic(() => import("@/components/MapView").then((m) => m.MapView), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

export default function AnalyticsPage() {
  const { mode } = useDataMode();
  const snap = useSnapshot(mode === "cached");
  const [cameras, setCameras] = useState<Camera[] | null>(null);
  const [travel, setTravel] = useState<any[] | null>(null);
  const [heat, setHeat] = useState<any | null>(null);

  useEffect(() => {
    if (mode === "live") {
      fetch("/api/cameras").then((r) => r.json()).then((d) => setCameras(d.cameras));
      fetch("/api/analytics/travel-times").then((r) => r.json()).then((d) => setTravel(d.travel_times));
      fetch("/api/analytics/heatmap").then((r) => r.json()).then((d) => setHeat(d));
    } else if (mode === "cached" && snap) {
      setCameras(snap.cameras);
      setTravel(computeTravelTimes(snap.sightings, snap.camera_links));
      setHeat(computeHeatmap(snap.sightings, snap.cameras));
    }
  }, [mode, snap]);

  const camName = (id: string) => cameras?.find((c) => c.id === id)?.name.split("—")[0].trim() ?? id;

  const hourlyChart = useMemo(
    () =>
      (heat?.hourly ?? []).map((h: any) => ({
        hour: fmtTime(h.hour).slice(0, 5),
        count: h.count,
      })),
    [heat]
  );

  const maxOd = useMemo(() => Math.max(1, ...(heat?.od_matrix ?? []).map((o: any) => o.count)), [heat]);

  const loading = !cameras || !travel || !heat;

  return (
    <div className="p-4 sm:p-6 max-w-[1600px] mx-auto">
      <div className="mb-5">
        <div className="eyebrow mb-1">Analytics</div>
        <h1 className="font-display text-2xl sm:text-3xl font-semibold">Grid-wide traffic intelligence</h1>
        <p className="text-sm text-[var(--muted)] mt-1">
          Travel times, volume, camera density and origin-destination flow, computed live from sighting pairs.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mb-4">
        <div className="card p-4">
          <div className="eyebrow mb-3">Travel times · congested pairs first</div>
          {loading ? (
            <Skeleton className="h-72" />
          ) : (
            <div className="flex flex-col divide-y divide-[var(--border)]">
              {travel!.map((t) => (
                <div key={`${t.from_camera}-${t.to_camera}`} className="py-2.5 flex items-center gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="text-xs font-medium truncate">
                      {camName(t.from_camera)} → {camName(t.to_camera)}
                    </div>
                    <div className="font-data text-[10px] text-[var(--muted)]">
                      {t.sample_count} samples · median {t.median_seconds}s · now {t.current_seconds}s
                    </div>
                  </div>
                  <div className="w-24 shrink-0">
                    <div className="h-1.5 rounded-full bg-[var(--surface-2)] overflow-hidden">
                      <div
                        className="h-full rounded-full"
                        style={{
                          width: `${Math.min(100, (t.delay_ratio / 2) * 100)}%`,
                          background: t.congested ? "var(--warn)" : "var(--ok)",
                        }}
                      />
                    </div>
                  </div>
                  <span
                    className="font-data text-xs w-10 text-right"
                    style={{ color: t.congested ? "var(--warn)" : "var(--ok)" }}
                  >
                    {t.delay_ratio}×
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="card p-4">
          <div className="eyebrow mb-3">Hourly sighting volume</div>
          {loading ? (
            <Skeleton className="h-72" />
          ) : (
            <ResponsiveContainer width="100%" height={288}>
              <BarChart data={hourlyChart}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                <XAxis dataKey="hour" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} width={28} />
                <Tooltip
                  contentStyle={{ background: "var(--surface-2)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: "rgba(122,59,46,0.08)" }}
                />
                <Bar dataKey="count" fill="var(--signal)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="eyebrow mb-3">Camera density</div>
          {loading ? (
            <Skeleton className="h-80" />
          ) : (
            <div className="h-80 rounded-lg overflow-hidden relative">
              <MapView cameras={cameras!} activeIds={new Set(cameras!.map((c) => c.id))} />
              <div className="absolute bottom-3 left-3 z-[400] glass rounded-lg px-3 py-2 max-h-32 overflow-y-auto">
                {heat!.per_camera
                  .slice()
                  .sort((a: any, b: any) => b.count - a.count)
                  .map((p: any) => (
                    <div key={p.camera_id} className="flex items-center justify-between gap-4 text-[11px] py-0.5">
                      <span className="text-[var(--muted)]">{camName(p.camera_id)}</span>
                      <span className="font-data text-[var(--signal)]">{p.count}</span>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </div>

        <div className="card p-4 overflow-x-auto">
          <div className="eyebrow mb-3">Origin → destination matrix</div>
          {loading ? (
            <Skeleton className="h-80" />
          ) : (
            <table className="w-full text-[10px] font-data border-collapse">
              <thead>
                <tr>
                  <th className="p-1 text-left text-[var(--muted)]"> </th>
                  {cameras!.map((c) => (
                    <th key={c.id} className="p-1 text-[var(--muted)]">{c.id.replace("CAM", "")}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {cameras!.map((rowCam) => (
                  <tr key={rowCam.id}>
                    <td className="p-1 text-[var(--muted)] text-right pr-2">{rowCam.id.replace("CAM", "")}</td>
                    {cameras!.map((colCam) => {
                      const entry = heat!.od_matrix.find(
                        (o: any) => o.from_camera === rowCam.id && o.to_camera === colCam.id
                      );
                      const v = entry?.count ?? 0;
                      const alpha = v / maxOd;
                      return (
                        <td key={colCam.id} className="p-1 text-center">
                          <div
                            className="rounded w-6 h-6 flex items-center justify-center mx-auto"
                            style={{ background: v ? `rgba(122,59,46,${0.12 + alpha * 0.7})` : "transparent", color: v ? "#FBF8F1" : "var(--muted)" }}
                          >
                            {v || "·"}
                          </div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
