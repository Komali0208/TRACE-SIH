import type { Metadata } from "next";
import "./globals.css";
import "leaflet/dist/leaflet.css";
import { Sidebar } from "@/components/Sidebar";
import { DataModeProvider } from "@/lib/mode";
import { RegistryProvider } from "@/lib/registry";
import { TopBar } from "@/components/TopBar";

export const metadata: Metadata = {
  title: "SENTINEL-ANPR — Command Centre",
  description:
    "Multi-camera ANPR intelligence platform: live vehicle tracking, trajectory reconstruction, and failure-aware OCR review.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Archivo+Condensed:wght@500;600;700&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-body bg-[var(--bg)] text-[var(--text)] min-h-screen">
        <DataModeProvider>
          <RegistryProvider>
            <Sidebar />
            <div className="pl-60 min-h-screen flex flex-col">
              <TopBar />
              <main className="flex-1">{children}</main>
            </div>
          </RegistryProvider>
        </DataModeProvider>
      </body>
    </html>
  );
}
