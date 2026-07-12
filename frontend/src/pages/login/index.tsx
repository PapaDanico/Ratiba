import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { ValidationMessage } from "@/components/ui/ValidationMessage";
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
  const [waking, setWaking] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);

  function validateEmail(value: string): string | null {
    if (!value) return "Email is required";
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(value)) return "Please enter a valid email address";
    return null;
  }

  function validatePassword(value: string, minLength = 1): string | null {
    if (!value) return "Password is required";
    if (value.length < minLength) return `Password must be at least ${minLength} characters`;
    return null;
  }

  function validateName(value: string): string | null {
    if (!value) return "Name is required";
    if (value.length < 2) return "Name must be at least 2 characters";
    return null;
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setWaking(false);

    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password);
    setEmailError(emailErr);
    setPasswordError(passwordErr);

    if (emailErr || passwordErr) return;

    setSubmitting(true);
    try {
      await login(email, password, () => setWaking(true));
      navigate("/app", { replace: true });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setError("Email or password not recognised.");
      } else {
        setError("Something went wrong. Please try again.");
      }
    } finally {
      setSubmitting(false);
      setWaking(false);
    }
  }

  async function onCreate(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const nameErr = validateName(fullName);
    const emailErr = validateEmail(email);
    const passwordErr = validatePassword(password, 8);
    setNameError(nameErr);
    setEmailError(emailErr);
    setPasswordError(passwordErr);

    if (nameErr || emailErr || passwordErr) return;

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
      navigate("/app", { replace: true });
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
    <main className="min-h-screen bg-gradient-to-br from-dn-steel-lt via-white to-dn-steel-lt flex flex-col lg:flex-row">
      {/* Left panel: brand column */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-16 relative">
        {/* Logo & Brand — top */}
        <div className="relative z-10">
          <div className="flex items-center gap-3">
            <DnLogo showText={true} width={200} />
          </div>
          <p className="mt-4 text-dn-steel-deep text-lg font-light max-w-xs leading-relaxed">
            Intelligent crew rostering for East African aviation
          </p>
        </div>

        {/* Key benefits — bottom */}
        <div className="relative z-10 space-y-6">
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dn-steel/10 flex items-center justify-center text-dn-steel-deep font-bold">
              ✓
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark">FTL Compliance</h3>
              <p className="text-sm text-dn-muted">Automatic KCAA regulation validation</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dn-steel/10 flex items-center justify-center text-dn-steel-deep font-bold">
              ✓
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark">Smart Scheduling</h3>
              <p className="text-sm text-dn-muted">AI-powered roster optimization</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-dn-steel/10 flex items-center justify-center text-dn-steel-deep font-bold">
              ✓
            </div>
            <div>
              <h3 className="font-semibold text-dn-dark">Crew Management</h3>
              <p className="text-sm text-dn-muted">Centralized database with all details</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right panel: auth form */}
      <div className="flex-1 flex items-center justify-center px-6 py-16 lg:py-0">
        <div className="w-full max-w-md">
          <div className="bg-white rounded-2xl shadow-2xl overflow-hidden border border-dn-steel-lt">
            {/* Card header */}
            <div className="bg-gradient-to-r from-dn-steel-lt to-transparent px-8 pt-8 pb-0">
              <div className="flex items-center gap-2 mb-4">
                <DnLogo showText={false} width={28} />
                <span className="text-sm font-semibold text-dn-dark">Ratiba</span>
              </div>
              <p className="text-sm text-dn-muted pb-6">
                {mode === "signin"
                  ? "Sign in to your dashboard"
                  : "Create a demo workspace to try Ratiba"}
              </p>
            </div>

            <div className="px-8 py-8 space-y-5">
              {/* Mode toggle */}
              <div className="flex rounded-lg border border-dn-steel-lt overflow-hidden text-sm bg-dn-steel-lt/30">
                <button
                  type="button"
                  onClick={() => {
                    setMode("signin");
                    setError(null);
                  }}
                  className={`flex-1 py-2.5 font-medium transition-colors ${
                    mode === "signin"
                      ? "bg-dn-steel-deep text-white shadow-sm"
                      : "bg-transparent text-dn-steel-deep hover:text-dn-dark"
                  }`}
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
                  className={`flex-1 py-2.5 font-medium transition-colors ${
                    mode === "create"
                      ? "bg-dn-steel-deep text-white shadow-sm"
                      : "bg-transparent text-dn-steel-deep hover:text-dn-dark"
                  }`}
                  data-testid="tab-create"
                >
                  Create workspace
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
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setEmailError(null);
                      }}
                      onBlur={(e) => {
                        const error = validateEmail(e.target.value);
                        if (error) setEmailError(error);
                      }}
                      placeholder="name@airline.com"
                      required
                      data-testid="login-email"
                    />
                    <ValidationMessage message={emailError} type="error" />
                  </div>
                  <div>
                    <Label htmlFor="password">Password</Label>
                    <Input
                      id="password"
                      type="password"
                      autoComplete="current-password"
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        setPasswordError(null);
                      }}
                      onBlur={(e) => {
                        const error = validatePassword(e.target.value);
                        if (error) setPasswordError(error);
                      }}
                      required
                      data-testid="login-password"
                    />
                    <ValidationMessage message={passwordError} type="error" />
                  </div>
                  {error && <ErrorAlert message={error} />}
                  <Button
                    type="submit"
                    className="w-full mt-2"
                    size="lg"
                    disabled={submitting}
                    data-testid="login-submit"
                  >
                    {waking ? "Waking the server…" : submitting ? "Signing in…" : "Sign in"}
                  </Button>
                  <p className="text-xs text-dn-muted text-center">
                    Don&apos;t have an account?{" "}
                    <button
                      type="button"
                      onClick={() => {
                        setMode("create");
                        setError(null);
                      }}
                      className="text-dn-steel-deep hover:underline"
                    >
                      Create one
                    </button>
                  </p>
                </form>
              ) : (
                <form onSubmit={onCreate} className="space-y-4" data-testid="create-form">
                  <div>
                    <Label htmlFor="full_name">Your name</Label>
                    <Input
                      id="full_name"
                      value={fullName}
                      onChange={(e) => {
                        setFullName(e.target.value);
                        setNameError(null);
                      }}
                      onBlur={(e) => {
                        const error = validateName(e.target.value);
                        if (error) setNameError(error);
                      }}
                      required
                      data-testid="create-name"
                    />
                    <ValidationMessage message={nameError} type="error" />
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
                      onChange={(e) => {
                        setEmail(e.target.value);
                        setEmailError(null);
                      }}
                      onBlur={(e) => {
                        const error = validateEmail(e.target.value);
                        if (error) setEmailError(error);
                      }}
                      required
                      data-testid="create-email"
                    />
                    <ValidationMessage message={emailError} type="error" />
                  </div>
                  <div>
                    <Label htmlFor="create_password">Password (8+ characters)</Label>
                    <Input
                      id="create_password"
                      type="password"
                      autoComplete="new-password"
                      minLength={8}
                      value={password}
                      onChange={(e) => {
                        setPassword(e.target.value);
                        setPasswordError(null);
                      }}
                      onBlur={(e) => {
                        const error = validatePassword(e.target.value, 8);
                        if (error) setPasswordError(error);
                      }}
                      required
                      data-testid="create-password"
                    />
                    <ValidationMessage message={passwordError} type="error" />
                  </div>
                  {error && <ErrorAlert message={error} />}
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
