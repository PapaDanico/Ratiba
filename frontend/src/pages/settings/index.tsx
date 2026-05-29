import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { TeamPanel } from "./TeamPanel";

type Operator = {
  id: string;
  aoc_number: string;
  name: string;
  base: string;
  timezone: string;
  contact_email: string;
  tier: "ENTRY" | "STANDARD" | "PLUS";
  default_soft_weights: Record<string, number>;
};

const TIMEZONE_OPTIONS = [
  { value: "Africa/Nairobi", label: "Africa/Nairobi — Kenya (EAT)" },
  { value: "Africa/Kampala", label: "Africa/Kampala — Uganda (EAT)" },
  { value: "Africa/Dar_es_Salaam", label: "Africa/Dar_es_Salaam — Tanzania (EAT)" },
  { value: "Africa/Addis_Ababa", label: "Africa/Addis_Ababa — Ethiopia (EAT)" },
  { value: "Africa/Mogadishu", label: "Africa/Mogadishu — Somalia (EAT)" },
  { value: "Africa/Juba", label: "Africa/Juba — South Sudan (CAT)" },
];

const WEIGHT_FIELDS: { key: string; label: string; help: string }[] = [
  {
    key: "balance_block_hours",
    label: "Balance block hours",
    help: "Penalty multiplier for spread between most- and least-utilised crew.",
  },
  {
    key: "faith_violation",
    label: "Faith observance",
    help: "Penalty when a faith-protected crew member is assigned on a protected day.",
  },
  {
    key: "leave_violation",
    label: "Honour pending leave",
    help: "Penalty when an assignment overlaps a pending (not-yet-approved) leave request.",
  },
  {
    key: "positioning_minimisation",
    label: "Minimise positioning",
    help: "Penalty for deadhead / positioning sectors. Phase 6 only.",
  },
];

type Tab = "operator" | "team";

export function SettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "ADMIN";
  const [tab, setTab] = useState<Tab>("operator");
  const [op, setOp] = useState<Operator | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await api<Operator>("/api/v1/settings/operator");
        if (!cancelled) setOp(data);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load settings");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  async function save(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (!op) return;
    setSaving(true);
    setSaved(false);
    try {
      const updated = await api<Operator>("/api/v1/settings/operator", {
        method: "PATCH",
        body: JSON.stringify({
          name: op.name,
          base: op.base,
          timezone: op.timezone,
          contact_email: op.contact_email,
          tier: op.tier,
          default_soft_weights: op.default_soft_weights,
        }),
      });
      setOp(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function setWeight(key: string, value: string) {
    if (!op) return;
    const num = value === "" ? 0 : Number(value);
    if (Number.isNaN(num)) return;
    setOp({ ...op, default_soft_weights: { ...op.default_soft_weights, [key]: num } });
  }

  const tabBar = isAdmin ? (
    <div className="flex gap-1 border-b border-dn-steel-lt" data-testid="settings-tabs">
      <button
        type="button"
        onClick={() => setTab("operator")}
        className={
          tab === "operator"
            ? "px-4 py-2 text-sm border-b-2 border-dn-steel text-dn-dark"
            : "px-4 py-2 text-sm text-dn-muted hover:text-dn-dark"
        }
        data-testid="tab-operator"
      >
        Operator
      </button>
      <button
        type="button"
        onClick={() => setTab("team")}
        className={
          tab === "team"
            ? "px-4 py-2 text-sm border-b-2 border-dn-steel text-dn-dark"
            : "px-4 py-2 text-sm text-dn-muted hover:text-dn-dark"
        }
        data-testid="tab-team"
      >
        Team
      </button>
    </div>
  ) : null;

  if (tab === "team" && isAdmin && user) {
    return (
      <div className="space-y-6">
        {tabBar}
        <TeamPanel currentUserId={user.id} />
      </div>
    );
  }

  if (!op) {
    return (
      <div className="space-y-6">
        {tabBar}
        <Card>
          <CardBody>
            {error ? (
              <p className="text-sm text-dn-red">{error}</p>
            ) : (
              <p className="text-sm text-dn-muted">Loading…</p>
            )}
          </CardBody>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {tabBar}
      <Card>
        <CardHeader>
          <CardTitle>Operator settings</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={save} className="space-y-4 max-w-xl">
            <div>
              <Label>AOC number</Label>
              <Input value={op.aoc_number} disabled />
            </div>
            <div>
              <Label htmlFor="name">Name</Label>
              <Input
                id="name"
                value={op.name}
                onChange={(e) => setOp({ ...op, name: e.target.value })}
              />
            </div>
            <div>
              <Label htmlFor="base">Base ICAO</Label>
              <Input
                id="base"
                value={op.base}
                onChange={(e) => setOp({ ...op, base: e.target.value.toUpperCase() })}
                maxLength={4}
              />
            </div>
            <div>
              <Label htmlFor="timezone">Home timezone</Label>
              <select
                id="timezone"
                value={op.timezone}
                onChange={(e) => setOp({ ...op, timezone: e.target.value })}
                className="w-full rounded-md border border-dn-steel-lt px-3 py-2 text-sm"
                data-testid="operator-timezone-select"
              >
                {!TIMEZONE_OPTIONS.some((t) => t.value === op.timezone) && (
                  <option value={op.timezone}>{op.timezone}</option>
                )}
                {TIMEZONE_OPTIONS.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
              <p className="mt-1 text-xs text-dn-muted">
                Anchors circadian (window-of-circadian-low) fatigue scoring to the operator&apos;s
                home base.
              </p>
            </div>
            <div>
              <Label htmlFor="contact">Contact email</Label>
              <Input
                id="contact"
                type="email"
                value={op.contact_email}
                onChange={(e) => setOp({ ...op, contact_email: e.target.value })}
              />
            </div>

            <fieldset className="border-t border-dn-steel-lt pt-4 space-y-3">
              <legend className="font-display text-lg text-dn-dark">Optimiser soft weights</legend>
              <p className="text-sm text-dn-muted">
                Persisted defaults the optimiser uses unless a request overrides them. Higher =
                stronger preference.{" "}
                <em>Edit with care — changes affect every roster generated thereafter.</em>
              </p>
              {WEIGHT_FIELDS.map((field) => (
                <div key={field.key}>
                  <Label htmlFor={`w-${field.key}`}>{field.label}</Label>
                  <Input
                    id={`w-${field.key}`}
                    type="number"
                    step="0.5"
                    min={0}
                    value={op.default_soft_weights[field.key] ?? 0}
                    onChange={(e) => setWeight(field.key, e.target.value)}
                    data-testid={`weight-${field.key}`}
                  />
                  <p className="mt-1 text-xs text-dn-muted">{field.help}</p>
                </div>
              ))}
            </fieldset>

            {error && <p className="text-sm text-dn-red">{error}</p>}
            {saved && <p className="text-sm text-dn-green">Saved.</p>}
            <Button type="submit" disabled={saving} data-testid="settings-save">
              {saving ? "Saving…" : "Save changes"}
            </Button>
          </form>
        </CardBody>
      </Card>
    </div>
  );
}
