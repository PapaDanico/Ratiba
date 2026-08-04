interface ValidationMessageProps {
  message?: string | null;
  type?: "error" | "success" | "warning";
}

export function ValidationMessage({ message, type = "error" }: ValidationMessageProps) {
  if (!message) return null;

  const colors = {
    error: "text-dn-red text-sm",
    success: "text-dn-green-deep text-sm",
    warning: "text-dn-amber-deep text-sm",
  };

  return <p className={colors[type]}>{message}</p>;
}
