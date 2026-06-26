import { expect, test } from "@playwright/test";

/**
 * Drag-and-drop crew reassignment on the roster calendar: dropping a captain
 * chip onto a CAPT slot fires /roster/amend, which recomputes FTL legality;
 * the card reflects the new crew and reconciled verdict.
 *
 * Gated on E2E_LIVE (needs a live backend + frontend + a published roster in
 * the default window). Run with:
 *   E2E_LIVE=1 PLAYWRIGHT_BASE_URL=http://localhost:3000 npm run e2e
 */

const ADMIN_EMAIL = process.env.E2E_ADMIN_EMAIL ?? "officer@demo-aoc-ac.example.aero";
const ADMIN_PASSWORD = process.env.E2E_ADMIN_PASSWORD ?? "hunter2pass";

test("drag-and-drop reassigns a captain and re-checks FTL", async ({ page }) => {
  test.skip(
    !process.env.E2E_LIVE,
    "Set E2E_LIVE=1 with a live backend + frontend stack to run this test.",
  );

  await page.goto("/login");
  await page.getByTestId("login-email").fill(ADMIN_EMAIL);
  await page.getByTestId("login-password").fill(ADMIN_PASSWORD);
  await Promise.all([
    page.waitForURL((u) => !u.pathname.startsWith("/login")),
    page.getByTestId("login-submit").click(),
  ]);
  await page.goto("/roster", { waitUntil: "networkidle" });

  const slot = page.locator('[data-testid^="slot-CAPT-"]').first();
  await expect(slot).toBeVisible();
  const slotTestId = await slot.getAttribute("data-testid");
  const before = (await slot.innerText()).replace(/\s+/g, " ").trim();
  const curEmp = before.match(/[A-Z]{2}-[A-Z]{3}-\d+/)?.[0] ?? "";
  // Captain employee numbers share the seat's prefix (e.g. "AC-CAP-").
  const prefix = curEmp.replace(/\d+$/, "");
  const empNos = await page
    .locator(`[data-testid^="crew-chip-${prefix}"]`)
    .evaluateAll((els) => els.map((e) => e.getAttribute("data-testid")!.replace("crew-chip-", "")));
  const newEmp = empNos.find((e) => e !== curEmp);
  expect(newEmp, "need a second captain to drag").toBeTruthy();

  // Native HTML5 drag-and-drop needs one shared DataTransfer dispatched in-page.
  const [amendResp] = await Promise.all([
    page.waitForResponse(
      (r) => r.url().includes("/roster/amend") && r.request().method() === "POST",
    ),
    page.evaluate(
      ({ slotSel, chipSel }) => {
        const chip = document.querySelector(chipSel);
        const target = document.querySelector(slotSel);
        if (!chip || !target) throw new Error("drag source/target not found");
        const dt = new DataTransfer();
        const fire = (el: Element, type: string) =>
          el.dispatchEvent(
            new DragEvent(type, { bubbles: true, cancelable: true, dataTransfer: dt }),
          );
        fire(chip, "dragstart");
        fire(target, "dragenter");
        fire(target, "dragover");
        fire(target, "drop");
        fire(chip, "dragend");
      },
      { slotSel: `[data-testid="${slotTestId}"]`, chipSel: `[data-testid="crew-chip-${newEmp}"]` },
    ),
  ]);

  expect(amendResp.status()).toBe(200);
  await expect(slot).toContainText(newEmp!);
});
