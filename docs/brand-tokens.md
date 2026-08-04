# DN brand tokens

Single source of truth for colour, type, and motion across Ratiba. Wired into
`frontend/tailwind.config.ts`, the Supabase edge function's PDF renderer
(`supabase/functions/api/pdf.ts`), and the local-dev WeasyPrint stylesheets
(`backend/app/services/crew_roster_pdf.py`, `audit_pack.py`) — all four must
stay in lockstep.

## Palette — navy + amber

DN Consultancy Aviation's stated brand ("navy and amber"), warmed with
parchment-toned neutrals instead of cool grey so the whole surface reads as
one temperature — no cool greys, no pure white. Ink and the primary accent
share one navy family; amber is the single secondary accent, carrying both
brand highlights and the warning/caution status role.

| Token           | Hex       | Purpose                                      |
|-----------------|-----------|-----------------------------------------------|
| `DN_DARK`       | `#0A192F` | Primary text / ink                            |
| `DN_DARK_DEEP`  | `#020C1B` | Deepest dark band — hero sections, footers    |
| `DN_NAVY`       | `#0A192F` | Primary brand accent — buttons, active states |
| `DN_NAVY_LT`    | `#DCE3ED` | Pale navy tint — badges, hover surfaces       |
| `DN_NAVY_DEEP`  | `#020C1B` | Hover/pressed, darkest                        |
| `DN_AMBER`      | `#D97706` | Secondary accent + warning/caution status     |
| `DN_AMBER_LT`   | `#FFF6E5` | Pale amber wash — callout panels              |
| `DN_AMBER_DEEP` | `#B45309` | AA-safe amber for text on tints               |
| `DN_FOG`        | `#F7F3EA` | Page background — warm parchment              |
| `DN_SAND`       | `#EDE6D3` | Card header tint — a step deeper than fog     |
| `DN_SAND_DEEP`  | `#E3D8BE` | Borders, dividers — warm, not cool grey       |
| `DN_MUTED`      | `#5C6B7D` | Body text, captions (AA-checked)              |
| `DN_GREEN`      | `#1E7A4A` | Compliant / positive                          |
| `DN_GREEN_DEEP` | `#166437` | Readable green text on light tints            |
| `DN_RED`        | `#C0392B` | Alerts / critical                             |

## Typography

| Role     | Family              | Source       | Notes                              |
|----------|---------------------|--------------|------------------------------------|
| Display  | Cormorant Garamond  | Google Fonts | Elegant serif for headings         |
| Body     | DM Sans             | Google Fonts | Matches the DN reference site body face |
| Code/data| JetBrains Mono      | Google Fonts | Monospace for IDs, times, figures  |

Cormorant Garamond ships old-style (text) figures by default — digits at
inconsistent heights, which reads as broken in a heading like "12,345" rather
than as a number. `body { font-variant-numeric: lining-nums; }` in
`frontend/src/styles/index.css` corrects this globally by inheritance; the
`.tnum` utility additionally sets `tabular-nums` for figures that sit in
columns or update in place.

## Tribal decorative system

Three CSS utility classes provide Maasai-inspired geometric accents:

- **`.tribal-stripe`** — 3-colour repeating horizontal stripe (amber / navy / deep navy).
  Used beneath card headers and as nav divider. Height: 3 px.
- **`.tribal-texture`** — Subtle diamond-grid overlay at 5% opacity, amber-tinted.
  Used on dark surfaces (login backdrop, nav header).
- **`.savanna-dawn`** — Navy-night-to-amber-dawn gradient (`#020C1B` → `#0A192F` → `#1E3A5F` → `#B45309`).
  Used as the login page full-bleed background.

## Tailwind binding

In `tailwind.config.ts` colours are namespaced under the `dn-` prefix:

```ts
colors: {
  dn: {
    dark: "#0A192F",
    navy: "#0A192F",
    "navy-lt": "#DCE3ED",
    amber: "#D97706",
    // ...
  },
}
```

Use them as `bg-dn-fog`, `text-dn-dark`, `border-dn-amber`, etc.

Large background areas (full-page gradients, hero backdrops) should lean on
`dn-fog`/`dn-amber-lt` rather than `dn-navy-lt` — navy is a cool hue, and
spreading its light tint across a whole viewport reads cold despite being
on-brand. Reserve navy tints for small accent touches (badges, chips, icon
circles); keep the dominant surface warm.

## PDF renderers

Both PDF pipelines mirror this palette via literal RGB/hex constants (no
shared token import across the Deno/Python/TypeScript boundary, so they must
be updated by hand together):

- `supabase/functions/api/pdf.ts` — pdf-lib `rgb()` triples, production.
- `backend/app/services/crew_roster_pdf.py` / `audit_pack.py` — WeasyPrint
  CSS hex values, local-dev only (parity with the edge function).
