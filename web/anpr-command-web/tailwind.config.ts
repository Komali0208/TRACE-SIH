import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0B1014",
        surface: "#131A20",
        surface2: "#1A232B",
        border2: "#26313B",
        text: "#E8EEF2",
        muted: "#8494A1",
        platewhite: "#F2F4F0",
        plateamber: "#E8B400",
        plateink: "#0A0A0A",
        signal: "#4CC3C8",
        warn: "#E8942E",
        danger: "#E0483B",
        ok: "#4FA96B",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        data: ["var(--font-data)", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.03) inset, 0 8px 24px rgba(0,0,0,0.35)",
        chip: "0 1px 3px rgba(0,0,0,0.5)",
      },
      keyframes: {
        pulseMarker: {
          "0%": { boxShadow: "0 0 0 0 rgba(76,195,200,0.55)" },
          "70%": { boxShadow: "0 0 0 14px rgba(76,195,200,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(76,195,200,0)" },
        },
        drawLine: {
          from: { strokeDashoffset: "1" },
          to: { strokeDashoffset: "0" },
        },
        rise: {
          from: { opacity: "0", transform: "translateY(6px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        pulseMarker: "pulseMarker 2.2s ease-out infinite",
        rise: "rise 0.35s ease-out both",
      },
    },
  },
  plugins: [],
};
export default config;
