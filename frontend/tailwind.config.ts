import type { Config } from "tailwindcss";

// DN brand tokens — Savanna Sky edition.
// Palette draws from Kenyan landscape: Rift Valley deep blue, Maasai shuka earth tones,
// Ngong Hills green, volcanic dark, warm parchment sand.
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        dn: {
          // Surfaces
          fog: "#F7EFE0", // warm parchment/sandy earth
          sand: "#EDE1C8", // deeper sand — card header tint

          // Text
          dark: "#1E0F05", // deep volcanic brown
          muted: "#7D6245", // warm taupe

          // Primary: Rift Valley deep blue (replaces cool steel)
          steel: "#1B4F72",
          "steel-lt": "#D0E8F5",

          // Gold — Maasai beadwork (unchanged, it was already right)
          gold: "#C9A84C",
          "gold-lt": "#FEF3CC",

          // Kenyan earth accent — Maasai shuka / savanna sunrise
          savanna: "#C47B2E",
          "savanna-lt": "#FDEBD5",

          // Status
          green: "#1A6B40", // Ngong Hills forest green
          red: "#A83822", // Kenyan red earth
          amber: "#C47B2E", // warm ochre (reuse savanna)

          // Dark nav surface — volcanic rock
          lava: "#1A0D05",
        },
      },
      fontFamily: {
        display: ['"Cormorant Garamond"', "Georgia", "serif"],
        // Ubuntu: humanist typeface created with East African design input (Dalton Maag)
        body: ['"Ubuntu"', '"DM Sans"', "system-ui", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
