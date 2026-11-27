# Agent-ready interface / AIエージェント向け公開形式

Base URL: https://yohi.github.io/agent-compass/

All exports are built from the same validated registry snapshot as the portal.
No JavaScript, credentials, server or LLM API is needed to retrieve them.
They are static files, not search/execute RPC endpoints.

| Path | Purpose |
| --- | --- |
| llms.txt / llms.ja.txt | Compact entry index (English/Japanese links) |
| llms-full.txt / llms-full.ja.txt | All registered practices by target |
| knowledge/common.md | Common guidance |
| knowledge/harnesses/opencode.md | Exact harness |
| knowledge/models/kimi-k3.md | Exact model |
| knowledge/families/kimi.md | Explicit family, no implicit inheritance |
| knowledge/frameworks/superpowers.md | Opted-in framework |
| api/v1/manifest.json | Schema version, base URL, target index, counts and exported file digests |
| api/v1/targets.json | All target IDs and exact paths |
| api/v1/targets/<id>.json | Scoped practices, placements and evidence |
| api/v1/models.json, families.json, harnesses.json, frameworks.json | Target subsets |
| api/v1/practices.json, sources.json | Canonical curated records |
| api/v1/generator.json | Exact profile to existing generated bundle path and digest |
| skills/agent-compass/SKILL.md | Optional portable Agent Skill |

Japanese scoped pages end in .ja.md. All paths in JSON resolve against the
public base URL, not the containing JSON directory. A target with no practices
still has explicit empty pages and JSON; unknown IDs are not silently mapped
to a sibling or family. The full index may be larger than necessary; prefer
scoped pages. Each record retains original status, scope, reviewed date,
local evaluation, evidence IDs/URLs and placement. English scope text is
preserved as curated even on Japanese pages.

API v1 is a static, versioned schema with a registry snapshot digest; clients
should reject unknown schema versions and retry if snapshot IDs or byte
digests mismatch during publication. The manifest's files map excludes the
manifest itself; generator bundle digests are in generator.json. No live
monitor state, private inputs, secrets or raw third-party documents are
exported. Source change discovery does not itself adopt recommendations.
Only canonical registry changes, after Owner-selected or policy-bounded
adoption and publication, appear in these exports. A published recommendation
does not imply local evaluation or permission to apply it.

## Skill

Use the repository's skills/agent-compass directory (SKILL.md plus references)
with the chosen harness's supported skill installation mechanism, only when
authorized. APM supports the manifestless single-skill subdirectory; see [APM distribution](APM.md). The same files are published to Pages for direct reading.
No automatic installation, global AGENTS.md edit or remote script execution.
The skill tells agents to retrieve scoped guidance at task time, verify its
scope and evidence, preserve existing project constraints and stop after the
requested work. It does not grant access or change the user's model/runtime.

## Example

For OpenCode + Kimi K3 + Superpowers, retrieve the manifest and four exact
Markdown pages. For a draft, look up opencode|kimi-k3|superpowers|ja in
api/v1/generator.json and retrieve the indicated bundle. A local checkout
can use the existing CLI without network access.

日本語: AIエージェントはHTMLを解析せずMarkdown/JSONを直接取得できる。
対象の完全一致と根拠・状態を確認し、既存の制約を尊重する。
公式情報の定期監視と採択済みナレッジの更新は別の状態である。
