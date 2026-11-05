// Full-video teaser donut. t = FRONT-camera seconds (montage time = t - 1.4).
// Variant Q2 "redacted": segments coloured, percentages visible, NAMES hidden under shimmering bars
// until their chapter starts. Medicine 10% always visible.
const CX=330,CY=350,R=270,r=112;
const REVEAL={life:14.35,env:42.30,her:69.90};
// appearance windows [in, out]
const WIN=[[5.45,21.00],[41.95,50.00],[69.55,73.60],[95.55,109.00]];   // env/her shorter: info cards follow
const FOCUS2=[[100.95,'life'],[104.40,'env'],[107.80,'her']];        // finale: highlight on each word
const FINAL=95.55;
function V(t){let v=0;for(const [a,b] of WIN)v=Math.max(v,ease((t-a)/0.45)*(1-ease((t-b)/0.5)));return v;}
function arc(a0,a1,R,r){const p=(a,rr)=>[CX+rr*Math.sin(a),CY-rr*Math.cos(a)];const L=a1-a0>Math.PI?1:0;
 const [x0,y0]=p(a0,R),[x1,y1]=p(a1,R),[x2,y2]=p(a1,r),[x3,y3]=p(a0,r);
 return `M${x0},${y0}A${R},${R} 0 ${L} 1 ${x1},${y1}L${x2},${y2}A${r},${r} 0 ${L} 0 ${x3},${y3}Z`;}
const mix=(c1,c2,u)=>{const h=c=>[1,3,5].map(i=>parseInt(c.substr(i,2),16));const a=h(c1),b=h(c2);return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*u)).join(',')})`;};
function render(t){
 const vis=V(t);
 if(vis<=0.001){document.getElementById('s').innerHTML='';document.getElementById('h').innerHTML='';return;}
 const intro=t<14.0;   // growth animation only in the intro
 // which factor is being revealed in this window (for emphasis)
 let focus=null, ft=0; for(const k in REVEAL){if(t>=REVEAL[k]-0.4&&t<REVEAL[k]+3.0&&t<FINAL){focus=k;ft=REVEAL[k];}}
 for(const [tt,k] of FOCUS2){if(t>=tt-0.2){focus=k;ft=tt;}}
 let svg='',html=''; let a=0; const gap=0.012; const order=['med','life','her','env'];
 for(const k of order){const f=F.find(x=>x.k==k); const span=f.v/100*2*Math.PI; const gg=intro?g(k,t):1;
  const rv=k=='med'?1:ease((t-REVEAL[k])/0.6);
  const pop=focus==k?1+0.05*Math.sin(Math.PI*cl((t-ft)/0.9)):1;
  const dim=(focus&&focus!=k&&k!='med')?0.85:1;
  if(gg>0.001){const a1=a+span*gg;
   let fill=C[k];
   let op=dim;
   const pulse=1;
   svg+=`<path d="${arc(a+gap,a1-gap,R*(0.92+0.08*back(gg))*pulse*pop,r)}" fill="${fill}" opacity="${op}" stroke="none" stroke-width="2"/>`;
   const am=a+span/2, rr=(R+r)/2+(k=='med'?8:0), lx=CX+rr*Math.sin(am), ly=CY-rr*Math.cos(am); const o=cl((gg-0.5)*2)*dim;
   if(k=='med'){
    html+=`<div style="position:absolute;left:${lx-150}px;top:${ly-44}px;width:300px;text-align:center;opacity:${o};font-weight:700;color:#2a3350">
     <div>${icon(k,26,'#2a3350')}</div><div style="font-size:13px;letter-spacing:.06em;text-transform:uppercase">Медицина</div>
     <div style="font-size:28px;font-weight:800;line-height:1.05">${intro?Math.round(10*cl((gg-0.5)*2)):10}%</div></div>`;
   } else {
    const big=k=='life'?54:40;
    const pct=`<div style="font-size:${big}px;font-weight:800;line-height:1.05">${Math.round(f.v*(intro?o:1))}%</div>`;
    const named=`<div>${icon(k,k=='life'?46:36,'#fff')}</div>
      <div style="font-size:${k=='life'?24:19}px;letter-spacing:.06em;text-transform:uppercase">${f.name.replace(' ','<br>')}</div>`;
    const sh=((t*0.9+(k=='her'?.3:k=='env'?.6:0))%1)*240-60;
    const bar=(w,h)=>`<div style="width:${w}px;height:${h}px;margin:5px auto;border-radius:${h/2}px;background:linear-gradient(90deg,rgba(255,255,255,.28) 0%,rgba(255,255,255,.28) ${sh}%,rgba(255,255,255,.75) ${sh+18}%,rgba(255,255,255,.28) ${sh+36}%)"></div>`;
    const hidden=`<div style="font-size:${k=='life'?40:30}px;font-weight:900;opacity:.9;line-height:1.1">?</div>${bar(k=='life'?150:110,k=='life'?18:14)}${k=='life'?bar(110,18):''}`;
    html+=`<div class=sh style="position:absolute;left:${lx-150}px;top:${ly-(k=='life'?78:62)}px;width:300px;text-align:center;opacity:${o};font-weight:700">
      <div style="position:relative;height:${k=='life'?118:92}px"><div style="position:absolute;inset:0;opacity:${1-rv}">${hidden}</div><div style="position:absolute;inset:0;opacity:${rv};transform:scale(${0.8+0.2*back(rv)})">${named}</div></div>${pct}</div>`;
   }}
  a+=span;}
 // centre
 let n=90, sub='3 фактора', co=1;
 if(intro){const s90=prog(t,9.4,0.5),s10=prog(t,7.15,0.4)*(1-s90); co=Math.max(s10,s90);
   n=Math.round(s90>0?10+80*prog(t,9.4,1.6):10*prog(t,7.15,0.75)); sub=s90>0.5?'3 фактора':'медицина';}
 else if(t>=FINAL) sub='';
 html+=`<div class=sh style="position:absolute;left:${CX-110}px;top:${CY-58}px;width:220px;text-align:center;opacity:${co}">
   <div style="font-size:64px;font-weight:800;line-height:1">${n}%</div>
   <div style="font-size:16px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.9">${sub}</div></div>`;
 const sc=intro?0.85+0.15*back(cl((t-IN)/0.6)):1;
 document.getElementById('s').innerHTML=`<g opacity="${vis}" transform="translate(${CX} ${CY}) scale(${sc}) translate(${-CX} ${-CY})">${svg}</g>`;
 document.getElementById('h').innerHTML=`<div style="opacity:${vis}">${html}</div>`;
}
