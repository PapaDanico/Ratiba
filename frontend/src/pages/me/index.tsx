import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Badge } from "@/components/ui/Badge";
import { pilotApi, pilotPair, pilotStore, type PilotProfile } from "@/lib/pilotAuth";
import { cn } from "@/lib/cn";

type DutyDay = {
  date_local: string;
  aircraft_reg: string;
  aircraft_type: string;
  sector_ids: string[];
  role_on_duty: string;
  report_time: string | null;
  off_duty_time: string | null;
  flight_hours: string | null;
  duty_hours: string | null;
  legality_state: string | null;
};

type DutyTodayResponse = { has_duty: boolean; duty_day?: DutyDay };
type RosterResponse = { date_from: string; date_to: string; duty_days: DutyDay[] };
type CurrencyResponse = {
  currencies: {
    currency_type: string;
    expires_date: string;
    days_remaining: number;
    state: "GREEN" | "AMBER" | "RED";
  }[];
};

type PilotNotice = {
  id: string;
  category: "OPERATIONAL" | "FLEET" | "SAFETY" | "SOCIAL";
  severity: "INFO" | "IMPORTANT" | "CRITICAL";
  title: string;
  body: string;
  image_url: string | null;
  requires_ack: boolean;
  pinned: boolean;
  acknowledged: boolean;
};

type Tab = "today" | "roster" | "currency" | "notices";

function PairingScreen({ onPaired }: { onPaired: (profile: PilotProfile) => void }) {
  const [code, setCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  // A one-tap pairing link carries ?pair=CODE; auto-redeem it on arrival.
  const [autoPairing, setAutoPairing] = useState(
    () => new URLSearchParams(window.location.search).get("pair") !== null,
  );

  async function pair(raw: string): Promise<void> {
    const profile = await pilotPair(raw.trim().toUpperCase());
    onPaired(profile);
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await pair(code);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Pairing failed");
    } finally {
      setSubmitting(false);
    }
  }

  const autoPairAttempted = useRef(false);
  useEffect(() => {
    // Guard against React StrictMode's double-invoked effect (and any remount):
    // the pairing code is single-use, so redeeming it twice would 400.
    if (autoPairAttempted.current) return;
    const linkCode = new URLSearchParams(window.location.search).get("pair");
    if (!linkCode) return;
    autoPairAttempted.current = true;
    // Strip the code from the URL so it isn't bookmarked/shared or re-run.
    window.history.replaceState(null, "", window.location.pathname);
    setCode(linkCode.toUpperCase());
    void pair(linkCode)
      .catch((err: unknown) => {
        setError(
          err instanceof Error
            ? `${err.message} — enter the code manually below.`
            : "Pairing link failed — enter the code manually below.",
        );
      })
      .finally(() => setAutoPairing(false));
    // Run once on mount.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (autoPairing) {
    return (
      <main className="min-h-screen flex items-center justify-center bg-dn-fog px-4">
        <Card className="w-full max-w-sm">
          <CardBody className="space-y-2 text-center">
            <p className="font-mono text-xs uppercase tracking-widest text-dn-steel">
              Ratiba · Crew
            </p>
            <h1 className="font-display text-2xl text-dn-dark">Pairing your device…</h1>
            <p className="text-sm text-dn-muted" data-testid="pairing-auto">
              One moment while we link this device to your roster.
            </p>
          </CardBody>
        </Card>
      </main>
    );
  }

  return (
    <main className="min-h-screen flex items-center justify-center bg-dn-fog px-4">
      <Card className="w-full max-w-sm">
        <CardBody className="space-y-4">
          <p className="font-mono text-xs uppercase tracking-widest text-dn-steel">Ratiba · Crew</p>
          <h1 className="font-display text-3xl text-dn-dark">Pair your device</h1>
          <p className="text-sm text-dn-muted">
            Ask your crewing officer for a one-time pairing code, then enter it below.
          </p>
          <form onSubmit={onSubmit} className="space-y-3" data-testid="pairing-form">
            <Label htmlFor="code">Pairing code</Label>
            <Input
              id="code"
              autoFocus
              value={code}
              onChange={(e) => setCode(e.target.value)}
              maxLength={16}
              placeholder="e.g. ABC12345"
              required
              data-testid="pairing-code-input"
            />
            {error && (
              <p className="text-sm text-dn-red" role="alert" data-testid="pairing-error">
                {error}
              </p>
            )}
            <Button
              type="submit"
              size="lg"
              className="w-full"
              disabled={submitting}
              data-testid="pairing-submit"
            >
              {submitting ? "Pairing…" : "Pair"}
            </Button>
          </form>
        </CardBody>
      </Card>
    </main>
  );
}

function DutyToday() {
  const [state, setState] = useState<{
    loading: boolean;
    error?: string;
    data?: DutyTodayResponse;
  }>({ loading: true });

  useEffect(() => {
    pilotApi<DutyTodayResponse>("/api/v1/crew/me/duty")
      .then((data) => setState({ loading: false, data }))
      .catch((err) =>
        setState({
          loading: false,
          error: err instanceof Error ? err.message : "Failed to load",
        }),
      );
  }, []);

  if (state.loading) return <p className="text-sm text-dn-muted">Loading…</p>;
  if (state.error) return <p className="text-sm text-dn-red">{state.error}</p>;
  if (!state.data?.has_duty) {
    return (
      <div className="rounded-md bg-dn-fog p-4 text-center">
        <p className="font-display text-2xl text-dn-dark">✅ No duty today</p>
        <p className="mt-1 text-sm text-dn-muted">Rest well.</p>
      </div>
    );
  }
  const d = state.data.duty_day!;
  return (
    <div className="space-y-2">
      <p className="font-mono text-sm text-dn-steel">{d.date_local}</p>
      <p className="font-display text-2xl text-dn-dark">
        {d.aircraft_reg} <Badge tone="steel">{d.aircraft_type}</Badge>
      </p>
      <p className="text-sm">
        Role: <span className="font-mono">{d.role_on_duty}</span>
      </p>
      <p className="text-sm">Sectors: {d.sector_ids.join(", ")}</p>
      {d.report_time && d.off_duty_time && (
        <p className="text-sm">
          Report{" "}
          <span className="font-mono">
            {new Date(d.report_time).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>{" "}
          · Off{" "}
          <span className="font-mono">
            {new Date(d.off_duty_time).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </p>
      )}
      {d.legality_state && (
        <p className="text-sm">
          FTL state:{" "}
          <Badge
            tone={
              d.legality_state === "LEGAL"
                ? "green"
                : d.legality_state === "AT_LIMIT"
                  ? "amber"
                  : "red"
            }
          >
            {d.legality_state}
          </Badge>
        </p>
      )}
    </div>
  );
}

function Roster() {
  const [state, setState] = useState<{
    loading: boolean;
    error?: string;
    data?: RosterResponse;
  }>({ loading: true });

  useEffect(() => {
    pilotApi<RosterResponse>("/api/v1/crew/me/roster")
      .then((data) => setState({ loading: false, data }))
      .catch((err) =>
        setState({
          loading: false,
          error: err instanceof Error ? err.message : "Failed to load",
        }),
      );
  }, []);

  if (state.loading) return <p className="text-sm text-dn-muted">Loading…</p>;
  if (state.error) return <p className="text-sm text-dn-red">{state.error}</p>;
  if (!state.data?.duty_days.length) {
    return <p className="text-sm text-dn-muted">No duty days in the next 14 days.</p>;
  }
  return (
    <ul className="space-y-3" data-testid="me-roster-list">
      {state.data.duty_days.map((d, i) => (
        <li key={i} className="rounded-md border border-dn-steel-lt bg-dn-fog p-3">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-dn-steel">{d.date_local}</span>
            <Badge tone="steel">{d.aircraft_type}</Badge>
          </div>
          <p className="mt-1 text-dn-dark">
            {d.aircraft_reg} · {d.role_on_duty}
          </p>
          <p className="text-xs text-dn-muted">Sectors: {d.sector_ids.join(", ")}</p>
        </li>
      ))}
    </ul>
  );
}

function Currency() {
  const [state, setState] = useState<{
    loading: boolean;
    error?: string;
    data?: CurrencyResponse;
  }>({ loading: true });

  useEffect(() => {
    pilotApi<CurrencyResponse>("/api/v1/crew/me/currency")
      .then((data) => setState({ loading: false, data }))
      .catch((err) =>
        setState({
          loading: false,
          error: err instanceof Error ? err.message : "Failed to load",
        }),
      );
  }, []);

  if (state.loading) return <p className="text-sm text-dn-muted">Loading…</p>;
  if (state.error) return <p className="text-sm text-dn-red">{state.error}</p>;
  if (!state.data?.currencies.length) {
    return <p className="text-sm text-dn-muted">No currencies on record.</p>;
  }
  return (
    <ul className="space-y-2" data-testid="me-currency-list">
      {state.data.currencies.map((c, i) => (
        <li
          key={i}
          className="flex items-center justify-between rounded-md border border-dn-steel-lt bg-white px-3 py-2"
        >
          <div>
            <p className="font-mono text-sm text-dn-dark">{c.currency_type}</p>
            <p className="text-xs text-dn-muted">
              expires {c.expires_date} ({c.days_remaining > 0 ? "+" : ""}
              {c.days_remaining}d)
            </p>
          </div>
          <Badge tone={c.state === "GREEN" ? "green" : c.state === "AMBER" ? "amber" : "red"}>
            {c.state}
          </Badge>
        </li>
      ))}
    </ul>
  );
}

function Notices() {
  const [rows, setRows] = useState<PilotNotice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    try {
      const data = await pilotApi<PilotNotice[]>("/api/v1/crew/me/notices");
      setRows(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function ack(id: string) {
    try {
      await pilotApi(`/api/v1/crew/me/notices/${id}/ack`, { method: "POST" });
      await reload();
    } catch {
      /* surfaced on next reload */
    }
  }

  if (loading) return <p className="text-sm text-dn-muted">Loading…</p>;
  if (error) return <p className="text-sm text-dn-red">{error}</p>;
  if (!rows.length) return <p className="text-sm text-dn-muted">No notices right now.</p>;

  return (
    <ul className="space-y-3" data-testid="me-notices-list">
      {rows.map((n) => (
        <li key={n.id} className="rounded-md border border-dn-steel-lt bg-dn-fog p-3">
          <div className="flex items-center gap-2 flex-wrap">
            {n.pinned && <Badge tone="gold">📌</Badge>}
            <Badge tone="steel">{n.category}</Badge>
            <Badge
              tone={n.severity === "INFO" ? "steel" : n.severity === "IMPORTANT" ? "amber" : "red"}
            >
              {n.severity}
            </Badge>
          </div>
          <p className="mt-1 font-medium text-dn-dark">{n.title}</p>
          <p className="mt-1 text-sm text-dn-muted whitespace-pre-line">{n.body}</p>
          {n.image_url && (
            <img
              src={n.image_url}
              alt=""
              className="mt-2 max-h-48 rounded border border-dn-steel-lt"
            />
          )}
          {n.requires_ack &&
            (n.acknowledged ? (
              <p className="mt-2 text-xs text-dn-green">✓ Acknowledged</p>
            ) : (
              <Button
                size="sm"
                className="mt-2"
                onClick={() => ack(n.id)}
                data-testid={`ack-${n.id}`}
              >
                Acknowledge
              </Button>
            ))}
        </li>
      ))}
    </ul>
  );
}

export function CrewMePage() {
  const [profile, setProfile] = useState<PilotProfile | null>(() => pilotStore.getProfile());
  const [tab, setTab] = useState<Tab>("today");

  if (!profile) {
    return <PairingScreen onPaired={setProfile} />;
  }

  return (
    <main className="min-h-screen bg-dn-fog">
      <header className="bg-white border-b border-dn-steel-lt">
        <div className="mx-auto max-w-md px-4 py-3 flex items-center justify-between">
          <div>
            <p className="font-mono text-xs uppercase tracking-widest text-dn-steel">Ratiba</p>
            <p className="font-display text-lg text-dn-dark">
              {profile.employee_no} <Badge tone="steel">{profile.role}</Badge>
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              pilotStore.clear();
              setProfile(null);
            }}
            data-testid="me-signout"
          >
            Sign out
          </Button>
        </div>
        <nav className="mx-auto max-w-md px-4 flex gap-1 -mb-px">
          {(["today", "roster", "currency", "notices"] as Tab[]).map((t) => (
            <button
              key={t}
              type="button"
              onClick={() => setTab(t)}
              className={cn(
                "px-3 py-2 text-sm font-medium border-b-2 capitalize",
                tab === t ? "border-dn-gold text-dn-dark" : "border-transparent text-dn-muted",
              )}
              data-testid={`me-tab-${t}`}
            >
              {t}
            </button>
          ))}
        </nav>
      </header>
      <section className="mx-auto max-w-md px-4 py-4">
        <Card>
          <CardHeader>
            <CardTitle className="capitalize">{tab}</CardTitle>
          </CardHeader>
          <CardBody>
            {tab === "today" && <DutyToday />}
            {tab === "roster" && <Roster />}
            {tab === "currency" && <Currency />}
            {tab === "notices" && <Notices />}
          </CardBody>
        </Card>
      </section>
    </main>
  );
}
