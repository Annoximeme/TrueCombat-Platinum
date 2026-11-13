const { chromium } = require('playwright');
const fs=require('fs');
const axe=fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8');
const pages=process.argv.slice(2);
(async()=>{
 const b=await chromium.launch(); const ctx=await b.newContext({viewport:{width:1366,height:900},bypassCSP:true});
 const agg={};
 for(const p of pages){
  const pg=await ctx.newPage();
  await pg.route(/^https?:\/\/(?!localhost)/, r=>r.abort());
  try{await pg.goto('http://localhost:8765/'+p,{waitUntil:'load',timeout:20000});}catch(e){}
  await pg.waitForTimeout(800);
  await pg.addScriptTag({content:axe});
  const r=await pg.evaluate(async()=>await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}}));
  for(const v of r.violations){const k=v.id; agg[k]=agg[k]||{impact:v.impact,help:v.help,n:0,pages:new Set(),ex:[]}; agg[k].n+=v.nodes.length; agg[k].pages.add(p); if(agg[k].ex.length<4) for(const n of v.nodes.slice(0,2)) agg[k].ex.push(p+': '+n.target.join(' ')+' | '+(n.failureSummary||'').split('\n').slice(1,2).join(' ').slice(0,160));}
  await pg.close();
 }
 for(const [k,v] of Object.entries(agg)) {console.log(`${k} [${v.impact}] ${v.n} nodes on ${v.pages.size} pages: ${v.help}`); v.ex.forEach(e=>console.log('   '+e));}
 await b.close();
})();
