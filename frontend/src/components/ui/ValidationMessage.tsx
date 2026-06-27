interface ValidationMessageProps {
  message?: string | null;
  type?: "error" | "success" | "warning";
}

export function ValidationMessage({ message, type = "error" }: ValidationMessageProps) {
  if (!message) return null;

  const colors = {
    error: "text-dn-red text-sm",
    success: "text-green-600 text-sm",
    warning: "text-amber-600 text-sm",
  };

  return <p className={colors[type]}>{message}</p>;
}
