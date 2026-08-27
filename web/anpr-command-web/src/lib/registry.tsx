"use client";
import { RegistryContextProvider, useRegistry } from "@/lib/registry-context";
import { RegistryPanel } from "@/components/RegistryPanel";

export { useRegistry } from "@/lib/registry-context";

export function RegistryProvider({ children }: { children: React.ReactNode }) {
  return (
    <RegistryContextProvider>
      {children}
      <RegistryPanelHost />
    </RegistryContextProvider>
  );
}

function RegistryPanelHost() {
  const { plate, closeRegistry } = useRegistry();
  if (!plate) return null;
  return <RegistryPanel plate={plate} onClose={closeRegistry} />;
}
