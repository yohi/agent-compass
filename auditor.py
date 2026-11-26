"""Read-only lexical audit. Findings are review candidates, never policy verdicts."""
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import unicodedata

import generator

ROOT = Path(__file__).resolve().parent
MAX_INPUT_BYTES = 256 * 1024
MAX_FINDINGS = 1000
KINDS = {"duplicate", "runtime-setting", "repeated-review", "unconditional-reread",
         "approval-checkpoint", "size", "other-model", "literal-coverage"}
RUNTIME = re.compile(
    r"\b(?:reasoning_effort|thinking_budget|budget_tokens|temperature|top_p|top_k)"
    r"\s*[\"']?\s*[:=]\s*[\w.\"'-]+"
    r"|\b(?:reasoning_content|tool_calls)\b", re.I)
REVIEW = re.compile(
    r"\b(?:until|unless)\b.{0,65}\b(?:zero|no|0)\s+(?:findings?|issues?|defects?)\b"
    r"|\b(?:repeat|rerun)\b.{0,65}\b(?:review|audit)\b.{0,65}\b(?:until|pass|clean)\b"
    r"|\b(?:always|must)\b.{0,50}\b(?:independent|separate)\s+review\b"
    r"|(?:指摘|finding|問題).{0,30}(?:ゼロ|0件|なくなるまで).{0,30}(?:レビュー|是正)"
    r"|(?:必ず|毎回).{0,35}(?:独立レビュー|再レビュー)"
    r"|(?:レビュー|是正).{0,35}(?:繰り返す|反復).{0,35}(?:ゼロ|0件|PASS)", re.I)
REREAD = re.compile(
    r"\b(?:always|must)\b.{0,60}\b(?:re[- ]?read|read again)\b.{0,65}\b(?:every|each)\b"
    r"|\b(?:before every|before each)\b.{0,35}\b(?:re[- ]?read|read again)\b"
    r"|(?:毎回|変更のたび|編集のたび).{0,35}(?:再読|読み直|再読み込み)"
    r"|(?:必ず).{0,35}(?:再読|読み直).{0,35}(?:毎回|たび)", re.I)
APPROVAL = re.compile(
    r"\b(?:every|each|all)\s+(?:routine\s+)?(?:step|action|operation|command)s?\b"
    r".{0,55}\b(?:approval|confirmation|permission)\b"
    r"|\b(?:approval|confirmation)\b.{0,50}\b(?:every|each)\s+(?:step|action|operation|command)\b"
    r"|(?:全て|すべて|毎回|各).{0,12}(?:手順|操作|コマンド|ステップ).{0,30}(?:承認|確認)", re.I)
FENCE = re.compile(r"^\s{0,3}(\x60{3,}|~{3,})")
BULLET = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$")
PROTECT = re.compile(
    r"\b(?:security|safety|permissions?|authorizations?|approvals?|secrets?|credentials?|production|"
    r"destructive|irreversible|sandbox|deny|must not|never|prohibit)\b"
    r"|(?:安全|権限|承認|機密|秘密|本番|破壊|不可逆|禁止|保護)", re.I)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def load_rules(practices):
    data = json.loads((ROOT / "registry/audit.json").read_text(encoding="utf-8"))
    require(data["schema_version"] == 1, "unsupported audit schema")
    require(type(data["advisory_line_count"]) is int and data["advisory_line_count"] > 0,
            "invalid line threshold")
    ids, kinds = set(), set()
    for row in data["rules"]:
        require(re.fullmatch(r"AC-A\d{2}", row["id"]) and row["id"] not in ids,
                "invalid or duplicate audit rule")
        require(row["kind"] in KINDS and row["kind"] not in kinds, "invalid or duplicate audit kind")
        require(isinstance(row["evidence"], list) and all(p in practices for p in row["evidence"]),
                "unknown audit evidence")
        require(isinstance(row["description"], str) and row["description"].strip(), "missing description")
        ids.add(row["id"])
        kinds.add(row["kind"])
    require(kinds == KINDS, "incomplete audit rule set")
    return data


def read_input(path):
    """Open only an explicitly selected regular file; bound the read, never follow symlinks."""
    path = Path(path)
    require(not path.is_symlink(), "symlink input not supported")
    # O_NOFOLLOW prevents final-component substitution on platforms that support it;
    # O_NONBLOCK avoids blocking on a substituted FIFO. No directory recursion.
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    fd = os.open(path, flags)
    with os.fdopen(fd, "rb") as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode), "audit input must be a regular file")
        require(info.st_size <= MAX_INPUT_BYTES, "audit input exceeds byte limit")
        raw = stream.read(MAX_INPUT_BYTES + 1)
    require(len(raw) <= MAX_INPUT_BYTES, "audit input exceeds byte limit")
    text = raw.decode("utf-8-sig")
    require("\x00" not in text, "binary input not supported")
    return text, hashlib.sha256(raw).hexdigest(), len(raw)


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold()
    return " ".join(text.strip().split())


def prose_lines(text):
    """Skip fenced blocks, blockquotes, indented code and HTML comments.
    This is a conservative line-oriented approximation, not a Markdown parser.
    """
    fence = None
    comment = False
    for number, line in enumerate(text.splitlines(), 1):
        if comment:
            if "-->" in line:
                comment = False
            continue
        if "<!--" in line:
            comment = "-->" not in line.split("<!--", 1)[1]
            continue
        marker = FENCE.match(line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and not line[marker.end():].strip():
                fence = None
            continue
        if fence or line.startswith(("    ", "\t")) or line.lstrip().startswith(">"):
            continue
        if line.strip():
            yield number, line


def normalized_bullet(line):
    match = BULLET.match(line)
    return normalize(match[1]) if match else None


def audit(text, input_hash, input_bytes, sources, targets, practices, generation, rules,
          harness, model=None, framework=None):
    layers, selected = generator.select(targets, practices, generation, harness, model, framework)
    scoped = {p["id"]: (p, disposition) for _, p, _, disposition in selected}
    rule_map = {row["kind"]: row for row in rules["rules"]}
    findings = []
    omitted = 0
    lines = list(prose_lines(text))
    all_lines = text.splitlines()

    def add(kind, numbers, observation, guidance, protection=False):
        nonlocal omitted
        if len(findings) >= MAX_FINDINGS:
            omitted += 1
            return
        rule = rule_map[kind]
        evidence = []
        for key in rule["evidence"]:
            if key not in scoped:
                continue
            p, disposition = scoped[key]
            if disposition in {"excluded-status-or-evaluation", "unclassified"}:
                continue
            evidence.append({"practice": key, "target": p["target"], "status": p["status"],
                             "local_eval": p["local_eval"], "scope": p["scope"],
                             "sources": [{"id": sid, "url": sources[sid]["url"]}
                                         for sid in p["evidence"]]})
        findings.append({"rule": rule["id"], "kind": kind, "lines": numbers,
                         "observation": observation, "guidance": guidance,
                         "classification": "review-candidate" if kind != "literal-coverage" else "information",
                         "evidence": evidence, "protected_context": protection})

    duplicates = {}
    for number, line in lines:
        bullet = normalized_bullet(line)
        if bullet and len(bullet) >= 12:
            duplicates.setdefault(bullet, []).append(number)
        protected = bool(PROTECT.search(line))
        if RUNTIME.search(line):
            add("runtime-setting", [number], "API/runtime token or assignment matched",
                "Check whether this is documentation or a runtime setting. If it is configuration, keep it "
                "in the appropriate adapter/config; do not remove required project constraints.", protected)
        if REVIEW.search(line):
            add("repeated-review", [number], "Review-loop or mandatory independent-review wording matched",
                "Check whether review is required by risk, policy or acceptance criteria. Avoid unnecessary "
                "automatic repetition only where authorized; retain mandatory safety reviews.", protected)
        if REREAD.search(line):
            add("unconditional-reread", [number], "Unconditional reread wording matched",
                "Check the selected model and freshness requirements; do not remove necessary reads.", protected)
        if APPROVAL.search(line):
            add("approval-checkpoint", [number], "Broad step-by-step approval wording matched",
                "Keep all genuine authorization and irreversible-action gates. Clarify only unnecessary "
                "routine checkpoints within already authorized scope.", True)
    for bullet, numbers in duplicates.items():
        if len(numbers) > 1:
            protected = any(PROTECT.search(all_lines[n-1]) for n in numbers)
            add("duplicate", numbers, "Identical normalized list-item text observed",
                "Check scope and intentional repetition before consolidation; preserve all constraints.", protected)
    if len(all_lines) > rules["advisory_line_count"]:
        add("size", [], f"Physical lines: {len(all_lines)}; local triage threshold: {rules['advisory_line_count']}",
            "Consider moving detail to references where appropriate. This is not a vendor limit or failure.")
    if model and targets[model]["kind"] == "model":
        other_ids = [k for k, t in targets.items() if t["kind"] == "model" and k != model]
        # Longer IDs win: gpt-6-astra is not a substring match for a sibling's identifier.
        pattern = re.compile(r"(?<![\w.-])(" + "|".join(re.escape(k) for k in
                             sorted(other_ids, key=lambda k: (-len(k), k))) + r")(?![\w.-])", re.I) if other_ids else None
        for number, line in lines:
            if pattern:
                matched = sorted({m.group().casefold() for m in pattern.finditer(line)})
                if matched:
                    add("other-model", [number], "Other registered model ID(s): " + ", ".join(matched),
                        "Check whether this is a migration note or intentional multi-model policy; no "
                        "obsolescence or incompatibility is inferred.", bool(PROTECT.search(line)))
    literal = {normalize(line) for _, line in lines}
    literal.update(b for _, line in lines if (b := normalized_bullet(line)))
    coverage = []
    for _, p, row, disposition in selected:
        if disposition != "instruction":
            continue
        matched = any(normalize(row["instruction"][lang]) in literal for lang in ("en", "ja"))
        coverage.append({"practice": p["id"], "literal_match": matched})
    return {"schema_version": 1, "input": {"sha256": input_hash, "bytes": input_bytes,
                                           "physical_lines": len(all_lines), "scanned_lines": len(lines)},
            "profile": {"harness": harness, "model": model, "framework": framework},
            "registry_sha256": generator.registry_digest(sources, targets, practices, generation),
            "audit_rules_sha256": hashlib.sha256(json.dumps(rules, sort_keys=True,
                                               separators=(",", ":")).encode()).hexdigest(),
            "verdict": "NOT_ASSESSED", "findings": findings, "omitted_findings": omitted,
            "literal_coverage": coverage,
            "limitations": ["Lexical review candidates only; no semantic compliance or safety verdict.",
                            "No missing-instruction inference from literal nonmatches.",
                            "Only the explicitly selected file is read; no nested files or runtime settings.",
                            "No raw input lines in report; inspect locally at the indicated line numbers."]}


LABELS = {
    "duplicate": "重複指示", "runtime-setting": "API・実行設定の混入候補",
    "repeated-review": "過剰レビュー候補", "unconditional-reread": "強制再読込候補",
    "approval-checkpoint": "承認要求の範囲確認", "size": "ファイル長の参考情報",
    "other-model": "他モデルへの言及", "literal-coverage": "字面一致の参考情報",
}
JA_GUIDANCE = {
    "duplicate": "統合前に適用範囲と意図的な反復を確認する。制約を失わないこと。",
    "runtime-setting": "文書化か実行設定かを確認する。設定なら対応する実行基盤側へ分離し、必要な制約を削除しない。",
    "repeated-review": "リスク・規約・受入条件に基づく必要性を確認する。承認済み範囲内で不要な自動反復のみ見直す。",
    "unconditional-reread": "モデルの適用範囲と情報の鮮度要件を確認する。必要な再読込は維持する。",
    "approval-checkpoint": "実際の権限境界・不可逆操作の承認は維持する。不要な通常手順の確認だけを見直す。",
    "size": "必要に応じ詳細を参照資料へ分離する。行数は公式上限でも不合格条件でもない。",
    "other-model": "移行資料や複数モデル運用の可能性を確認する。廃止・非互換とは断定しない。",
}


def render(report, language="ja"):
    require(language in {"ja", "en"}, "unsupported language")
    ja = language == "ja"
    out = ["# " + ("AGENTS.md 評価候補" if ja else "AGENTS.md audit candidates"), "",
           "Verdict: NOT_ASSESSED", "",
           "Input SHA-256: " + report["input"]["sha256"],
           "Registry SHA-256: " + report["registry_sha256"],
           "Audit rules SHA-256: " + report["audit_rules_sha256"], "",
           "Profile: " + " / ".join(str(v) for v in report["profile"].values() if v), "",
           f"Lines: {report['input']['physical_lines']}; scanned: {report['input']['scanned_lines']}",
           f"Findings: {len(report['findings'])}; omitted: {report['omitted_findings']}", "",
           "字面に基づく確認候補。適合性・安全性の判定ではない。原文は出力しない。" if ja
           else "Lexical review candidates only. No compliance or safety verdict. Raw input omitted.", ""]
    for finding in report["findings"]:
        kind = finding["kind"]
        out += [f"## {finding['rule']} — {LABELS[kind] if ja else kind}", "",
                "Lines: " + (", ".join(map(str, finding["lines"])) or "file"),
                finding["observation"], "", JA_GUIDANCE.get(kind, finding["guidance"]) if ja
                else finding["guidance"], ""]
        if finding["protected_context"]:
            out.extend(["保護・承認に関係する可能性あり。自動緩和禁止。" if ja
                        else "Potential protected context: no automatic relaxation.", ""])
        if not finding["evidence"]:
            out.extend(["適用範囲内の直接根拠なし。一般的な確認候補のみ。" if ja
                        else "No scoped supporting practice; general review candidate only.", ""])
        for item in finding["evidence"]:
            out.extend([f"- {item['practice']} ({item['target']}; {item['status']}; "
                        f"local_eval={item['local_eval']}) — {item['scope']}"])
            out.extend(f"  - {s['url']}" for s in item["sources"])
        out.append("")
    out += ["## " + ("字面一致（非一致は欠落を意味しない）" if ja else
                     "Literal coverage (nonmatch does not imply absence)"), ""]
    out += [f"- {row['practice']}: {'literal match' if row['literal_match'] else 'not established'}"
            for row in report["literal_coverage"]]
    out += ["", "## " + ("制限" if ja else "Limitations"), "",
            *("- " + item for item in report["limitations"]), ""]
    return "\n".join(out) + "\n"


def write_report(path, content):
    # Explicit output only, exclusive create, including existing symlinks.
    with Path(path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
