"use strict";
const $=id=>document.getElementById(id);
let data, lang="ja", bundle=null, serial=0;
const tr=(ja,en)=>lang==="ja"?ja:en;
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
function link(text,url){
  const a=el("a",text);
  const parsed=new URL(url);
  if(parsed.protocol!=="https:")throw Error("Unsafe evidence URL");
  a.href=parsed.href;a.rel="noopener noreferrer";return a;
}
function options(id,rows,initial){
  const s=$(id), previous=s.value;s.replaceChildren();
  for(const [value,label] of rows){const o=el("option",label);o.value=value;s.append(o);}
  if(rows.some(r=>r[0]===previous))s.value=previous;
  else if(initial && rows.some(r=>r[0]===initial))s.value=initial;
}
const all=()=>["",tr("すべて","All")];
const none=()=>["",tr("指定なし","None")];
const targetMap=()=>new Map(data.targets.map(t=>[t.id,t]));
const sourceMap=()=>new Map(data.sources.map(s=>[s.id,s]));
function card(p){
  const t=targetMap().get(p.target), s=sourceMap(), n=el("article",undefined,"practice");
  const meta=el("div",undefined,"meta");meta.append(el("span",p.id),el("span",t.name,"tag"),el("span",p.category),el("span",p.status));n.append(meta);
  n.append(el("p",p[lang],"rule-text"));
  const scope=el("p",p.scope,"scope");scope.lang="en";n.append(scope);
  n.append(el("p",tr("確認日 / 実測：","Reviewed / local eval: ")+p.reviewed+" · "+p.local_eval,"scope"));
  const evidence=el("div",undefined,"evidence");
  p.evidence.forEach(id=>evidence.append(link(s.get(id).publisher+" · "+id,s.get(id).url)));
  n.append(evidence);return n;
}
function filters(){
  options("kind",[all(),...["common","harness","model","family"].map(x=>[x,x])]);
  const kind=$("kind").value;
  options("target",[all(),...data.targets.filter(t=>!kind||t.kind===kind).map(t=>[t.id,t.name])]);
  options("category",[all(),...[...new Set(data.practices.map(p=>p.category))].sort().map(x=>[x,x])]);
  options("practice-status",[all(),...[...new Set(data.practices.map(p=>p.status))].sort().map(x=>[x,x])]);
}
function list(){
  const q=$("query").value.normalize("NFKC").toLowerCase().trim(), kind=$("kind").value, t=$("target").value;
  const cat=$("category").value, state=$("practice-status").value, targets=targetMap(), sources=sourceMap();
  const rows=data.practices.filter(p=>{
    const words=[p.id,p.en,p.ja,p.scope,p.target,targets.get(p.target).name,p.category,p.status,...p.evidence.map(id=>sources.get(id).publisher)].join(" ").normalize("NFKC").toLowerCase();
    return (!kind||targets.get(p.target).kind===kind)&&(!t||p.target===t)&&(!cat||p.category===cat)&&(!state||p.status===state)&&q.split(/\s+/).every(v=>words.includes(v));
  });
  const out=$("practice-list");out.replaceChildren(...rows.map(card));
  $("result-count").textContent=rows.length+" / "+data.practices.length;
  if(!rows.length)out.append(el("p",tr("該当する推奨事項なし。未登録は非推奨を意味しません。","No matching practices. Unregistered does not mean discouraged."),"muted"));
}
function comparison(){
  for(const x of ["a","b"]){
    const target=$("compare-"+x).value, rows=data.practices.filter(p=>p.target===target);
    const out=$("compare-out-"+x);out.replaceChildren(...rows.map(card));
    if(!rows.length)out.append(el("p",tr("推奨事項は未登録です。","No registered practices."),"muted"));
  }
}
function profileOptions(prefix){
  options(prefix+"-harness",Object.keys(data.generation.harnesses).map(id=>[id,targetMap().get(id).name]),"opencode");
  options(prefix+"-model",[none(),...data.targets.filter(t=>["model","family"].includes(t.kind)).map(t=>[t.id,t.name])]);
  options(prefix+"-framework",[none(),...data.generation.frameworks.map(id=>[id,targetMap().get(id).name])]);
}
function profile(prefix){return {harness:$(prefix+"-harness").value,model:$(prefix+"-model").value,framework:$(prefix+"-framework").value};}
function clearGenerator(){
  serial++;bundle=null;$("gen-output").hidden=true;$("gen-status").textContent="";
}
function preview(){if(bundle)$("gen-preview").textContent=bundle[$("gen-file").value];}
async function generate(){
  clearGenerator();const request=serial,p=profile("gen"),key=[p.harness,p.model,p.framework,lang].join("|"), entry=data.profiles[key];
  $("gen-status").textContent=tr("取得中…","Loading…");
  try{
    if(!entry||!/^bundles\/[a-z0-9._-]+\.json$/.test(entry.path))throw Error("Invalid profile");
    const r=await fetch("./"+entry.path,{cache:"no-store"});if(!r.ok)throw Error("Bundle unavailable");
    const bytes=await r.arrayBuffer();
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),n=>n.toString(16).padStart(2,"0")).join("");
    if(hash!==entry.sha256)throw Error("Bundle identity mismatch");
    const next=JSON.parse(new TextDecoder().decode(bytes));
    if(!["AGENTS.draft.md","CONFIGURATION.md","EVIDENCE.md"].every(k=>typeof next[k]==="string"))throw Error("Invalid bundle");
    if(serial!==request)return;bundle=next;$("gen-output").hidden=false;preview();
    $("gen-status").textContent=tr("生成候補・未適用。プロジェクト固有情報は要記入。","Draft only. Complete project-specific fields.");
  }catch(e){if(serial===request)$("gen-status").textContent=tr("取得失敗。再試行してください。","Unable to load verified bundle. Retry.");}
}
function audit(){
  const out=$("audit-output");out.replaceChildren();
  try{
    const result=CompassAudit.run($("audit-input").value,data,profile("audit"));
    out.append(el("p",result.verdict+" · "+result.findings.length+tr("件の確認候補"," review candidates")+" · "+result.lines+tr("行"," lines"),"tag"));
    if(result.omitted)out.append(el("p",tr("表示上限超過：","Omitted: ")+result.omitted));
    const practices=new Map(data.practices.map(p=>[p.id,p])), sources=sourceMap();
    for(const f of result.findings){
      const n=el("article",undefined,"practice");
      n.append(el("h3",f.rule+" — "+CompassAudit.labels[f.kind][lang==="ja"?1:0]));
      n.append(el("p",f.lines.length?"Lines: "+f.lines.join(", "):tr("ファイル全体","Whole file"),"muted"));
      n.append(el("p",tr("文脈と適用範囲を確認。必要な制約は維持する。","Inspect context and scope; retain necessary constraints.")));
      if(f.protectedContext)n.append(el("p",tr("保護・承認境界の可能性。自動緩和禁止。","Potential protected boundary. No automatic relaxation."),"scope"));
      if(!f.evidence.length)n.append(el("p",tr("適用範囲内の直接根拠なし。","No scoped supporting practice."),"muted"));
      for(const id of f.evidence){const p=practices.get(id);const l=el("p",id+" · "+p.local_eval+" ");for(const sid of p.evidence)l.append(link(sid,sources.get(sid).url),document.createTextNode(" "));n.append(l);}
      out.append(n);
    }
    out.append(el("p",tr("0件でも適合性を保証しません。入力は送信・保存しません。","Zero findings does not imply compliance. Input is not sent or stored."),"muted"));
  }catch(e){out.append(el("p",tr("入力が上限を超えているか無効です。","Invalid or oversized input.")));}
}
function render(){
  document.documentElement.lang=lang;$("language").textContent=lang==="ja"?"EN":"日本語";
  for(const n of document.querySelectorAll("[data-ja][data-en]"))n.textContent=n.dataset[lang];
  if(!data)return;
  const stats=$("stats");stats.replaceChildren(...[[data.practices.length,tr("推奨事項","Practices")],[data.sources.length,tr("公式情報源","Sources")],[data.targets.length,tr("対象","Targets")]].map(([v,t])=>{const n=el("div",undefined,"stat");n.append(el("strong",String(v)),el("span",t));return n;}));
  $("version").textContent="v"+data.version+" · Registry "+data.registry_sha256.slice(0,12);
  filters();list();
  const rows=data.targets.map(t=>[t.id,t.name]);options("compare-a",rows,"gpt-6.2-astra");options("compare-b",rows,"claude-sonnet-5.5");comparison();
  profileOptions("gen");profileOptions("audit");
  $("source-list").replaceChildren(...data.sources.map(s=>{const n=el("article");n.append(el("h3",s.publisher+" · "+s.id),el("p",s.kind+" · "+s.target+" · "+s.checked,"muted"),link(s.url,s.url));return n;}));
  clearGenerator();$("audit-output").replaceChildren();
}
$("language").addEventListener("click",()=>{lang=lang==="ja"?"en":"ja";render();});
$("query").addEventListener("input",()=>{if(data)list();});
for(const id of ["kind","target","category","practice-status"])$(id).addEventListener("change",()=>{if(data){if(id==="kind")filters();list();}});
for(const id of ["compare-a","compare-b"])$(id).addEventListener("change",()=>{if(data)comparison();});
for(const id of ["gen-harness","gen-model","gen-framework"])$(id).addEventListener("change",clearGenerator);
for(const id of ["audit-harness","audit-model","audit-framework","audit-input"])$(id).addEventListener("input",()=>$("audit-output").replaceChildren());
$("generate").addEventListener("click",()=>{if(data)generate();});
$("gen-file").addEventListener("change",preview);
$("gen-copy").addEventListener("click",async()=>{if(bundle){try{await navigator.clipboard.writeText(bundle[$("gen-file").value]);$("gen-status").textContent=tr("コピーしました。","Copied.");}catch(e){$("gen-status").textContent=tr("コピーできません。手動で選択してください。","Clipboard unavailable. Select text manually.");}}});
$("gen-download").addEventListener("click",()=>{if(!bundle)return;const name=$("gen-file").value,url=URL.createObjectURL(new Blob([bundle[name]],{type:"text/markdown;charset=utf-8"}));const a=el("a");a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$("audit-run").addEventListener("click",()=>{if(data)audit();});
for(const id of ["generate","audit-run"])$(id).disabled=true;
fetch("./data.json",{cache:"no-store"}).then(r=>{if(!r.ok)throw Error("Registry unavailable");return r.json();}).then(d=>{
  if(d.schema_version!==1)throw Error("Registry schema unsupported");data=d;render();$("status").textContent="";
  for(const id of ["generate","audit-run"])$(id).disabled=false;
}).catch(()=>{$("status").textContent="Registry unavailable / Registryを取得できません。";});
