# DN brand tokens

Single source of truth for colour, type, and motion across Ratiba. Wired into
`frontend/tailwind.config.ts` and into the WeasyPrint stylesheet for audit packs.

## Palette — DN reference

Exact hex values from the DN Consultancy reference site
(dnconsultancydiagnostictoolkit.netlify.app `:root`). Legacy token names
(`DN_SAND`, `DN_SAVANNA`, `DN_LAVA`) are kept and remapped for compatibility.

| Token         | Hex       | Purpose                                   |
|---------------|-----------|-------------------------------------------|
| `DN_DARK`     | `#1C1C1C` | Primary text; dark hero/nav surfaces      |
| `DN_STEEL`    | `#4A7FA5` | Primary brand accent — DN steel blue      |
| `DN_STEEL_LT` | `#D6E4F0` | Tint backgrounds                          |
| `DN_STEEL_DEEP` | `#3A6584` | Deep accent (links, hovers)             |
| `DN_GOLD`     | `#C9A84C` | Accents, dividers — DN gold               |
| `DN_GOLD_LT`  | `#FFF8E6` | Callout panels                            |
| `DN_FOG`      | `#F4F4F2` | Page background — light fog               |
| `DN_SAND`     | `#ECECE9` | Card header tint — a step deeper than fog |
| `DN_MUTED`    | `#6B7280` | Body text, captions                       |
| `DN_GREEN`    | `#1E8449` | Compliant / positive                      |
| `DN_RED`      | `#C0392B` | Alerts / critical                         |
| `DN_AMBER`    | `#D4AC0D` | Watch items                               |
| `DN_SAVANNA`  | `#C9A84C` | Legacy warm accent → mapped to gold       |
| `DN_LAVA`     | `#1C1C1C` | Legacy nav surface → mapped to dark       |

## Typography

| Role     | Family              | Source       | Notes                              |
|----------|---------------------|--------------|------------------------------------|
| Display  | Cormorant Garamond  | Google Fonts | Elegant serif for headings         |
| Body     | DM Sans             | Google Fonts | Matches the DN reference site body face |
| Code/data| JetBrains Mono      | Google Fonts | Monospace for IDs, times, figures  |

## Tribal decorative system

Three CSS utility classes provide Maasai-inspired geometric accents:

- **`.tribal-stripe`** — 3-colour repeating horizontal stripe (gold / earth-red / rift-blue).
  Used beneath card headers and as nav divider. Height: 3 px.
- **`.tribal-texture`** — Subtle diamond-grid overlay at 6% opacity.
  Used on dark surfaces (login backdrop, nav header).
- **`.savanna-dawn`** — Kenyan sunrise gradient (#1A0D05 → #C9A84C).
  Used as the login page full-bleed background.

## Tailwind binding

In `tailwind.config.ts` colours are namespaced under the `dn-` prefix:

```ts
colors: {
  dn: {
    dark: "#1E0F05",
    steel: "#1B4F72",
    "steel-lt": "#D0E8F5",
    gold: "#C9A84C",
    // ...
  },
}
```

Use them as `bg-dn-fog`, `text-dn-dark`, `border-dn-gold`, etc.

## Audit pack

The WeasyPrint stylesheet mirrors these tokens via CSS custom properties so
that the PDF audit pack and the dashboard are visually consistent.
