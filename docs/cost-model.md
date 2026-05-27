# LLM cost model

> **Status:** Phase 0 placeholder. Phase 4 will populate this document with
> measured token usage and a unit-cost-per-pilot estimate.

Two distinct LLM call sites with different cost profiles:

| Call site                  | Model                  | Volume               | Phase |
|----------------------------|------------------------|----------------------|------:|
| Bot intent routing         | Claude Haiku 4.5       | Hundreds / pilot / mo|     4 |
| OM-A constraint parsing    | Claude Sonnet 4.5      | Few / operator       |     7 |

Phase 4 acceptance criterion (Plan §5): bot LLM cost ≤ **USD 2 / pilot / month**
at Haiku 4.5 prices. This target is measured and reported here once the
bot ships.
