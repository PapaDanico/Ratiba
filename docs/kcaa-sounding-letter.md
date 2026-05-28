# Sounding letter to KCAA Flight Operations Inspectorate (FOI)

> **Owner:** Capt. Dan Ng'ong'a (sender). Drafted by Claude Code in Phase 0
> per Plan §5 Phase 5 "Critical dependency for Dan". One A4 page. Final
> wording subject to Dan's review and sign-off.

---

**To:** The Chief Inspector, Flight Operations Inspectorate
Kenya Civil Aviation Authority
KCAA Headquarters, Aviation House
Jomo Kenyatta International Airport
Nairobi

**From:** Capt. Daniel Ng'ong'a
Principal, DN Consultancy
[address line]
[email · phone]

**Date:** [to be inserted before sending]
**Reference:** DN/RATIBA/SOUND-001

**Subject:** Sounding on the acceptable format of an automated FTL
compliance audit pack — KCARs 2025 Part 8

---

Dear Inspector,

I am writing in my capacity as Principal of DN Consultancy to request your
informal guidance on the format and content of an automated Flight Time
Limitation (FTL) compliance audit pack that we are preparing for use by
sub-scale Kenyan AOC holders.

We are developing **Ratiba**, a crew rostering platform tailored to the
3–10 aircraft / 15–60 flight crew segment of the East African market. The
platform combines a deterministic constraint solver (Google OR-Tools
CP-SAT) with structured rule definitions drawn directly from KCARs 2025
Part 8. One of its deliverables to an operator is a periodic PDF "audit
pack" intended to be presentable, on request, to your Inspectorate as
contemporaneous evidence of FTL/FRMS compliance.

In its current draft, an audit pack contains:

1. **Cover page** — operator AOC number, reporting period,
   generation timestamp, and a SHA-256 hash signature that allows tamper
   detection.
2. **Executive summary** — total FDPs flown in the period, count of
   anomalies, count of recency / currency exceptions.
3. **Per-crew FTL summary** — for every crew member, rolling 7-day,
   28-day, and 365-day duty and block hour utilisation against the
   applicable limits, with a clear visual indicator of margin.
4. **Anomaly log** — every FDP flagged at-limit or above with a
   regulatory citation and any corrective action recorded.
5. **Currency status snapshot** at period close (OPC, LPC, line check,
   90-day landings, route familiarisation, etc.).
6. **Immutable audit trail extract** — every roster change in the period,
   showing actor, timestamp, before/after state.
7. **Methodology page** — the precise rule set applied, with citations to
   KCARs 2025 Part 8 articles, and the generator software version.

We would value your informal view on the following points **before** we
finalise the format:

- Is the structure described above broadly aligned with what the
  Inspectorate would expect to see if requested during a routine or
  no-notice audit?
- Are there additional sections, citations, or evidentiary artefacts that
  you would prefer to see included from the outset?
- Is a SHA-256 generator signature (with a separate verification
  endpoint) considered acceptable tamper-evidence, or would the
  Inspectorate prefer a different mechanism?
- Are there electronic-records guidelines, beyond KCARs 2025 Part 8, that
  we should observe in how the underlying data are retained?

Any of these points may of course be best discussed in person; I would be
pleased to call on the Inspectorate at your convenience to demonstrate a
draft pack and gather your feedback.

We expect first operational use of Ratiba in approximately 16 weeks. Our
preference is to co-design the audit pack with your guidance from the
outset, rather than ask you to react to a finished artefact.

Thank you in advance for your time and counsel.

Yours faithfully,

**Capt. Daniel Ng'ong'a**
Principal, DN Consultancy
[signature]

---

*Encl.: One-page Ratiba programme summary (optional, attach if Dan agrees).*
