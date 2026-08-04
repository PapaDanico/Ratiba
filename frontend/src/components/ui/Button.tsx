import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-dn-navy-deep text-white hover:bg-dn-navy-deep/85 disabled:bg-dn-navy-deep/40 focus-visible:ring-dn-navy",
  secondary:
    "bg-white text-dn-dark border border-dn-sand hover:bg-dn-fog focus-visible:ring-dn-navy",
  ghost: "bg-transparent text-dn-dark hover:bg-dn-sand/60 focus-visible:ring-dn-muted",
  danger: "bg-dn-red text-white hover:bg-dn-red/90 disabled:bg-dn-red/40 focus-visible:ring-dn-red",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-sm",
  md: "h-10 px-4 text-sm",
  lg: "h-12 px-6 text-base",
};

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
};

export function Button({
  variant = "primary",
  size = "md",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded font-medium transition duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-dn-fog",
        "active:scale-[0.98] motion-reduce:transform-none disabled:cursor-not-allowed disabled:active:scale-100",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...rest}
    >
      {children}
    </button>
  );
}
