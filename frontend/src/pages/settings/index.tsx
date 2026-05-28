import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError } from "@/lib/api";

type Operator = {
  id: string;
  aoc_number: string;
  name: string;
  base: string;
  contact_email: string;
  tier: "ENTRY" | "STANDARD" | "PLUS";
};

export function SettingsPage() {
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
          contact_email: op.contact_email,
          tier: op.tier,
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

  if (!op) {
    return (
      <Card>
        <CardBody>
          {error ? (
            <p className="text-sm text-dn-red">{error}</p>
          ) : (
            <p className="text-sm text-dn-muted">Loading…</p>
          )}
        </CardBody>
      </Card>
    );
  }

  return (
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
            <Label htmlFor="contact">Contact email</Label>
            <Input
              id="contact"
              type="email"
              value={op.contact_email}
              onChange={(e) => setOp({ ...op, contact_email: e.target.value })}
            />
          </div>
          {error && <p className="text-sm text-dn-red">{error}</p>}
          {saved && <p className="text-sm text-dn-green">Saved.</p>}
          <Button type="submit" disabled={saving} data-testid="settings-save">
            {saving ? "Saving…" : "Save changes"}
          </Button>
        </form>
      </CardBody>
    </Card>
  );
}
