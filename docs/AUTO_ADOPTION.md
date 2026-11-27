# Controlled auto adoption

Default: manual, no new writes. The repository Owner enables the explicit
standing policy via Settings → Secrets and variables → Actions → Variables.

| Variable | Default / example |
| --- | --- |
| KNOWLEDGE_ADOPTION_MODE | manual / assisted / conservative |
| GEMINI_CLASSIFY_MODEL | gemini-3.5-flash-lite |
| GEMINI_ANALYZE_MODEL | gemini-3.8-flash |
| GEMINI_COMPLEX_MODEL | gemini-4-hydrogen |
| GEMINI_ALTERNATE_MODEL | gemini-3.6-flash |
| NVIDIA_PRIMARY_MODEL | moonshotai/kimi-k3.1-pro |
| NVIDIA_FALLBACK_MODEL | z-ai/glm-5.3-flash |
| OPENROUTER_MODEL | nvidia/nemotron-3-ultra-550b-a55b:free |
| GROQ_MODEL | openai/gpt-oss-120b |

Unset model variables use the existing defaults. API keys remain Secrets;
existing explicit free-tier confirmations apply to each newly selected
model. Confirm actual free-tier availability before changing IDs.
OpenRouter requires an exact :free model and a live zero-price catalog
check; no auto-router or paid fallback. NVIDIA is manual prototype only.
Changing an advisory model clears inherited model-specific reasoning effort.
Gemini unknown IDs have a five-attempt cap, all historical reservations
remain valid, and the aggregate daily cap remains 70. Advisory caps remain
10/day and 300/month. No model call is made by auto adoption.

## Modes

- manual (or unset): no auto adoption.
- assisted: prepare a validated candidate PR diff, leave draft for Owner.
- conservative: prepare, mark ready, merge via the ordinary GitHub API
  only when GitHub reports clean/mergeable, then dispatch Pages.
  Other values are unsupported; no extended mode.

Policy is registry/adoption-policy.json. Only exact model/family scoped
new additions in reasoning, prompting, context; configuration (api-or-runtime)
or author-guidance; recommended or conditional; full source context;
all items ADOPT by the existing bot advisory. Sensitive wording is excluded
conservatively; lexical screening does not guarantee semantic safety.
No common/harness/framework changes, existing-record edits, retirement,
standing instructions, security/permissions advice, partial adoption,
new source/model registration or rejected/deferred candidates.
Revalidate exact source snapshot and locator, compare advisory registry
base with current registry, run the existing adoption planner and full
build checks in trusted master checkout. Never execute candidate code.
The receipt identifies the bot advisory, policy, exact proposal, decisions
and model; it does not assert human semantic evidence review.

Runs after successful master advisory, daily 05:57 UTC (14:57 JST), or
Owner manual dispatch. At most one preparation per run. Uses existing
adoption concurrency group. If registry changed since advice, leave for
Owner; no automatic repeated LLM review. Only unmodified candidate drafts
are eligible. Prepared but blocked PRs remain for manual disposition;
do not automatically amend/retry them. A manual mode change stops newly
started jobs, not a job already executing; cancel any active run to stop it.

## Merge and publication

Mark the selected draft ready, require GitHub clean/mergeable, use exact
HEAD SHA and ordinary merge (no forced push, approval or rule bypass).
Required checks may not run on bot pushes; if pending, leave for Owner.
Check current master immediately before merge and verify merged commit
parents/tree afterwards. GitHub merge API's expected SHA guards HEAD,
not an atomic expected master SHA: concurrent base changes are a residual
race, detected by post-merge verification. No automatic rollback.
Use a protected master with appropriate required checks where practical.

Dispatch existing pages.yml on master with Actions write permission.
GITHUB_TOKEN push suppression does not prevent workflow_dispatch.
The existing portal-health workflow checks the published manifest and
endpoints after deployment. Dispatch success is not deployment success.
If dispatch or deployment fails after merge, recover via existing
Publish knowledge portal workflow; never repeat the adoption.
No PAT, new external service or extra LLM subscription required.
Existing Pages environment rules remain in force.

References:
- https://docs.github.com/en/rest/pulls/pulls#merge-a-pull-request
- https://docs.github.com/en/graphql/reference/pulls
- https://docs.github.com/en/rest/actions/workflows#create-a-workflow-dispatch-event
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow

Offline tests do not prove live merge authorization, model judgment quality,
branch protections, or deployment. Owner is responsible for policy opt-in.
