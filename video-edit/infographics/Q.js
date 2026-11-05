// Teaser donut (based on variant A). MODE='Q1' (question marks) or 'Q2' (redacted names).
// Reveal demo: at chapter "образ жизни" (14.29) the donut comes back and opens that factor.
const CX=330,CY=350,R=270,r=112;
const REVEAL={life:14.35};            // later: env 42.2, her 69.8
const W2=[14.10,16.70];               // second appearance window (reveal)
function arc(a0,a1,R,r){const p=(a,rr)=>[CX+rr*Math.sin(a),CY-rr*Math.cos(a)];const L=a1-a0>Math.PI?1:0;
 const [x0,y0]=p(a0,R),[x1,y1]=p(a1,R),[x2,y2]=p(a1,r),[x3,y3]=p(a0,r);
 return `M${x0},${y0}A${R},${R} 0 ${L} 1 ${x1},${y1}L${x2},${y2}A${r},${r} 0 ${L} 0 ${x3},${y3}Z`;}
const mix=(c1,c2,u)=>{const h=c=>[1,3,5].map(i=>parseInt(c.substr(i,2),16));const a=h(c1),b=h(c2);return `rgb(${a.map((v,i)=>Math.round(v+(b[i]-v)*u)).join(',')})`;};
function render(t){
 const V=Math.max(vis(t), ease((t-W2[0])/0.4)*(1-ease((t-W2[1])/0.5)));
 let svg='',html=''; let a=0; const gap=0.012; const order=['med','life','her','env'];
 for(const k of order){const f=F.find(x=>x.k==k); const span=f.v/100*2*Math.PI; const gg=t>W2[0]-0.1?1:g(k,t);
  const rv=REVEAL[k]?ease((t-REVEAL[k])/0.6):0;   // 0 hidden .. 1 revealed
  if(gg>0.001){const a1=a+span*gg;
   let fill=C[k], op=1;
   if(k!='med'&&MODE=='Q1'){fill=mix('#3A4468',C[k],rv); op=0.85+0.15*rv;}
   if(k=='med'&&t>9.3) op=0.75;
   const pulse=(k!='med'&&rv<1&&MODE=='Q1')?1+0.03*Math.sin((t-9.4)*5+(k=='her'?1.5:k=='env'?3:0)):1;
   svg+=`<path d="${arc(a+gap,a1-gap,R*(0.92+0.08*back(gg))*pulse,r)}" fill="${fill}" opacity="${op}" stroke="${MODE=='Q1'&&k!='med'&&rv<1?'rgba(255,255,255,.35)':'none'}" stroke-width="2"/>`;
   const am=a+span/2, rr=(R+r)/2+(k=='med'?8:0), lx=CX+rr*Math.sin(am), ly=CY-rr*Math.cos(am); const o=cl((gg-0.5)*2);
   if(k=='med'){
    html+=`<div style="position:absolute;left:${lx-150}px;top:${ly-44}px;width:300px;text-align:center;opacity:${o};font-weight:700;color:#2a3350">
     <div>${icon(k,26,'#2a3350')}</div><div style="font-size:13px;letter-spacing:.06em;text-transform:uppercase">Медицина</div>
     <div style="font-size:28px;font-weight:800;line-height:1.05">${Math.round(10*o)}%</div></div>`;
   } else {
    const big=k=='life'?54:40;
    // revealed label
    const named=`<div>${icon(k,k=='life'?46:36,'#fff')}</div>
      <div style="font-size:${k=='life'?24:19}px;letter-spacing:.06em;text-transform:uppercase">${f.name.replace(' ','<br>')}</div>
      <div style="font-size:${big}px;font-weight:800;line-height:1.05">${f.v}%</div>`;
    let hidden;
    if(MODE=='Q1'){
      const bob=Math.sin((t-9.4)*3+(k=='her'?1:k=='env'?2:0))*5;
      hidden=`<div style="font-size:${k=='life'?120:84}px;font-weight:900;line-height:1;transform:translateY(${bob}px);color:#fff">?</div>`;
    } else {
      const sh=((t*0.9+(k=='her'?.3:k=='env'?.6:0))%1)*240-60;
      const bar=(w,h)=>`<div style="width:${w}px;height:${h}px;margin:5px auto;border-radius:${h/2}px;background:linear-gradient(90deg,rgba(255,255,255,.28) 0%,rgba(255,255,255,.28) ${sh}%,rgba(255,255,255,.75) ${sh+18}%,rgba(255,255,255,.28) ${sh+36}%)"></div>`;
      hidden=`<div style="font-size:${k=='life'?40:30}px;font-weight:900;opacity:.9">?</div>${bar(k=='life'?150:110,k=='life'?18:14)}${k=='life'?bar(110,18):''}
        <div style="font-size:${big}px;font-weight:800;line-height:1.05">${Math.round(f.v*o)}%</div>`;
    }
    html+=`<div class=sh style="position:absolute;left:${lx-150}px;top:${ly-(k=='life'?78:62)}px;width:300px;text-align:center;opacity:${o};font-weight:700">
      <div style="position:absolute;inset:0;opacity:${1-rv}">${hidden}</div><div style="opacity:${rv};transform:scale(${0.8+0.2*back(rv)})">${named}</div></div>`;
   }}
  a+=span;}
 const show90=prog(t,9.4,0.5), show10=prog(t,7.15,0.4)*(1-show90);
 const n=Math.round(show90>0?10+80*prog(t,9.4,1.6):10*prog(t,7.15,0.75));
 const sub=show90>0.5?(MODE=='Q1'?'от чего?':'3 фактора'):'медицина';
 html+=`<div class=sh style="position:absolute;left:${CX-110}px;top:${CY-58}px;width:220px;text-align:center;opacity:${Math.max(show10,show90)}">
   <div style="font-size:64px;font-weight:800;line-height:1">${n}%</div>
   <div style="font-size:${MODE=='Q1'&&show90>.5?22:16}px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;opacity:.9">${sub}</div></div>`;
 document.getElementById('s').innerHTML=`<g opacity="${V}" transform="translate(${CX} ${CY}) scale(${0.85+0.15*back(cl((t-IN)/0.6))}) translate(${-CX} ${-CY})">${svg}</g>`;
 document.getElementById('h').innerHTML=`<div style="opacity:${V}">${html}</div>`;
}
