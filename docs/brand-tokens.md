# DN brand tokens

Single source of truth for colour, type, and motion across Ratiba. Wired into
`frontend/tailwind.config.ts` and into the WeasyPrint stylesheet for audit packs.

## Palette — Savanna Sky

Inspired by East African landscape and Maasai visual culture: volcanic earth,
Rift Valley deep blue, Ngong Hills green, Maasai beadwork gold, warm parchment sand.

| Token         | Hex       | Purpose / Inspiration                    |
|---------------|-----------|------------------------------------------|
| `DN_DARK`     | `#1E0F05` | Primary text — deep volcanic brown       |
| `DN_STEEL`    | `#1B4F72` | Primary brand — Rift Valley deep blue    |
| `DN_STEEL_LT` | `#D0E8F5` | Tint backgrounds                         |
| `DN_GOLD`     | `#C9A84C` | Accents, dividers — Maasai beadwork gold |
| `DN_GOLD_LT`  | `#FEF3CC` | Callout panels                           |
| `DN_FOG`      | `#F7EFE0` | Page background — warm parchment sand    |
| `DN_SAND`     | `#EDE1C8` | Card header tint — deeper sand           |
| `DN_MUTED`    | `#7D6245` | Body text, captions — warm taupe         |
| `DN_GREEN`    | `#1A6B40` | Compliant / positive — Ngong Hills green |
| `DN_RED`      | `#A83822` | Alerts / critical — Kenyan red earth     |
| `DN_AMBER`    | `#C47B2E` | Watch items — savanna ochre              |
| `DN_SAVANNA`  | `#C47B2E` | Kenyan earth accent / active states      |
| `DN_LAVA`     | `#1A0D05` | Nav header surface — volcanic rock dark  |

## Typography

| Role     | Family              | Source       | Notes                              |
|----------|---------------------|--------------|------------------------------------|
| Display  | Cormorant Garamond  | Google Fonts | Elegant serif for headings         |
| Body     | Ubuntu              | Google Fonts | Humanist; East African design heritage (Dalton Maag) |
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
