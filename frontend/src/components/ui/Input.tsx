import { forwardRef } from "react";
import type { InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type InputProps = InputHTMLAttributes<HTMLInputElement>;

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className, ...rest },
  ref,
) {
  return (
    <input
      ref={ref}
      className={cn(
        "block w-full rounded-md border border-dn-steel-lt bg-white px-3 py-2 text-sm",
        "text-dn-dark placeholder:text-dn-muted",
        "focus-visible:outline-none focus-visible:border-dn-steel focus-visible:ring-2 focus-visible:ring-dn-steel/30",
        "disabled:bg-dn-fog disabled:cursor-not-allowed",
        className,
      )}
      {...rest}
    />
  );
});
