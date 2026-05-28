import { useId } from "react";

interface DnLogoProps {
  /** "light" = gold on dark (header/login panel); "dark" = charcoal on white */
  variant?: "light" | "dark";
  /** Show CONSULTANCY + spear + tagline text */
  showText?: boolean;
  width?: number;
  className?: string;
}

export function DnLogo({ variant = "dark", showText = true, width = 200, className }: DnLogoProps) {
  const uid = useId();
  const gradId = `dn-arc-${uid}`.replace(/:/g, "");

  const ink = variant === "light" ? "#C9A84C" : "#1a1a1a";
  const inkFaint = variant === "light" ? "rgba(201,168,76,0.45)" : "#666";
  const arcTip = variant === "light" ? "#D0E8F5" : "#6AB4D8";

  const viewH = showText ? 430 : 295;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox={`0 0 400 ${viewH}`}
      width={width}
      className={className}
      aria-label="DN Consultancy"
      role="img"
    >
      <defs>
        <linearGradient
          id={gradId}
          gradientUnits="userSpaceOnUse"
          x1="74"
          y1="273"
          x2="336"
          y2="150"
        >
          <stop offset="0%" stopColor={ink} />
          <stop offset="75%" stopColor={ink} />
          <stop offset="100%" stopColor={arcTip} />
        </linearGradient>
      </defs>

      {/* Partial circle arc — large arc (~230°), open at lower-right */}
      <path
        d="M 74 273 A 145 145 0 1 0 336 150"
        stroke={`url(#${gradId})`}
        strokeWidth="3.5"
        strokeLinecap="round"
        fill="none"
      />

      {/* D/N monogram */}
      <text
        x="200"
        y="228"
        fontFamily="Georgia, 'Times New Roman', serif"
        fontSize="145"
        textAnchor="middle"
        fill={ink}
      >
        D/N
      </text>

      {showText && (
        <>
          {/* CONSULTANCY */}
          <text
            x="200"
            y="278"
            fontFamily="'Helvetica Neue', Arial, sans-serif"
            fontSize="26"
            fontWeight="700"
            textAnchor="middle"
            fill={ink}
            letterSpacing="10"
          >
            CONSULTANCY
          </text>

          {/* Decorative spear */}
          <line x1="35" y1="321" x2="158" y2="321" stroke={ink} strokeWidth="1.2" />
          <line x1="242" y1="321" x2="365" y2="321" stroke={ink} strokeWidth="1.2" />
          <polygon points="35,321 45,316 45,326" fill={ink} />
          <polygon points="365,321 355,316 355,326" fill={ink} />
          {/* Beaded ornaments — Maasai colours */}
          <g transform="translate(200,321)">
            <polygon points="0,-8 8,0 0,8 -8,0" fill="#5C2D73" />
            <polygon points="-17,-6 -11,0 -17,6 -23,0" fill="#8B1C1C" />
            <polygon points="17,-6 23,0 17,6 11,0" fill="#8B1C1C" />
            <polygon points="-31,-5 -26,0 -31,5 -36,0" fill="#C9A84C" />
            <polygon points="31,-5 36,0 31,5 26,0" fill="#C9A84C" />
          </g>

          {/* Tagline */}
          <text
            x="200"
            y="372"
            fontFamily="Georgia, 'Times New Roman', serif"
            fontStyle="italic"
            fontSize="17"
            textAnchor="middle"
            fill={inkFaint}
            letterSpacing="0.5"
          >
            Shaping Africa&apos;s Future, Together.
          </text>
        </>
      )}
    </svg>
  );
}
