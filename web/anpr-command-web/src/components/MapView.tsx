"use client";
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from "react-leaflet";
import L from "leaflet";
import { useEffect, useMemo } from "react";
import { Camera } from "@/lib/types";

function markerIcon(active: boolean, danger = false) {
  const color = danger ? "#A13A2E" : active ? "#7A3B2E" : "#6B6254";
  return L.divIcon({
    className: "",
    html: `<svg width="22" height="32" viewBox="0 0 22 32" fill="none" xmlns="http://www.w3.org/2000/svg" style="display:block">
      <path d="M11 1C5.477 1 1 5.477 1 11c0 7.5 10 19 10 19s10-11.5 10-19C21 5.477 16.523 1 11 1z"
        fill="${color}" stroke="#FBF8F1" stroke-width="1.5"/>
      <circle cx="11" cy="11" r="3.2" fill="#FBF8F1"/>
    </svg>`,
    iconSize: [22, 32],
    iconAnchor: [11, 32],
    popupAnchor: [0, -28],
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
          attribution='&copy; OpenStreetMap contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
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
            <Polyline positions={path} pathOptions={{ color: "#7A3B2E", weight: 4, opacity: 0.9 }} />
            <FitBounds points={path} />
          </>
        )}
      </MapContainer>
    </div>
  );
}
