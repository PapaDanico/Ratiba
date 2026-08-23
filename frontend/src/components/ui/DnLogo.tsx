interface DnLogoProps {
  showText?: boolean;
  width?: number;
  className?: string;
}

/** Ratiba’s supplied aviation-clock emblem, cropped from the approved brand sheet. */
export function DnLogo({ showText = true, width = 200, className }: DnLogoProps) {
  return (
    <div className={className} style={{ width }}>
      <div className="flex items-center gap-2.5">
        <img src="/icon-192.png" width={showText ? 34 : width} height={showText ? 34 : width} alt="Ratiba" className="rounded-[22%]" />
        {showText && (
          <span className="font-body text-[1.35rem] font-bold tracking-[0.22em] text-dn-dark">
            RATIBA
          </span>
        )}
      </div>
    </div>
  );
}
