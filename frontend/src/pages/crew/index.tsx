import { useEffect, useRef, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Modal } from "@/components/ui/Modal";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { EmptyState } from "@/components/ui/EmptyState";
import { ShareButtons } from "@/components/ui/ShareButtons";
import { api, ApiError, authFetch } from "@/lib/api";

type Crew = {
  id: string;
  employee_no: string;
  first_name: string;
  last_name: string;
  role: "CAPT" | "FO" | "SO" | "PURSER" | "CABIN_CREW" | "ENGINEER";
  crew_category: "FLIGHT_DECK" | "CABIN" | "ENGINEERING";
  base_station: string;
  contract_type: string;
  active: boolean;
  email: string | null;
  phone_number: string | null;
};

type CrossOpWindow = {
  label: string;
  metric: string;
  days: number;
  total_h: number;
  limit_h: number;
  state: "LEGAL" | "AT_LIMIT" | "OVER";
};

type CrossOpFtl = {
  crew_employee_no: string;
  person_ref: string | null;
  linked: boolean;
  operator_count: number;
  as_of: string;
  windows: CrossOpWindow[];
};

const XOP_TONE: Record<CrossOpWindow["state"], "green" | "amber" | "red"> = {
  LEGAL: "green",
  AT_LIMIT: "amber",
  OVER: "red",
};

function CrossOpFtlButton({ crew }: { crew: Crew }) {
  const [open, setOpen] = useState(false);
  const [data, setData] = useState<CrossOpFtl | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    setOpen(true);
    setBusy(true);
    setError(null);
    setData(null);
    try {
      const body = await api<CrossOpFtl>(`/api/v1/crew/${crew.id}/cross-operator-ftl`);
      setData(body);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button
        type="button"
        onClick={load}
        className="text-dn-steel underline text-xs hover:text-dn-dark"
        data-testid={`xop-ftl-${crew.employee_no}`}
      >
        Cross-op FTL
      </button>
      {open && (
        <Modal
          title={`Cross-operator FTL — ${crew.first_name} ${crew.last_name}`}
          onClose={() => setOpen(false)}
          maxWidth="max-w-lg"
        >
          {busy ? (
            <p className="text-sm text-dn-muted">Loading…</p>
          ) : error ? (
            <p className="text-sm text-dn-red">{error}</p>
          ) : data ? (
            <>
              <p className="text-sm text-dn-muted mb-3">
                {data.linked ? (
                  <>
                    Aggregated across <strong>{data.operator_count}</strong> operators sharing ref{" "}
                    <span className="font-mono">{data.person_ref}</span>. Totals only — other
                    operators&apos; duty detail is not shown.
                  </>
                ) : (
                  <>
                    Not linked to another operator
                    {data.person_ref ? (
                      <>
                        {" "}
                        (ref <span className="font-mono">{data.person_ref}</span>)
                      </>
                    ) : null}{" "}
                    — these are this operator&apos;s cumulative totals.
                  </>
                )}
              </p>
              <table className="w-full text-sm responsive-table">
                <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Window</th>
                    <th className="py-2 pr-4 font-medium">Total</th>
                    <th className="py-2 pr-4 font-medium">Limit</th>
                    <th className="py-2 pr-4 font-medium">State</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dn-steel-lt">
                  {data.windows.map((w) => (
                    <tr key={w.label}>
                      <td data-label="Window" className="py-2 pr-4 text-dn-dark">
                        {w.label}
                      </td>
                      <td data-label="Total" className="py-2 pr-4 font-mono">
                        {w.total_h}h
                      </td>
                      <td data-label="Limit" className="py-2 pr-4 font-mono text-dn-muted">
                        {w.limit_h}h
                      </td>
                      <td data-label="State" className="py-2 pr-4">
                        <Badge tone={XOP_TONE[w.state]}>{w.state}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs text-dn-muted">As of {data.as_of}.</p>
            </>
          ) : null}
          <div className="flex justify-end pt-3">
            <Button type="button" variant="secondary" size="sm" onClick={() => setOpen(false)}>
              Close
            </Button>
          </div>
        </Modal>
      )}
    </>
  );
}

const CATEGORY_LABEL: Record<Crew["crew_category"], string> = {
  FLIGHT_DECK: "Flight deck",
  CABIN: "Cabin",
  ENGINEERING: "Engineering",
};

const CATEGORY_TONE: Record<Crew["crew_category"], "steel" | "gold" | "amber"> = {
  FLIGHT_DECK: "steel",
  CABIN: "gold",
  ENGINEERING: "amber",
};

function todayYearMonth(): { year: number; month: number } {
  const d = new Date();
  return { year: d.getFullYear(), month: d.getMonth() + 1 };
}

function RosterPdfButton({ crew }: { crew: Crew }) {
  const { year: curYear, month: curMonth } = todayYearMonth();
  const [year, setYear] = useState(curYear);
  const [month, setMonth] = useState(curMonth);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  async function download() {
    setBusy(true);
    setError(null);
    try {
      const url = `/api/v1/roster/crew/${crew.id}/monthly-pdf?year=${year}&month=${month}`;
      const res = await authFetch(url);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const blob = await res.blob();
      const link = document.createElement("a");
      link.href = URL.createObjectURL(blob);
      link.download = `roster_${crew.employee_no}_${year}-${String(month).padStart(2, "0")}.pdf`;
      link.click();
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Download failed");
    } finally {
      setBusy(false);
    }
  }

  const months = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  const years = [curYear - 1, curYear, curYear + 1];

  return (
    <div className="relative" ref={ref}>
      <Button
        size="sm"
        variant="secondary"
        onClick={() => setOpen((o) => !o)}
        data-testid={`roster-pdf-btn-${crew.id}`}
      >
        Roster PDF
      </Button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-52 bg-white border border-dn-steel-lt rounded-lg shadow-lg p-3 space-y-2">
          <p className="text-xs font-medium text-dn-dark">Download monthly roster</p>
          <div className="flex gap-2">
            <select
              value={month}
              onChange={(e) => setMonth(Number(e.target.value))}
              className="flex-1 text-xs border border-dn-steel-lt rounded px-1 py-1"
            >
              {months.map((m, i) => (
                <option key={i} value={i + 1}>
                  {m}
                </option>
              ))}
            </select>
            <select
              value={year}
              onChange={(e) => setYear(Number(e.target.value))}
              className="flex-1 text-xs border border-dn-steel-lt rounded px-1 py-1"
            >
              {years.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="text-xs text-dn-red">{error}</p>}
          <Button size="sm" className="w-full" onClick={download} disabled={busy}>
            {busy ? "Generating…" : "Download PDF"}
          </Button>
        </div>
      )}
    </div>
  );
}

function CalendarFeedButton({ crew }: { crew: Crew }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [url, setUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  async function generate() {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await api<{ path: string }>(`/api/v1/crew/${crew.id}/calendar-feed`, {
        method: "POST",
      });
      setUrl(`${window.location.origin}${res.path}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to create feed");
    } finally {
      setBusy(false);
    }
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    if (next && !url) await generate();
  }

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <Button
        size="sm"
        variant="secondary"
        onClick={toggle}
        data-testid={`calendar-feed-btn-${crew.id}`}
      >
        Calendar feed
      </Button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-72 bg-white border border-dn-steel-lt rounded-lg shadow-lg p-3 space-y-2">
          <p className="text-xs font-medium text-dn-dark">Subscribe this roster in a calendar</p>
          <p className="text-xs text-dn-muted">
            Add this URL in Google/Apple/Outlook as a subscribed calendar — it stays in sync.
          </p>
          {busy ? (
            <p className="text-xs text-dn-muted">Generating…</p>
          ) : error ? (
            <p className="text-xs text-dn-red">{error}</p>
          ) : url ? (
            <>
              <textarea
                readOnly
                value={url}
                className="w-full text-[10px] font-mono border border-dn-steel-lt rounded p-1 h-16"
                onFocus={(e) => e.currentTarget.select()}
              />
              <Button size="sm" className="w-full" onClick={copy}>
                {copied ? "Copied ✓" : "Copy link"}
              </Button>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

function PairDeviceButton({ crew }: { crew: Crew }) {
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [code, setCode] = useState<string | null>(null);
  const [expiresAt, setExpiresAt] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const link = code ? `${window.location.origin}/crew/me?pair=${code}` : null;
  // Share the magic link straight to the pilot via their own messaging app.
  const shareMessage = `Pair your Ratiba crew app — open this link on your phone: ${link}`;

  useEffect(() => {
    if (!open) return;
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  async function generate() {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      const res = await api<{ code: string; expires_at: string }>(
        `/api/v1/crew/${crew.id}/pairing-token`,
        { method: "POST" },
      );
      setCode(res.code);
      setExpiresAt(res.expires_at);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to issue pairing code");
    } finally {
      setBusy(false);
    }
  }

  async function toggle() {
    const next = !open;
    setOpen(next);
    // Always mint a fresh single-use code when (re)opening.
    if (next) await generate();
  }

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  return (
    <div className="relative" ref={ref}>
      <Button
        size="sm"
        variant="secondary"
        onClick={toggle}
        data-testid={`pair-device-btn-${crew.id}`}
      >
        Pair device
      </Button>
      {open && (
        <div className="absolute right-0 z-20 mt-1 w-72 bg-white border border-dn-steel-lt rounded-lg shadow-lg p-3 space-y-2">
          <p className="text-xs font-medium text-dn-dark">Pair {crew.employee_no}&rsquo;s device</p>
          <p className="text-xs text-dn-muted">
            Send this one-tap link — opening it on the pilot&rsquo;s phone pairs the{" "}
            <span className="font-mono">/crew/me</span> view automatically. Single-use.
          </p>
          {busy ? (
            <p className="text-xs text-dn-muted">Issuing…</p>
          ) : error ? (
            <p className="text-xs text-dn-red">{error}</p>
          ) : link ? (
            <>
              <textarea
                readOnly
                value={link}
                className="w-full text-[10px] font-mono border border-dn-steel-lt rounded p-1 h-16"
                onFocus={(e) => e.currentTarget.select()}
                data-testid={`pair-link-${crew.id}`}
              />
              <Button size="sm" className="w-full" onClick={copy}>
                {copied ? "Copied ✓" : "Copy pairing link"}
              </Button>
              <ShareButtons
                message={shareMessage}
                phone={crew.phone_number}
                email={crew.email}
                subject="Ratiba crew app pairing"
                testidPrefix={`pair-share-${crew.id}`}
              />
              <p className="text-[10px] text-dn-muted">
                Or dictate the code <span className="font-mono text-dn-steel">{code}</span>
                {expiresAt ? ` · expires ${new Date(expiresAt).toLocaleString()}` : ""}
              </p>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

export function CrewPage() {
  const [rows, setRows] = useState<Crew[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await api<Crew[]>("/api/v1/crew");
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load crew");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Crew roster</CardTitle>
      </CardHeader>
      <CardBody>
        {loading ? (
          <TableSkeleton rows={6} cols={6} />
        ) : error ? (
          <p className="text-sm text-dn-red">{error}</p>
        ) : rows.length === 0 ? (
          <EmptyState
            icon="👥"
            title="No crew yet"
            hint="Import your roster via the Import page, or add crew through the API."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="rtable min-w-full text-sm" data-testid="crew-table">
              <thead className="sticky-head text-left text-dn-muted border-b border-dn-steel-lt">
                <tr>
                  <th className="py-3 pr-4 font-medium">Employee #</th>
                  <th className="py-3 pr-4 font-medium">Name</th>
                  <th className="py-3 pr-4 font-medium">Role</th>
                  <th className="py-3 pr-4 font-medium">Category</th>
                  <th className="py-3 pr-4 font-medium">Base</th>
                  <th className="py-3 pr-4 font-medium">Email</th>
                  <th className="py-3 pr-4 font-medium">Phone</th>
                  <th className="py-3 pr-4 font-medium">Status</th>
                  <th className="py-3 pr-4 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-dn-steel-lt">
                {rows.map((c) => (
                  <tr key={c.id} className="group transition-colors hover:bg-dn-fog">
                    <td data-label="Employee #" className="py-3 pr-4 font-mono text-dn-steel">
                      {c.employee_no}
                    </td>
                    <td data-label="Name" className="py-3 pr-4 text-dn-dark">
                      {c.first_name} {c.last_name}
                    </td>
                    <td data-label="Role" className="py-3 pr-4">
                      <Badge tone="steel">{c.role}</Badge>
                    </td>
                    <td data-label="Category" className="py-3 pr-4">
                      <Badge tone={CATEGORY_TONE[c.crew_category]}>
                        {CATEGORY_LABEL[c.crew_category]}
                      </Badge>
                    </td>
                    <td data-label="Base" className="py-3 pr-4 font-mono">
                      {c.base_station}
                    </td>
                    <td data-label="Email" className="py-3 pr-4 text-xs text-dn-muted">
                      {c.email ?? "—"}
                    </td>
                    <td data-label="Phone" className="py-3 pr-4 font-mono text-xs">
                      {c.phone_number ?? "—"}
                    </td>
                    <td data-label="Status" className="py-3 pr-4">
                      {c.active ? (
                        <Badge tone="green">Active</Badge>
                      ) : (
                        <Badge tone="neutral">Inactive</Badge>
                      )}
                    </td>
                    {/* Actions recede until the row is hovered/focused — calmer grid,
                        but kept full-opacity on touch (no hover) and on focus-within
                        for keyboard users. */}
                    <td data-label="" className="py-3 pr-4">
                      <div className="row-actions flex flex-wrap justify-end gap-2">
                        <RosterPdfButton crew={c} />
                        <CalendarFeedButton crew={c} />
                        <PairDeviceButton crew={c} />
                        <CrossOpFtlButton crew={c} />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
