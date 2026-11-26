# AGENTS.md Auditor / 指示ファイル評価候補

Read-only, deterministic lexical analysis of one explicitly selected UTF-8
instruction file. No network, LLM, command execution, repository traversal,
automatic correction, score, or compliance verdict.

## Usage

```sh
python compass.py audit ./AGENTS.md --harness opencode --model kimi-k3 --framework superpowers
python compass.py audit ./AGENTS.md --harness codex --model gpt-6.2-astra --format json --output ./audit.json
```

The command uses the same exact target selection as the generator. Model and
framework are optional. The default output is Japanese Markdown; --language en
selects English Markdown. JSON has stable field names and English observations.
--output must name a new file; no overwrite option. Standard output is the
default. Exit 0 means the audit ran, not that the file is compliant. Invalid
input or profile produces a nonzero exit. A report is never an authorization
to change the source. The file is not rewritten, and raw lines are not copied
into the report. Report identifiers and local line numbers may still be sensitive.

## What is checked

| Rule | Observable signal | Interpretation |
| --- | --- | --- |
| AC-A01 | Repeated normalized list-item text | Possible consolidation; context may differ |
| AC-A02 | Selected API parameter assignments / tool protocol names | Check whether configuration or intentional documentation |
| AC-A03 | Review-loop / mandatory-review wording | Evaluate necessity; mandatory reviews may be valid |
| AC-A04 | Unconditional reread wording | Evaluate model and freshness scope |
| AC-A05 | Broad step-by-step approval wording | Preserve actual authorization boundaries |
| AC-A06 | Physical line count above local threshold (200) | Informational triage, not a vendor limit |
| AC-A07 | Exact other registered model ID in prose | Could be migration or multi-model policy |
| AC-A08 | Literal match against selected generated instruction | Nonmatch does not establish a missing instruction |

Evidence references are filtered to the selected common/harness/model/framework
profile and active, classified practices. Rules without relevant evidence are
general lexical review candidates only. Exact duplicate observations are not
proof of redundant behavior. Protected wording is flagged for caution, never
relaxed. Each report has input, registry and audit-rule fingerprints.

The scanner skips fenced examples, blockquotes, indented code and HTML comment
lines using a line-oriented approximation; it is not a complete Markdown
parser. It cannot distinguish all negations, examples, multiline conditions,
semantic duplicates, intentional repetition, or project-specific safety rules.
Other-model checks use registered IDs, not all natural-language aliases.
No implicit model-family inheritance or model compatibility claim. The
literal-coverage table does not impose generated guidance as requirements.
The 256 KiB input limit and 1,000 finding cap are operational bounds; omitted
findings are counted, not silently treated as absent.

## Adoption

Read the line in its project context. Compare the cited scoped practice to the
actual official source, identify the practical impact, and decide whether a
change is warranted. Preserve approved requirements, permissions, data integrity,
and necessary verification. No automatic follow-up tasks or reviews.

日本語: 指示ファイルの改善候補を行番号と根拠付きで提示する。
適合性や安全性を機械的に判定せず、原文を変更・転送しない。
