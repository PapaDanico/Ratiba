import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Label } from "@/components/ui/Label";
import { Modal } from "@/components/ui/Modal";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { api, ApiError } from "@/lib/api";

type Sector = {
  id: string;
  flight_no: string;
  date: string;
  origin: string;
  destination: string;
  std: string; // UTC ISO
  sta: string; // UTC ISO
  aircraft_reg: string;
  aircraft_type: string;
  status: string;
  block_hours: number;
};

type AircraftType = { icao: string; label: string };

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function addDays(iso: string, days: number): string {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/** Format a UTC ISO datetime as "HH:MM" with a Z marker. */
function utcTime(iso: string): string {
  const d = new Date(iso);
  const hh = String(d.getUTCHours()).padStart(2, "0");
  const mm = String(d.getUTCMinutes()).padStart(2, "0");
  return `${hh}:${mm}Z`;
}

/** datetime-local value (no tz) -> UTC ISO by treating the input as UTC. */
function localInputToUtcIso(value: string): string {
  // value like "2025-06-01T08:30"; we treat it as already-UTC and append Z.
  return value.length === 16 ? `${value}:00Z` : `${value}Z`;
}

function AddRoutingForm({
  defaultDate,
  aircraftTypes,
  onAdded,
}: {
  defaultDate: string;
  aircraftTypes: AircraftType[];
  onAdded: () => void;
}) {
  const [flightNo, setFlightNo] = useState("");
  const [flightDate, setFlightDate] = useState(defaultDate);
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [std, setStd] = useState(`${defaultDate}T08:00`);
  const [sta, setSta] = useState(`${defaultDate}T10:00`);
  const [reg, setReg] = useState("");
  const [type, setType] = useState(aircraftTypes[0]?.icao ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/sectors", {
        method: "POST",
        body: JSON.stringify({
          flight_no: flightNo.trim(),
          date: flightDate,
          origin: origin.trim(),
          destination: destination.trim(),
          std: localInputToUtcIso(std),
          sta: localInputToUtcIso(sta),
          aircraft_reg: reg.trim(),
          aircraft_type: type,
        }),
      });
      setFlightNo("");
      setOrigin("");
      setDestination("");
      setReg("");
      onAdded();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add routing");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3" data-testid="add-routing-form">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <Label htmlFor="flight_no">Flight no.</Label>
          <Input
            id="flight_no"
            value={flightNo}
            onChange={(e) => setFlightNo(e.target.value)}
            placeholder="KQ410"
            required
          />
        </div>
        <div>
          <Label htmlFor="flight_date">Date</Label>
          <Input
            id="flight_date"
            type="date"
            value={flightDate}
            onChange={(e) => setFlightDate(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="origin">Origin</Label>
          <Input
            id="origin"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            placeholder="HKJK"
            required
          />
        </div>
        <div>
          <Label htmlFor="destination">Destination</Label>
          <Input
            id="destination"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="HKMO"
            required
          />
        </div>
        <div>
          <Label htmlFor="std">Departure (UTC)</Label>
          <Input
            id="std"
            type="datetime-local"
            value={std}
            onChange={(e) => setStd(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="sta">Arrival (UTC)</Label>
          <Input
            id="sta"
            type="datetime-local"
            value={sta}
            onChange={(e) => setSta(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="reg">Aircraft reg.</Label>
          <Input
            id="reg"
            value={reg}
            onChange={(e) => setReg(e.target.value)}
            placeholder="5Y-ABC"
            required
          />
        </div>
        <div>
          <Label htmlFor="type">Type</Label>
          <Select id="type" value={type} onChange={(e) => setType(e.target.value)} required>
            {aircraftTypes.map((t) => (
              <option key={t.icao} value={t.icao}>
                {t.icao}
              </option>
            ))}
          </Select>
        </div>
      </div>
      {error && <ErrorAlert message={error} />}
      <div className="flex justify-end">
        <Button type="submit" disabled={busy} data-testid="add-routing-submit">
          {busy ? "Adding…" : "Add routing"}
        </Button>
      </div>
    </form>
  );
}

const WEEKDAYS = [
  { idx: 0, label: "Mon" },
  { idx: 1, label: "Tue" },
  { idx: 2, label: "Wed" },
  { idx: 3, label: "Thu" },
  { idx: 4, label: "Fri" },
  { idx: 5, label: "Sat" },
  { idx: 6, label: "Sun" },
];

function AddRecurringForm({
  defaultFrom,
  aircraftTypes,
  onAdded,
}: {
  defaultFrom: string;
  aircraftTypes: AircraftType[];
  onAdded: (msg: string) => void;
}) {
  const [flightNo, setFlightNo] = useState("");
  const [origin, setOrigin] = useState("");
  const [destination, setDestination] = useState("");
  const [stdTime, setStdTime] = useState("08:00");
  const [staTime, setStaTime] = useState("10:00");
  const [reg, setReg] = useState("");
  const [type, setType] = useState(aircraftTypes[0]?.icao ?? "");
  const [dateFrom, setDateFrom] = useState(defaultFrom);
  const [dateTo, setDateTo] = useState(addDays(defaultFrom, 27));
  const [days, setDays] = useState<number[]>([0, 1, 2, 3, 4]); // weekdays default
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function toggleDay(idx: number) {
    setDays((prev) => (prev.includes(idx) ? prev.filter((d) => d !== idx) : [...prev, idx].sort()));
  }

  async function onSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const result = await api<{ created: number; skipped_existing: number }>(
        "/api/v1/sectors/recurring",
        {
          method: "POST",
          body: JSON.stringify({
            flight_no: flightNo.trim(),
            origin: origin.trim(),
            destination: destination.trim(),
            std_time: stdTime,
            sta_time: staTime,
            aircraft_reg: reg.trim(),
            aircraft_type: type,
            date_from: dateFrom,
            date_to: dateTo,
            days_of_week: days,
          }),
        },
      );
      setFlightNo("");
      setOrigin("");
      setDestination("");
      setReg("");
      const skipped =
        result.skipped_existing > 0 ? ` (${result.skipped_existing} already existed)` : "";
      onAdded(`Created ${result.created} routing${result.created === 1 ? "" : "s"}${skipped}.`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to add recurring routings");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={onSubmit} className="space-y-3" data-testid="add-recurring-form">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>
          <Label htmlFor="r-flight">Flight no.</Label>
          <Input
            id="r-flight"
            value={flightNo}
            onChange={(e) => setFlightNo(e.target.value)}
            placeholder="KQ410"
            required
          />
        </div>
        <div>
          <Label htmlFor="r-origin">Origin</Label>
          <Input
            id="r-origin"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            placeholder="HKJK"
            required
          />
        </div>
        <div>
          <Label htmlFor="r-dest">Destination</Label>
          <Input
            id="r-dest"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            placeholder="HKMO"
            required
          />
        </div>
        <div>
          <Label htmlFor="r-type">Type</Label>
          <Select id="r-type" value={type} onChange={(e) => setType(e.target.value)} required>
            {aircraftTypes.map((t) => (
              <option key={t.icao} value={t.icao}>
                {t.icao}
              </option>
            ))}
          </Select>
        </div>
        <div>
          <Label htmlFor="r-std">Departure (UTC)</Label>
          <Input
            id="r-std"
            type="time"
            value={stdTime}
            onChange={(e) => setStdTime(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="r-sta">Arrival (UTC)</Label>
          <Input
            id="r-sta"
            type="time"
            value={staTime}
            onChange={(e) => setStaTime(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="r-reg">Aircraft reg.</Label>
          <Input
            id="r-reg"
            value={reg}
            onChange={(e) => setReg(e.target.value)}
            placeholder="5Y-ABC"
            required
          />
        </div>
        <div>
          <Label htmlFor="r-from">From</Label>
          <Input
            id="r-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            required
          />
        </div>
        <div>
          <Label htmlFor="r-to">To</Label>
          <Input
            id="r-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            required
          />
        </div>
      </div>
      <div>
        <Label>Operating days</Label>
        <div className="flex flex-wrap items-center gap-2 mt-1">
          {WEEKDAYS.map((d) => (
            <button
              key={d.idx}
              type="button"
              onClick={() => toggleDay(d.idx)}
              className={[
                "px-2 py-1 rounded text-xs border",
                days.includes(d.idx)
                  ? "bg-dn-steel-deep text-white border-dn-steel"
                  : "bg-white text-dn-steel-deep border-dn-steel-lt",
              ].join(" ")}
              data-testid={`weekday-${d.idx}`}
            >
              {d.label}
            </button>
          ))}
          <span className="mx-1 text-dn-steel-lt">|</span>
          <button
            type="button"
            onClick={() => setDays([0, 1, 2, 3, 4, 5, 6])}
            className="text-xs underline text-dn-steel-deep"
          >
            Daily
          </button>
          <button
            type="button"
            onClick={() => setDays([0, 1, 2, 3, 4])}
            className="text-xs underline text-dn-steel-deep"
          >
            Weekdays
          </button>
        </div>
      </div>
      {error && <ErrorAlert message={error} />}
      <div className="flex justify-end">
        <Button
          type="submit"
          disabled={busy || days.length === 0}
          data-testid="add-recurring-submit"
        >
          {busy ? "Creating…" : "Create recurring routings"}
        </Button>
      </div>
    </form>
  );
}

export function RoutingsPage() {
  const [from, setFrom] = useState(todayIso());
  const [to, setTo] = useState(addDays(todayIso(), 27));
  const [rows, setRows] = useState<Sector[]>([]);
  const [aircraftTypes, setAircraftTypes] = useState<AircraftType[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [mode, setMode] = useState<"single" | "recurring">("single");
  const [notice, setNotice] = useState<string | null>(null);

  // Delete confirmation state
  const [deleteModal, setDeleteModal] = useState<Sector | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const types = await api<AircraftType[]>("/api/v1/reference/aircraft-types");
        if (!cancelled) setAircraftTypes(types);
      } catch {
        if (!cancelled) setAircraftTypes([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        const list = await api<Sector[]>(`/api/v1/sectors?date_from=${from}&date_to=${to}`);
        if (!cancelled) setRows(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load routings");
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to, reloadKey]);

  async function confirmDelete() {
    if (!deleteModal) return;
    setDeleting(true);
    try {
      await api(`/api/v1/sectors/${deleteModal.id}`, { method: "DELETE" });
      setReloadKey((k) => k + 1);
      setDeleteModal(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to delete routing");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Add flight routing</CardTitle>
            <div className="inline-flex rounded-md border border-dn-steel-lt overflow-hidden text-sm">
              <button
                type="button"
                onClick={() => setMode("single")}
                className={
                  mode === "single"
                    ? "px-3 py-1 bg-dn-steel-deep text-white"
                    : "px-3 py-1 bg-white text-dn-steel-deep"
                }
                data-testid="mode-single"
              >
                Single
              </button>
              <button
                type="button"
                onClick={() => setMode("recurring")}
                className={
                  mode === "recurring"
                    ? "px-3 py-1 bg-dn-steel-deep text-white"
                    : "px-3 py-1 bg-white text-dn-steel-deep"
                }
                data-testid="mode-recurring"
              >
                Recurring
              </button>
            </div>
          </div>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-dn-muted mb-4">
            Build the flight schedule the auto-roster assigns crew to. Departure and arrival times
            are entered and stored in <strong>UTC</strong>.
            {mode === "recurring" &&
              " Recurring mode creates one routing per operating day across the date range."}
          </p>
          {notice && (
            <p className="mb-3 text-sm text-dn-steel-deep" data-testid="routing-notice">
              {notice}
            </p>
          )}
          {mode === "single" ? (
            <AddRoutingForm
              defaultDate={from}
              aircraftTypes={aircraftTypes}
              onAdded={() => {
                setNotice(null);
                setReloadKey((k) => k + 1);
              }}
            />
          ) : (
            <AddRecurringForm
              defaultFrom={from}
              aircraftTypes={aircraftTypes}
              onAdded={(msg) => {
                setNotice(msg);
                setReloadKey((k) => k + 1);
              }}
            />
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <CardTitle>Scheduled routings</CardTitle>
            <div className="flex items-center gap-2 text-sm text-dn-muted">
              <input
                type="date"
                aria-label="Schedule range from"
                value={from}
                onChange={(e) => setFrom(e.target.value)}
                className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
              />
              <span>→</span>
              <input
                type="date"
                aria-label="Schedule range to"
                value={to}
                onChange={(e) => setTo(e.target.value)}
                className="rounded-md border border-dn-steel-lt px-2 py-1 font-mono"
              />
            </div>
          </div>
        </CardHeader>
        <CardBody>
          {loading ? (
            <TableSkeleton rows={6} cols={9} />
          ) : error ? (
            <ErrorAlert message={error} />
          ) : rows.length === 0 ? (
            <p className="text-sm text-dn-muted" data-testid="routings-empty">
              No routings in this window. Add flights above, then go to Roster → Auto-generate.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="rtable min-w-full text-sm" data-testid="routings-table">
                <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Flight</th>
                    <th className="py-2 pr-4 font-medium">Date</th>
                    <th className="py-2 pr-4 font-medium">Route</th>
                    <th className="py-2 pr-4 font-medium">Dep (UTC)</th>
                    <th className="py-2 pr-4 font-medium">Arr (UTC)</th>
                    <th className="py-2 pr-4 font-medium">Block</th>
                    <th className="py-2 pr-4 font-medium">Aircraft</th>
                    <th className="py-2 pr-4 font-medium">Status</th>
                    <th className="py-2 pr-4 font-medium" />
                  </tr>
                </thead>
                <tbody className="divide-y divide-dn-steel-lt">
                  {rows.map((s) => (
                    <tr key={s.id} className="hover:bg-dn-fog">
                      <td data-label="Flight" className="py-2 pr-4 font-mono text-dn-steel-deep">
                        {s.flight_no}
                      </td>
                      <td data-label="Date" className="py-2 pr-4 font-mono">
                        {s.date}
                      </td>
                      <td data-label="Route" className="py-2 pr-4 font-mono">
                        {s.origin}→{s.destination}
                      </td>
                      <td data-label="Dep (UTC)" className="py-2 pr-4 font-mono">
                        {utcTime(s.std)}
                      </td>
                      <td data-label="Arr (UTC)" className="py-2 pr-4 font-mono">
                        {utcTime(s.sta)}
                      </td>
                      <td data-label="Block" className="py-2 pr-4 font-mono">
                        {s.block_hours.toFixed(1)}h
                      </td>
                      <td data-label="Aircraft" className="py-2 pr-4">
                        <span className="font-mono">{s.aircraft_reg}</span>{" "}
                        <Badge tone="steel">{s.aircraft_type}</Badge>
                      </td>
                      <td data-label="Status" className="py-2 pr-4">
                        <Badge tone={s.status === "PUBLISHED" ? "green" : "neutral"}>
                          {s.status}
                        </Badge>
                      </td>
                      <td data-label="" className="py-2 pr-4">
                        {s.status === "PLANNED" && (
                          <button
                            type="button"
                            onClick={() => setDeleteModal(s)}
                            className="text-dn-red underline text-xs"
                            data-testid={`delete-routing-${s.id}`}
                          >
                            delete
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {deleteModal && (
            <Modal
              title="Delete routing"
              onClose={() => setDeleteModal(null)}
              disableEscape={deleting}
            >
              <div className="space-y-4">
                <p className="text-sm text-dn-dark">
                  Delete {deleteModal.flight_no} on {deleteModal.date}? This action cannot be
                  undone.
                </p>
                <div className="flex justify-end gap-3">
                  <Button
                    variant="secondary"
                    onClick={() => setDeleteModal(null)}
                    disabled={deleting}
                  >
                    Cancel
                  </Button>
                  <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
                    {deleting ? "Deleting…" : "Delete"}
                  </Button>
                </div>
              </div>
            </Modal>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
