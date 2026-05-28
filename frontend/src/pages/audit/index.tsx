import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { api, ApiError, tokenStore } from "@/lib/api";

type AuditPack = {
  id: string;
  period_from: string;
  period_to: string;
  sha256_hex: string;
  byte_size: number;
  generator_version: string;
  crew_count: number;
  fdp_count: number;
  anomaly_count: number;
  created_at: string;
};

function defaultPeriod(): { from: string; to: string } {
  const today = new Date();
  const ninety = new Date(today.getTime() - 89 * 24 * 60 * 60 * 1000);
  return {
    from: ninety.toISOString().slice(0, 10),
    to: today.toISOString().slice(0, 10),
  };
}

export function AuditPage() {
  const [rows, setRows] = useState<AuditPack[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState(false);
  const { from, to } = defaultPeriod();
  const [periodFrom, setPeriodFrom] = useState(from);
  const [periodTo, setPeriodTo] = useState(to);

  async function reload() {
    setLoading(true);
    try {
      const list = await api<AuditPack[]>("/api/v1/audit/packs");
      setRows(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load audit packs");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function generate() {
    setGenerating(true);
    setError(null);
    try {
      await api("/api/v1/audit/generate", {
        method: "POST",
        body: JSON.stringify({ period_from: periodFrom, period_to: periodTo }),
      });
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function verify(id: string) {
    try {
      const body = await api<{
        verified: boolean;
        expected_sha256: string;
        actual_sha256?: string;
      }>(`/api/v1/audit/packs/${id}/verify`);
      alert(
        body.verified
          ? `✅ Verified.\nSHA-256: ${body.expected_sha256}`
          : `⚠️ Hash mismatch.\nExpected: ${body.expected_sha256}\nActual:   ${body.actual_sha256 ?? "—"}`,
      );
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Verify failed");
    }
  }

  async function startDownload(id: string) {
    try {
      const resp = await fetch(`/api/v1/audit/packs/${id}/download`, {
        headers: { Authorization: `Bearer ${tokenStore.getAccess() ?? ""}` },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const cd = resp.headers.get("Content-Disposition") || "";
      const m = cd.match(/filename="([^"]+)"/);
      a.download = (m && m[1]) || `audit-pack-${id}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Download failed");
    }
  }

  async function downloadPayroll() {
    try {
      const url = `/api/v1/reports/payroll.csv?date_from=${periodFrom}&date_to=${periodTo}`;
      const resp = await fetch(url, {
        headers: { Authorization: `Bearer ${tokenStore.getAccess() ?? ""}` },
      });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const blob = await resp.blob();
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = `payroll_${periodFrom}_${periodTo}.csv`;
      a.click();
      URL.revokeObjectURL(objectUrl);
    } catch (err) {
      alert(err instanceof Error ? err.message : "Payroll export failed");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Payroll / duty-hours export</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="mb-4 text-sm text-dn-muted">
            Export per-crew duty hours, block hours, standby, and leave/sick days for the selected
            period as a CSV — ready to drop into your payroll system. Uses the period dates below.
          </p>
          <Button variant="secondary" onClick={downloadPayroll} data-testid="payroll-export">
            Download payroll CSV
          </Button>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Generate KCAA audit pack</CardTitle>
        </CardHeader>
        <CardBody>
          <div className="grid gap-3 md:grid-cols-3 max-w-2xl">
            <div>
              <Label htmlFor="from">Period from</Label>
              <Input
                id="from"
                type="date"
                value={periodFrom}
                onChange={(e) => setPeriodFrom(e.target.value)}
                data-testid="audit-period-from"
              />
            </div>
            <div>
              <Label htmlFor="to">Period to</Label>
              <Input
                id="to"
                type="date"
                value={periodTo}
                onChange={(e) => setPeriodTo(e.target.value)}
                data-testid="audit-period-to"
              />
            </div>
            <div className="flex items-end">
              <Button onClick={generate} disabled={generating} data-testid="audit-generate">
                {generating ? "Generating…" : "Generate pack"}
              </Button>
            </div>
          </div>
          {error && <p className="mt-3 text-sm text-dn-red">{error}</p>}
          <p className="mt-3 text-sm text-dn-muted">
            Each pack is a DN-branded PDF carrying the cover, executive summary, per-crew FTL
            summary, anomaly log, currency snapshot, audit-trail extract, and the methodology +
            KCARs cross-reference. A SHA-256 hash is stored per pack so any byte-level edit is
            detectable via the verify endpoint.
          </p>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Recent audit packs</CardTitle>
        </CardHeader>
        <CardBody>
          {loading ? (
            <p className="text-sm text-dn-muted">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-dn-muted" data-testid="no-audit-packs">
              No packs generated yet. Use the form above.
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm" data-testid="audit-packs-table">
                <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                  <tr>
                    <th className="py-2 pr-4 font-medium">Period</th>
                    <th className="py-2 pr-4 font-medium">FDPs</th>
                    <th className="py-2 pr-4 font-medium">Anomalies</th>
                    <th className="py-2 pr-4 font-medium">Size</th>
                    <th className="py-2 pr-4 font-medium">SHA-256</th>
                    <th className="py-2 pr-4 font-medium">Generated</th>
                    <th className="py-2 pr-4 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dn-steel-lt">
                  {rows.map((r) => (
                    <tr key={r.id} className="hover:bg-dn-fog">
                      <td className="py-2 pr-4 font-mono">
                        {r.period_from} → {r.period_to}
                      </td>
                      <td className="py-2 pr-4 font-mono">{r.fdp_count}</td>
                      <td className="py-2 pr-4">
                        {r.anomaly_count === 0 ? (
                          <Badge tone="green">0</Badge>
                        ) : (
                          <Badge tone="amber">{r.anomaly_count}</Badge>
                        )}
                      </td>
                      <td className="py-2 pr-4 font-mono">{(r.byte_size / 1024).toFixed(1)} kB</td>
                      <td className="py-2 pr-4 font-mono truncate max-w-[140px]">
                        {r.sha256_hex.slice(0, 12)}…
                      </td>
                      <td className="py-2 pr-4 font-mono">
                        {r.created_at.slice(0, 16).replace("T", " ")}
                      </td>
                      <td className="py-2 pr-4 flex gap-2">
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => verify(r.id)}
                          data-testid={`verify-${r.id}`}
                        >
                          Verify
                        </Button>
                        <Button
                          size="sm"
                          onClick={() => startDownload(r.id)}
                          data-testid={`download-${r.id}`}
                        >
                          Download
                        </Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
