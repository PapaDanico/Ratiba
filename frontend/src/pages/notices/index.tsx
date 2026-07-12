import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { api, ApiError } from "@/lib/api";

type Category = "OPERATIONAL" | "FLEET" | "SAFETY" | "SOCIAL";
type Severity = "INFO" | "IMPORTANT" | "CRITICAL";

type Notice = {
  id: string;
  category: Category;
  severity: Severity;
  title: string;
  body: string;
  image_url: string | null;
  requires_ack: boolean;
  published: boolean;
  pinned: boolean;
  created_at: string;
  ack_count: number;
  crew_total: number;
};

const CATEGORIES: { value: Category; label: string }[] = [
  { value: "OPERATIONAL", label: "Operational comms" },
  { value: "FLEET", label: "Fleet notice" },
  { value: "SAFETY", label: "Safety" },
  { value: "SOCIAL", label: "Crew room (social / morale)" },
];

const SEVERITIES: Severity[] = ["INFO", "IMPORTANT", "CRITICAL"];

function severityTone(s: Severity): "steel" | "amber" | "red" {
  return s === "INFO" ? "steel" : s === "IMPORTANT" ? "amber" : "red";
}

export function NoticesPage() {
  const [rows, setRows] = useState<Notice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [category, setCategory] = useState<Category>("OPERATIONAL");
  const [severity, setSeverity] = useState<Severity>("INFO");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [imageUrl, setImageUrl] = useState("");
  const [requiresAck, setRequiresAck] = useState(false);
  const [pinned, setPinned] = useState(false);
  const [posting, setPosting] = useState(false);

  async function reload() {
    setLoading(true);
    try {
      const list = await api<Notice[]>("/api/v1/notices");
      setRows(list);
      setError(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Failed to load notices");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void reload();
  }, []);

  async function post(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPosting(true);
    setError(null);
    try {
      await api("/api/v1/notices", {
        method: "POST",
        body: JSON.stringify({
          category,
          severity,
          title: title.trim(),
          body: body.trim(),
          image_url: imageUrl.trim() || null,
          requires_ack: requiresAck,
          pinned,
          published: true,
        }),
      });
      setTitle("");
      setBody("");
      setImageUrl("");
      setRequiresAck(false);
      setPinned(false);
      await reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Post failed");
    } finally {
      setPosting(false);
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Post a notice</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={post} className="space-y-4 max-w-2xl">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <Label htmlFor="cat">Category</Label>
                <Select
                  id="cat"
                  value={category}
                  onChange={(e) => setCategory(e.target.value as Category)}
                  data-testid="notice-category"
                >
                  {CATEGORIES.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </Select>
              </div>
              <div>
                <Label htmlFor="sev">Severity</Label>
                <Select
                  id="sev"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as Severity)}
                  data-testid="notice-severity"
                >
                  {SEVERITIES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </Select>
              </div>
            </div>
            <div>
              <Label htmlFor="title">Title</Label>
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                required
                data-testid="notice-title"
              />
            </div>
            <div>
              <Label htmlFor="body">Message</Label>
              <textarea
                id="body"
                value={body}
                onChange={(e) => setBody(e.target.value)}
                required
                rows={4}
                className="block w-full rounded-md border border-dn-steel-lt bg-white px-3 py-2 text-sm"
                data-testid="notice-body"
              />
            </div>
            <div>
              <Label htmlFor="img">
                Image URL (optional — for fleet photos or crew-room posts)
              </Label>
              <Input
                id="img"
                value={imageUrl}
                onChange={(e) => setImageUrl(e.target.value)}
                placeholder="https://…"
                data-testid="notice-image"
              />
            </div>
            <div className="flex gap-6 text-sm">
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={requiresAck}
                  onChange={(e) => setRequiresAck(e.target.checked)}
                  data-testid="notice-requires-ack"
                />
                Require acknowledgement
              </label>
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={pinned}
                  onChange={(e) => setPinned(e.target.checked)}
                  data-testid="notice-pinned"
                />
                Pin to top
              </label>
            </div>
            {error && <ErrorAlert message={error} />}
            <Button type="submit" disabled={posting} data-testid="notice-post">
              {posting ? "Posting…" : "Post + push to crew"}
            </Button>
            <p className="text-xs text-dn-muted">
              Published notices appear in every paired pilot&apos;s bot + crew web view, and (if a
              Telegram bot token is configured) are pushed to their chat.
            </p>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Posted notices</CardTitle>
        </CardHeader>
        <CardBody>
          {loading ? (
            <p className="text-sm text-dn-muted">Loading…</p>
          ) : rows.length === 0 ? (
            <p className="text-sm text-dn-muted" data-testid="no-notices">
              No notices yet.
            </p>
          ) : (
            <ul className="divide-y divide-dn-steel-lt" data-testid="notices-list">
              {rows.map((n) => (
                <li key={n.id} className="py-3">
                  <div className="flex items-center gap-2 flex-wrap">
                    {n.pinned && <Badge tone="gold">📌 pinned</Badge>}
                    <Badge tone="steel">{n.category}</Badge>
                    <Badge tone={severityTone(n.severity)}>{n.severity}</Badge>
                    <span className="font-medium text-dn-dark">{n.title}</span>
                  </div>
                  <p className="mt-1 text-sm text-dn-muted whitespace-pre-line">{n.body}</p>
                  {n.requires_ack && (
                    <p className="mt-1 text-xs text-dn-steel-deep">
                      Acknowledged by {n.ack_count} / {n.crew_total} crew
                    </p>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
