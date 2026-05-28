# LLM cost model

## Two distinct call sites

| Call site                  | Model                  | Volume per pilot/mo | Phase |
|----------------------------|------------------------|---------------------|------:|
| Bot intent routing         | Claude Haiku 4.5       | 60–120 messages     |     4 |
| OM-A constraint parsing    | Claude Sonnet 4.5      | ~10 calls / operator|     7 |

The optimiser, the FTL engine, and audit-pack generation never call an
LLM. LLM outages can at worst degrade the bot to keyword-only routing.

## Bot intent routing — Haiku 4.5

### Per-call shape

`bot/nlp_router.py` sends:

- **System prompt:** ~280 tokens (fixed; cached after first request per
  rolling window via Anthropic's prompt caching).
- **User message:** typically 5–30 tokens (a pilot's question).
- **Max output:** 64 tokens; actual output is consistently 15–25 tokens of
  JSON (`{"intent": "...", "confidence": ...}`).

Effective per-call tokens (steady state, after cache warm):

- Input (cached portion): 280 tokens at **0.1 × base price**
- Input (uncached portion): 15 tokens at base price
- Output: 25 tokens at base price

### Per-pilot estimate

Assuming an active pilot sends ~3 bot messages per duty day and operates
~20 duty days per month → **~60 messages / pilot / month**.

Anthropic Haiku 4.5 list pricing (illustrative — confirm against current
pricing page before invoicing operators):

- Input: $0.80 / 1 M tokens
- Output: $4.00 / 1 M tokens
- Cached input: $0.08 / 1 M tokens

Per call: `(280 × 0.08 + 15 × 0.80 + 25 × 4.00) / 1 000 000 ≈ $0.000134`

Per pilot / month (60 calls): `60 × $0.000134 ≈ **$0.008**`

**Headroom against the Plan §5 Phase 4 target of ≤ USD 2 / pilot / month
is ~250×.** Even a 10× usage spike (heavy adoption, plus free-text-only
pilots who never use slash commands) leaves us well under the budget.

### Measurement plan

`backend/app/services/llm_client.py` returns `input_tokens` and
`output_tokens` on every call. Phase 6 will start aggregating these into
a `llm_usage` table (one row per pilot per day) so Dan can verify the
estimate above against real traffic before the first operator is invoiced.

## OM-A constraint parser — Sonnet 4.5 (Phase 7)

OM-A FTL chapters land at ~50 pages of dense regulatory text. Per parse:

- Input: ~25 k tokens (one full OM-A chapter)
- Output: ~3 k tokens (proposed YAML constraint set)

Sonnet 4.5 illustrative pricing:

- Input: $3.00 / 1 M
- Output: $15.00 / 1 M

Per parse: `~$0.12`. A new operator runs this perhaps 10× across review
cycles → **~$1.20 / operator** for the entire onboarding. Negligible.

## Updated when

This document is refreshed at the end of each phase that touches an LLM
call site, and again when Anthropic adjusts list pricing.

**Last updated:** Phase 4 baseline, 2026-05-28.
