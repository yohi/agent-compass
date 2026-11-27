# Knowledge adoption / 知識の採択

This document describes the manual, Owner-selected path introduced in v0.7.0.
It prepares the actual registry diff on an existing candidate PR, without
new LLM requests, separate review PRs, auto-approval or auto-merge.
For optional low-risk automatic adoption, see [Controlled auto adoption](AUTO_ADOPTION.md).
Use the manual path for all changes outside that policy.

## Owner workflow

1. Open a generated draft proposal PR. Read its candidate JSON, linked official
   source and exact scope. Select the items that are supported. Indices are
   **1-based positions in the proposals array**. Record the exact PR HEAD
   commit (not the base commit, branch name or proposal identity).
2. In Actions → **Prepare knowledge adoption** → Run workflow on master,
   enter proposal_pr, proposal_head and a JSON decisions array. Check
   evidence_reviewed only after reviewing the actual source and candidate
   text, status and placement. The workflow only permits the repository
   owner to dispatch it (including reruns).
3. The workflow fetches the registered source, verifies its normalized
   fingerprint and each evidence locator, checks current-record digests,
   applies selected decisions in a disposable trusted master checkout,
   regenerates BEST_PRACTICES.md, and runs the full Python and web tests.
4. If successful, it appends one commit to the **same** candidate branch,
   preserving the candidate JSON and adding an adoption receipt plus the
   actual registry diff. Inspect that diff, mark ready and merge normally
   if accepted. No write to master is performed by this workflow.
   A GITHUB_TOKEN-generated commit may suppress push workflows or leave a
   PR workflow awaiting approval; this workflow runs the tests before updating
   the branch. Existing GitHub rules still apply.

Example decision for a verified runtime configuration recommendation:
```json
[
  {"index":1,"status":"recommended","placement":"configuration","configuration_kind":"api-or-runtime"}
]
```

This is an example only, not approval of an existing PR. For two selected
items provide two objects. Unselected indices are recorded as unselected,
not silently accepted. If the source changes, the old evidence cannot be
verified, the current practice was modified, the PR has extra changes,
or master/PR HEAD advances during execution, the workflow stops without
updating the branch. Do not reset the maintenance ledger to retry.

## Decision rules

- For recommended/conditional, explicitly select configuration
  (configuration_kind: api-or-runtime, permissions or integration),
  author-guidance, or instruction. For instruction supply explicit
  owner-reviewed bilingual single-line instruction text:
  {"index":1,"status":"recommended","placement":"instruction","instruction":{"en":"...","ja":"..."}}.
  Reasoning, tools, integration and migration categories cannot enter
  standing instructions.
- For candidate, discouraged, unverified, deprecated or superseded,
  use placement none. Retirement actions must retain their corresponding
  retired status; other actions cannot select retirement statuses.
- New IDs are deterministic and collision-free against the current
  registry; exact duplicate text for the same target is rejected.
- Add/amend use the candidate's exact bilingual text, scope and evidence.
  Changed guidance resets local_eval to not_verified, never inherits a
  prior performance claim. Retirement preserves existing text/evidence
  and records the new status; its reason and evidence remain in the
  candidate and receipt.
- Replacing an existing practice removes its stale Generator placement
  and replaces it only with the explicitly approved one. It also detaches
  that practice from lexical Auditor rule evidence, rather than silently
  retaining a now-unverified rule mapping. This does not change the
  Auditor rule itself. Reattach separately only if justified.
- The inspected source's checked date and changed practice reviewed date
  use the UTC adoption-preparation date. No local benchmark is inferred.

The receipt under adoptions/<proposal-identity>.json contains the selected
indices/assigned IDs, decisions, approved HEAD, master base, source and
proposal identity/digest. Its state OWNER_SELECTED_PENDING_MERGE describes
the action that created the commit, not a live merge-status field. A
successful manual merge publishes canonical registry data through the
existing Pages workflow. Merging an untouched candidate PR remains a
record-only operation, not adoption.

## Boundaries

Literal source verification is not proof of semantic correctness. Owner
review is necessary, especially for configuration values, retirement
and exact model scope. No discovery candidate is automatically registered.
This phase does not change the maintenance ledger, quotas, source discovery,
API contracts or repository settings. Strict source identity may block
adoption for dynamically changing pages; inspect/recreate a fresh proposal
rather than bypassing the check. Unsupported manual edits remain possible
through the ordinary owner-approved Git workflow.
