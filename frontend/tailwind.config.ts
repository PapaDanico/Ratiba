import type { Config } from "tailwindcss";

// DN brand tokens — aligned with the DN Consultancy reference site
// (dnconsultancydiagnostictoolkit.netlify.app :root palette, exact hex).
// Legacy token names (sand/savanna/lava) are kept and remapped so existing
// components restyle without churn.
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        dn: {
          // Surfaces
          fog: "#F4F4F2", // --dn-fog
          sand: "#ECECE9", // card header tint — a step deeper than fog

          // Text
          dark: "#1C1C1C", // --dn-dark
          muted: "#5B6472", // --dn-muted, darkened for WCAG AA on tinted surfaces

          // Primary accent — DN steel blue
          steel: "#4A7FA5", // --dn-steel / --accent
          "steel-lt": "#D6E4F0", // --dn-steel-lt
          "steel-deep": "#3A6584", // --accent-deep

          // Gold
          gold: "#C9A84C", // --dn-gold
          "gold-lt": "#FFF8E6", // --dn-gold-lt

          // Warm accent (legacy savanna) — mapped to brand gold
          savanna: "#C9A84C",
          "savanna-lt": "#FFF8E6",

          // Status
          green: "#1E8449", // --dn-green
          "green-deep": "#166437", // readable green text on light tints
          red: "#C0392B", // --dn-red
          amber: "#D4AC0D", // --dn-amber
          "amber-deep": "#7A5C00", // readable amber text on light tints

          // Dark nav surface (legacy lava) — brand dark
          lava: "#1C1C1C",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", '"Times New Roman"', "serif"],
        body: [
          '"DM Sans"',
          "system-ui",
          "-apple-system",
          '"Segoe UI"',
          "Roboto",
          "Arial",
          "sans-serif",
        ],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
      borderRadius: {
        dn: "12px", // --radius
        "dn-sm": "8px", // --radius-sm
      },
      boxShadow: {
        dn: "0 6px 24px rgba(28,28,28,.08)", // --shadow
        "dn-lg": "0 18px 48px rgba(28,28,28,.14)", // --shadow-lg
      },
    },
  },
  plugins: [],
};

export default config;
