# Walkthrough for prospective users

> If you're a Crewing Officer, Chief Pilot, or Director of Flight Operations
> at a sub-scale East African aviation operator, this is a 10-minute
> guided tour of Ratiba. By the end of it you'll have seen every screen
> a Crewing Officer would use day-to-day, and you'll have a downloaded
> KCAA-presentable audit pack on your desktop.

This is the doc to share with the people whose feedback we want.

## Prerequisites

`docs/getting-started.md` walks you from a fresh `git clone` to a
populated dashboard in 10 minutes. Once you're logged in, come back here.

## The questions we want feedback on

Before you start clicking, the four questions whose answers shape the
product:

1. **Where in your current process does this save time?** And where, if
   anywhere, does it cost you time?
2. **Does the KCAA audit pack look like something you'd present to FOI?**
   What's missing? What's there but you wouldn't include? Where's the
   wording off?
3. **How would your pilots want to receive their roster?** Ratiba now offers
   three reach options — a Telegram bot, a phone web view, and one-tap
   **WhatsApp / SMS / email** sharing of the roster/duty and the pairing link.
   Which fits how your crew actually communicate today?
4. **What's the one thing that has to be true for you to roll this out
   to your full crew complement?** (Be brutal — we'd rather hear "no"
   now than discover it after a contract.)

Email the answers (and screenshots, and anything else you noticed) to
the operator who showed you Ratiba.

## The 10-minute click-path

### 1. Overview tile (30 s)

The landing page leads with an **attention banner** — "one thing that needs
you" — that surfaces the single most-urgent item by severity (an expired
currency, a HIGH fatigue flag, expiring currencies, pending approvals, or
unacknowledged notices) and links straight to the screen that resolves it.
Below it are the at-a-glance tiles: pending leave + swaps, a currency
traffic-light, fatigue watch, and notices.
**Does the "one thing that needs you" banner pick what *you'd* triage first on
your morning standup?**

### 2. Roster calendar (3 min) — `/roster`

A 28-day rolling grid. Each cell is a duty day (one aircraft × one
date). Coloured pills surface FTL legality at a glance — green
(`LEGAL`), amber (`AT_LIMIT`), or red (`REQUIRES_FRMS_DEROGATION` /
`ILLEGAL`).

Try this:

- **Drag-and-drop reassign.** Drag a crew member from the palette (or an
  already-assigned name) onto a duty's CAPT or FO slot. The FTL check runs
  live and the legality pill reconciles; an invalid drop (e.g. an FO onto a
  Captain seat) is refused with a reason, and a backend rejection rolls the
  move back. Every drop is a reason-stamped amendment in the audit trail.
- **Amend a duty day** via the "amend" link for the same effect with a custom
  reason. The audit trail records before/after; the next audit pack shows it.
- **Notice the legality pill recompute** on every change — each FDP runs
  through `app.services.ftl_engine`, and the change cascades to that crew's
  later days too (cumulative / rest / weekly-rest windows are backward-looking).
- **Toggle Comfortable / Compact** (top-right) to fit more of the 28-day grid
  on screen; the choice is remembered.

Question for feedback: **does the calendar grid — and dragging crew between
duties — match the mental model you have when you look at your current Excel
roster?** If not, what shape would?

### 3. Crew + currency dashboard (1 min) — `/crew` and `/currency`

The crew page lists every pilot with their role + base + active state.
The currency dashboard shows OPC / LPC / 90-day landings etc. with a
GREEN / AMBER (≤ 30 d to expiry) / RED (expired at period close)
state per row.

The seed data deliberately spreads pilots across the traffic-light
states so you can see all three at once.

Question for feedback: **what currency / recency types are we missing
that your operator tracks?**

### 4. Leave + swap workflows (1 min) — `/leave` and `/swaps`

Pending leave requests are listed for the Crewing Officer to approve
or reject. Same for swap requests. Decisions are audit-logged with the
actor's identity and a timestamp.

Question for feedback: **is the approve / reject dichotomy enough, or
do you need an "approve with conditions" + free-text reply path?**

### 5. KCAA audit pack (3 min) — `/audit`

This is the most important screen.

Try this:

- Set the period to "last 90 days".
- Click **Generate pack**. It takes 1–3 seconds against the seeded
  data; against a 25-pilot operator we measure < 30 s.
- Click **Download** to inspect the PDF. The seven sections —
  cover, executive summary, per-crew FTL summary, anomaly log,
  currency snapshot, audit-trail extract, methodology — are
  documented at `docs/audit-pack-spec.md`.
- Click **Verify** to re-derive the SHA-256 over the PDF bytes.
  Try editing the PDF in a hex editor, then click Verify again — the
  hash mismatch is the tamper-evidence we'd show KCAA FOI.

**This is the screen most prospective users want most. Spend the
biggest chunk of your evaluation here.**

Question for feedback: **what would your KCAA inspector look for in
this document that isn't there?** What's there that they wouldn't?

### 6. Telegram bot + `/crew/me` mobile web view (2 min) — `/crew/me`

Pilots interact with Ratiba either through Telegram or through a
phone-sized web view. Same data, same surface.

To try the web view:

1. On `/crew`, find a pilot row and click **"Pair device"**. This issues a
   single-use code and shows a one-tap pairing **link** — plus **WhatsApp /
   SMS / Email** buttons that open your own messaging app with the link
   pre-filled to send to the pilot.
2. Open that link (`/crew/me?pair=…`) in a mobile-sized browser window — it
   **auto-pairs** on arrival, no code typing. (You can still paste the raw
   code manually if you prefer.)

Now click through the tabs — Today, Roster, Currency, Notices. Each of Today
and Roster has its own **Share** row (WhatsApp / SMS / Email) so a pilot can
forward their duty or roster the way they actually communicate. **Does this
give your pilots enough? What's the one extra thing they'd ask for?**

(If `TELEGRAM_BOT_TOKEN` is set in `.env`, the same surface is
available through your bot's chat — Phase 4 wired all seven commands.)

### 7. Fleet registry (1 min) — `/fleet`

Register your aircraft by picking the type from a curated dropdown —
grouped by category (turboprops, light utility, regional jets,
narrowbodies) and scoped to what sub-scale East & Central African
operators actually fly. Each option shows the ICAO designator,
manufacturer + model, and typical seats. Types not on the list can
still be entered free-form and are flagged as "custom".

Question for feedback: **is your fleet's type in the list? If not,
which one are we missing?**

### 8. Notices — crew comms (2 min) — `/notices`

Post operational comms, fleet notices, safety bulletins, or crew-room
/ morale posts. Each notice has a category + severity, can require
acknowledgement (the dashboard tracks who's ack'd), can be pinned, and
can carry an image URL (for fleet photos or the occasional meme).

Published notices land in every paired pilot's `/crew/me` **Notices**
tab and their Telegram `/notices` command — and, when a bot token is
configured, are pushed straight to their chat.

Try this:

- Post a `SAFETY` / `CRITICAL` notice with "require acknowledgement"
  on. Then open `/crew/me`, go to the Notices tab, and acknowledge it.
  Back on `/notices`, the ack count ticks up.
- Post a `SOCIAL` / `INFO` notice with an image URL — that's the
  crew-room / morale channel.

Question for feedback: **would this replace your current WhatsApp
broadcast group, or live alongside it?**

### 9. Operator settings (30 s) — `/settings`

Tweak the optimiser's soft-constraint weights:

- `balance_block_hours` — how aggressively to spread flight time evenly.
- `faith_violation` — penalty for putting a Sunday-protected crew
  member on a Sunday.
- `leave_violation` — penalty for assigning over a pending leave.
- `positioning_minimisation` — discourage deadhead positioning.

Higher = stronger preference. The defaults are reasonable for most
sub-scale operators; the editor exists for the cases where they aren't.

## What's intentionally out of scope for the demo

These are deferred per Plan §1 ("explicitly out of scope (deferred)"):

- Cabin crew / engineers / ground staff (future versions)
- Real-time disruption recovery with predictive elements
- Full FOS / FRMS biomathematical fatigue modelling
- Integration with Sabre / Amadeus / other PSS
- Native iOS / Android apps (Telegram + responsive web first)

If any of these are deal-breakers, tell us — sequencing is a
conversation, not a fixed plan.

## What's deferred until first-pilot commit

These land in the post-feedback phase:

- httpOnly cookies + CSRF (security hardening)
- ADC Nairobi or AWS Cape Town hosting (KDPA-compliant region pick)
- ODPC (KDPA 2019) registration paperwork
- LLM constraint parser that ingests your OM-A FTL chapter and proposes
  a constraint set for human review

## Sending feedback

The best feedback we've ever received fits in five sentences. Don't
polish — send rough.

We'd particularly value: what surprised you (good or bad), the one
thing that has to be true for you to use this, and one moment where
the screen didn't match your expectation.
