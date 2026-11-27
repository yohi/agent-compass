# Change intelligence / 変更分析・新規情報源の発見

Monitor/discovery (introduced in Phase 2): no paid API and no registry adoption by these workflows.

## Daily operation

The existing scheduled workflow runs two independent operations:

- Source monitor: preserve the Phase 1 issue and SHA-256/chunk fingerprints;
  enrich successful observations with per-topic lexical fingerprints.
- Discovery: scan the 10 explicit official indexes in
  [registry/discovery.json](../registry/discovery.json). Extract same-host,
  path-allowlisted relevant links and model-shaped identifiers from normalized
  text. Publish to a separate bot-owned issue with deduplicated identities.
  New candidate links are **never** automatically fetched or registered.

The two processes report errors independently; the workflow fails if either
fails. Source failures preserve the last good state. On Phase 1 migration,
same-content enrichment is not a content change. If content changed before
topic fingerprints existed, classification is unknown.

## Interpreting candidates

A changed page reports topic hints (instructions, prompting, context,
skills/tools, verification, reasoning, security, migration). Matching-line
hashes and counts detect changes to text associated with a topic, not the meaning,
direction or correctness of recommendations. Changes can be missed, and
unrelated changes can be flagged. A missing topic is not evidence of irrelevance.
No third-party document excerpts are persisted.

The source monitor maps changed evidence IDs to current practice IDs and proposes
checking whether to keep, amend, narrow, deprecate or supersede them. It does
not decide that any of these actions is warranted. Unlinked sources can suggest
a new scoped practice candidate. The issue contains links and before/after
fingerprints. Read the actual official source before making any decision.

Discovery initial inventory includes old links and model mentions; later reports
show previously unseen identities, not release dates. A mention does not establish
availability, version, lifecycle, or suitability. A discovery index can omit
documents or dynamically render incomplete content. Non-English or differently
formatted model names can be missed. Index summaries display up to 12 candidates per index/run (model mentions first).
All selected candidates are archived in bounded issue comments before the state
is advanced. Local scans append to the companion JSONL file before updating state.
Retries after interrupted writes can duplicate archive entries; deduplicate using
(index, identity). Phase 2.0 migration re-observes currently available candidates
once without resetting historical identities. Removed or filtered legacy
identities cannot be reconstructed from hashes; their count is explicitly reported.
They remain pending and will be archived if rediscovered under the current filters.
GitHub organization indexes exclude repository navigation subpaths.
Google uses the official AI Studio llms.txt index directly.
Fetch diagnostics use fixed reason codes, not arbitrary exception text.
Seen identities (96-bit truncated SHA-256) are retained across runs;
a removed/reappearing candidate is not new. Total capacity is 1500; exceeding
capacity fails before state replacement. Both state issues are operational
metadata; do not edit or delete their markers. If capacity is reached, explicitly
migrate the state representation rather than silently discarding history.

## Adoption (separate workflow)

Read source, verify publisher, target version and applicable scope. If useful,
edit the canonical JSON records, regenerate docs, validate, and commit via
the normal approved workflow. No LLM-generated recommendations, automatic
commits, PR creation or new model registration occur during monitoring.
Separate maintenance can generate candidate PRs; the explicit
[controlled-adoption policy](AUTO_ADOPTION.md) can adopt eligible new guidance.
Discovery registration itself remains Owner-selected.

日本語要約: 公式索引のリンク・モデル名候補を検出し、既存推奨事項の根拠変更を
分類する。単語に基づく推定であり、意味的な変更や廃止を確定するものではない。
初回発見は新規公開を意味しない。監視処理は採択を行わない。
採択はOwnerの判断、または明示的に許可された限定自動採択ポリシーに従う。
