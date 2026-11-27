# Agent Compass

Living, evidence-linked guidance for AI coding agents and LLMs.
AIコーディングエージェント・LLMの公式指針を継続的に収集し、対象別に整理・検証・公開するナレッジ基盤。

**[Open the public portal](https://yohi.github.io/agent-compass/)** ·
[日本語ナレッジ索引](https://yohi.github.io/agent-compass/llms.ja.txt) ·
[API manifest](https://yohi.github.io/agent-compass/api/v1/manifest.json) ·
[Changelog](CHANGELOG.md)

## What it does / 機能

| Capability | Purpose |
| --- | --- |
| Knowledge registry | Bilingual, scoped guidance with official source links, status, placement and local-evaluation metadata |
| Monitor / discovery | Detect source fingerprint changes and previously unseen official links/model identifiers |
| Generator | Draft AGENTS.md, separate configuration advice and evidence for an explicit harness/model/framework |
| Auditor | Read-only lexical review candidates; CLI and browser-local lightweight versions |
| Agent interface | Static Markdown, llms.txt, JSON API v1 and portable APM-compatible Skill |
| Knowledge maintenance | Optional free-tier Gemini classification/analysis and candidate-only draft PRs |
| Independent advisory | Separate non-Gemini model judgment with exact evidence/HEAD validation |
| Controlled auto adoption | Owner-opt-in policy-bounded preparation, validation, merge and Pages publication |

The registry snapshot after the first live auto-adoption (2026-11-27, commit
[fd9c0a4](https://github.com/yohi/agent-compass/commit/fd9c0a407d83ac2021007ca839f088dfac799b67))
contains 35 registered sources, 31 targets and 54 practices. These are snapshot
counts, not a completeness or latest-model claim. See the live manifest for
current counts. All local evaluation states in this snapshot remain not_verified.

## For users and AI agents / 利用方法

Use the portal to search and compare guidance, generate draft bundles or run
Auditor Lite locally in the browser. For automated retrieval, use:

- [llms.txt](https://yohi.github.io/agent-compass/llms.txt) / [日本語](https://yohi.github.io/agent-compass/llms.ja.txt)
- [API manifest](https://yohi.github.io/agent-compass/api/v1/manifest.json) and [scoped API example](https://yohi.github.io/agent-compass/api/v1/targets/opencode.json)
- [Portable Agent Skill](skills/agent-compass/SKILL.md)

Select common guidance, the exact harness/model and an explicitly adopted
framework; family guidance is a separate explicit choice. Never infer
compatibility, service availability or local effectiveness. Preserve existing
project instructions and permission boundaries. Registry adoption is not
authorization to install instructions or execute configuration in a consumer project.

### APM

From an authorized consumer project:

~~~sh
apm install yohi/agent-compass/skills/agent-compass --target opencode
~~~

Use the appropriate supported harness target and pin a reviewed commit for
reproducibility. Retain the consumer lockfile. The skill retrieves scoped
current guidance when used. See [APM distribution](docs/APM.md).

### CLI

Python 3.11+; core CLI/build commands require no third-party runtime packages,
LLM API keys or paid services. Web tests additionally use Node.js.

~~~sh
python compass.py validate
python compass.py render --check
python -m unittest discover -s tests -v
python compass.py show --target gpt-6-astra
python compass.py generate --harness opencode --model kimi-k3 --framework superpowers --output-dir ./compass-draft
python compass.py audit ./AGENTS.md --harness opencode --model kimi-k3
python compass.py monitor --state .local-state.json --output .local-report.json
python discovery.py --state .local-discovery.json
# Optional developer tools:
uv run --extra dev pytest
uv run --extra dev ruff check .
~~~

Generate into a new directory. The generator never installs or overwrites
existing AGENTS.md files; the auditor never edits input and does not issue
semantic compliance or safety verdicts.

## Knowledge lifecycle / 更新・採択・公開

~~~mermaid
flowchart TD
    S[Registered official sources] --> M[Monitor and discovery]
    M --> I[Change and discovery issues]
    I --> R[Owner-selected source registration]
    R --> S
    S --> G[Gemini maintenance]
    G --> P[Candidate-only draft PR]
    P --> A[Independent advisory]
    A --> D{Owner or bounded policy}
    D -->|Manual / outside policy| H[Owner-selected adoption]
    D -->|Eligible assisted / conservative| V[Controlled adoption preparation]
    V --> C[Trusted CI]
    C -->|Conservative and merge conditions met| X[GitHub merge]
    C -->|Assisted or blocked| W[Owner disposition]
    H --> W
    W -->|Accepted and merged| X
    X --> B[Pages build and deploy]
    B --> Q[HTTP and digest verification]
~~~

Source monitoring is not semantic change detection. The first successful fetch
establishes a baseline; failures retain the last successful observation.
Discovery links/model mentions are candidates, not verified releases.
Maintenance proposes only unadopted data records; merging such a record
alone does not change canonical practices. Advisory comments are suggestions,
not proof of semantic correctness.

The separate controlled-adoption workflow defaults to manual. The Owner may
explicitly enable assisted or conservative modes. Conservative mode permits
only narrow additive model/family guidance with complete source context and
all-item ADOPT advice, within the policy in
[registry/adoption-policy.json](registry/adoption-policy.json).
Existing-record edits, standing instructions, security/permission changes,
retirements, source/model registration and partial/rejected/deferred advice
remain outside automatic adoption. No paid fallback, candidate code execution,
rule bypass, automatic PR approval or writes to consuming repositories.

## Repository owner setup / 運用設定

Consumer use needs none of the following credentials. To run automated
maintenance in this repository, configure GitHub Settings → Secrets and
variables → Actions. Keep keys in Secrets, never in PRs or logs.

| Secret | Enablement variable (exactly true) |
| --- | --- |
| GEMINI_API_KEY | GEMINI_FREE_TIER_CONFIRMED |
| OPENROUTER_API_KEY | OPENROUTER_FREE_TIER_CONFIRMED |
| GROQ_API_KEY | GROQ_FREE_TIER_CONFIRMED |
| NVIDIA_API_KEY | NVIDIA_FREE_TIER_CONFIRMED and NVIDIA_PROTOTYPE_USE_CONFIRMED |

Set ADVISORY_ENABLED=true for independent advisory. Only enable providers
whose actual account and endpoint are confirmed free and permitted. NVIDIA
free prototype access is manual-only; scheduled advisory uses OpenRouter
then Groq. A missing key/confirmation disables that route. No ChatGPT/Codex
subscription calls are required.

Model IDs can be changed using eight Actions Variables. Unset values fall
back to repository defaults. The free-tier gates and durable caps remain;
see [model variables and adoption modes](docs/AUTO_ADOPTION.md).

| KNOWLEDGE_ADOPTION_MODE | Effect |
| --- | --- |
| manual (default / unset) | No automated adoption |
| assisted | Prepare eligible adoption diff and leave the draft for Owner |
| conservative | Prepare, verify, merge eligible changes and dispatch Pages |

Example for an Owner who has approved the conservative policy:

~~~sh
gh variable set KNOWLEDGE_ADOPTION_MODE --repo yohi/agent-compass --body conservative
~~~

Set manual to stop new automated adoption jobs; cancel an already running job
if immediate stop is required. Do not enable billing or disable branch
protections to make automation succeed. See the
[operator runbook](docs/AUTO_ADOPTION.md) for setup, recovery and limitations.

### Workflow schedule (JST)

| Workflow | Scheduled time / trigger |
| --- | --- |
| [Monitor official guidance](.github/workflows/monitor.yml) | 12:17 daily |
| [Maintain knowledge candidates](.github/workflows/maintenance.yml) | 12:47 daily |
| [Verify public portal](.github/workflows/portal-health.yml) | 13:23 daily; deployment-triggered/manual checks |
| [Independent adoption advisory](.github/workflows/advisory.yml) | 14:17 daily |
| [Controlled auto adoption](.github/workflows/auto-adopt.yml) | 14:57 daily; successful advisory completion; Owner dispatch |
| [Validate prepared adoption](.github/workflows/validate-adoption.yml) | Explicit trusted dispatch |
| [Publish knowledge portal](.github/workflows/pages.yml) | master push or explicit dispatch after auto merge |

Scheduled times are nominal, not guaranteed start times. Maintenance quotas
use Pacific calendar days; advisory quotas use UTC day/month. Do not
edit/delete/reset bot-owned issue markers. Resume a blocked conservative
preparation only by explicit Owner dispatch; no repeated LLM review is needed.
Successful CI and deployment are separate from HTTP reachability and semantic
quality.

## Verified milestone / 実証状況

v0.10.3, 2026-11-27: [PR #4](https://github.com/yohi/agent-compass/pull/4)
added BP-053/BP-054 (Qwen3 configuration guidance, conditional). Existing
Gemini candidate generation and NVIDIA Kimi K3.1 Pro advisory were reused.
The recovered conservative adoption verified the exact prepared HEAD,
passed 125 Python tests plus web checks, merged via the ordinary GitHub
API, and dispatched a successful Pages build/deploy without additional
LLM inference.

Evidence: [advisory](https://github.com/yohi/agent-compass/actions/runs/45957878164) ·
[auto adoption](https://github.com/yohi/agent-compass/actions/runs/45964746461) ·
[trusted CI](https://github.com/yohi/agent-compass/actions/runs/45964791876) ·
[Pages deployment](https://github.com/yohi/agent-compass/actions/runs/45964910305).

This proves the Owner-dispatched recovery-to-deploy path, not every scheduled
path. Unattended end-to-end operation, actual OpenRouter/Groq inference and
fallback, exact post-adoption HTTP snapshot verification for this deployment,
and local model effectiveness were not established by these runs. No
additional development phase is necessary solely to obtain more reviews.

## Documentation

| Area | Reference |
| --- | --- |
| Canonical knowledge | [Best practices](docs/BEST_PRACTICES.md), [sources](registry/sources.json), [targets](registry/targets.json), [practices](registry/practices.json) |
| Curation and discovery | [Curation](docs/CURATION.md), [change intelligence](docs/CHANGE_INTELLIGENCE.md), [registration](docs/REGISTRATION.md) |
| Consumer tools | [Generator](docs/GENERATOR.md), [Auditor](docs/AUDITOR.md), [practical pilot](docs/PILOT.md) |
| Distribution | [Portal](docs/PORTAL.md), [agent interface](docs/AGENT_INTERFACE.md), [APM](docs/APM.md) |
| Repository operation | [Maintenance](docs/MAINTENANCE.md), [advisory](docs/ADVISORY.md), [manual adoption](docs/ADOPTION.md), [controlled adoption](docs/AUTO_ADOPTION.md) |
| Durable state and evidence | [Issues](https://github.com/yohi/agent-compass/issues), [Actions](https://github.com/yohi/agent-compass/actions), [Changelog](CHANGELOG.md) |

日本語: 公式資料の取得・候補生成・採択・公開・ローカル実測は異なる状態として扱う。
低リスクの新規指針のみOwnerの明示設定で自動採択可能。生成したAGENTS.mdや設定案は
利用側プロジェクトの承認なしに適用しない。
