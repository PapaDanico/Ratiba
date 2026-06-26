import { useEffect, useState } from "react";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import { Select } from "@/components/ui/Select";
import { ErrorAlert } from "@/components/ui/ErrorAlert";
import { Modal } from "@/components/ui/Modal";
import { api, ApiError } from "@/lib/api";
import { useToast } from "@/lib/toast";

type Member = {
  id: string;
  email: string;
  full_name: string;
  role: "CREWING_OFFICER" | "CHIEF_PILOT" | "ADMIN";
  is_active: boolean;
};

const ROLE_OPTIONS: { value: Member["role"]; label: string }[] = [
  { value: "CREWING_OFFICER", label: "Crewing officer" },
  { value: "CHIEF_PILOT", label: "Chief pilot" },
  { value: "ADMIN", label: "Administrator" },
];

const ROLE_LABEL: Record<Member["role"], string> = {
  CREWING_OFFICER: "Crewing officer",
  CHIEF_PILOT: "Chief pilot",
  ADMIN: "Administrator",
};

export function TeamPanel({ currentUserId }: { currentUserId: string }) {
  const toast = useToast();
  const [members, setMembers] = useState<Member[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [confirmDeactivate, setConfirmDeactivate] = useState<Member | null>(null);

  // Invite form
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [role, setRole] = useState<Member["role"]>("CREWING_OFFICER");
  const [password, setPassword] = useState("");
  const [inviting, setInviting] = useState(false);
  const [inviteErr, setInviteErr] = useState<string | null>(null);
  const [inviteOk, setInviteOk] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setError(null);
    (async () => {
      try {
        const list = await api<Member[]>("/api/v1/users");
        if (!cancelled) setMembers(list);
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Failed to load team");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  async function invite(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setInviting(true);
    setInviteErr(null);
    setInviteOk(null);
    try {
      const created = await api<Member>("/api/v1/users", {
        method: "POST",
        body: JSON.stringify({ email, full_name: fullName, role, password }),
      });
      setInviteOk(`Added ${created.full_name}.`);
      toast.show(`Added ${created.full_name}`, "success");
      setEmail("");
      setFullName("");
      setRole("CREWING_OFFICER");
      setPassword("");
      setReloadKey((k) => k + 1);
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Could not add user";
      setInviteErr(msg);
      toast.show(msg, "error");
    } finally {
      setInviting(false);
    }
  }

  async function patch(id: string, body: Partial<Pick<Member, "role" | "is_active">>) {
    setError(null);
    try {
      await api<Member>(`/api/v1/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(body),
      });
      setReloadKey((k) => k + 1);
      const what =
        "role" in body
          ? "Role updated"
          : body.is_active
            ? "Member reactivated"
            : "Member deactivated";
      toast.show(what, "success");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : "Update failed";
      setError(msg);
      toast.show(msg, "error");
    }
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Team members</CardTitle>
        </CardHeader>
        <CardBody>
          <p className="text-sm text-dn-muted mb-4">
            Dashboard logins for your operator. Roles govern what each member can do; pilots use the
            separate crew app and are not listed here.
          </p>

          {error && <ErrorAlert message={error} className="mb-3" />}

          {members === null ? (
            <p className="text-sm text-dn-muted">Loading…</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm responsive-table">
                <thead className="text-left text-dn-muted border-b border-dn-steel-lt">
                  <tr>
                    <th className="py-3 pr-4 font-medium">Name</th>
                    <th className="py-3 pr-4 font-medium">Email</th>
                    <th className="py-3 pr-4 font-medium">Role</th>
                    <th className="py-3 pr-4 font-medium">Status</th>
                    <th className="py-3 pr-4 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-dn-steel-lt">
                  {members.map((m) => {
                    const isSelf = m.id === currentUserId;
                    return (
                      <tr key={m.id}>
                        <td data-label="Name" className="py-3 pr-4 text-dn-dark">
                          {m.full_name}
                          {isSelf && <span className="text-dn-muted text-xs"> (you)</span>}
                        </td>
                        <td data-label="Email" className="py-3 pr-4 font-mono text-xs">
                          {m.email}
                        </td>
                        <td data-label="Role" className="py-3 pr-4">
                          {isSelf ? (
                            <Badge tone="steel">{ROLE_LABEL[m.role]}</Badge>
                          ) : (
                            <Select
                              value={m.role}
                              onChange={(e) =>
                                patch(m.id, { role: e.target.value as Member["role"] })
                              }
                              className="text-xs"
                              data-testid={`role-${m.email}`}
                            >
                              {ROLE_OPTIONS.map((r) => (
                                <option key={r.value} value={r.value}>
                                  {r.label}
                                </option>
                              ))}
                            </Select>
                          )}
                        </td>
                        <td data-label="Status" className="py-3 pr-4">
                          <Badge tone={m.is_active ? "green" : "red"}>
                            {m.is_active ? "Active" : "Inactive"}
                          </Badge>
                        </td>
                        <td data-label="Actions" className="py-3 pr-4">
                          {isSelf ? (
                            <span className="text-dn-muted text-xs">—</span>
                          ) : (
                            <div className="row-actions flex justify-end">
                              <button
                                type="button"
                                onClick={() =>
                                  m.is_active
                                    ? setConfirmDeactivate(m)
                                    : patch(m.id, { is_active: true })
                                }
                                className="text-dn-steel underline text-xs hover:text-dn-dark"
                                data-testid={`toggle-${m.email}`}
                              >
                                {m.is_active ? "Deactivate" : "Reactivate"}
                              </button>
                            </div>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Add a team member</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={invite} className="space-y-4 max-w-xl">
            <div>
              <Label htmlFor="member-name">Full name</Label>
              <Input
                id="member-name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                required
                data-testid="member-name"
              />
            </div>
            <div>
              <Label htmlFor="member-email">Email</Label>
              <Input
                id="member-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                data-testid="member-email"
              />
            </div>
            <div>
              <Label htmlFor="member-role">Role</Label>
              <Select
                id="member-role"
                value={role}
                onChange={(e) => setRole(e.target.value as Member["role"])}
                data-testid="member-role"
              >
                {ROLE_OPTIONS.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </Select>
            </div>
            <div>
              <Label htmlFor="member-password">Temporary password</Label>
              <Input
                id="member-password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={8}
                data-testid="member-password"
              />
              <p className="mt-1 text-xs text-dn-muted">
                At least 8 characters. Share it with the member; they sign in with it.
              </p>
            </div>
            {inviteErr && <ErrorAlert message={inviteErr} />}
            {inviteOk && (
              <div className="rounded border border-dn-green/30 bg-dn-green/5 px-3 py-2 text-sm text-dn-green">
                {inviteOk}
              </div>
            )}
            <Button type="submit" disabled={inviting} data-testid="member-submit">
              {inviting ? "Adding…" : "Add member"}
            </Button>
          </form>
        </CardBody>
      </Card>

      {confirmDeactivate && (
        <Modal
          title="Deactivate member?"
          onClose={() => setConfirmDeactivate(null)}
          testId="confirm-deactivate"
        >
          <p className="text-sm text-dn-dark">
            {confirmDeactivate.full_name} ({confirmDeactivate.email}) will no longer be able to sign
            in. You can reactivate them later.
          </p>
          <div className="mt-4 flex justify-end gap-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setConfirmDeactivate(null)}
            >
              Cancel
            </Button>
            <Button
              type="button"
              size="sm"
              data-testid="confirm-deactivate-submit"
              onClick={() => {
                patch(confirmDeactivate.id, { is_active: false });
                setConfirmDeactivate(null);
              }}
            >
              Deactivate
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
