import logoFull from "@/assets/dn-consultancy-logo.png";
import logoMark from "@/assets/dn-consultancy-mark.png";

interface DnLogoProps {
  /** Full lockup (arc + monogram + CONSULTANCY + tagline) vs. monogram mark only */
  showText?: boolean;
  width?: number;
  className?: string;
}

export function DnLogo({ showText = true, width = 200, className }: DnLogoProps) {
  return (
    <img
      src={showText ? logoFull : logoMark}
      width={width}
      alt="DN Consultancy"
      className={className}
      style={{ height: "auto" }}
    />
  );
}
