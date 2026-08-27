import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        bg: "#F5F1E8",
        surface: "#FBF8F1",
        surface2: "#F0EBE0",
        border2: "#D8CFB8",
        text: "#2B2620",
        muted: "#6B6254",
        platewhite: "#F2F4F0",
        plateamber: "#E8B400",
        plateink: "#0A0A0A",
        signal: "#7A3B2E",
        warn: "#C4842A",
        danger: "#A13A2E",
        ok: "#5C7A4A",
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
        data: ["var(--font-data)", "monospace"],
      },
      boxShadow: {
        panel: "0 1px 0 rgba(255,255,255,0.4) inset, 0 8px 24px rgba(43,38,32,0.08)",
        chip: "0 1px 3px rgba(0,0,0,0.18)",
      },
      keyframes: {
        pulseMarker: {
          "0%": { boxShadow: "0 0 0 0 rgba(122,59,46,0.45)" },
          "70%": { boxShadow: "0 0 0 14px rgba(122,59,46,0)" },
          "100%": { boxShadow: "0 0 0 0 rgba(122,59,46,0)" },
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
