# Best practices / ベストプラクティス

Generated from registry/*.json. Provider guidance is not local benchmark evidence.
公式資料に基づく整理。ローカル実測による裏付けは未実施。

## Shared conventions (common)

### BP-001 — recommended

Put project-specific setup, test commands and conventions in a predictable agent instruction file.

プロジェクト固有のセットアップ・テスト・規約を、予測可能な指示ファイルに記載する。

Scope: Format guidance; not a guarantee of every harness's loading behavior.

Evidence: [agents-md](https://agents.md/)

Local evaluation: not_verified

### BP-002 — recommended

Keep detailed reusable procedures in skills and load their references as needed.

再利用する詳細手順はSkillsに分離し、必要時に参照する。

Scope: Applies to skills-compatible harnesses.

Evidence: [agent-skills](https://agentskills.io/specification)

Local evaluation: not_verified

Monitored sources: [agents-md](https://agents.md/), [agent-skills](https://agentskills.io/specification), [mcp](https://blog.modelcontextprotocol.io/posts/2026-07-28/), [superpowers](https://github.com/obra/superpowers/releases)

## Codex (harness)

### BP-003 — conditional

Use a short AGENTS.md as a map to deeper repository knowledge rather than a comprehensive manual.

AGENTS.mdを巨大な説明書ではなく、詳細なリポジトリ知識への索引として使う。

Scope: OpenAI engineering case study; not a universal line limit.

Evidence: [codex-harness](https://openai.com/index/harness-engineering/)

Local evaluation: not_verified

### BP-004 — recommended

Account for directory scope and override files when configuring Codex instructions.

Codexの指示設定ではディレクトリの適用範囲とoverrideファイルを考慮する。

Scope: Codex-specific loading rules.

Evidence: [codex-instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

Local evaluation: not_verified

### BP-018 — conditional

Use a concise navigation map to repository knowledge and load details when the task requires them; the case study is not a mandated line count.

AGENTS.mdはリポジトリ知識への短い案内とし、詳細は必要に応じて読む。行数の一律制限ではない。

Scope: OpenAI harness-engineering case study; implementation pattern, not a format requirement.

Evidence: [codex-harness](https://openai.com/index/harness-engineering/)

Local evaluation: not_verified

Monitored sources: [codex-instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [codex-harness](https://openai.com/index/harness-engineering/), [codex-prompting](https://developers.openai.com/cookbook/examples/gpt-5/codex_prompting_guide)

## Claude Code (harness)

### BP-006 — recommended

Keep persistent instructions concise and scope rules to the relevant part of the codebase.

常時指示を簡潔に保ち、ルールを対象コードの範囲に限定する。

Scope: Claude Code guidance.

Evidence: [claude-code-practices](https://code.claude.com/docs/en/best-practices), [claude-code-memory](https://code.claude.com/docs/en/memory)

Local evaluation: not_verified

### BP-007 — recommended

Provide a concrete check; use deterministic controls for rules that cannot have exceptions.

具体的な検証方法を示し、例外を許さないルールは決定的な制御で強制する。

Scope: A check is not equivalent to an authorization gate.

Evidence: [claude-code-practices](https://code.claude.com/docs/en/best-practices)

Local evaluation: not_verified

Monitored sources: [claude-code-practices](https://code.claude.com/docs/en/best-practices), [claude-code-memory](https://code.claude.com/docs/en/memory)

## OpenCode (harness)

### BP-009 — recommended

Use AGENTS.md and configured instruction sources according to OpenCode's documented loading rules.

OpenCodeの読み込み仕様に従いAGENTS.mdと設定された指示源を使う。

Scope: Harness-specific; verify installed version.

Evidence: [opencode-instructions](https://opencode.ai/docs/instructions/)

Local evaluation: not_verified

### BP-047 — recommended

Avoid assuming configured instructions override AGENTS.md; initial sources are combined and nested instructions are discovered during exploration.

設定した指示がAGENTS.mdを上書きすると仮定しない。初期指示は結合され、下位指示は探索時に発見される。

Scope: Current OpenCode docs; check installed release.

Evidence: [opencode-instructions](https://opencode.ai/docs/instructions/)

Local evaluation: not_verified

### BP-048 — conditional

Start a new session if an already-discovered nested AGENTS.md must take effect immediately after editing.

読み込み済みの下位AGENTS.mdを編集し、即時反映が必須なら新規セッションを開始する。

Scope: Nested-file behavior differs from global/upward instruction refresh.

Evidence: [opencode-instructions](https://opencode.ai/docs/instructions/)

Local evaluation: not_verified

### BP-049 — recommended

Use policy denies for hard boundaries; a policy allow only lifts a prior deny and does not grant permission beyond the agent's own rules.

強制境界にはpolicy denyを利用する。policy allowは先行denyの解除に留まり、エージェント自身の権限を超えて許可しない。

Scope: Current OpenCode policy semantics; do not substitute prompts for enforcement.

Evidence: [opencode-policies](https://opencode.ai/docs/policies/)

Local evaluation: not_verified

### BP-050 — recommended

Place reusable task instructions in SKILL.md with a description of triggering conditions and verify skill permission settings.

再利用する手順をSKILL.mdへ置き、適用条件をdescriptionで示し、skill権限設定を確認する。

Scope: OpenCode skill discovery; actual paths and autoinvoke depend on configuration.

Evidence: [opencode-skills](https://opencode.ai/docs/skills/)

Local evaluation: not_verified

Monitored sources: [opencode-instructions](https://opencode.ai/docs/instructions/), [opencode-models](https://opencode.ai/docs/models/), [opencode-policies](https://opencode.ai/docs/policies/), [opencode-skills](https://opencode.ai/docs/skills/)

## Gemini CLI (harness)

### BP-010 — recommended

Use scoped GEMINI.md files and account for contextual discovery.

GEMINI.mdの適用範囲とコンテキストに応じた探索を考慮する。

Scope: Gemini CLI only.

Evidence: [gemini-cli-context](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/gemini-md.md)

Local evaluation: not_verified

Monitored sources: [gemini-cli-context](https://raw.githubusercontent.com/google-gemini/gemini-cli/main/docs/cli/gemini-md.md)

## Cursor (harness)

### BP-012 — recommended

Use scoped project rules when instructions only apply to certain files.

特定ファイルだけに適用する指示は範囲指定されたプロジェクトルールに置く。

Scope: Cursor rules; check active product version.

Evidence: [cursor-rules](https://prod.cursor.com/docs/rules)

Local evaluation: not_verified

Monitored sources: [cursor-rules](https://prod.cursor.com/docs/rules), [cursor-agent-guide](https://cursor.com/blog/agent-best-practices)

## GitHub Copilot (harness)

### BP-013 — conditional

Choose custom instruction types supported by the Copilot surface in use.

利用するCopilot機能が対応する指示ファイル形式を選択する。

Scope: Support differs across surfaces.

Evidence: [copilot-instructions](https://docs.github.com/en/copilot/reference/custom-instructions-support)

Local evaluation: not_verified

Monitored sources: [copilot-instructions](https://docs.github.com/en/copilot/reference/custom-instructions-support)

## GPT-6 Astra (model)

### BP-005 — recommended

Reassess accumulated prompts and skills for this model; remove redundant constraints when evaluations support it.

このモデルへの移行時に既存指示を見直し、評価で不要と判断できる制約を削除する。

Scope: Specific to the cited model guidance; do not remove security boundaries.

Evidence: [astra-prompting](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)

Local evaluation: not_verified

### BP-019 — conditional

Reconsider instructions that force a file reread before every edit when the necessary context is already present.

編集前のファイル再読込を常に強制する指示は、必要な情報が既にある場合に見直す。

Scope: GPT-6 Astra; preserve necessary freshness and safety checks.

Evidence: [astra-prompting](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)

Local evaluation: not_verified

Monitored sources: [astra-prompting](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra)

## Claude (family)

### BP-008 — recommended

Use clear explicit instructions and evaluate model-specific behavior rather than assuming identical behavior across versions.

明確な指示を使い、世代間で同じ動作を仮定せずモデル別に評価する。

Scope: Family-level guidance; model-specific exceptions need separate records.

Evidence: [claude-prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

Local evaluation: not_verified

Monitored sources: [claude-prompting](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

## Gemini (family)

### BP-011 — recommended

Start with clear specific instructions and refine prompts against observed responses.

明確で具体的な指示から始め、応答の実測で改善する。

Scope: General Gemini prompt guidance.

Evidence: [gemini-prompting](https://aistudio.google.com/docs/prompting-strategies)

Local evaluation: not_verified

Monitored sources: [gemini-prompting](https://aistudio.google.com/docs/prompting-strategies)

## Kimi (family)

No verified recommendation yet; source discovery only. / 推奨事項は未登録。

Monitored sources: [moonshot-discovery](https://github.com/MoonshotAI)

## Kimi K2.5 (model)

### BP-014 — conditional

Consider the provider's recommended Kimi Code CLI for this particular model.

このモデルについて提供元が推奨するKimi Code CLIを選択肢にする。

Scope: Provider recommendation, not independent comparative evidence. Historical model-card guidance; availability not asserted.

Evidence: [kimi-k25-card](https://raw.githubusercontent.com/MoonshotAI/Kimi-K2.5/master/README.md)

Local evaluation: not_verified

Monitored sources: [kimi-k25-card](https://raw.githubusercontent.com/MoonshotAI/Kimi-K2.5/master/README.md)

## GLM (family)

No verified recommendation yet; source discovery only. / 推奨事項は未登録。

Monitored sources: [zai-docs](https://docs.z.ai/llms.txt)

## GLM 5.3 / 5.3 Flash (model)

### BP-015 — conditional

Use the documented reasoning_effort parameter for GLM-5.3 and GLM-5.3-Flash on compatible endpoints.

対応するAPIではGLM-5.3/Flashのreasoning_effort設定を利用する。

Scope: Provider API capability, not evidence of the optimal effort.

Evidence: [glm5-card](https://github.com/zai-org/GLM-5)

Local evaluation: not_verified

### BP-042 — conditional

Set low or high explicitly when evaluating cost-sensitive work; the documented default is max, also used for benchmark reproduction.

費用を抑える評価ではlow/highを明示する。モデルカード上の既定値maxはベンチマーク再現にも使われる。

Scope: GLM-5.3 and 5.3 Flash; provider support required.

Evidence: [glm5-card](https://github.com/zai-org/GLM-5)

Local evaluation: not_verified

Monitored sources: [glm5-card](https://github.com/zai-org/GLM-5)

## DeepSeek (family)

### BP-016 — conditional

Follow the documented reasoning_content handling for tool-call continuations in thinking mode.

Thinking modeのツール呼び出し継続時はreasoning_contentの扱いを公式仕様に従う。

Scope: API integration only; not an AGENTS.md rule.

Evidence: [deepseek-thinking](https://api-docs.deepseek.com/guides/thinking_mode/)

Local evaluation: not_verified

Monitored sources: [deepseek-thinking](https://api-docs.deepseek.com/guides/thinking_mode/)

## Qwen (family)

### BP-017 — conditional

Use the supported thinking-mode control for the relevant model and chat template.

対象モデルとチャットテンプレートに対応するthinking mode制御を使用する。

Scope: Do not generalize to all Qwen variants.

Evidence: [qwen-quickstart](https://qwen.readthedocs.io/en/stable/getting_started/quickstart.html)

Local evaluation: not_verified

Monitored sources: [qwen-quickstart](https://qwen.readthedocs.io/en/stable/getting_started/quickstart.html), [qwen-tools](https://qwen.readthedocs.io/en/stable/framework/function_call.html)

## GPT-6.2 Astra (model)

### BP-020 — recommended

State the deliverable, permitted autonomous steps and decisions reserved for the user; allow reversible assumptions within scope.

成果物・自律実行可能な範囲・ユーザー判断事項を明示し、範囲内の可逆な仮定を許容する。

Scope: Task completion guidance for GPT-6.2; does not confer authorization.

Evidence: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

Local evaluation: not_verified

### BP-021 — recommended

Specify project conventions, compatibility expectations and checks that demonstrate the requested behavior.

プロジェクト規約、互換性の要求、依頼された挙動を実証する検証方法を明示する。

Scope: Coding guidance; avoid unsupported completion claims.

Evidence: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

Local evaluation: not_verified

### BP-022 — conditional

Begin a new API integration at medium reasoning effort and evaluate higher effort for complex work.

新規API統合ではmediumを起点に、複雑な作業では高い推論設定の効果を測る。

Scope: API default starting point, not a Codex UI guarantee.

Evidence: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

Local evaluation: not_verified

Monitored sources: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

## GPT-6.2 Sol (model)

### BP-023 — recommended

Define the outcome and which decisions require user involvement rather than requiring a checkpoint for every routine operation.

通常操作ごとの承認ではなく、目的とユーザー判断が必要な事項を定義する。

Scope: Guide explicitly covers GPT-6.2 Astra and Sol; retain genuine approval gates.

Evidence: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

Local evaluation: not_verified

### BP-024 — conditional

Use medium reasoning effort as an initial API configuration and tune against task outcomes.

APIではmediumを初期設定とし、実際のタスク成果で調整する。

Scope: API integration only; effort labels are not interchangeable with other vendors.

Evidence: [gpt62-guide](https://developers.openai.com/api/docs/guides/latest-model)

Local evaluation: not_verified

Monitored sources: 

## Claude Opus 5.5 (model)

### BP-025 — conditional

Start effort calibration at medium, explicitly set the level, and reserve xhigh or max for measured benefit.

mediumを明示的な起点にして推論量を評価し、xhigh/maxは品質向上が実測できる場合に選ぶ。

Scope: Claude Opus 5.5 API; not the Opus 5 default.

Evidence: [opus55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

Local evaluation: not_verified

### BP-026 — recommended

Recalibrate effort instead of carrying forward the value selected for Opus 5; adjust effort before adding prompts to reduce thinking.

Opus 5のeffort設定をそのまま移植せず再評価する。思考量を抑える際は指示追加よりeffort調整を優先する。

Scope: Applies to supported effort configuration; local eval required.

Evidence: [opus55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

Local evaluation: not_verified

Monitored sources: [opus55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5)

## Claude Sonnet 5.5 (model)

### BP-027 — conditional

For well-defined agentic coding start at medium; try high for harder or longer tasks, then evaluate cost and quality.

明確なエージェント実装タスクはmediumから、難しい・長いタスクはhighを試し費用と品質を評価する。

Scope: Provider starting points for coding, not universal optimal settings.

Evidence: [sonnet55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)

Local evaluation: not_verified

### BP-028 — conditional

If low or medium effort causes premature check-ins, evaluate higher effort or clarify the expected completion boundary; constrain scope at higher effort.

low/mediumで途中確認が増える場合はeffort引上げ又は完了境界の明確化を試す。高effortでは作業範囲の逸脱を防ぐ。

Scope: Behavior-dependent; risky operations still require approval.

Evidence: [sonnet55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)

Local evaluation: not_verified

### BP-029 — recommended

Require a real executable check of changed behavior; a syntax check alone or a command that never started is not equivalent evidence.

変更挙動を実際に通す検証を求める。構文確認だけや起動不能のコマンドは同等の証拠としない。

Scope: Report blocked checks; no unapproved environment changes.

Evidence: [sonnet55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)

Local evaluation: not_verified

Monitored sources: [sonnet55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5)

## Claude Haiku 5.5 (model)

### BP-030 — conditional

Replace obsolete budget_tokens settings when migrating from Haiku 4.5 and compare supported effort levels.

Haiku 4.5から移行する際は旧budget_tokens設定を除き、対応するeffortを比較評価する。

Scope: Claude Haiku 5.5 API; budget_tokens requests can fail.

Evidence: [haiku55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)

Local evaluation: not_verified

### BP-031 — recommended

Explicitly require an executable check before reporting coding changes complete, especially if the model tends to skip verification.

コード変更の完了報告前に実行可能な検証を明示し、検証省略が観測される場合に重点的に適用する。

Scope: Model-specific coding guidance; no mandatory independent review implied.

Evidence: [haiku55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)

Local evaluation: not_verified

Monitored sources: [haiku55-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-haiku-5-5)

## Claude Fable 5.2 (model)

### BP-032 — conditional

Start with high effort and retune against representative tasks instead of copying the previous model's level.

highを起点に代表タスクで調整し、旧モデルのeffortをそのまま流用しない。

Scope: Claude Fable 5.2 API starting point.

Evidence: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

Local evaluation: not_verified

### BP-033 — recommended

Name routine steps that need no additional approval, narrow obsolete stopping conditions, and retain confirmation for risky or irreversible actions.

追加承認不要な通常手順を明示し、不要な停止条件を限定する。危険・不可逆な操作の承認は維持する。

Scope: Only within existing authorization; does not relax policy.

Evidence: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

Local evaluation: not_verified

### BP-034 — conditional

If delegation exceeds task needs, first revisit standing instructions in agent files and skills; remove unnecessary delegation requirements after evaluation.

委譲が過剰な場合はAGENTS.mdやSkills等の常設委譲指示を見直し、評価で不要と判断した指示を除く。

Scope: Behavior-dependent; independent review remains appropriate where justified.

Evidence: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

Local evaluation: not_verified

### BP-035 — conditional

Use append-only conversation history outside supported context editing or compaction; rewriting earlier messages can invalidate preserved thinking blocks.

対応するコンテキスト編集・圧縮を除き会話履歴を追記型に保つ。過去メッセージの書換えは保存済みthinking blockを無効化し得る。

Scope: API harness integration only, not repository instructions.

Evidence: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

Local evaluation: not_verified

Monitored sources: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

## Claude Mythos 5.2 (model)

### BP-036 — conditional

Consult the shared Fable 5.2/Mythos 5.2 prompting guide when migrating and validate model-specific behavior against your own tasks.

移行時にはFable 5.2/Mythos 5.2共通の公式プロンプトガイドを参照し、対象モデルで挙動を検証する。

Scope: Guide covers both models; no claim of general access or identical behavior.

Evidence: [fable52-guide](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-2)

Local evaluation: not_verified

Monitored sources: 

## Kimi K2.7 Code (model)

### BP-037 — conditional

Treat thinking and preserved thinking as enabled in the provider's documented K2.7 Code API; do not assume instant mode is available.

K2.7 Code公式APIではthinkingとpreserved thinkingが有効という仕様に従い、instant modeの利用を前提にしない。

Scope: Official model card; third-party endpoints and lifecycle may differ.

Evidence: [kimi-k27-card](https://huggingface.co/moonshotai/Kimi-K2.7-Code)

Local evaluation: not_verified

### BP-038 — conditional

For compatible self-hosted vLLM/SGLang deployments use the provider's generation recommendations as an evaluation baseline, temperature 1.0 and top_p 0.95.

対応するvLLM/SGLang環境では提供元推奨のtemperature 1.0、top_p 0.95を評価の起点にする。

Scope: Self-hosted inference settings, not an AGENTS.md rule or universal API setting.

Evidence: [kimi-k27-card](https://huggingface.co/moonshotai/Kimi-K2.7-Code)

Local evaluation: not_verified

Monitored sources: [kimi-k27-card](https://huggingface.co/moonshotai/Kimi-K2.7-Code)

## Kimi K2.8 Preview (research target) (model)

No verified recommendation yet; source discovery only. / 推奨事項は未登録。

Monitored sources: 

## Kimi K3 (model)

### BP-039 — conditional

Configure reasoning_effort with the supported low, high or max values; the model card documents max as default and thinking as always enabled.

reasoning_effortはlow/high/maxの対応値で設定する。モデルカードではmaxが既定でthinkingは常時有効。

Scope: Official Kimi K3 interface; validate provider adapter compatibility.

Evidence: [kimi-k3-card](https://github.com/MoonshotAI/Kimi-K3)

Local evaluation: not_verified

### BP-040 — recommended

Preserve complete assistant messages across model turns and tool continuations, including reasoning_content and tool_calls.

複数ターン・ツール継続時にreasoning_contentとtool_callsを含むassistant messageを保持する。

Scope: API integration requirement; do not expose or publicly log reasoning.

Evidence: [kimi-k3-card](https://github.com/MoonshotAI/Kimi-K3)

Local evaluation: not_verified

Monitored sources: [kimi-k3-card](https://github.com/MoonshotAI/Kimi-K3)

## GLM 5.2 (model)

### BP-041 — conditional

Use the documented high or max reasoning_effort options; do not assume GLM-5.3's low setting exists in GLM-5.2.

GLM-5.2ではhigh/maxの公式対応値を利用し、GLM-5.3のlowが使えると仮定しない。

Scope: Model card; max is the documented default.

Evidence: [glm5-card](https://github.com/zai-org/GLM-5)

Local evaluation: not_verified

Monitored sources: 

## DeepSeek V4 Pro (model)

### BP-043 — conditional

Do not tune thinking behavior via temperature or penalties; in thinking mode top_p is fixed according to tool availability.

thinking時にtemperatureやpenaltyで推論を調整しない。top_pはツール利用可否に応じて固定される。

Scope: Current DeepSeek V4 Pro API, not third-party inference servers.

Evidence: [deepseek-thinking](https://api-docs.deepseek.com/guides/thinking_mode/)

Local evaluation: not_verified

Monitored sources: 

## DeepSeek Flash (API identifier) (model)

### BP-044 — conditional

Use documented thinking and effort controls; in thinking mode top_p below 0.95 is clamped to 0.95.

公式thinking/effort制御を使用する。thinking時のtop_pは0.95未満が0.95に補正される。

Scope: Current deepseek-flash API identifier; do not infer alias equivalence or lifecycle.

Evidence: [deepseek-thinking](https://api-docs.deepseek.com/guides/thinking_mode/)

Local evaluation: not_verified

Monitored sources: 

## Gemini 3 series (family)

### BP-045 — recommended

Put key behavioral constraints first, use consistent delimiters, and place specific questions after large context blocks.

重要な行動制約は先に置き、区切り形式を統一し、大量の文脈の後に具体的な質問を配置する。

Scope: Gemini 3 prompting guidance; distinguish task data from instructions.

Evidence: [gemini-prompting](https://aistudio.google.com/docs/prompting-strategies)

Local evaluation: not_verified

### BP-046 — conditional

For Gemini 3.6 and later remove custom temperature, top_p and top_k from requests; earlier Gemini 3 models should use defaults.

Gemini 3.6以降ではtemperature/top_p/top_kの独自指定を除く。以前のGemini 3では既定値を使用する。

Scope: Version-specific Gemini API parameter guidance, not an instruction-file rule.

Evidence: [gemini-prompting](https://aistudio.google.com/docs/prompting-strategies)

Local evaluation: not_verified

Monitored sources: 

## Superpowers (workflow framework) (common)

### BP-051 — conditional

Use the upstream workflow of design agreement, implementation planning and test-driven execution when that methodology is adopted.

Superpowersを採用する場合は設計合意、実装計画、TDDによる実行という上流の方法論を利用する。

Scope: Framework-specific; not a universal rule or authorization for repeated review cycles.

Evidence: [superpowers-guide](https://github.com/obra/superpowers)

Local evaluation: not_verified

### BP-052 — conditional

Use the framework's composable skills rather than reproducing the complete workflow in every persistent instruction file.

フレームワークの組み合わせ可能なSkillsを利用し、全手順を常設指示へ複製しない。

Scope: Agent Compass synthesis of upstream methodology and skill specification; not verbatim vendor requirement.

Evidence: [superpowers-guide](https://github.com/obra/superpowers), [agent-skills](https://agentskills.io/specification)

Local evaluation: not_verified

Monitored sources: [superpowers-guide](https://github.com/obra/superpowers)

