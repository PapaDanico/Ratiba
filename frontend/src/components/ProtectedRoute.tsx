import type { ReactNode } from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";

export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  if (status === "unknown" || status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-dn-muted">Loading…</div>
    );
  }
  if (status !== "authenticated") {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}
