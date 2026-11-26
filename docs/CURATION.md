# Knowledge base curation / ナレッジベース更新

## Scope and workflow

Phase 3 P0 first curated batch, 2026-11-27: 35 monitored sources, 31 targets,
52 practice records. The input is the [discovery archive](https://github.com/yohi/agent-compass/issues/2)
(497 indexed candidate entries; duplicates across indexes are possible) and targeted
official-source checks. The batch prioritizes persistent instructions, model effort,
completion boundaries, verification, tool-state handling, and migration.

1. Examine changed-source notifications and complete candidate archive comments.
2. Select official documentation or upstream model cards relevant to coding agents.
   Do not equate model mentions or navigation links with a new release.
3. Read the actual evidence and record its URL, inspection date, precise target,
   and limits. Separate provider guidance, API requirements and curator synthesis.
4. Add or update a small number of actionable practice records. Use stable IDs.
   Preserve earlier model records unless official evidence warrants a status change.
   For deprecated/superseded practices, explain the reason and replacement in scope.
5. Keep local_eval as not_verified unless a reproducible local evaluation exists.
6. Regenerate docs and run the existing validation suite. Commit only the approved
   batch. No automatic adoption or changes to consuming repositories.

## Practical selection

- Start from common guidance and the chosen harness; add only relevant model-specific
  records. A model family does not imply every model version shares a behavior.
- API integration requirements (effort, sampling parameters, tool continuation)
  belong in the adapter/configuration, not in AGENTS.md.
- Workflow framework advice applies only to projects that adopt that framework.
- Do not expand persistent instructions just to include every recommendation.
- Treat the current source as evidence for the recorded scope, not proof of local
  effectiveness or current service availability.

## Coverage and gaps

| Area | First batch coverage | Remaining uncertainty |
| --- | --- | --- |
| OpenAI | GPT-6 Astra, GPT-6.2 Astra/Sol, Codex | Other GPT variants not exhaustively curated |
| Anthropic | Opus/Sonnet/Haiku 5.5, Fable/Mythos 5.2 | Earlier variants not individually curated |
| Moonshot | K2.5, K2.7 Code, K3 | K2.8 Preview research target; no model-specific practice admitted without direct evidence |
| Z.ai | GLM 5.2, 5.3 and 5.3 Flash | Endpoint and local behavior not tested |
| DeepSeek | V4 Pro and deepseek-flash API identifier | No alias equivalence or service availability assertion |
| Google | Gemini 3 series, Gemini CLI | Other variants not exhaustively curated |
| OpenCode/Superpowers | Current upstream instruction, policy and workflow guidance | Installed versions and framework configuration differ |

This is a prioritized batch, not a review of every archived candidate.
Neither a discovery mention nor an official API specification proves model-specific
AGENTS.md effectiveness. All local evaluations remain not_verified.

## Ongoing operation

Daily monitoring continues on the existing schedule. The discovery and monitor
issues remain machine-maintained state; curator decisions go in the registry
and Git history. Curate when material changes warrant it rather than on each
page-hash change. The source-monitor issue has a 60,000-character guard and
discovery has a bounded identity store; check capacity before expanding large
batches. No state reset or automated write to external projects is authorized.

日本語: 公式根拠を読んだ上で対象モデル・実行基盤・API設定の範囲を限定して登録する。
候補発見・採択・ローカル実測は別の状態として扱う。実測なしに最適性を断定しない。
