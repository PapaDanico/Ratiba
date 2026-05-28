import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { DnLogo } from "@/components/ui/DnLogo";
import { useAuth } from "@/lib/auth";
import { api, ApiError } from "@/lib/api";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"signin" | "create">("signin");
  const [fullName, setFullName] = useState("");
  const [operatorName, setOperatorName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email or password not recognised.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  async function onCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await api("/api/v1/auth/demo-workspace", {
        method: "POST",
        body: JSON.stringify({
          full_name: fullName,
          email,
          password,
          operator_name: operatorName || null,
        }),
      });
      // The chosen credentials are now live — sign straight in.
      await login(email, password);
      navigate("/", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setError("An account with that email already exists. Try signing in instead.");
      } else if (err instanceof ApiError && err.status === 429) {
        setError("Too many workspaces created from this network. Try again later.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Enter a name, a valid email, and a password of at least 8 characters.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen flex savanna-dawn tribal-texture">
      {/* Left panel: brand column */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-16 relative">
        {/* DN Consultancy logo — top */}
        <div className="relative z-10">
          <DnLogo variant="light" showText={true} width={240} />
        </div>

        {/* Ratiba product identity — bottom */}
        <div className="relative z-10">
          <div className="tribal-stripe mb-6 w-24" />
          <h1 className="font-display text-6xl text-dn-gold leading-tight">Ratiba</h1>
          <p className="mt-3 text-dn-gold/60 text-lg font-light max-w-xs leading-relaxed">
            Crew rostering for East African aviation operations.
          </p>
          <p className="mt-6 font-mono text-xs uppercase tracking-widest text-dn-gold/30">
            KCAA FTL Scheme · ICAO Annex 6
          </p>
        </div>
      </div>

      {/* Right panel: auth form */}
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-lg shadow-2xl overflow-hidden">
            {/* Card header strip */}
            <div className="bg-dn-lava px-8 pt-8 pb-0">
              <div className="flex items-center gap-3 mb-4">
                <DnLogo variant="light" showText={false} width={28} />
                <span className="font-mono text-xs uppercase tracking-widest text-dn-gold/50">
                  DN Consultancy
                </span>
              </div>
              <div className="lg:hidden mb-6">
                <h2 className="font-display text-3xl text-dn-gold">Ratiba</h2>
                <p className="font-display italic text-sm text-dn-gold/40">
                  Shaping Africa&apos;s Future, Together.
                </p>
              </div>
              <p className="text-sm text-dn-gold/60 pb-6">
                {mode === "signin"
                  ? "Sign in to the Crewing Officer dashboard."
                  : "Create your own demo workspace to explore Ratiba."}
              </p>
              <div className="tribal-stripe -mx-8" />
            </div>

            <div className="px-8 py-8 space-y-5">
              {/* Mode toggle */}
              <div className="flex rounded-md border border-dn-steel-lt overflow-hidden text-sm">
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError(null);
                  }}
                  className={
                    mode === "signin"
                      ? "flex-1 py-2 bg-dn-steel text-white"
                      : "flex-1 py-2 bg-white text-dn-steel"
                  }
                  data-testid="tab-signin"
                >
                  Sign in
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setMode("create");
                    setError(null);
                  }}
                  className={
                    mode === "create"
                      ? "flex-1 py-2 bg-dn-steel text-white"
                      : "flex-1 py-2 bg-white text-dn-steel"
                  }
                  data-testid="tab-create"
                >
                  Create demo workspace
                </button>
              </div>

              {mode === "signin" ? (
                <form onSubmit={onSubmit} className="space-y-4" data-testid="login-form">
                  <div>
                    <Label htmlFor="email">Email</Label>
                    <Input
                      id="email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      data-testid="login-email"
                    />
                  </div>
                  <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      data-testid="login-password"
                    />
                  </div>
                  {error && (
                    <p className="text-sm text-dn-red" role="alert" data-testid="login-error">
                      {error}
                    </p>
                  )}
                  <Button
                    type="submit"
                    className="w-full mt-2"
                    size="lg"
                    disabled={submitting}
                    data-testid="login-submit"
                  >
                    {submitting ? "Signing in…" : "Sign in"}
                  </Button>
                </form>
              ) : (
                <form onSubmit={onCreate} className="space-y-4" data-testid="create-form">
                  <div>
                    <Label htmlFor="full_name">Your name</Label>
                    <Input
                      id="full_name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      required
                      data-testid="create-name"
                    />
                  </div>
                  <div>
                    <Label htmlFor="operator_name">Airline name (optional)</Label>
                    <Input
                      id="operator_name"
                      value={operatorName}
                      onChange={(e) => setOperatorName(e.target.value)}
                      placeholder="e.g. Savanna Air"
                      data-testid="create-operator"
                    />
                  </div>
                  <div>
                    <Label htmlFor="create_email">Email</Label>
                    <Input
                      id="create_email"
                      type="email"
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      data-testid="create-email"
                    />
                  </div>
                  <div>
                    <Label htmlFor="create_password">Password (8+ characters)</Label>
                    <Input
                      id="create_password"
                      type="password"
                      autoComplete="new-password"
                      minLength={8}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      required
                      data-testid="create-password"
                    />
                  </div>
                  {error && (
                    <p className="text-sm text-dn-red" role="alert" data-testid="create-error">
                      {error}
                    </p>
                  )}
                  <Button
                    type="submit"
                    className="w-full mt-2"
                    size="lg"
                    disabled={submitting}
                    data-testid="create-submit"
                  >
                    {submitting ? "Creating…" : "Create workspace & enter"}
                  </Button>
                  <p className="text-xs text-dn-muted">
                    Your workspace is private and comes pre-loaded with sample crew, aircraft, and
                    flights so you can try the full flow right away. By creating a workspace you
                    agree to our{" "}
                    <Link to="/terms" className="underline">
                      Terms of Use
                    </Link>{" "}
                    and{" "}
                    <Link to="/privacy" className="underline">
                      Privacy Policy
                    </Link>
                    .
                  </p>
                </form>
              )}

              <p className="pt-2 text-center text-xs text-dn-muted">
                <Link to="/privacy" className="underline">
                  Privacy Policy
                </Link>{" "}
                ·{" "}
                <Link to="/terms" className="underline">
                  Terms of Use
                </Link>
              </p>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
