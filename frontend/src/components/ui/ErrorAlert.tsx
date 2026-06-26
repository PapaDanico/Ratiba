import { cn } from "@/lib/cn";

export function ErrorAlert({ message, className }: { message: string; className?: string }) {
  return (
    <div
      role="alert"
      className={cn(
        "rounded border border-dn-red/30 bg-dn-red/5 px-3 py-2 text-sm text-dn-red",
        className,
      )}
    >
      {message}
    </div>
  );
}
