# DN brand tokens

Single source of truth for colour, type, and motion across Ratiba. Wired into
`frontend/tailwind.config.ts` (Phase 0) and into the WeasyPrint stylesheet for
audit packs (Phase 5).

## Palette

| Token         | Hex       | Purpose                                  |
|---------------|-----------|------------------------------------------|
| `DN_DARK`     | `#1C1C1C` | Primary text, headers                    |
| `DN_STEEL`    | `#4A7FA5` | Secondary, section banners               |
| `DN_STEEL_LT` | `#D6E4F0` | Tint backgrounds                         |
| `DN_GOLD`     | `#C9A84C` | Accents, dividers                        |
| `DN_GOLD_LT`  | `#FFF8E6` | Callout panels                           |
| `DN_FOG`      | `#F4F4F2` | Alternating rows, panels                 |
| `DN_MUTED`    | `#6B7280` | Body text, captions                      |
| `DN_GREEN`    | `#1E8449` | Compliant / positive                     |
| `DN_RED`      | `#C0392B` | Alerts / critical                        |
| `DN_AMBER`    | `#D4AC0D` | Watch items                              |

## Typography

| Role     | Family               | Source        |
|----------|----------------------|---------------|
| Display  | Cormorant Garamond   | Google Fonts  |
| Body     | DM Sans              | Google Fonts  |
| Code/data| JetBrains Mono       | Google Fonts  |

## Tailwind binding

In `tailwind.config.ts` colours are namespaced under the `dn-` prefix:

```ts
colors: {
  dn: {
    dark: "#1C1C1C",
    steel: "#4A7FA5",
    "steel-lt": "#D6E4F0",
    // ...
  },
}
```

Use them as `bg-dn-fog`, `text-dn-dark`, `border-dn-gold`, etc.

## Audit pack (Phase 5)

The WeasyPrint stylesheet mirrors these tokens via CSS custom properties so
that the PDF audit pack and the dashboard are visually identical.
