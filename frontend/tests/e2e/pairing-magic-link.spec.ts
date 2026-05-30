import { expect, test } from "@playwright/test";

/**
 * Magic-link pilot pairing: an officer issues a one-tap link from the crew
 * page; opening it on a fresh device auto-redeems the single-use code and lands
 * on the paired /crew/me view — no code typed.
 *
 * Gated on E2E_LIVE (needs a live backend + frontend + seeded demo). Run with:
 *   E2E_LIVE=1 PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run e2e
 */

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "officer@demo-aoc-ac.example.aero";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "hunter2pass";

test("magic-link pairs a fresh device without typing a code", async ({ page, browser }) => {
  test.skip(
    !process.env.E2E_LIVE,
    "Set E2E_LIVE=1 with a live backend + frontend stack to run this test.",
  );

  // Officer logs in and issues a pairing link for the first crew member.
  await page.goto("/login");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL((u) => !u.pathname.startsWith("/login")),
    page.getByTestId("login-submit").click(),
  ]);
  await page.goto("/crew", { waitUntil: "networkidle" });
  await page.locator('[data-testid^="pair-device-btn-"]').first().click();
  const link = await page.locator('[data-testid^="pair-link-"]').first().inputValue();
  expect(link).toContain("/crew/me?pair=");

  // A fresh device (no session) opens the link → auto-pairs.
  const pilotCtx = await browser.newContext();
  const pilot = await pilotCtx.newPage();
  await pilot.goto(link, { waitUntil: "networkidle" });

  // The manual pairing form should never appear, and the profile is stored.
  await expect(pilot.locator('[data-testid="pairing-form"]')).toHaveCount(0);
  await expect
    .poll(() => pilot.evaluate(() => localStorage.getItem("ratiba.pilot_profile")))
    .not.toBeNull();
  // The single-use code is stripped from the URL.
  expect(new URL(pilot.url()).search).toBe("");

  await pilotCtx.close();
});
