import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

const GUIDE_COLLAPSE_KEY = "ratiba.guide.collapsed";

const GUIDE_STEPS: Array<{ title: string; tab: string; detail: string }> = [
  {
    title: "Add your aircraft & crew",
    tab: "Fleet · Crew",
    detail:
      "Register aircraft under Fleet and add pilots under Crew. (A demo workspace already comes with sample aircraft and crew, so you can skip ahead.)",
  },
  {
    title: "Qualify your crew",
    tab: "Training",
    detail:
      "Give each pilot a type rating for the aircraft they fly. The auto-roster only assigns crew who are type-rated and current, so this step is what makes scheduling work.",
  },
  {
    title: "Build the flight schedule",
    tab: "Routings",
    detail:
      "Add flights individually, or switch to Recurring to create a daily/weekly pattern across a date range in one go. Departure and arrival times are entered in UTC.",
  },
  {
    title: "Auto-generate the roster",
    tab: "Roster",
    detail:
      "Click “Auto-generate roster”. Ratiba runs the FTL-aware optimiser and shows a legal draft — assigned duties, any that couldn’t be filled, and solve time. Review it, then Publish.",
  },
  {
    title: "Share & export",
    tab: "Crew · Audit packs",
    detail:
      "From Crew, download a pilot’s monthly roster PDF or copy their calendar-feed link to subscribe in Google/Apple/Outlook. From Audit packs, generate a KCAA audit pack and export the payroll CSV.",
  },
  {
    title: "Stay ahead of expiries",
    tab: "Training · Documents",
    detail:
      "Record licences and medicals under Documents. Training → Recurrency then lists every rating, currency, and document about to lapse — colour-coded by urgency.",
  },
];

function DemoGuide() {
  const [collapsed, setCollapsed] = useState(
    () => localStorage.getItem(GUIDE_COLLAPSE_KEY) === "1",
  );

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(GUIDE_COLLAPSE_KEY, next ? "1" : "0");
  }

  return (
    <Card className="border-dn-gold/40 bg-dn-gold/5">
      <CardBody>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-xl text-dn-dark">Getting started</h2>
            {!collapsed && (
              <p className="mt-1 text-sm text-dn-muted">
                The fastest path from an empty workspace to a published, FTL-legal roster:
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={toggle}
            className="text-xs text-dn-steel underline shrink-0"
            data-testid="toggle-guide"
          >
            {collapsed ? "Show guide" : "Hide"}
          </button>
        </div>

        {!collapsed && (
          <ol className="mt-4 space-y-3">
            {GUIDE_STEPS.map((step, i) => (
              <li key={step.title} className="flex gap-3">
                <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-dn-gold/80 text-xs font-semibold text-dn-lava">
                  {i + 1}
                </span>
                <div className="min-w-0">
                  <p className="text-sm">
                    <span className="font-medium text-dn-dark">{step.title}</span>{" "}
                    <span className="font-mono text-[11px] uppercase tracking-wide text-dn-steel">
                      {step.tab}
                    </span>
                  </p>
                  <p className="text-sm text-dn-muted">{step.detail}</p>
                </div>
              </li>
            ))}
          </ol>
        )}
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

type SwapRequest = {
  id: string;
  status: string;
};

type FatigueRow = {
  employee_no: string;
  peak_band: "LOW" | "ELEVATED" | "HIGH";
};

type NoticeStat = {
  id: string;
  requires_ack: boolean;
  ack_count: number;
  crew_total: number;
};

function isoDaysAgo(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

type RecurrencyItem = {
  crew_id: string;
  employee_no: string;
  crew_name: string;
  kind: string;
  label: string;
  expires_date: string;
  days_remaining: number;
  state: "GREEN" | "AMBER" | "RED";
};

function attentionTone(state: RecurrencyItem["state"]): "amber" | "red" | "neutral" {
  if (state === "RED") return "red";
  if (state === "AMBER") return "amber";
  return "neutral";
}

export function DashboardPage() {
  const { user } = useAuth();
  const [pendingLeave, setPendingLeave] = useState<number>(0);
  const [pendingSwaps, setPendingSwaps] = useState<number>(0);
  const [fatigueHigh, setFatigueHigh] = useState<number | null>(null);
  const [noticesPendingAck, setNoticesPendingAck] = useState<number>(0);
  const [currencyCounts, setCurrencyCounts] = useState({
    green: 0,
    amber: 0,
    red: 0,
  });
  const [attention, setAttention] = useState<RecurrencyItem[]>([]);
  const [schemeSource, setSchemeSource] = useState<"operator" | "baseline" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [pending, swaps, currencies, recurrency, notices, fatigue, limits] =
          await Promise.all([
            api<LeaveRequest[]>("/api/v1/leave?status=PENDING"),
            api<SwapRequest[]>("/api/v1/swap?status=PENDING"),
            api<CurrencyStatus[]>("/api/v1/crew/currency/dashboard"),
            api<RecurrencyItem[]>("/api/v1/training/recurrency?within_days=30"),
            api<NoticeStat[]>("/api/v1/notices").catch(() => null),
            // Fatigue screen over the trailing 28 days — advisory; never block load.
            api<FatigueRow[]>(
              `/api/v1/reports/fatigue?date_from=${isoDaysAgo(28)}&date_to=${isoDaysAgo(0)}`,
            ).catch(() => null),
            // Cosmetic only — never let it fail the dashboard load.
            api<{ source: "operator" | "baseline" }>("/api/v1/ftl/limits").catch(() => null),
          ]);
        if (cancelled) return;
        setPendingLeave(pending.length);
        setPendingSwaps(swaps.length);
        if (notices)
          setNoticesPendingAck(
            notices.filter((n) => n.requires_ack && n.ack_count < n.crew_total).length,
          );
        if (fatigue) setFatigueHigh(fatigue.filter((r) => r.peak_band === "HIGH").length);
        if (limits) setSchemeSource(limits.source);
        const counts = { green: 0, amber: 0, red: 0 };
        for (const c of currencies) {
          if (c.state === "GREEN") counts.green++;
          else if (c.state === "AMBER") counts.amber++;
          else counts.red++;
        }
        setCurrencyCounts(counts);
        setAttention(recurrency);
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
          {schemeSource === "operator"
            ? "Operations overview — your operator FTL scheme (over the KCAA baseline)."
            : "Operations overview — KCAA Flight Duty Time Scheme (generic baseline)."}
        </p>
      </div>
      {error && (
        <Card>
          <CardBody className="text-sm text-dn-red">{error}</CardBody>
        </Card>
      )}
      <DemoGuide />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Link to="/leave" className="block">
          <Card interactive>
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
        </Link>
        <Link to="/swaps" className="block">
          <Card interactive>
            <CardHeader>
              <CardTitle>Pending swaps</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="font-display text-5xl text-dn-dark" data-testid="pending-swaps-count">
                {pendingSwaps}
              </div>
              <p className="mt-2 text-sm text-dn-muted">Duty-swap requests to review.</p>
            </CardBody>
          </Card>
        </Link>
        <Link to="/currency" className="block">
          <Card interactive>
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
        </Link>
        <Link to="/fatigue" className="block">
          <Card interactive>
            <CardHeader>
              <CardTitle>Fatigue watch</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="font-display text-5xl text-dn-dark" data-testid="fatigue-high-count">
                {fatigueHigh ?? "—"}
              </div>
              <p className="mt-2 text-sm text-dn-muted">
                Crew at a HIGH fatigue band over the last 28 days.
              </p>
            </CardBody>
          </Card>
        </Link>
        <Link to="/notices" className="block">
          <Card interactive>
            <CardHeader>
              <CardTitle>Notices</CardTitle>
            </CardHeader>
            <CardBody>
              <div className="font-display text-5xl text-dn-dark" data-testid="notices-pending-ack">
                {noticesPendingAck}
              </div>
              <p className="mt-2 text-sm text-dn-muted">
                Notices still awaiting crew acknowledgement.
              </p>
            </CardBody>
          </Card>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between gap-3">
            <CardTitle>Needs attention — next 30 days</CardTitle>
            <Link to="/training" className="text-xs text-dn-steel underline">
              View all
            </Link>
          </div>
        </CardHeader>
        <CardBody>
          {attention.length === 0 ? (
            <p className="text-sm text-dn-muted" data-testid="attention-empty">
              Nothing expiring in the next 30 days. ✅
            </p>
          ) : (
            <ul className="divide-y divide-dn-steel-lt" data-testid="attention-list">
              {attention.slice(0, 8).map((i, idx) => (
                <li
                  key={`${i.crew_id}-${i.label}-${idx}`}
                  className="flex items-center justify-between gap-3 py-2"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-dn-dark truncate">
                      {i.crew_name}{" "}
                      <span className="font-mono text-xs text-dn-muted">({i.employee_no})</span>
                    </p>
                    <p className="text-xs text-dn-muted truncate">{i.label}</p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className="font-mono text-xs text-dn-muted">
                      {i.days_remaining < 0
                        ? `${Math.abs(i.days_remaining)}d ago`
                        : `${i.days_remaining}d`}
                    </span>
                    <Badge tone={attentionTone(i.state)}>{i.state}</Badge>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
