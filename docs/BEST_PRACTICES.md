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

Monitored sources: [opencode-instructions](https://opencode.ai/docs/instructions/), [opencode-models](https://opencode.ai/docs/models/), [opencode-policies](https://opencode.ai/docs/policies/)

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

Scope: Provider recommendation, not independent comparative evidence.

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

