// node shoot.js VARIANT t0 t1 fps outdir   (or a single time: t0==t1)
const {chromium}=require('playwright');
(async()=>{const [v,t0,t1,fps,out]=process.argv.slice(2);const b=await chromium.launch();
 const p=await b.newPage({viewport:{width:1080,height:1920}});
 await p.goto('file://'+__dirname+'/'+v+'.html'); await p.evaluate(()=>document.fonts.ready);
 const fs=require('fs'); fs.mkdirSync(out,{recursive:true});
 const n=Math.max(1,Math.round((t1-t0)*fps)); 
 for(let i=0;i<n;i++){const t=+t0+i/fps; await p.evaluate(t=>render(t),t);
  await p.screenshot({path:`${out}/${String(i).padStart(4,'0')}.png`,omitBackground:true,clip:{x:0,y:0,width:1080,height:960}});}
 await b.close();})();
