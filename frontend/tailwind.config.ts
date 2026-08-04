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
          fog: "#F7F3EA", // page background
          sand: "#EDE6D3", // card header tint / recessed surface
          "sand-deep": "#E3D8BE", // borders, dividers — warm, not cool grey

          // Ink — navy doing text duty (was near-black #1C1C1C)
          dark: "#0A192F",
          "dark-deep": "#020C1B", // deepest dark band — hero sections, footers
          muted: "#5C6B7D", // secondary text, AA-checked on fog/sand/white

          // Primary accent — navy (was steel blue)
          navy: "#0A192F",
          "navy-lt": "#DCE3ED", // pale navy tint — badges, hover surfaces
          "navy-deep": "#020C1B", // hover/pressed, darkest

          // Secondary accent — amber (was gold; also carries warning status)
          amber: "#D97706",
          "amber-lt": "#FFF6E5", // pale amber wash — callout panels
          "amber-deep": "#B45309", // AA-safe amber for text on tints

          // Status
          green: "#1E7A4A",
          "green-deep": "#166437", // readable green text on light tints
          red: "#C0392B",
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
