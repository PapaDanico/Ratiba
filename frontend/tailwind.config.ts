import type { Config } from "tailwindcss";

// DN Consultancy Aviation brand tokens — navy + amber, per the brand as
// stated in the DNCA platform CLAUDE.md ("DN Consultancy brand colours:
// navy and amber"), warmed with parchment-toned neutrals instead of cool
// grey so the whole surface reads as one temperature (no cool greys, no
// pure white — the same restraint principle behind Claude's own cream/ink
// product palette). Ink and primary-accent share one navy family; amber is
// the single secondary accent carrying both brand highlights and the
// warning/caution status role — one accent doing double duty rather than
// two similar ambers competing.
const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        dn: {
          // Warm parchment surfaces
          fog: "#0B0D0F", // cockpit-black application canvas
          sand: "#161A1E", // elevated dark surface
          "sand-deep": "#2B3035", // structural borders

          // Ink — navy doing text duty (was near-black #1C1C1C)
          dark: "#F4E8D0", // ivory operational text
          "dark-deep": "#07090B", // deepest black
          muted: "#A99F91", // muted ivory

          // Primary accent — navy (was steel blue)
          navy: "#D96528", // Ratiba copper
          "navy-lt": "#243F52", // aviation blue surface
          "navy-deep": "#F08943", // copper highlight

          // Secondary accent — amber (was gold; also carries warning status)
          amber: "#E7AE54", // warm flight-deck gold
          "amber-lt": "#3A2C19", // gold wash
          "amber-deep": "#F5C574", // readable gold

          // Status
          green: "#629B69",
          "green-deep": "#8ACB91",
          red: "#D8634F",
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
        dn: "0 6px 24px rgba(10,25,47,.08)", // --shadow, navy-tinted
        "dn-lg": "0 18px 48px rgba(10,25,47,.16)", // --shadow-lg
      },
    },
  },
  plugins: [],
};

export default config;
