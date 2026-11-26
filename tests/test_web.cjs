const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const audit = require("../web/audit.js");
const registry = name => JSON.parse(fs.readFileSync("registry/"+name+".json","utf8"));
const data = {practices:registry("practices"), generation:registry("generation"),
              audit:{...registry("audit"),max_bytes:262144,max_findings:1000}};
const profile={harness:"opencode",model:"kimi-k3",framework:"superpowers"};
test("local candidates with scoped evidence and no raw lines",()=>{
  const r=audit.run("- reasoning_effort = max # PRIVATE\n- Preserve credentials securely.\n- Preserve credentials securely.\n- 毎回独立レビューを行う。",data,profile);
  assert.equal(r.verdict,"NOT_ASSESSED");
  assert.equal(r.findings.length,3);
  const runtime=r.findings.find(f=>f.kind==="runtime-setting");
  assert.ok(runtime.evidence.includes("BP-039"));
  assert.ok(!runtime.evidence.includes("BP-025"));
  assert.ok(r.findings.find(f=>f.kind==="duplicate").protectedContext);
  assert.ok(!JSON.stringify(r).includes("PRIVATE"));
});
test("examples skipped; size advisory; limits",()=>{
  assert.equal(audit.run("~~~js\nreasoning_effort = max\n~~~\n> Always use independent review.\n<!-- tool_calls -->",data,profile).findings.length,0);
  assert.equal(audit.run("# heading\n".repeat(201),data,profile).findings[0].kind,"size");
  assert.throws(()=>audit.run("x".repeat(262145),data,profile));
});
test("profile-specific evidence and inactive exclusion",()=>{
  const copy=structuredClone(data);copy.practices.find(p=>p.id==="BP-039").status="deprecated";
  assert.ok(!audit.run("reasoning_effort = max",copy,profile).findings[0].evidence.includes("BP-039"));
});
