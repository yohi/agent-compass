# Phase 4 — Practical pilot / 実プロジェクト実証

The scope is a read-only evaluation of the root AGENTS.md at pinned public commits
and preparation of one experimental A/B case. No consuming repository is modified.
Profiles are experimental assumptions, not verified production runtime configurations.

| Project | Pinned input | Initial human-context interpretation |
| --- | --- | --- |
| Justice | [AGENTS.md](https://github.com/yohi/justice/blob/478551de23a39b5ae93018b145c0bcb0d9854033/AGENTS.md) | 61 lines; clear invariants, progressive disclosure; line 30 applies four fresh checks to any task. Compare narrowly scoped read-only exception, retaining all implementation checks. |
| Nexus | [AGENTS.md](https://github.com/yohi/nexus/blob/70e2010fda9f84bfe059049439d03e1c5b79050e/AGENTS.md) | 60 lines; build check already conditional; initial setup choice and MCP/Skill gates are meaningful, retain them. No immediate change proposed. |
| ChronosGraph | [AGENTS.md](https://github.com/yohi/chronos-graph/blob/6eaf561a36cb80d6b57d7d18a2ddfacb16abf70b/AGENTS.md) | 133 lines; setup-specific details and repeated constraints could be consolidated, but DB lock, SSOT, migration and authorization rules are essential. Formatting command can write files; distinguish validation from formatting in future changes if needed. No immediate change proposed. |

Run from Agent Compass:

```sh
python pilot.py
python pilot.py --prepare-dir ./justice-pilot
```

The script fetches only the fixed public input files and verifies Git blob IDs,
runs the actual Auditor and Generator, and prints report properties without
copying project instruction lines into logs. Generic draft size is not a measure
of quality and the draft is not a replacement for the project instructions.
The pilot workflow runs on changes to pilot inputs or manual invocation, not daily.

## One real-task comparison

The prepared case is a read-only Justice provenance investigation. A = original
root AGENTS.md, B = one experimental wording change limiting mandatory full
verification for strictly read-only tasks; all implementation verification and
safety/authorization constraints are retained. The candidate is not an approved
project policy. The case includes a fixed prompt, source identity, five rubric
items and expected metric fields; no claims of model improvement are made.

To run with a real agent:

1. Use two disposable independent copies of the pinned Justice commit, with
   identical harness, model/provider version, permissions, tools, skills,
   dependencies, cache policy, and token limits. No credentials or external
   writes; run with an appropriately restricted sandbox. Keep the task prompt
   identical. Install the selected variant only inside its disposable copy.
2. Use fresh sessions, with the same allowed commands. Run A and B once each
   initially; record the actual loaded instructions and variant SHA-256. Do not
   feed the rubric/expected answer or other arm's transcript into the agent.
3. Judge the answer using the pinned evidence and manifest rubric. Independently
   observe command history, tracked file changes, approvals and unauthorized
   actions. Record provider-reported token usage and wall time, not model estimates.
   Unknown measurements are null, not zero. Separate failures from unexecuted checks.
4. A candidate is worth further evaluation only if correctness and safety are
   maintained and unnecessary work decreases; a single pair is a smoke test,
   not proof of general effectiveness. Stop after the bounded comparison and
   leave adoption to the Human Owner.

The existing benchmark repository is a separate collection of model benchmarks;
this case is intentionally staged in Agent Compass for portability. Export
results to benchmark only after actual model runs and explicit authorization.
No LLM runtime is invoked by this pilot. Execution status stays NOT_RUN until
observed model trials exist. Neither the auditor nor generator results alone
can establish improved task success or reduced token use.

日本語: 実プロジェクトの固定コミットを対象に読み取り専用評価を行う。
Justiceの調査タスクでのみ、現行指示と限定変更候補を比較する準備を行う。
実測していないモデル性能やトークン削減率を結果として登録しない。
