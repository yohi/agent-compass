# Autonomous knowledge maintenance / ナレッジ更新支援

## Enablement (owner only)

1. Use a dedicated **unbilled Free Tier** Google AI Studio project. Never enable
   billing for this key. The API does not attest billing tier to this workflow;
   the owner must keep it unbilled.
2. Register the key as Actions repository secret GEMINI_API_KEY.
3. Set Actions repository variable GEMINI_FREE_TIER_CONFIRMED to exactly true.
   Without both values, the workflow does not make model calls or write its ledger.
4. Settings → Actions → General: allow GitHub Actions to create pull requests
   if acceptable. This setting also allows approvals at the GitHub level;
   the workflow never approves PRs. If policy disallows it, leave it disabled:
   archived candidates remain durable, PR creation is blocked.
5. Run Maintain knowledge candidates manually on master. Scheduled runs use
   03:47 UTC (12:47 JST); provider quotas use Pacific calendar days.

## Design

Separate serialized workflow, no modifications to existing monitor/discovery.
Initial observations are a bounded inventory review of registered sources,
not claims of newly released guidance. Later observations compare normalized
content hashes. A bot-owned ledger issue records the latest pending snapshot,
stage, reservations and completed disposition per source. The original
monitor and discovery continue independently. New discovery URLs are not
automatically registered or sent to a model.

The old source body is not available; analysis compares current normalized
source and linked registry records. Latest pending snapshots coalesce;
superseded pending counts are explicit, not a complete historical diff.
Source data is held only in memory. Input excerpts are bounded by bytes,
not an exact token count; the prompt is capped near 18 KB plus request
overhead. Long sources are traversed in bounded chunks (at most one completed chunk
per source per run); a persisted character cursor advances even if a chunk
has no proposal. A changed snapshot resets the cursor and counts supersession.
Chunk boundaries can omit cross-boundary context; model classifications are
not proof of relevance or absence.

Roles and per-Pacific-day reserved attempts:
- gemini-3.5-flash-lite: 50 (classification)
- gemini-3.8-flash: 10 (analysis)
- gemini-4-hydrogen: 5 (complex)
- gemini-3.6-flash: 5 (alternate only for primary HTTP 404/503, not quota)

The ledger persists reservation before each request, including failure and
interruption. At least 15 seconds between requests, serialized. HTTP 503
permits exactly one retry after 30 seconds, only if the same Pacific day and
a new durable reservation is available. A second 503 stops the role for that
run. No retry for authentication, quota, validation or other errors. Quota
failures persistently block the model until the next Pacific day;
authentication failures block all model calls for the same period.
The code only allows these explicitly listed model IDs and caps, no paid
fallback, grounding, tools, external callbacks or alternate providers.
Free-tier eligibility and project-wide shared usage are not programmatically
verified. A crash between API success and archive can require a later
re-analysis; reservations still count. Keep the ledger intact.

Structured output is validated locally for action, exact target, linked
practice, status, bounded text, evidence quote matching and identity.
An excerpt hash, chunk cursor and within-chunk line/character locator replace the source quote in
the archive. This checks literal evidence presence, not semantic entailment.
No source body, prompt, key or raw response is persisted or logged.
Diagnostics identify the registered source, role, model and chunk cursor,
with fixed reason codes for response envelope/finish/JSON, proposal structure,
scope, status and literal evidence checks. Unknown provider finish values and
exception messages are never printed. Category values are constrained by the
response schema as well as local validation. Existing failed attempts remain
subject to the original daily retry guard; do not reset the ledger.

## Proposal and adoption

A validated candidate is archived to a bot-owned issue comment before marking
it ready. If PR publication fails, retry publication without invoking the model.
The branch is compass-proposals/<identity>; the only added file is
proposals/<source>/<identity>.json. It contains concrete candidate field values,
current practice digest, source URL/hash and evidence locator.
PRs are draft, one per source snapshot/chunk identity, never auto-approved or merged.
An existing PR (including closed) is treated as owner disposition.
**Merging a proposal record does not adopt the guidance.** Owner verifies
the official evidence and selects candidate items, statuses and placements in
[Prepare knowledge adoption](ADOPTION.md); the owner-only workflow prepares
the actual registry diff, regenerates docs and tests on the same candidate PR.
This is deliberately separated from executing model-supplied patches.
No new model/source is automatically registered. The model cannot choose
paths, branch names, API tools, permissions or commands.

## Portal health

Verify public portal runs daily, after successful Pages deployments and manually.
It checks the manifest and seven agent files by HTTP and SHA-256, plus index
HTML; deployment-triggered checks compare the exact built manifest. A scheduled
check validates served consistency, not necessarily latest master. Bounded
retry handles propagation; failures are visible in Actions. No credentials.

Offline tests exercise state, quota, input limits, validation, proposal
idempotence, disabled behavior and portal integrity. Live API/PR acceptance
requires owner enablement and is not inferred from offline tests.
