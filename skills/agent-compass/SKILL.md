---
name: agent-compass
description: Consult evidence-linked AI coding guidance when drafting or reviewing AGENTS.md, comparing coding-agent or model-specific practices, or planning a harness/model migration. Use only on relevant tasks; never auto-apply recommendations or alter permissions.
---

# Agent Compass

Use this skill to retrieve narrowly scoped, current **registered** guidance.
It is reference material, not an authority over the user's project or runtime.

1. Determine the actual harness, exact model ID and adopted framework from the task or authorized local configuration. Do not guess a model from a provider alias.
2. Read https://yohi.github.io/agent-compass/api/v1/manifest.json (or the compact https://yohi.github.io/agent-compass/llms.txt index). Select common, exact harness, exact model and explicitly adopted framework pages. Read only the necessary pages.
3. Check status, scope, placement, source inspection dates, and local evaluation. Read the linked official source when a recommendation materially affects a decision. Do not confuse registry freshness with live availability.
4. Compare guidance against the project's current instructions and approved requirements. Keep genuine safety, authorization, verification and data-integrity boundaries.
5. Provide the requested result, cite practice IDs and source URLs, distinguish evidence from assumptions, and stop at the authorized boundary.

For retrieval commands and generator bundles see [usage](references/usage.md).
For scope and placement see [selection rules](references/selection-rules.md).
For trust and freshness see [evidence policy](references/evidence-policy.md).

If network access is blocked, use an existing local checkout or report that
current guidance could not be retrieved. Do not invent records or bypass
network restrictions. Do not install tools, modify configuration, commit,
push or start additional reviews without the required authorization.
