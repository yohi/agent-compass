/* Local lightweight checks. No network, file writes, telemetry or input excerpts. */
"use strict";
(function (root) {
  const labels = {
    duplicate: ["Repeated normalized list item", "重複指示候補"],
    "runtime-setting": ["API/runtime token", "API・実行設定の混入候補"],
    "repeated-review": ["Repeated or mandatory review wording", "過剰レビュー候補"],
    "unconditional-reread": ["Repeated read wording", "強制再読込候補"],
    "approval-checkpoint": ["Broad approval wording", "承認範囲の確認候補"],
    size: ["Local line-count threshold", "ファイル長の参考情報"]
  };
  const patterns = {
    "runtime-setting": /\b(?:reasoning_effort|thinking_budget|budget_tokens|temperature|top_p|top_k)\s*["']?\s*[:=]\s*[\w."'-]+|\b(?:reasoning_content|tool_calls)\b/i,
    "repeated-review": /\b(?:until|unless)\b.{0,65}\b(?:zero|no|0)\s+(?:findings?|issues?|defects?)\b|\b(?:repeat|rerun)\b.{0,65}\b(?:review|audit)\b.{0,65}\b(?:until|pass|clean)\b|\b(?:always|must)\b.{0,50}\b(?:independent|separate)\s+review\b|(?:指摘|finding|問題).{0,30}(?:ゼロ|0件|なくなるまで).{0,30}(?:レビュー|是正)|(?:必ず|毎回).{0,35}(?:独立レビュー|再レビュー)/i,
    "unconditional-reread": /\b(?:always|must)\b.{0,60}\b(?:re[- ]?read|read again)\b.{0,65}\b(?:every|each)\b|\b(?:before every|before each)\b.{0,35}\b(?:re[- ]?read|read again)\b|(?:毎回|変更のたび|編集のたび).{0,35}(?:再読|読み直|再読み込み)/i,
    "approval-checkpoint": /\b(?:every|each|all)\s+(?:routine\s+)?(?:step|action|operation|command)s?\b.{0,55}\b(?:approval|confirmation|permission)\b|\b(?:approval|confirmation)\b.{0,50}\b(?:every|each)\s+(?:step|action|operation|command)\b|(?:全て|すべて|毎回|各).{0,12}(?:手順|操作|コマンド|ステップ).{0,30}(?:承認|確認)/i
  };
  const protect = /\b(?:security|safety|permissions?|authorizations?|approvals?|secrets?|credentials?|production|destructive|irreversible|sandbox|deny|must not|never|prohibit)\b|(?:安全|権限|承認|機密|秘密|本番|破壊|不可逆|禁止|保護)/i;
  function run(text, data, profile) {
    if (new TextEncoder().encode(text).length > data.audit.max_bytes || text.includes("\0")) throw Error("Invalid or oversized input");
    const rules = new Map(data.audit.rules.map(r => [r.kind, r]));
    const scoped = new Set(["common", profile.harness, profile.model, profile.framework].filter(Boolean));
    const placements = new Set(data.generation.placements.map(r => r.id));
    const practice = new Map(data.practices.map(p => [p.id, p]));
    const found = [], dup = new Map();
    let omitted = 0, fence = null, comment = false;
    function add(kind, lines, protectedContext) {
      if (found.length >= data.audit.max_findings) { omitted++; return; }
      const rule = rules.get(kind);
      const evidence = rule.evidence.filter(id => {
        const p = practice.get(id);
        return p && scoped.has(p.target) && placements.has(id) && ["recommended","conditional"].includes(p.status)
          && !["mixed","contradicted"].includes(p.local_eval);
      });
      found.push({rule:rule.id, kind, lines, protectedContext, evidence});
    }
    const lines = text === "" ? [] : text.split(/\r\n|\n|\r/);
    if (lines.length && lines.at(-1) === "" && /[\r\n]$/.test(text)) lines.pop();
    lines.forEach((line, i) => {
      if (comment) { if (line.includes("-->")) comment=false; return; }
      if (line.includes("<!--")) { comment=!line.split("<!--")[1].includes("-->"); return; }
      const mark=line.match(/^\s{0,3}(\x60{3,}|~{3,})/);
      if (mark) {
        const token=mark[1];
        if (!fence) fence=token;
        else if (fence[0]===token[0] && token.length>=fence.length && !line.slice(mark[0].length).trim()) fence=null;
        return;
      }
      if (fence || /^(?:    |\t)/.test(line) || /^\s*>/.test(line)) return;
      const bullet=line.match(/^\s*(?:[-*+]\s+|\d+[.)]\s+)(.+)$/);
      if (bullet) {
        const key=bullet[1].normalize("NFKC").toLowerCase().trim().replace(/\s+/g," ");
        if (key.length>=12) { const d=dup.get(key)||[]; d.push(i+1); dup.set(key,d); }
      }
      for (const [kind, pattern] of Object.entries(patterns))
        if (pattern.test(line)) add(kind,[i+1],kind==="approval-checkpoint" || protect.test(line));
    });
    for (const nums of dup.values()) if (nums.length>1) add("duplicate",nums,nums.some(n=>protect.test(lines[n-1])));
    if (lines.length>data.audit.advisory_line_count) add("size",[],false);
    return {verdict:"NOT_ASSESSED", lines:lines.length, findings:found, omitted};
  }
  const api={run,labels};
  if (typeof module!=="undefined" && module.exports) module.exports=api;
  else root.CompassAudit=api;
})(typeof globalThis!=="undefined"?globalThis:this);
