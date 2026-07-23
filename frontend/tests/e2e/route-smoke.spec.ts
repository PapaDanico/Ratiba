import { expect, test } from "@playwright/test";

/**
 * Cross-route smoke test: log in, visit every authenticated route, and assert
 * each renders without a page error, console error, or failing API call.
 *
 * Gated on E2E_LIVE (needs a live backend + frontend + seeded demo), matching
 * login-publish-flow.spec.ts. Run with:
 *   E2E_LIVE=1 PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run e2e
 *
 * Env (override in CI / against staging):
 *   E2E_ADMIN_EMAIL / E2E_ADMIN_PASSWORD — a seeded login (default Acacia officer)
 */

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "officer@demo-aoc-ac.example.aero";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "hunter2pass";

const ROUTES = [
  "/",
  "/app",
  "/routings",
  "/roster",
  "/crew",
  "/postings",
  "/import",
  "/fleet",
  "/training",
  "/documents",
  "/currency",
  "/leave",
  "/swaps",
  "/notices",
  "/constraints",
  "/fatigue",
  "/irop",
  "/audit",
  "/settings",
];

test("every authenticated route renders without errors", async ({ page }) => {
  test.skip(
    !process.env.E2E_LIVE,
    "Set E2E_LIVE=1 with a live backend + frontend stack to run this test.",
  );

  const pageErrors: string[] = [];
  const consoleErrors: string[] = [];
  const badResponses: string[] = [];
  let current = "(login)";

  page.on("pageerror", (e) => pageErrors.push(`${current}: ${e.message}`));
  page.on("console", (m) => {
    // Blocked external assets (fonts/analytics) under a restrictive network
    // policy surface as cert errors — not an app fault.
    if (m.type() === "error" && !m.text().includes("ERR_CERT_AUTHORITY_INVALID")) {
      consoleErrors.push(`${current}: ${m.text().slice(0, 160)}`);
    }
  });
  page.on("response", (r) => {
    if (r.url().includes("/api/v1/") && r.status() >= 400) {
      badResponses.push(`${current}: ${r.status()} ${new URL(r.url()).pathname}`);
    }
  });

  await page.goto("/login");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL((u) => !u.pathname.startsWith("/login")),
    page.getByTestId("login-submit").click(),
  ]);

  for (const route of ROUTES) {
    current = route;
    await page.goto(route, { waitUntil: "networkidle" });
    // Did not silently bounce back to the login screen.
    expect(page.url(), `route ${route} redirected to login`).not.toContain("/login");
    // Rendered some content (a heading or any test-id'd element). :visible
    // filters out things like the mobile nav toggle, which is display:none on
    // desktop viewports but sits first in DOM order.
    await expect(
      page.locator("h1:visible, h2:visible, [data-testid]:visible").first(),
    ).toBeVisible();
  }

  expect(pageErrors, "page errors").toEqual([]);
  expect(consoleErrors, "console errors").toEqual([]);
  expect(badResponses, "API responses >= 400").toEqual([]);
});
