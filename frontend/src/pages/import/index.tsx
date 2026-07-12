import { useRef, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { authFetch } from "@/lib/api";

type ImportKind = {
  key: string;
  label: string;
  path: string;
  required: string[];
  optional: string[];
  sample: string;
  note?: string;
};

const KINDS: ImportKind[] = [
  {
    key: "crew",
    label: "Crew",
    path: "/api/v1/onboarding/crew",
    required: [
      "employee_no",
      "first_name",
      "last_name",
      "role",
      "date_of_hire",
      "date_of_birth",
      "base_station",
      "contract_type",
    ],
    optional: ["languages", "faith_observance_flags", "email", "phone_number"],
    sample:
      "EMP001,Amani,Mwangi,CAPT,2020-01-15,1985-06-01,HKJK,FULL_TIME,en;sw,,amani@example.aero,+254700000000",
    note: "role = CAPT | FO | SO | PURSER | CABIN_CREW | ENGINEER · contract_type = FULL_TIME | CONTRACT | FREELANCE · languages ;-separated.",
  },
  {
    key: "type-ratings",
    label: "Type ratings",
    path: "/api/v1/onboarding/type-ratings",
    required: ["employee_no", "aircraft_type", "valid_from", "valid_until"],
    optional: ["evidence_ref"],
    sample: "EMP001,C208,2024-01-01,2026-01-01,TR-123",
  },
  {
    key: "currencies",
    label: "Currencies",
    path: "/api/v1/onboarding/currencies",
    required: ["employee_no", "currency_type", "last_completed_date", "expires_date"],
    optional: ["evidence_ref"],
    sample: "EMP001,OPC,2025-01-15,2025-07-15,OPC-2025",
    note: "currency_type = OPC | LPC | LANDINGS_90D | LINE_CHECK | … (see Training).",
  },
  {
    key: "historical-fdps",
    label: "Historical duties (90-day context)",
    path: "/api/v1/onboarding/historical-fdps",
    required: [
      "employee_no",
      "date",
      "report_time",
      "off_duty_time",
      "sectors_count",
      "flight_hours",
      "duty_hours",
    ],
    optional: [],
    sample: "EMP001,2025-05-01,2025-05-01T06:00:00+03:00,2025-05-01T14:00:00+03:00,2,5.5,8.0",
    note: "report_time / off_duty_time must be ISO 8601 with a timezone. Loads prior FDPs so cumulative FTL windows are populated on day one.",
  },
];

type ImportResult = {
  inserted: number;
  updated: number;
  skipped: number;
  errors: { row: number; message: string }[];
  commit: boolean;
  detail?: string;
};

export function ImportPage() {
  const [kindKey, setKindKey] = useState(KINDS[0]!.key);
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const kind = KINDS.find((k) => k.key === kindKey) ?? KINDS[0]!;
  const columns = [...kind.required, ...kind.optional];

  function downloadTemplate() {
    const csv = `${columns.join(",")}\n${kind.sample}\n`;
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ratiba_${kind.key}_template.csv`;
    a.click();
    URL.revokeObjectURL(a.href);
  }

  async function upload(commit: boolean) {
    if (!file) {
      setError("Choose a CSV file first.");
      return;
    }
    setBusy(true);
    setError(null);
    if (!commit) setResult(null);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const res = await authFetch(`${kind.path}?commit=${commit}`, {
        method: "POST",
        body: fd,
      });
      const body = (await res.json()) as ImportResult;
      if (!res.ok) {
        setError(body.detail ?? `Upload failed (HTTP ${res.status})`);
        return;
      }
      setResult(body);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setBusy(false);
    }
  }

  const hasErrors = (result?.errors.length ?? 0) > 0;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Bulk import (CSV)</CardTitle>
        </CardHeader>
        <CardBody className="space-y-4">
          <p className="text-sm text-dn-muted">
            Onboard data from a spreadsheet. Pick what you&apos;re importing, download the template,
            then <strong>validate</strong> (a dry run that changes nothing) before you{" "}
            <strong>import</strong>.
          </p>

          <div className="flex flex-wrap gap-2">
            {KINDS.map((k) => (
              <button
                key={k.key}
                type="button"
                onClick={() => {
                  setKindKey(k.key);
                  setResult(null);
                  setError(null);
                }}
                className={[
                  "px-3 py-1.5 rounded-md text-sm border",
                  k.key === kindKey
                    ? "bg-dn-steel-deep text-white border-dn-steel"
                    : "bg-white text-dn-steel-deep border-dn-steel-lt",
                ].join(" ")}
                data-testid={`import-kind-${k.key}`}
              >
                {k.label}
              </button>
            ))}
          </div>

          <div className="rounded-md border border-dn-steel-lt bg-dn-fog p-3 text-xs">
            <p className="mb-1">
              <span className="font-semibold text-dn-dark">Required columns:</span>{" "}
              <span className="font-mono">{kind.required.join(", ")}</span>
            </p>
            {kind.optional.length > 0 && (
              <p className="mb-1">
                <span className="font-semibold text-dn-dark">Optional:</span>{" "}
                <span className="font-mono">{kind.optional.join(", ")}</span>
              </p>
            )}
            {kind.note && <p className="text-dn-muted">{kind.note}</p>}
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <Button variant="secondary" size="sm" onClick={downloadTemplate}>
              Download template
            </Button>
            <input
              ref={fileRef}
              type="file"
              aria-label="CSV file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
                setError(null);
              }}
              className="text-sm"
              data-testid="import-file"
            />
          </div>

          <div className="flex gap-2">
            <Button
              variant="secondary"
              onClick={() => upload(false)}
              disabled={busy || !file}
              data-testid="import-validate"
            >
              {busy ? "Working…" : "Validate (dry run)"}
            </Button>
            <Button
              onClick={() => upload(true)}
              disabled={busy || !file}
              data-testid="import-commit"
            >
              {busy ? "Working…" : "Import"}
            </Button>
          </div>

          {error && <p className="text-sm text-dn-red">{error}</p>}

          {result && (
            <div
              className={[
                "rounded-md border p-3 text-sm",
                hasErrors ? "border-dn-red/40 bg-dn-red/5" : "border-dn-gold/40 bg-dn-gold/5",
              ].join(" ")}
              data-testid="import-result"
            >
              <p className="font-medium text-dn-dark">
                {result.commit ? "Import complete" : "Dry run — nothing was saved"}
                {hasErrors && " (fix errors below, then re-run)"}
              </p>
              <p className="mt-1 text-dn-muted">
                Inserted {result.inserted} · Updated {result.updated} · Skipped {result.skipped} ·
                Errors {result.errors.length}
              </p>
              {hasErrors && (
                <ul className="mt-2 space-y-1 text-xs text-dn-red max-h-48 overflow-y-auto">
                  {result.errors.map((e, i) => (
                    <li key={i}>
                      Row {e.row}: {e.message}
                    </li>
                  ))}
                </ul>
              )}
              {!result.commit && !hasErrors && (
                <p className="mt-2 text-xs text-dn-muted">
                  Looks good — click <strong>Import</strong> to save.
                </p>
              )}
            </div>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
