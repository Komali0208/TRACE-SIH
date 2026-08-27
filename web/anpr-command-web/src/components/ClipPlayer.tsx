"use client";

import { useEffect, useRef, useState } from "react";

export function ClipPlayer({
  src,
  offsetS,
  label,
  onClose,
}: {
  src?: string | null;
  offsetS: number;
  label?: string;
  onClose?: () => void;
}) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!src) {
      setReady(false);
      return;
    }
    let cancelled = false;
    fetch(src, { method: "HEAD" })
      .then((r) => {
        if (!cancelled) setReady(r.ok);
      })
      .catch(() => {
        if (!cancelled) setReady(false);
      });
    return () => {
      cancelled = true;
    };
  }, [src]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !ready) return;

    const seekAndPlay = () => {
      video.currentTime = offsetS;
      video.play().catch(() => {});
    };

    if (video.readyState >= 1) {
      seekAndPlay();
      return;
    }

    video.addEventListener("loadedmetadata", seekAndPlay);
    return () => video.removeEventListener("loadedmetadata", seekAndPlay);
  }, [src, offsetS, ready]);

  if (!src || !ready) return null;

  return (
    <div className="card overflow-hidden">
      {(label || onClose) && (
        <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-[var(--border)] bg-[var(--surface)]">
          {label ? (
            <span className="text-sm font-medium text-[var(--text)] truncate">{label}</span>
          ) : (
            <span />
          )}
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="shrink-0 rounded-md px-2 py-1 text-sm text-[var(--muted)] hover:text-[var(--text)] hover:bg-black/5"
              aria-label="Close player"
            >
              ✕
            </button>
          )}
        </div>
      )}
      <video
        ref={videoRef}
        key={src}
        src={src}
        controls
        playsInline
        onError={() => setReady(false)}
        className="w-full max-h-[280px] bg-[var(--surface-2)]"
      />
    </div>
  );
}
