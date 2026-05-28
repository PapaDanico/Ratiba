import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { useAuth } from "@/lib/auth";
import { ApiError } from "@/lib/api";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
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

  return (
    <main className="min-h-screen flex savanna-dawn tribal-texture">
      {/* Left panel: decorative brand column */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-end p-16 relative">
        {/* Decorative Maasai diamond stack */}
        <div className="absolute top-12 left-12 flex flex-col gap-4 opacity-20">
          {[40, 28, 18, 12].map((size, i) => (
            <svg key={i} width={size} height={size} viewBox="0 0 20 20" fill="#C9A84C">
              <polygon points="10,0 20,10 10,20 0,10" />
            </svg>
          ))}
        </div>

        <div className="relative z-10">
          <div className="tribal-stripe mb-6 w-24" />
          <h1 className="font-display text-6xl text-dn-gold leading-tight">Ratiba</h1>
          <p className="mt-3 text-dn-gold/60 text-lg font-light max-w-xs leading-relaxed">
            Crew rostering for East African aviation operations.
          </p>
          <p className="mt-6 font-mono text-xs uppercase tracking-widest text-dn-gold/30">
            KCARs 2025 Part 8 · DN Consultancy
          </p>
        </div>
      </div>

      {/* Right panel: login form */}
      <div className="flex-1 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-md">
          {/* Card — elevated over the gradient */}
          <div className="bg-white rounded-lg shadow-2xl overflow-hidden">
            {/* Card header strip */}
            <div className="bg-dn-lava px-8 pt-8 pb-0">
              <div className="flex items-center gap-2 mb-4">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="#C9A84C">
                  <polygon points="6,0 12,6 6,12 0,6" />
                </svg>
                <span className="font-mono text-xs uppercase tracking-widest text-dn-gold/50">
                  DN Consultancy
                </span>
              </div>
              <h2 className="font-display text-3xl text-dn-gold mb-6 lg:hidden">Ratiba</h2>
              <p className="text-sm text-dn-gold/60 pb-6">
                Sign in to the Crewing Officer dashboard.
              </p>
              <div className="tribal-stripe -mx-8" />
            </div>

            <div className="px-8 py-8 space-y-5">
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
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
