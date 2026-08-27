"use client";
import { createContext, useCallback, useContext, useMemo, useState } from "react";

type RegistryCtx = {
  openRegistry: (plate: string) => void;
  closeRegistry: () => void;
  plate: string | null;
};

const Ctx = createContext<RegistryCtx>({
  openRegistry: () => {},
  closeRegistry: () => {},
  plate: null,
});

export function useRegistry() {
  return useContext(Ctx);
}

export function RegistryContextProvider({ children }: { children: React.ReactNode }) {
  const [plate, setPlate] = useState<string | null>(null);

  const openRegistry = useCallback((p: string) => {
    const cleaned = p.trim().toUpperCase();
    if (cleaned) setPlate(cleaned);
  }, []);

  const closeRegistry = useCallback(() => setPlate(null), []);

  const value = useMemo(
    () => ({ openRegistry, closeRegistry, plate }),
    [openRegistry, closeRegistry, plate]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}
