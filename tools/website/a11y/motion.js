const { chromium } = require('playwright');
(async()=>{const b=await chromium.launch();
for(const rm of ['no-preference','reduce']){const ctx=await b.newContext({bypassCSP:true,viewport:{width:1366,height:900},reducedMotion:rm});
for(const p of ['index.html','maps.html','media.html','studio.html']){const pg=await ctx.newPage();await pg.route(/^https?:\/\/(?!localhost)/, r=>r.abort());
await pg.goto('http://localhost:8765/'+p,{waitUntil:'load'});await pg.mouse.move(400,300);await pg.waitForTimeout(1500);await pg.mouse.wheel(0,1500);await pg.waitForTimeout(1500);
const a=await pg.evaluate(()=>document.getAnimations().filter(x=>x.playState==='running').map(x=>(x.animationName||x.transitionProperty||'?')+'@'+(x.effect&&x.effect.target?x.effect.target.className:'')).slice(0,12));
console.log(rm,p,a.length,JSON.stringify(a));await pg.close();}await ctx.close();}
await b.close();})();
