import { forwardRef } from "react";
import type { SelectHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type SelectProps = SelectHTMLAttributes<HTMLSelectElement>;

export const Select = forwardRef<HTMLSelectElement, SelectProps>(function Select(
  { className, ...rest },
  ref,
) {
  return (
    <select
      ref={ref}
      className={cn(
        "block w-full rounded border border-dn-sand-deep bg-dn-dark-deep px-3 py-2 text-sm",
        "text-dn-dark placeholder:text-dn-muted",
        "focus-visible:outline-none focus-visible:border-dn-navy focus-visible:ring-2 focus-visible:ring-dn-navy/30",
        "disabled:bg-dn-dark-deep disabled:cursor-not-allowed",
        'appearance-none bg-[url(\'data:image/svg+xml;utf8,<svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 12 12"><path fill="%23F4E8D0" d="M6 9L1 4h10z"/></svg>\')] bg-no-repeat bg-right pr-8',
        className,
      )}
      {...rest}
    />
  );
});
