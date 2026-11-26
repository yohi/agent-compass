# AGENTS.md Generator / 指示ファイル生成

Generate a deterministic, offline draft from the curated registry. No network,
LLM calls, repository scanning or automatic installation.

## Usage

```sh
python compass.py generate --harness opencode --model kimi-k3 --framework superpowers --language ja
python compass.py generate --harness opencode --model kimi-k3 --framework superpowers --language ja --output-dir ./compass-draft
```

The first command prints the draft only; use the second for all three files.
The output directory must not exist; its parent must already exist. No overwrite
option is provided. The files are proposals and do not activate instructions.
If writing fails, a partial new directory can remain; inspect it or choose another
new directory. Existing files are never replaced by the generator.

| File | Contents |
| --- | --- |
| AGENTS.draft.md | Short candidate instructions, grouped by common/harness/model/framework; project-specific placeholders |
| CONFIGURATION.md | API, integration and permission guidance, not executable config |
| EVIDENCE.md | Selected record dispositions, source links, scopes, local-evaluation status, registry fingerprint and native entry-point suggestion |

Supported harness IDs: codex, claude-code, opencode, gemini-cli, cursor,
github-copilot. Model is optional; if supplied, it must be an exact model or
explicit family target ID in registry/targets.json. Framework is optional and
currently supports superpowers. Languages: ja, en.

## Selection rules

The generator uses registry/generation.json to explicitly classify practices:
instruction, configuration, or author-guidance. Instruction text is a curated
adaptation, not a direct vendor quotation. Author-guidance includes advice for
writing/maintaining instructions and task prompts. It remains in EVIDENCE.md.
A newly added practice without a classification is listed as unclassified and
never silently inserted into the draft.

Only the common target, chosen harness, explicitly chosen model/family and
opted-in framework are considered. No implicit family or sibling-model
inheritance; compatibility of any combination is not established. A model
without applicable standing instructions receives an explicit evidence warning.
Inactive or locally mixed/contradicted practices are excluded from the draft
and configuration. Conditional standing instructions are not auto-selected
except for explicitly selected framework guidance, retaining its condition.
Conditional configuration is advisory only and preserves the original scope.
Identical instruction text is deduplicated. All selected records and their
dispositions remain traceable in EVIDENCE.md.

The draft does not set reasoning effort, temperature, tool-message protocols,
hard permission rules, approval policy or project commands. It provides
placeholders for the latter and records configuration separately. The owner
must fill those fields and reconcile existing project rules. No new authorization
is granted by generated text. Use native entry-point suggestions only after
verifying the installed harness and its loading behavior.

## Example adoption

1. Generate to a new directory; read the draft and evidence.
2. Retain the project's existing authoritative constraints and approved commands.
3. Choose only useful instruction adaptations; move settings to the appropriate
   harness/provider configuration after checking compatibility.
4. Adopt the reviewed text using the normal authorized project workflow.

日本語: 自動適用しない短い指示候補・設定候補・根拠一覧を生成する。
API設定や指示作成者向けの助言を常時指示へ混入させない。
未分類の新規推奨事項や別モデルの指示は自動挿入しない。
