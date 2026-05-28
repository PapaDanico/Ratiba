# ADR 0006: Pivot to operator-agnostic, demo-first

* **Status:** Accepted — 2026-05-28
* **Supersedes:** ADR 0005 (preserved as a template; calls are now deferred)
* **Deciders:** Capt. Dan Ng'ong'a, Claude Code
* **Reference:** Project Plan v1.0 §1, §10

## Context

The original plan in §5 Phase 6 paired "ship the MVP" with "deploy to
the first pilot operator (Jubba Airways or I-Fly Air Solutions) on
ADC Nairobi". ADR 0005 selected I-Fly + ADC and produced an
onboarding playbook + deployment runbook against those choices.

After Phase 6 software shipped, Dan called a course correction:

> At this juncture, we should prioritize the development of an
> operator-agnostic platform. Establishing a functional system is
> paramount before we delve into contractual negotiations (like ADC
> Nairobi or ODPC). Our immediate objective is to gather feedback from
> one or two prospective users.

That's the correct sequencing — better to gather feedback against a
runnable system than to commit to contracts whose specifics we can
only refine after seeing real users react.

## Decision

**Defer the I-Fly + ADC Nairobi commitments. Optimise for
prospective-user evaluation.**

Specifically:

1. The platform remains multi-tenant from day one (no change — every
   business table already carries `operator_id`).
2. ADC Nairobi credentials, ODPC registration, and the I-Fly pilot
   contract are paused until at least one round of prospective-user
   feedback has shaped the product.
3. The previous I-Fly-specific `docs/onboarding-playbook.md` becomes
   an **operator-agnostic onboarding template**.
4. The previous ADC-specific `docs/deployment-runbook.md` becomes a
   **hosting-agnostic deployment guide** — `docker compose` is the
   default, with cloud notes as appendices.
5. `scripts/seed.py` gains a `--demo` mode that populates two
   fictional operators with realistic crew, sectors, rosters,
   currencies, leave + swap requests, and a generated audit pack so a
   prospective user can poke at every screen within minutes.
6. A new `docs/getting-started.md` walks from `git clone` to "I see
   a roster" in under 10 minutes.
7. A new `docs/walkthrough.md` for prospective-user evaluation
   sessions — what to try, what to look for, what feedback to give us.

## Consequences

- ADR 0005's operator + region calls are paused, not reversed. Both
  remain viable when we re-engage. The justifications still apply.
- The Plan §5 Phase 6 "first pilot deployment" milestone becomes
  contingent on prospective-user feedback; we'll re-plan its
  scope after the first 1–2 evaluation conversations.
- Phase 7 (LLM constraint parser) and Phase 6's KDPA / S3 hardening
  remain Phase-6.5 work that lands once a pilot operator commits.
- The product surface is unchanged — what's changing is the framing,
  the docs, and the demo experience.
