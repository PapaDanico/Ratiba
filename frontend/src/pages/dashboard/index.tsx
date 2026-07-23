import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Skeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";
import { safeStorage } from "@/lib/safeStorage";
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
  const [collapsed, setCollapsed] = useState(() => safeStorage.get(GUIDE_COLLAPSE_KEY) === "1");

  function toggle() {
    const next = !collapsed;
    setCollapsed(next);
    safeStorage.set(GUIDE_COLLAPSE_KEY, next ? "1" : "0");
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
            className="text-xs text-dn-steel-deep underline shrink-0"
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
                    <span className="font-mono text-[11px] uppercase tracking-wide text-dn-steel-deep">
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

type ComplianceAlert = {
  severity: "RED" | "AMBER";
  category: "FTL" | "DOCUMENT" | "CURRENCY" | "TYPE_RATING";
  title: string;
  detail: string;
  date: string;
  crew_id: string;
  link: string;
};

type AlertsResponse = {
  generated_at: string;
  counts: { red: number; amber: number };
  alerts: ComplianceAlert[];
};

const CATEGORY_LABEL: Record<ComplianceAlert["category"], string> = {
  FTL: "FTL",
  DOCUMENT: "Document",
  CURRENCY: "Currency",
  TYPE_RATING: "Type rating",
};

/**
 * Live compliance sweep: non-LEGAL duties in the recent window plus anything
 * expired or expiring within 30 days, worst first. The one card an officer
 * must read before doing anything else — hidden only if the endpoint is
 * unavailable (older backend), never on error.
 */
function ComplianceAlerts({ data, error }: { data: AlertsResponse | null; error: boolean }) {
  if (error) {
    return (
      <Card className="border-dn-red/40">
        <CardBody className="text-sm text-dn-red">Compliance alerts failed to load.</CardBody>
      </Card>
    );
  }
  if (!data) return null;
  const { counts, alerts } = data;
  if (!alerts.length) {
    return (
      <Card className="border-dn-green/30 bg-dn-green/5" data-testid="alerts-clear">
        <CardBody className="flex items-center gap-3">
          <span aria-hidden className="text-xl">
            ✅
          </span>
          <p className="text-sm text-dn-dark">
            <span className="font-medium">No compliance alerts.</span>{" "}
            <span className="text-dn-muted">
              All recorded duties are legal and nothing expires within 30 days.
            </span>
          </p>
        </CardBody>
      </Card>
    );
  }
  const shown = alerts.slice(0, 8);
  return (
    <Card
      className={
        counts.red > 0 ? "border-dn-red/40 bg-dn-red/5" : "border-dn-amber/40 bg-dn-amber/5"
      }
      data-testid="alerts-panel"
    >
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <CardTitle>Compliance alerts</CardTitle>
          <div className="flex gap-2 text-xs">
            {counts.red > 0 && <Badge tone="red">{counts.red} critical</Badge>}
            {counts.amber > 0 && <Badge tone="amber">{counts.amber} warning</Badge>}
          </div>
        </div>
      </CardHeader>
      <CardBody>
        <ul className="divide-y divide-dn-steel-lt/60">
          {shown.map((a, i) => (
            <li key={i} className="py-2 first:pt-0 last:pb-0">
              <Link to={a.link} className="group flex items-start gap-3">
                <Badge tone={a.severity === "RED" ? "red" : "amber"}>
                  {CATEGORY_LABEL[a.category]}
                </Badge>
                <span className="min-w-0 text-sm">
                  <span className="font-medium text-dn-dark group-hover:underline">{a.title}</span>{" "}
                  <span className="text-dn-muted">· {a.detail}</span>
                </span>
              </Link>
            </li>
          ))}
        </ul>
        {alerts.length > shown.length && (
          <p className="mt-2 text-xs text-dn-muted">…and {alerts.length - shown.length} more.</p>
        )}
      </CardBody>
    </Card>
  );
}

type HeroTone = "red" | "amber" | "steel" | "green";

const HERO_STYLE: Record<HeroTone, string> = {
  red: "border-dn-red/40 bg-dn-red/5",
  amber: "border-dn-amber/40 bg-dn-amber/5",
  steel: "border-dn-steel/30 bg-dn-steel/5",
  green: "border-dn-green/30 bg-dn-green/5",
};

/**
 * "One thing that needs you" — surfaces the single most-urgent item above the
 * tiles, by descending severity. Reuses counts already loaded for the tiles
 * (no extra requests); links straight to the screen that resolves it.
 */
function AttentionHero({
  expiredCurrency,
  expiringCurrency,
  fatigueHigh,
  pendingApprovals,
  noticesPendingAck,
}: {
  expiredCurrency: number;
  expiringCurrency: number;
  fatigueHigh: number;
  pendingApprovals: number;
  noticesPendingAck: number;
}) {
  let hero: { tone: HeroTone; icon: string; title: string; detail: string; to: string };
  if (expiredCurrency > 0) {
    hero = {
      tone: "red",
      icon: "⛔",
      title: `${expiredCurrency} crew with an expired currency`,
      detail: "These crew can't be legally rostered until renewed. Review the currency dashboard.",
      to: "/currency",
    };
  } else if (fatigueHigh > 0) {
    hero = {
      tone: "red",
      icon: "🌙",
      title: `${fatigueHigh} crew at a HIGH fatigue band`,
      detail: "Advisory fatigue screen flagged elevated risk over the last 28 days.",
      to: "/fatigue",
    };
  } else if (expiringCurrency > 0) {
    hero = {
      tone: "amber",
      icon: "⏳",
      title: `${expiringCurrency} currency item${expiringCurrency > 1 ? "s" : ""} expiring within 30 days`,
      detail: "Schedule renewals before they lapse to keep crew available.",
      to: "/currency",
    };
  } else if (pendingApprovals > 0) {
    hero = {
      tone: "steel",
      icon: "📝",
      title: `${pendingApprovals} request${pendingApprovals > 1 ? "s" : ""} awaiting your decision`,
      detail: "Leave and swap requests are pending approval.",
      to: "/leave",
    };
  } else if (noticesPendingAck > 0) {
    hero = {
      tone: "steel",
      icon: "📣",
      title: `${noticesPendingAck} notice${noticesPendingAck > 1 ? "s" : ""} awaiting crew acknowledgement`,
      detail: "Some crew haven't yet acknowledged a required notice.",
      to: "/notices",
    };
  } else {
    hero = {
      tone: "green",
      icon: "✅",
      title: "All clear — nothing needs your attention",
      detail: "No expired currencies, fatigue flags, or pending approvals right now.",
      to: "/roster",
    };
  }

  return (
    <Link to={hero.to} className="block" data-testid="attention-hero">
      <div
        className={`flex items-center gap-4 rounded-lg border p-4 transition-all duration-150 hover:-translate-y-0.5 hover:shadow-md ${HERO_STYLE[hero.tone]}`}
      >
        <span aria-hidden className="text-3xl">
          {hero.icon}
        </span>
        <div>
          <p className="font-display text-xl text-dn-dark" data-testid="attention-hero-title">
            {hero.title}
          </p>
          <p className="text-sm text-dn-muted">{hero.detail}</p>
        </div>
      </div>
    </Link>
  );
}

type TodayAssignment = {
  duty_day_key: string;
  aircraft_reg: string;
  sector_ids: string[];
  captain_id: string;
  fo_id: string;
  legality_state: "LEGAL" | "AT_LIMIT" | "REQUIRES_FRMS_DEROGATION" | "ILLEGAL" | null;
};

type TodayDuty = {
  id: string;
  crew_name: string;
  type: string;
  start: string;
  end: string;
};

type CrewName = { id: string; employee_no: string; first_name: string; last_name: string };

const LEGALITY_TONE: Record<string, "green" | "amber" | "red"> = {
  LEGAL: "green",
  AT_LIMIT: "amber",
  REQUIRES_FRMS_DEROGATION: "amber",
  ILLEGAL: "red",
};

function utcHm(iso: string): string {
  return `${new Date(iso).toISOString().slice(11, 16)}Z`;
}

/** Answers the morning question at a glance: who is flying today, who is on
 * standby, and whether everything is legal. Fetches on its own so a failure
 * or slow response never holds up the rest of the dashboard. */
function TodayStrip() {
  const [flights, setFlights] = useState<TodayAssignment[] | null>(null);
  const [duties, setDuties] = useState<TodayDuty[]>([]);
  const [crewById, setCrewById] = useState<Record<string, string>>({});
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    const today = isoDaysAgo(0);
    Promise.all([
      api<TodayAssignment[]>(`/api/v1/roster?date_from=${today}&date_to=${today}`),
      api<TodayDuty[]>(`/api/v1/duties?date_from=${today}&date_to=${today}`).catch(() => []),
      api<CrewName[]>("/api/v1/crew"),
    ]).then(
      ([r, d, crew]) => {
        if (cancelled) return;
        setFlights(r);
        setDuties(d);
        // The roster endpoint identifies crew by employee number; map both
        // keys so either identifier resolves to a name.
        setCrewById(
          Object.fromEntries(
            crew.flatMap((c) => {
              const name = `${c.first_name} ${c.last_name}`;
              return [
                [c.id, name],
                [c.employee_no, name],
              ];
            }),
          ),
        );
      },
      () => !cancelled && setFailed(true),
    );
    return () => {
      cancelled = true;
    };
  }, []);

  if (failed) return null; // advisory panel — vanish quietly rather than alarm

  const name = (id: string) => crewById[id] ?? "—";
  const empty = flights !== null && flights.length === 0 && duties.length === 0;

  return (
    <Card data-testid="today-strip">
      <CardHeader>
        <div className="flex items-baseline justify-between">
          <CardTitle>Today</CardTitle>
          <span className="text-xs text-dn-muted">
            {new Date().toLocaleDateString("en-GB", {
              weekday: "long",
              day: "numeric",
              month: "long",
            })}
          </span>
        </div>
      </CardHeader>
      <CardBody className="p-4">
        {flights === null ? (
          <Skeleton className="h-14 w-full" />
        ) : empty ? (
          <p className="px-2 py-1 text-sm text-dn-muted">
            No flights or standby today. Tomorrow&apos;s roster is on the{" "}
            <Link to="/app/roster" className="underline hover:text-dn-dark">
              Roster page
            </Link>
            .
          </p>
        ) : (
          <div className="flex gap-3 overflow-x-auto pb-1">
            {flights.map((f) => (
              <div
                key={f.duty_day_key}
                className="min-w-[15rem] shrink-0 rounded-dn-sm border border-dn-sand bg-dn-fog/40 px-4 py-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-sm font-medium text-dn-steel-deep">
                    {f.sector_ids.join(" · ")}
                  </span>
                  {f.legality_state && (
                    <Badge tone={LEGALITY_TONE[f.legality_state] ?? "neutral"}>
                      {f.legality_state === "REQUIRES_FRMS_DEROGATION"
                        ? "FRMS"
                        : f.legality_state.replace("_", " ")}
                    </Badge>
                  )}
                </div>
                <p className="mt-1 text-xs text-dn-muted">
                  <span className="font-mono">{f.aircraft_reg}</span> · {name(f.captain_id)} /{" "}
                  {name(f.fo_id)}
                </p>
              </div>
            ))}
            {duties.map((d) => (
              <div
                key={d.id}
                className="min-w-[13rem] shrink-0 rounded-dn-sm border border-dn-sand bg-white px-4 py-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <span className="text-sm font-medium text-dn-dark">Standby</span>
                  <span className="font-mono text-xs text-dn-muted">
                    {utcHm(d.start)}–{utcHm(d.end)}
                  </span>
                </div>
                <p className="mt-1 text-xs text-dn-muted">{d.crew_name}</p>
              </div>
            ))}
          </div>
        )}
      </CardBody>
    </Card>
  );
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
  const [alertsData, setAlertsData] = useState<AlertsResponse | null>(null);
  const [alertsError, setAlertsError] = useState(false);
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
        // Separate fetch: a 404/501 (older backend) hides the card; a real
        // failure shows an inline error rather than silently hiding risk.
        api<AlertsResponse>("/api/v1/alerts").then(
          (a) => !cancelled && setAlertsData(a),
          (e) => {
            if (cancelled) return;
            if (!(e instanceof ApiError && (e.status === 404 || e.status === 501)))
              setAlertsError(true);
          },
        );
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
      <AttentionHero
        expiredCurrency={currencyCounts.red}
        expiringCurrency={currencyCounts.amber}
        fatigueHigh={fatigueHigh ?? 0}
        pendingApprovals={pendingLeave + pendingSwaps}
        noticesPendingAck={noticesPendingAck}
      />
      <TodayStrip />
      <ComplianceAlerts data={alertsData} error={alertsError} />
      <DemoGuide />
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
        <Link to="/app/leave" className="block">
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
        <Link to="/app/swaps" className="block">
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
        <Link to="/app/currency" className="block">
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
        <Link to="/app/fatigue" className="block">
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
        <Link to="/app/notices" className="block">
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
            <Link to="/app/training" className="text-xs text-dn-steel-deep underline">
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
