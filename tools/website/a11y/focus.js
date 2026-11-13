const { chromium } = require('playwright');
const pages=process.argv.slice(2);
(async()=>{const b=await chromium.launch();const ctx=await b.newContext({bypassCSP:true,viewport:{width:1366,height:900}});
for(const p of pages){const pg=await ctx.newPage();await pg.route(/^https?:\/\/(?!localhost)/, r=>r.abort());
try{await pg.goto('http://localhost:8765/'+p,{waitUntil:'load',timeout:20000});}catch(e){}
await pg.waitForTimeout(800);
const bad=[];const seen=new Set();
for(let i=0;i<150;i++){await pg.keyboard.press('Tab');
 const r=await pg.evaluate(()=>{const e=document.activeElement;if(!e||e===document.body)return null;const cs=getComputedStyle(e);const r=e.getBoundingClientRect();
  return {id:e.tagName+'.'+(e.className||'')+' '+(e.getAttribute('href')||e.getAttribute('aria-label')||e.textContent.trim().slice(0,25)),ol:cs.outlineStyle!=='none'&&parseFloat(cs.outlineWidth)>0,bs:cs.boxShadow!=='none',vis:r.width>0&&r.height>0&&cs.visibility!=='hidden'};});
 if(!r)break;if(seen.has(r.id))break;seen.add(r.id);if(!r.ol&&!r.bs||!r.vis)bad.push(r);}
console.log(p,'focusables',seen.size,'problems',bad.length);bad.slice(0,8).forEach(x=>console.log('   ',JSON.stringify(x)));await pg.close();}
await b.close();})();
