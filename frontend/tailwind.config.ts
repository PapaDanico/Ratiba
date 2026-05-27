import type { Config } from "tailwindcss";

// DN brand tokens — see docs/brand-tokens.md (single source of truth).
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        dn: {
          dark: "#1C1C1C",
          steel: "#4A7FA5",
          "steel-lt": "#D6E4F0",
          gold: "#C9A84C",
          "gold-lt": "#FFF8E6",
          fog: "#F4F4F2",
          muted: "#6B7280",
          green: "#1E8449",
          red: "#C0392B",
          amber: "#D4AC0D",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", "serif"],
        body: ['"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
