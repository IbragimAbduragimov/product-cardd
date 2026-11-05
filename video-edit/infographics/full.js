// Full-video teaser donut. t = FRONT-camera seconds (montage time = t - 1.4).
// Medicine 10% always visible; other factors hidden ("?") until their chapter starts.
const CX=330,CY=350,R=270,r=112;
const REVEAL={life:14.35,env:42.30,her:69.90};
// appearance windows [in, out]
const WIN=[[5.45,13.35],[14.10,17.00],[41.95,44.90],[69.55,72.50],[95.55,100.10]];
const FINAL=95.55;
function V(t){let v=0;for(const [a,b] of WIN)v=Math.max(v,ease((t-a)/0.45)*(1-ease((t-b)/0.5)));return v;}
function arc(a0,a1,R,r){const p=(a,rr)=>[CX+rr*Math.sin(a),CY-rr*Math.cos(a)];const L=a1-a0>Math.PI?1:0;
 const [x0,y0]=p(a0,R),[x1,y1]=p(a1,R),[x2,y2]=p(a1,r),[x3,y3]=p(a0,r);
 return `M${x0},${y0}A${R},${R} 0 ${L} 1 ${x1},${y1}L${x2},${y2}A${r},${r} 0 ${L} 0 ${x3},${y3}Z`;}
const mix=(c1,c2,u)=>{const h=c=>[1,3,5].map(i=>parseInt(c.substr(i,2),16));const a=h(c1),b=h(c2);return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*u)).join(',')})`;};
function render(t){
 const vis=V(t);
 if(vis<=0.001){document.getElementById('s').innerHTML='';document.getElementById('h').innerHTML='';return;}
 const intro=t<14.0;
 // which factor is being revealed in this window (for emphasis)
 let focus=null; for(const k in REVEAL){if(t>=REVEAL[k]-0.4&&t<REVEAL[k]+3.0&&t<FINAL)focus=k;}
 let svg='',html=''; let a=0; const gap=0.012; const order=['med','life','her','env'];
 for(const k of order){const f=F.find(x=>x.k==k); const span=f.v/100*2*Math.PI; const gg=intro?g(k,t):1;
  const rv=k=='med'?1:ease((t-REVEAL[k])/0.6);
  const pop=focus==k?1+0.05*Math.sin(Math.PI*cl((t-REVEAL[k])/0.9)):1;
  const dim=(focus&&focus!=k&&k!='med')?0.75:1;
  if(gg>0.001){const a1=a+span*gg;
   let fill=k=='med'?C.med:mix('#3A4468',C[k],rv);
   let op=(k=='med'?1:0.85+0.15*rv)*dim;
   const pulse=(k!='med'&&rv<1)?1+0.03*Math.sin((t-9.4)*5+(k=='her'?1.5:k=='env'?3:0)):1;
   svg+=`<path d="${arc(a+gap,a1-gap,R*(0.92+0.08*back(gg))*pulse*pop,r)}" fill="${fill}" opacity="${op}" stroke="${k!='med'&&rv<1?'rgba(255,255,255,.35)':'none'}" stroke-width="2"/>`;
   const am=a+span/2, rr=(R+r)/2+(k=='med'?8:0), lx=CX+rr*Math.sin(am), ly=CY-rr*Math.cos(am); const o=cl((gg-0.5)*2)*dim;
   if(k=='med'){
    html+=`<div style="position:absolute;left:${lx-150}px;top:${ly-44}px;width:300px;text-align:center;opacity:${o};font-weight:700;color:#2a3350">
     <div>${icon(k,26,'#2a3350')}</div><div style="font-size:13px;letter-spacing:.06em;text-transform:uppercase">Медицина</div>
     <div style="font-size:28px;font-weight:800;line-height:1.05">${intro?Math.round(10*cl((gg-0.5)*2)):10}%</div></div>`;
   } else {
    const big=k=='life'?54:40;
    const named=`<div>${icon(k,k=='life'?46:36,'#fff')}</div>
      <div style="font-size:${k=='life'?24:19}px;letter-spacing:.06em;text-transform:uppercase">${f.name.replace(' ','<br>')}</div>
      <div style="font-size:${big}px;font-weight:800;line-height:1.05">${Math.round(f.v*cl((t-REVEAL[k]-0.15)/0.7))}%</div>`;
    const bob=Math.sin((t-9.4)*3+(k=='her'?1:k=='env'?2:0))*5;
    const hidden=`<div style="font-size:${k=='life'?120:84}px;font-weight:900;line-height:1;transform:translateY(${bob}px)">?</div>`;
    html+=`<div class=sh style="position:absolute;left:${lx-150}px;top:${ly-(k=='life'?78:62)}px;width:300px;text-align:center;opacity:${o};font-weight:700">
      <div style="position:absolute;inset:0;opacity:${1-rv}">${hidden}</div><div style="opacity:${rv};transform:scale(${0.8+0.2*back(rv)})">${named}</div></div>`;
   }}
  a+=span;}
 // centre
 let n=90, sub='от чего?', co=1;
 if(intro){const s90=prog(t,9.4,0.5),s10=prog(t,7.15,0.4)*(1-s90); co=Math.max(s10,s90);
   n=Math.round(s90>0?10+80*prog(t,9.4,1.6):10*prog(t,7.15,0.75)); sub=s90>0.5?'от чего?':'медицина';}
 else if(t>=FINAL) sub='зависит от вас';
 html+=`<div class=sh style="position:absolute;left:${CX-110}px;top:${CY-58}px;width:220px;text-align:center;opacity:${co}">
   <div style="font-size:64px;font-weight:800;line-height:1">${n}%</div>
   <div style="font-size:${sub=='от чего?'?22:16}px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.9">${sub}</div></div>`;
 const sc=intro?0.85+0.15*back(cl((t-IN)/0.6)):1;
 document.getElementById('s').innerHTML=`<g opacity="${vis}" transform="translate(${CX} ${CY}) scale(${sc}) translate(${-CX} ${-CY})">${svg}</g>`;
 document.getElementById('h').innerHTML=`<div style="opacity:${vis}">${html}</div>`;
}
