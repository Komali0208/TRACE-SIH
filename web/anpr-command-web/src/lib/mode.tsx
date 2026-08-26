"use client";
import { createContext, useContext, useEffect, useRef, useState } from "react";

type Mode = "checking" | "live" | "cached";

const ModeCtx = createContext<{ mode: Mode; generatedAt: string | null }>({
  mode: "checking",
  generatedAt: null,
});

export function DataModeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<Mode>("checking");
  const [generatedAt, setGeneratedAt] = useState<string | null>(null);
  const checked = useRef(false);

  useEffect(() => {
    if (checked.current) return;
    checked.current = true;
    const controller = new AbortController();
    const t = setTimeout(() => controller.abort(), 2000);
    fetch("/api/health", { signal: controller.signal, cache: "no-store" })
      .then((r) => {
        if (!r.ok) throw new Error("unhealthy");
        return r.json();
      })
      .then((j) => {
        setMode("live");
        setGeneratedAt(j.generated_at ?? null);
      })
      .catch(() => setMode("cached"))
      .finally(() => clearTimeout(t));
  }, []);

  return <ModeCtx.Provider value={{ mode, generatedAt }}>{children}</ModeCtx.Provider>;
}

export function useDataMode() {
  return useContext(ModeCtx);
}
