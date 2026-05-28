import { expect, test } from "@playwright/test";

/**
 * End-to-end coverage of the Plan §5 Phase 3 critical path:
 *
 *   login → generate roster (via backend API) → publish → roster appears in dashboard
 *
 * The test seeds its own operator, user, crew, and sectors via the API so it
 * can run against any backend that has the migration applied and Redis up.
 *
 * Seed env vars (override in CI):
 *   E2E_API_BASE        — base URL for the backend (default http://localhost:8000)
 *   E2E_ADMIN_EMAIL     — pre-seeded crewing-officer email
 *   E2E_ADMIN_PASSWORD  — pre-seeded password
 */

const API_BASE = process.env.E2E_API_BASE ?? "http://localhost:8000";
const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "officer@example.aero";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "hunter2pass";

async function obtainToken(): Promise<string> {
  const resp = await (
    await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: ADMIN_EMAIL, password: ADMIN_PASSWORD }),
    })
  ).json();
  return resp.access_token;
}

test("login → publish a one-day roster → see it on the calendar", async ({ page }) => {
  test.skip(
    !process.env.E2E_LIVE,
    "Set E2E_LIVE=1 with a live backend + frontend stack to run this test.",
  );

  // --- seed via API ---------------------------------------------------------
  const token = await obtainToken();
  const auth = { Authorization: `Bearer ${token}`, "Content-Type": "application/json" };

  const cap = await (
    await fetch(`${API_BASE}/api/v1/crew`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({
        employee_no: `E2E-CAP-${Date.now()}`,
        first_name: "E2E",
        last_name: "Captain",
        role: "CAPT",
        date_of_hire: "2020-01-01",
        date_of_birth: "1985-01-01",
        base_station: "HKJK",
        contract_type: "FULL_TIME",
      }),
    })
  ).json();
  const fo = await (
    await fetch(`${API_BASE}/api/v1/crew`, {
      method: "POST",
      headers: auth,
      body: JSON.stringify({
        employee_no: `E2E-FO-${Date.now()}`,
        first_name: "E2E",
        last_name: "FirstOfficer",
        role: "FO",
        date_of_hire: "2022-01-01",
        date_of_birth: "1993-01-01",
        base_station: "HKJK",
        contract_type: "FULL_TIME",
      }),
    })
  ).json();

  const day = new Date(Date.now() + 7 * 86_400_000).toISOString().slice(0, 10);
  const std = `${day}T06:00:00+00:00`;
  const sta = `${day}T09:00:00+00:00`;
  await fetch(`${API_BASE}/api/v1/roster/publish`, {
    method: "POST",
    headers: auth,
    body: JSON.stringify({
      horizon_from: day,
      horizon_to: day,
      sectors: [
        {
          sector_id: `E2E-${day}`,
          date_local: day,
          std,
          sta,
          aircraft_reg: "5Y-E2E",
          aircraft_type: "DH8D",
          block_hours: "3.0",
        },
      ],
      assignments: [
        {
          duty_day_key: `5Y-E2E|${day}`,
          date_local: day,
          aircraft_reg: "5Y-E2E",
          aircraft_type: "DH8D",
          sector_ids: [`E2E-${day}`],
          captain_id: cap.employee_no,
          fo_id: fo.employee_no,
        },
      ],
    }),
  });

  // --- login through the UI -------------------------------------------------
  await page.goto("/login");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await page.getByTestId("login-submit").click();

  // --- overview loads and shows the welcome heading -------------------------
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByText("Welcome back,")).toBeVisible();

  // --- navigate to roster and verify the published day is rendered ----------
  await page.getByRole("link", { name: "Roster" }).click();
  await page.getByTestId("roster-date-from").fill(day);
  await page.getByTestId("roster-date-to").fill(day);

  const calendar = page.getByTestId("roster-calendar");
  await expect(calendar.getByText("5Y-E2E")).toBeVisible();
});
