"use client";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { useEffect, useMemo } from "react";
import { Camera } from "@/lib/types";

function markerIcon(active: boolean, danger = false) {
  const color = danger ? "#E0483B" : active ? "#4CC3C8" : "#8494A1";
  return L.divIcon({
    className: "",
    html: `<div style="position:relative;width:14px;height:14px;">
      <div style="position:absolute;inset:0;border-radius:50%;background:${color};box-shadow:0 0 0 2px #0B1014, 0 0 10px ${color}99;${
      active ? `animation:pulseMarker 2.2s ease-out infinite;` : ""
    }"></div>
    </div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 1) {
      map.fitBounds(points, { padding: [40, 40] });
    }
  }, [points, map]);
  return null;
}

export function MapView({
  cameras,
  activeIds = new Set<string>(),
  onSelectCamera,
  routePoints,
  routeAnomalyIndex,
  height = "100%",
}: {
  cameras: Camera[];
  activeIds?: Set<string>;
  onSelectCamera?: (id: string) => void;
  routePoints?: { lat: number; lon: number; danger?: boolean }[];
  routeAnomalyIndex?: number;
  height?: string;
}) {
  const center = useMemo<[number, number]>(() => [12.94, 77.63], []);
  const path = (routePoints ?? []).map((p) => [p.lat, p.lon]) as [number, number][];

  return (
    <div style={{ height, width: "100%" }} className="overflow-hidden rounded-xl">
      <MapContainer center={center} zoom={11} style={{ height: "100%", width: "100%" }} zoomControl={true}>
        <TileLayer
          attribution='&copy; <a href="https://carto.com/attributions">CARTO</a>'
          url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
        />
        {cameras.map((c) => (
          <Marker
            key={c.id}
            position={[c.lat, c.lon]}
            icon={markerIcon(activeIds.has(c.id))}
            eventHandlers={{ click: () => onSelectCamera?.(c.id) }}
          >
            <Popup>
              <div className="font-body text-xs">
                <div className="font-semibold">{c.name}</div>
                <div className="text-[var(--muted)]">
                  {c.road_name} · {c.direction}
                </div>
              </div>
            </Popup>
          </Marker>
        ))}
        {path.length > 1 && (
          <>
            <Polyline positions={path} pathOptions={{ color: "#4CC3C8", weight: 3, opacity: 0.9 }} />
            <FitBounds points={path} />
          </>
        )}
      </MapContainer>
    </div>
  );
}
