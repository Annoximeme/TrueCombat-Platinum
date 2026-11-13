const { chromium } = require('playwright');
const pages=process.argv.slice(2);
(async()=>{const b=await chromium.launch();const ctx=await b.newContext({bypassCSP:true,viewport:{width:1366,height:900}});
const agg={};
for(const p of pages){const pg=await ctx.newPage();await pg.route(/^https?:\/\/(?!localhost)/, r=>r.abort());
try{await pg.goto('http://localhost:8765/'+p,{waitUntil:'load',timeout:20000});}catch(e){}
await pg.evaluate(()=>{document.querySelectorAll('.rv').forEach(e=>e.classList.add('in'))});
await pg.waitForTimeout(1200);
const res=await pg.evaluate(()=>{
 function rgb(s){const m=s.match(/rgba?\(([^)]+)\)/);if(!m)return null;const a=m[1].split(/[ ,\/]+/).filter(Boolean).map(Number);return [a[0],a[1],a[2],a.length>3?a[3]:1];}
 function lum(c){const f=v=>{v/=255;return v<=0.03928?v/12.92:Math.pow((v+0.055)/1.055,2.4)};return 0.2126*f(c[0])+0.7152*f(c[1])+0.0722*f(c[2]);}
 function bg(el){let layers=[];while(el){const cs=getComputedStyle(el);if(cs.backgroundImage&&cs.backgroundImage!=='none'&&!cs.backgroundImage.startsWith('linear'))return null;const c=rgb(cs.backgroundColor);if(c&&c[3]>0){layers.push(c);if(c[3]>=1)break;}el=el.parentElement;}
  let base=[0,0,0];for(let i=layers.length-1;i>=0;i--){const c=layers[i];base=[0,1,2].map(k=>c[k]*c[3]+base[k]*(1-c[3]));}return base;}
 const out=[];
 for(const el of document.querySelectorAll('body *')){
  if(!el.childNodes.length)continue;let txt='';for(const n of el.childNodes)if(n.nodeType===3)txt+=n.textContent;txt=txt.trim();if(!txt)continue;
  const cs=getComputedStyle(el);if(cs.visibility==='hidden'||cs.display==='none'||parseFloat(cs.opacity)===0)continue;const r=el.getBoundingClientRect();if(!r.width||!r.height)continue;
  const fg=rgb(cs.color);const b=bg(el);if(!fg||!b)continue;
  const f=[0,1,2].map(k=>fg[k]*fg[3]+b[k]*(1-fg[3]));
  const L1=lum(f),L2=lum(b);const ratio=(Math.max(L1,L2)+0.05)/(Math.min(L1,L2)+0.05);
  const size=parseFloat(cs.fontSize),bold=parseInt(cs.fontWeight)>=700;const large=size>=24||(size>=18.66&&bold);
  const need=large?3:4.5;
  if(ratio<need)out.push({sel:el.tagName.toLowerCase()+(el.className&&typeof el.className==='string'?'.'+el.className.trim().split(/\s+/).join('.'):''),txt:txt.slice(0,40),ratio:+ratio.toFixed(2),fg:cs.color,size});
 }return out;});
for(const o of res){const k=o.sel+' '+o.fg;agg[k]=agg[k]||{...o,pages:new Set()};agg[k].pages.add(p);}
await pg.close();}
for(const v of Object.values(agg).sort((a,b)=>a.ratio-b.ratio))console.log(v.ratio, v.sel, JSON.stringify(v.txt), v.fg, v.size+'px', [...v.pages].slice(0,4).join(','));
await b.close();})();
