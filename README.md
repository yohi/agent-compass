# Agent Compass

Living, evidence-based guidance for AI coding agents and LLMs.
AIコーディングエージェント・LLMの公式推奨事項を継続管理する。

- [Current bilingual best practices](docs/BEST_PRACTICES.md)
- [Source registry](registry/sources.json) / [Target registry](registry/targets.json)
- [Practice registry](registry/practices.json)
- [Monitor workflow](.github/workflows/monitor.yml) / [monitor state and notifications](../../issues)

## Quick start

Python 3.11+; no runtime packages, LLM API or paid services required.

```sh
python compass.py validate
python compass.py render --check
python -m unittest discover -s tests -v
python compass.py show --target gpt-6-astra
python compass.py monitor --state .local-state.json --output .local-report.json
# Optional developer tools:
uv run --extra dev pytest
uv run --extra dev ruff check .
```

## Operating model / 運用

JSON is the canonical registry (also a YAML 1.2 subset). Source records, target
records and practice records are deliberately separate. A model family does not
imply that every version shares its guidance. Unknown model-specific guidance
remains unknown. Source date denotes human source inspection, not a live fetch.

Daily UTC 03:17 (JST 12:17) and manual workflow: fetch configured official
sources, normalize visible text, compare content and chunk fingerprints, report
source changes or fetch failures in one bot-owned GitHub issue. The first
successful fetch establishes a baseline; failures retain the last successful
fingerprint. No raw source bodies or model-generated claims are persisted.
Chunk changes are approximate, not semantic diffs. Dynamic websites may cause
false positives or failures. Inspect the linked official source before adoption.
The initial source set is not exhaustive; provider indexes can signal new models
but do not automatically add sources.

The monitor uses the issue as durable state. Do not delete/edit its state marker;
closing it does not reset it. A changed issue receives a comment; duplicate
notifications are possible if publishing is interrupted. Workflow concurrency
serializes runs. No automatic practice adoption, code execution from fetched
content, repository settings changes, or changes to other repositories.

To adopt guidance: edit registry records with scoped evidence, regenerate docs,
run tests, and use the normal human-approved Git workflow. Do not confuse
provider guidance, project policy, and local evaluation. More monitoring coverage
and semantic analysis are future work, not required for using this registry.

日本語・英語の一覧は上記リンク。取得失敗は「変更なし」と区別する。
公式資料の変更を検出しても推奨事項を自動採択しない。
