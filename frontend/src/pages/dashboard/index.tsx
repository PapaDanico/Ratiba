import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const GUIDE_DISMISS_KEY = "ratiba.guide.dismissed";

const GUIDE_STEPS = [
  ["Routings", "Add flights — single, or recurring across a date range (UTC times)."],
  ["Crew + Training", "Add crew, then give each a type rating under Training."],
  ["Roster → Auto-generate", "One click builds a legal draft roster; review and Publish."],
  ["Crew → Roster PDF", "Download a per-pilot monthly roster to share."],
  ["Audit packs", "Generate a KCAA audit pack and export the payroll CSV."],
];

function DemoGuide() {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(GUIDE_DISMISS_KEY) === "1");
  if (dismissed) return null;
  return (
    <Card className="border-dn-gold/40 bg-dn-gold/5">
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl text-dn-dark mb-2">Getting started</h2>
            <ol className="space-y-1 text-sm text-dn-muted list-decimal list-inside">
              {GUIDE_STEPS.map(([title, desc]) => (
                <li key={title}>
                  <span className="font-medium text-dn-dark">{title}</span> — {desc}
                </li>
              ))}
            </ol>
          </div>
          <button
            type="button"
            onClick={() => {
              localStorage.setItem(GUIDE_DISMISS_KEY, "1");
              setDismissed(true);
            }}
            className="text-xs text-dn-steel underline shrink-0"
            data-testid="dismiss-guide"
          >
            Dismiss
          </button>
        </div>
      </CardBody>
    </Card>
  );
}

type CurrencyStatus = {
  crew_id: string;
  currency_type: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

type LeaveRequest = {
  id: string;
  status: string;
};

export function DashboardPage() {
  const { user } = useAuth();
  const [pendingLeave, setPendingLeave] = useState<number>(0);
  const [currencyCounts, setCurrencyCounts] = useState({
    green: 0,
    amber: 0,
    red: 0,
  });
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [pending, currencies] = await Promise.all([
          api<LeaveRequest[]>("/api/v1/leave?status=PENDING"),
          api<CurrencyStatus[]>("/api/v1/crew/currency/dashboard"),
        ]);
        if (cancelled) return;
        setPendingLeave(pending.length);
        const counts = { green: 0, amber: 0, red: 0 };
        for (const c of currencies) {
          if (c.state === "GREEN") counts.green++;
          else if (c.state === "AMBER") counts.amber++;
          else counts.red++;
        }
        setCurrencyCounts(counts);
      } catch (err) {
        setError(err instanceof ApiError ? err.message : "Failed to load");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-3xl text-dn-dark">
          Welcome back, {user?.full_name.split(" ")[0]}
        </h1>
        <p className="mt-1 text-dn-muted text-sm">
          Operations overview — KCARs 2025 Part 8 baseline.
        </p>
      </div>
      {error && (
        <Card>
          <CardBody className="text-sm text-dn-red">{error}</CardBody>
        </Card>
      )}
      <DemoGuide />
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Pending leave</CardTitle>
          </CardHeader>
          <CardBody>
            <div className="font-display text-5xl text-dn-dark" data-testid="pending-leave-count">
              {pendingLeave}
            </div>
            <p className="mt-2 text-sm text-dn-muted">Requests awaiting your decision.</p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Currency status</CardTitle>
          </CardHeader>
          <CardBody className="space-y-2">
            <div className="flex items-center justify-between">
              <Badge tone="green">Current</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.green}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="amber">Expiring ≤ 30 d</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.amber}</span>
            </div>
            <div className="flex items-center justify-between">
              <Badge tone="red">Expired</Badge>
              <span className="font-mono text-dn-dark">{currencyCounts.red}</span>
            </div>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>This week</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-dn-muted">
              Roster calendar lives under{" "}
              <a href="/roster" className="text-dn-steel underline">
                Roster
              </a>
              . FTL violations show inline before publication.
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
