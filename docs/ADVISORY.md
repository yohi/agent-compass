# Independent adoption advisory / 独立採択判断

Optional Phase 9. Public candidate-only PRs produced by Gemini maintenance
are checked against the current official source and canonical registry,
then evaluated by one non-Gemini model. Advice is a PR comment, not
approval, adoption or merge. No changes to the existing maintenance ledger,
quota, PR branches, registry or repository settings.

## Enable only confirmed free access

In Settings → Secrets and variables → Actions, add only the providers you
intend to use. Never paste keys into issues or workflow inputs.

| Secret | Required variable (true) | Scope |
| --- | --- | --- |
| OPENROUTER_API_KEY | OPENROUTER_FREE_TIER_CONFIRMED | Free model only, scheduled/manual |
| GROQ_API_KEY | GROQ_FREE_TIER_CONFIRMED | Free-tier account only, scheduled/manual |
| NVIDIA_API_KEY | NVIDIA_FREE_TIER_CONFIRMED | Free prototype access, manual only |

Set ADVISORY_ENABLED=true to enable the workflow. NVIDIA additionally
requires NVIDIA_PROTOTYPE_USE_CONFIRMED=true, only for authorized development
and testing. NVIDIA hosted free endpoints are for prototyping, not a
production-service entitlement; unattended scheduled runs deliberately skip
NVIDIA. Verify the actual account, terms, billing settings and endpoint
before enabling any provider. These flags are owner attestations, not
provider billing attestation. Disable a provider if its terms or pricing
change. Use dedicated unbilled/free-tier keys and do not attach paid fallback.
The workflow cannot independently prove a Groq or NVIDIA account is free.

Default ordered routes in registry/advisory.json:
1. NVIDIA moonshotai/kimi-k3.1-pro (high reasoning; manual test only)
2. NVIDIA z-ai/glm-5.3-flash (manual test only)
3. OpenRouter nvidia/nemotron-3-ultra-550b-a55b:free
4. Groq openai/gpt-oss-120b

The free OpenRouter route requires exact :free model ID, live catalog zero
pricing and zero max_price, with automatic provider fallback disabled.
Model ID mismatch is rejected. No arbitrary endpoints, model router,
BYOK or paid models. Model IDs may be overridden with GitHub Actions Variables (see
docs/AUTO_ADOPTION.md); the provider, exact-ID checks, free-tier confirmation
and OpenRouter zero-price checks remain mandatory. Changing a model removes
its inherited model-specific reasoning effort. Provider API features and
availability are not guaranteed. The code uses plain JSON replies, not
tool calls; Groq JSON mode is requested where applicable. Exact ID
aliases and unsupported parameters may cause DEFER.

Official references (inspected 2026-11-27):
- https://developer.nvidia.com/nim
- https://build.nvidia.com/moonshotai/kimi-k3_1-pro/build
- https://build.nvidia.com/z-ai/glm-5-3-flash/build
- https://openrouter.ai/nvidia/nemotron-3-ultra-550b-a55b:free
- https://openrouter.ai/docs/guides/routing/provider-selection
- https://console.groq.com/docs/rate-limits
- https://console.groq.com/docs/billing-faqs

## Run

Actions → Independent adoption advisory → Run workflow on master.
Optionally specify a candidate PR number; blank scans eligible open drafts.
Scheduled UTC 05:17 (JST 14:17) uses OpenRouter/Groq only. No API call or
ledger write if disabled or no confirmed provider. Only untouched bot-owned
candidate PRs are eligible. Never check out or execute PR-controlled code.

The separate advisory issue holds a durable UTC daily/monthly reservation
ledger, max 10 inference calls/day and 300/month (all providers and retries
combined); 15 seconds minimum interval; reserve before each inference.
A failed persistence operation stops processing. Account-wide quotas from
other applications are not known. OpenRouter pricing GET requests are not
inference reservations. By default a PR HEAD is attempted at most once per
UTC day (except bounded transport fallback inside that attempt). The
Owner-only recovery option below is the sole same-day exception. Existing
bot result comments deduplicate exact HEAD indefinitely. Never reset the
ledger to force a retry. No automatic re-review just because another
registry record changed. Results record the exact registry base and
source fingerprint.

Transport errors, missing model, auth/payment/quota errors or service
unavailability may proceed to the next enabled free route. Auth/payment/
quota block that provider for the UTC day. A valid ADOPT, PARTIAL_ADOPT,
REJECT or DEFER is final for that HEAD; malformed/incomplete responses
produce a terminal DEFER comment without querying another model for a
favorable verdict or retrying the same HEAD tomorrow. Transport failures
without a result comment can be retried on a later day.
GitHub write errors stop the run; inspect state before a manual retry.

### Same-day recovery (v0.9.2)

For an interrupted attempt without a published result, dispatch a **new**
workflow on master as the repository Owner, specifying one proposal_pr
and checking retry_failed. The original and triggering actor must both
be the Owner. A scheduled run or an all-PR scan cannot use this option.
The existing exact-HEAD result comment (including terminal DEFER) always
wins, even on recovery. Recheck master, candidate HEAD and comments before
a same-day retry reservation; keep previous reservations, provider blocks,
free-tier gates and daily/monthly limits. Every new inference requires
another durable reservation. No change to ledger schema or reset.

A prior reservation without a comment cannot establish whether inference
actually completed. The Owner explicitly authorizes another attempt
after checking the failed run and PR. This is recovery, not a way to seek
another verdict. Without a same-day reservation the selected PR follows
the normal first-attempt path. Do not use Re-run jobs of an older revision.

### Safe diagnostics (v0.9.1)

Runtime logs identify the PR, allowlisted provider/model, stage and fixed
diagnostic code. Stage start/ok/failure separates candidate checks, ledger
reservation, HTTP connect/read, response parsing, semantic decision
validation, master/PR HEAD checks, and comment lookup/write. GitHub CLI
failures report a recognized numeric HTTP status or a generic command/
timeout code; no raw stderr, exception message, API key, request, source
text or model response is logged. A reserved request is not proof of
successful inference. Unit-test mock logs are not live API observations.
The existing ledger schema, quota, and provider routing are unchanged.
Normal deduplication remains in force; only the explicit recovery option
above may bypass a same-day reservation, never an existing result.

## Evidence and output

Validate proposal commit scope, exact source hash and evidence locators
using adoption.py. Send only public source/registry/candidate data to the
selected provider. All registry records are included, bounded source
windows are explicitly marked partial when necessary, and an oversized
context defers instead of silently dropping registry records.
The full source is never persisted in comments or ledger. Model output
is untrusted; only bounded paraphrased reasons and validated decision
objects are published, with Markdown/mention escaping. Do not assume
model-generated reasons are correct or that they never quote source text.

ADOPT means all candidate items recommended; PARTIAL_ADOPT means only some;
REJECT means all rejected; DEFER means none accepted and at least one
uncertain. The existing adoption planner validates suggested decision JSON
without writing files. Owner still reviews evidence, exact scope, status
and placement before using Prepare knowledge adoption. Literal evidence
checks cannot prove semantic correctness. An advice comment may be stale
after master/source changes; adoption rechecks current evidence and records.
No independent follow-up review is automatically started after a judgment.

## Boundaries and tests

No GPT/ChatGPT/Codex subscription calls, no Gemini review, no Sakura,
no paid fallback. Groq gpt-oss is an independent hosted open-weight
model, not ChatGPT. Tests use synthetic fixtures and mocked API calls;
real account access, model response format, semantic accuracy and comment
permissions require one actual authorized run. A free model's existence
in a catalog is not proof of access from a particular account.
