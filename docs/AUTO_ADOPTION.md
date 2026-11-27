# Controlled auto adoption

Default: manual, no new adoption writes. The repository Owner enables the
explicit standing policy via Settings → Secrets and variables → Actions → Variables.
This is the repository operator's runbook, not a consumer project instruction.

## Setup and stop

1. Configure the existing Pages deployment source as GitHub Actions.
2. Enable only confirmed free maintenance/advisory routes using Secrets and
   confirmation Variables in [Maintenance](MAINTENANCE.md) and [Advisory](ADVISORY.md).
   Advisory is independently enabled by ADVISORY_ENABLED=true.
3. Set KNOWLEDGE_ADOPTION_MODE to assisted or conservative only after accepting
   the policy below. Keep manual (or unset) otherwise.
4. For the first exercise, run Controlled auto adoption on master from Actions.
   An eligible untouched bot candidate with existing ADOPT advice is required;
   a prepared conservative receipt is eligible only for Owner-dispatched recovery.
   No additional LLM request occurs in this workflow.

Example commands (execute only as the repository Owner):

~~~sh
gh variable set KNOWLEDGE_ADOPTION_MODE --repo yohi/agent-compass --body conservative
gh workflow run auto-adopt.yml --repo yohi/agent-compass --ref master
# Stop new adoption jobs:
gh variable set KNOWLEDGE_ADOPTION_MODE --repo yohi/agent-compass --body manual
~~~

A running job is not revoked by a variable change; cancel it explicitly if
immediate stop is required. Never reset ledger markers to recover.

## Model variables

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
Gemini unknown IDs have a five-attempt cap, historical reservations remain
valid, and the aggregate Pacific-day cap remains 70. Advisory caps remain
10/day and 300/month (UTC). These are attempt reservations, not billing
guarantees. All Gemini roles require distinct IDs; NVIDIA routes must also
use distinct IDs. Provider settings do not attest actual billing status.
No model call is made by auto adoption.

Example model override:

~~~sh
gh variable set GROQ_MODEL --repo yohi/agent-compass --body openai/gpt-oss-120b
~~~

To restore a default, remove the corresponding Variable. Verify the new model
is permitted and free before switching; model-specific reasoning effort is
not inherited on an advisory override.

## Modes

- manual (or unset): no auto adoption.
- assisted: prepare a validated candidate PR diff, leave draft for Owner.
- conservative: prepare, mark ready, merge via the ordinary GitHub API
  only after trusted CI and GitHub mergeability checks, then dispatch Pages.
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
Owner; no automatic repeated LLM review. Only unmodified candidate drafts may be prepared.
A previously prepared conservative-policy PR may resume without changing
its commit, only if the complete tree, original candidate, policy receipt,
advisory, source and unchanged registry base are reconstructed exactly.
Resume existing preparations only on explicit Owner workflow_dispatch;
scheduled/upstream runs skip them to avoid repeated CI/merge attempts.
Assisted/owner-selected or modified preparations remain manual. A manual mode change stops newly
started jobs, not a job already executing; cancel any active run to stop it.

## Merge and publication

Dispatch Validate prepared adoption on trusted master, with exact PR,
HEAD, base and unique run identity. Its read-only job reconstructs and
validates only data files; no candidate code is executed. Wait for that
exact successful job and test step, bound to the run attempt. Reuse a
successful bot-dispatched validation for the identical PR HEAD and exact
master SHA (including policy/validator code), only after verifying its
run metadata and actual successful job. A changed master requires fresh
validation even when the registry is unchanged. Allow up to five waits
for initially inconsistent/missing run metadata, with fixed field-name
diagnostics; never accept a mismatched identity. Bounded PR state polling tolerates
propagation lag only if the branch ref is exact. Mark draft ready, then
use ordinary GitHub merge with exact HEAD. No approval, check status
fabrication or rule bypass. On an unprotected master only, the known
bot-triggered Validate registry action_required run may be nonblocking
after the separate successful trusted validation; any other failing or
pending checks/statuses, protected branch or actual merge-rule refusal
remain blocking. This does not satisfy or override required PR checks.
Before merging, use exact live master and proposal branch Git refs,
not the cached PR base.sha or GitHub's temporary merge ref. Compare the
immutable merge base and reconstruct the conflict-free three-way file
tree (no overlapping edits or path collisions); it must equal the
previously verified expected tree. Recheck both live refs immediately
before the ordinary merge API call. Verify merged commit parents/tree
afterwards. GitHub merge API's expected SHA guards HEAD,
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

## Operational recovery

| Observation | Owner action |
| --- | --- |
| AUTO_ADOPTION_DISABLED | Check intended mode; do not enable by default |
| AUTO_ADOPTION_OWNER_REVIEW_REQUIRED / NO_ELIGIBLE_CANDIDATE | Inspect proposal and evidence; leave outside-policy or stale candidates manual |
| AUTO_ADOPTION_PREPARED_OWNER_RESUME_REQUIRED | If desired, dispatch Controlled auto adoption on current master; exact receipt/tree reconstruction is required |
| AUTO_ADOPTION_STOPPED before merge | Inspect actual PR HEAD, current master and validation run; do not regenerate advice or reset ledger |
| AUTO_ADOPTION_PENDING_GITHUB_CHECKS | Respect pending/required checks and decide manually; no forced merge |
| AUTO_ADOPTION_MERGED but no successful deployment | Check actual master, dispatch only pages.yml as needed |
| Deployment success but HTTP check unknown | Check actual health run or use exact-manifest comparison in PORTAL.md |

A receipt is immutable preparation evidence, not a mutable merge-status
field. Use the actual GitHub PR/merge commit and deployment records for state.
Existing prepared PRs do not automatically loop through CI or merge attempts.
An exact successful CI can be reused only for unchanged prepared HEAD and
master SHA, not after a code/policy commit.

## First live milestone (2026-11-27)

v0.10.3, [PR #4](https://github.com/yohi/agent-compass/pull/4),
prepared HEAD 17e95231eb26d24b26486f4fe150908cc94b632b, validated master
7a060b4fb09a8027669dcce4adcd07998a9a792f, merge
[fd9c0a4](https://github.com/yohi/agent-compass/commit/fd9c0a407d83ac2021007ca839f088dfac799b67).

- [Advisory](https://github.com/yohi/agent-compass/actions/runs/45957878164):
  Kimi K3.1 Pro ADOPT, both items conditional/API-runtime configuration.
- [Trusted validation](https://github.com/yohi/agent-compass/actions/runs/45964791876):
  exact prepared HEAD, 125 Python tests and web checks passed.
- [Controlled adoption](https://github.com/yohi/agent-compass/actions/runs/45964746461):
  recovered the existing preparation, verified merge inputs, merged normally,
  verified parents/tree and dispatched Pages. No new inference.
- [Pages deployment](https://github.com/yohi/agent-compass/actions/runs/45964910305):
  build and deploy successful for the resulting master.
- BP-053 and BP-054 are present in master; both local_eval not_verified.

This is live evidence for the owner-dispatched recovery path through
deployment. Scheduled OpenRouter/Groq inference and fallback, a wholly
unattended fresh candidate-to-publication cycle, long-term reliability and
exact post-adoption HTTP verification for this deployment remain unverified.
Do not treat unit-test output or dispatch success as live execution evidence.
No additional phase is required merely to repeat successful reviews.
