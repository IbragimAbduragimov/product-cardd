// render only frames inside appearance windows of full.html; names = montage frame index
const {chromium}=require('playwright');
(async()=>{const b=await chromium.launch(); const p=await b.newPage({viewport:{width:1080,height:1920}});
 await p.goto('file://'+__dirname+'/full.html'); await p.evaluate(()=>document.fonts.ready);
 const fs=require('fs'); fs.mkdirSync('seq_full',{recursive:true});
 const WIN=await p.evaluate(()=>WIN); const T0=1.4, FPS=30;
 for(const [a,bq] of WIN){const f0=Math.floor((a-T0)*FPS), f1=Math.ceil((bq+0.55-T0)*FPS);
  for(let f=f0;f<=f1;f++){const t=T0+f/FPS; await p.evaluate(t=>render(t),t);
   await p.screenshot({path:`seq_full/${String(f).padStart(5,'0')}.png`,omitBackground:true,clip:{x:0,y:0,width:1080,height:960}});}}
 await b.close();})();
