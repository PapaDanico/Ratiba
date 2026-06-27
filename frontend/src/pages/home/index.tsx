import { Navigate } from "react-router-dom";
import { useAuth } from "@/lib/auth";
import { LandingPage } from "@/pages/landing";

export function HomePage() {
  const { status } = useAuth();

  // Loading state
  if (status === "unknown" || status === "loading") {
    return (
      <div className="flex min-h-screen items-center justify-center text-dn-muted">
        Loading…
      </div>
    );
  }

  // Authenticated: redirect to app
  if (status === "authenticated") {
    return <Navigate to="/app" replace />;
  }

  // Unauthenticated: show landing page
  return <LandingPage />;
}
