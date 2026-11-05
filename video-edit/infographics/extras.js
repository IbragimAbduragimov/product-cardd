// Extra infographics between the donut windows. t = FRONT-camera seconds (montage = t - 1.4).
// Every element appears on the word it illustrates (word timings from GigaAM, see transcript.md).
const I={
 apple:`<path d="M12 7c-1.5-1.3-4.5-1.6-6 .5-1.8 2.6-.6 7.2 1.6 9.8 1.3 1.6 2.7 2.4 4.4 1.5 1.7.9 3.1.1 4.4-1.5 2.2-2.6 3.4-7.2 1.6-9.8-1.5-2.1-4.5-1.8-6-.5zM12 7c0-2 1-3.5 3-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
 moon:`<path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>`,
 run:ICON.life,
 more:`<circle cx="6" cy="12" r="1.8" fill="currentColor"/><circle cx="12" cy="12" r="1.8" fill="currentColor"/><circle cx="18" cy="12" r="1.8" fill="currentColor"/>`,
 cig:`<path d="M3 14h13v4H3zM18 14v4M21 14v4M17 10c0-2 2-2 2-4M20 10c0-2 2-2 2-4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 3l18 18" stroke="#FF5A5A" stroke-width="2.4" stroke-linecap="round"/>`,
 wine:`<path d="M8 3h8l-.5 5a3.5 3.5 0 0 1-7 0zM12 11.5V20M8.5 20h7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><path d="M3 3l18 18" stroke="#FF5A5A" stroke-width="2.4" stroke-linecap="round"/>`,
 wind:`<path d="M3 8h11a3 3 0 1 0-3-3M3 12h15a3 3 0 1 1-3 3M3 16h7" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>`,
 drop:`<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>`,
 house:`<path d="M3 11l9-7 9 7M5 9.5V20h14V9.5M10 20v-6h4v6" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
 shield:`<path d="M12 3l8 3v6c0 4.5-3.4 8-8 9-4.6-1-8-4.5-8-9V6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M8.5 12l2.5 2.5 4.5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
 globe:`<circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18" fill="none" stroke="currentColor" stroke-width="1.8"/>`,
 bolt:`<path d="M13 2L4 14h7l-1 8 9-12h-7z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>`,
 brain:`<path d="M9 4a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 3 3h1V4zM15 4a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-3 3h-1V4z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>`,
 family:`<circle cx="7" cy="6" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="17" cy="6" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/><circle cx="12" cy="13" r="2" fill="none" stroke="currentColor" stroke-width="2"/><path d="M3 20v-4a4 4 0 0 1 8 0M13 20v-4a4 4 0 0 1 8 0M9.5 21a2.5 2.5 0 0 1 5 0" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>`,
 heart:`<path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M5 12h3l1.5-2.5 2 5 1.5-2.5h6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round"/>`,
 sugar:`<path d="M7 4h10M8 4v4l-3 5v6a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-6l-3-5V4" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><path d="M9 15h6M12 12v6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>`,
 flag:`<path d="M5 21V4M5 4h11l-2 4 2 4H5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
 check:`<path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>`,
 cross:`<path d="M6 6l12 12M18 6L6 18" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/>`};
const ic=(k,s,col)=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" style="color:${col};flex:none">${I[k]}</svg>`;
const BLUE='#4C86FF',ORANGE='#FF9433',GREEN='#3CC46B',RED='#FF5A5A';
const SC=[ // [in, out, renderer(t, enterAlpha)]
 [1.45,5.25,hook],[21.55,31.75,lifeList],[31.90,41.75,habits],   // removed by request: envGroups 46.40–53.70, control 54.00–59.95
 [60.30,68.95,stress],[73.75,80.70,fate],[81.00,93.30,family],[111.25,116.60,finale]];
function A(t,t0,d=0.45){return ease((t-t0)/d);}
function item(a,html,extra=''){return `<div style="opacity:${a};transform:translateY(${(1-a)*22}px);${extra}">${html}</div>`;}
const panel=(inner,w=590)=>`<div style="position:absolute;left:44px;top:92px;width:${w}px;padding:28px 30px 24px;border-radius:30px;box-sizing:border-box;
  background:linear-gradient(160deg,rgba(20,27,58,.80),rgba(10,14,34,.66));border:1.5px solid rgba(255,255,255,.13);box-shadow:0 20px 60px rgba(0,0,0,.35)">${inner}</div>`;
const tag=(txt,col)=>`<div style="display:inline-block;padding:7px 16px;border-radius:99px;background:${col}26;color:${col};font-size:19px;font-weight:800;letter-spacing:.12em;text-transform:uppercase;margin-bottom:18px">${txt}</div>`;
function row(a,icon,col,txt,sub){return item(a,`<div style="display:flex;align-items:center;gap:16px;margin-bottom:14px">
   <div style="width:58px;height:58px;border-radius:17px;background:${col}22;display:flex;align-items:center;justify-content:center;flex:none">${ic(icon,32,col)}</div>
   <div><div style="font-size:27px;font-weight:700;line-height:1.15">${txt}</div>${sub?`<div style="font-size:19px;font-weight:600;opacity:.7;margin-top:2px">${sub}</div>`:''}</div></div>`);}
// ---------- scenes ----------
function hook(t){return `<div class=sh style="position:absolute;left:56px;top:150px;width:600px">
  ${item(A(t,1.5),`<div style="font-size:26px;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:${BLUE}">Вопрос дня</div>`)}
  ${item(A(t,1.75),`<div style="font-size:60px;font-weight:900;line-height:1.05;margin-top:12px">От чего на самом деле зависит ваше здоровье?</div>`)}</div>`;}
function lifeList(t){return panel(tag('Образ жизни',BLUE)+
  row(A(t,21.95),'apple',BLUE,'Питание')+row(A(t,23.10),'moon',BLUE,'Сон и отдых')+row(A(t,24.65),'run',BLUE,'Физическая активность')+
  row(A(t,27.25),'more',BLUE,'…и многое другое')+
  item(A(t,29.25),`<div style="display:flex;align-items:center;gap:12px;margin-top:6px;padding-top:16px;border-top:1px solid rgba(255,255,255,.14);font-size:24px;font-weight:700">${ic('check',30,GREEN)}Повлиять можно практически на всё</div>`));}
function habits(t){const n=Math.round(200*ease((t-39.55)/0.95)), y=Math.round(15*ease((t-36.75)/0.7));
 const card=(a,icon,name,big,sub)=>item(a,`<div style="flex:1;padding:22px 20px;border-radius:24px;background:rgba(255,90,90,.10);border:1.5px solid rgba(255,90,90,.35)">
   <div style="display:flex;align-items:center;gap:12px;font-size:25px;font-weight:800">${ic(icon,36,'#fff')}${name}</div>
   <div style="font-size:66px;font-weight:900;line-height:1;margin-top:16px;color:${RED}">${big}</div>
   <div style="font-size:19px;font-weight:600;opacity:.8;margin-top:6px">${sub}</div></div>`,'flex:1;display:flex');
 return panel(tag('Отказаться от',RED)+`<div style="display:flex;gap:16px">`+
   card(A(t,33.75),'cig','Табак',t>36.7?`−${y}`:'',t>36.7?'лет жизни в среднем':'&nbsp;')+
   card(A(t,34.20),'wine','Алкоголь',t>39.5?`${n>=200?'>200':n}`:'',t>39.5?'связанных заболеваний':'&nbsp;')+`</div>`);}
function envGroups(t){const col=(a,title,items)=>item(a,`<div style="flex:1;padding:20px 18px;border-radius:22px;background:rgba(255,148,51,.10);border:1.5px solid rgba(255,148,51,.32)">
   <div style="font-size:22px;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:${ORANGE};margin-bottom:14px">${title}</div>${items}</div>`,'flex:1;display:flex');
 const li=(a,icon,txt)=>item(a,`<div style="display:flex;align-items:center;gap:10px;font-size:24px;font-weight:700;margin-bottom:12px">${ic(icon,28,ORANGE)}${txt}</div>`);
 return panel(tag('Окружающая среда',ORANGE)+`<div style="display:flex;gap:14px">`+
  col(A(t,46.45),'Физическая',li(A(t,48.15),'wind','Воздух')+li(A(t,48.75),'drop','Вода')+li(A(t,49.15),'house','Жильё'))+
  col(A(t,50.45),'Социальная',li(A(t,52.15),'shield','Безопасность'))+`</div>`);}
function control(t){const r=(a,icon,txt,ok,okA)=>item(a,`<div style="display:flex;align-items:center;gap:16px;padding:18px 20px;border-radius:22px;margin-bottom:14px;background:rgba(255,255,255,.06);opacity:${ok?1:1-0.35*okA}">
   ${ic(icon,40,'#fff')}<div style="flex:1;font-size:27px;font-weight:700;line-height:1.15">${txt}</div>
   <div style="width:52px;height:52px;border-radius:50%;display:flex;align-items:center;justify-content:center;background:${ok?GREEN:RED};transform:scale(${back(okA)});opacity:${okA}">${ic(ok?'check':'cross',30,'#fff')}</div></div>`);
 return panel(tag('Что в наших силах',ORANGE)+r(A(t,54.20),'globe','Глобальная экология',false,A(t,56.45,0.4))+r(A(t,57.65),'house','Своя микросреда',true,A(t,58.90,0.4)));}
function stress(t){const lv=ease((t-63.6)/0.6)*0.35+ease((t-64.65)/1.2)*0.6; const col=lv<0.5?ORANGE:RED;
 return panel(tag('Психологический климат',ORANGE)+
  item(A(t,63.55),`<div style="display:flex;align-items:center;gap:12px;font-size:25px;font-weight:700;margin-bottom:12px">${ic('bolt',30,col)}Напряжение<span style="margin-left:auto;font-weight:800;color:${col}">${t>64.6?'постоянное':'временное'}</span></div>
   <div style="height:18px;border-radius:9px;background:rgba(255,255,255,.12);overflow:hidden"><div style="height:100%;width:${lv*100}%;border-radius:9px;background:linear-gradient(90deg,${ORANGE},${RED})"></div></div>`)+
  item(A(t,66.05),`<div style="display:flex;align-items:center;gap:14px;margin-top:20px;padding:16px 18px;border-radius:20px;background:rgba(255,90,90,.12);border:1.5px solid rgba(255,90,90,.35);font-size:24px;font-weight:700;line-height:1.25">${ic('brain',36,RED)}Подрывает здоровье не хуже физических условий</div>`));}
function fate(t){const s=ease((t-76.2)/0.35);
 return `<div class=sh style="position:absolute;left:56px;top:140px;width:620px">
  ${item(A(t,75.5),`<div style="position:relative;display:inline-block;font-size:56px;font-weight:900;opacity:${1-0.45*s}">НЕ ПРИГОВОР<div style="position:absolute;left:-6px;top:52%;height:7px;border-radius:4px;background:${RED};width:${s*104}%"></div></div>`)}
  ${item(A(t,76.35),`<div style="font-size:24px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;opacity:.8;margin-top:22px">а</div><div style="font-size:58px;font-weight:900;line-height:1;color:${GREEN}">ПРЕДРАСПОЛО&shy;ЖЕННОСТЬ</div>`)}
  ${item(A(t,77.95),`<div style="font-size:29px;font-weight:700;line-height:1.3;margin-top:22px">Мы можем повлиять на то,<br>как проявятся гены</div>`)}</div>`;}
function family(t){return panel(tag('Семейная история',GREEN)+
  item(A(t,84.05),`<div style="font-size:22px;font-weight:600;opacity:.75;margin-bottom:14px">Если у близких родственников были:</div>`)+
  row(A(t,85.80),'heart',RED,'Сердечно-сосудистые заболевания')+row(A(t,87.55),'sugar',RED,'Диабет')+
  item(A(t,88.75),`<div style="display:flex;align-items:center;gap:14px;margin-top:8px;padding:16px 18px;border-radius:20px;background:${RED};font-size:26px;font-weight:800;transform:scale(${0.9+0.1*back(A(t,88.75,0.5))})">${ic('flag',34,'#fff')}Красный флаг</div>`)+
  item(A(t,90.80),`<div style="display:flex;align-items:center;gap:12px;margin-top:14px;font-size:23px;font-weight:700">${ic('shield',30,GREEN)}Больше внимания профилактике</div>`));}
function finale(t){return `<div class=sh style="position:absolute;left:56px;top:150px;width:620px">
  ${item(A(t,111.35),`<div style="display:flex;align-items:center;gap:12px;font-size:32px;font-weight:700;opacity:.85">${ic('shield',36,'#fff')}Медицина подстрахует</div>`)}
  ${item(A(t,113.15),`<div style="font-size:30px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;margin-top:26px;opacity:.9">но фундамент закладываете</div>`)}
  ${item(A(t,115.05,0.35),`<div style="font-size:150px;font-weight:900;line-height:.95;color:${BLUE};transform:scale(${0.85+0.15*back(A(t,115.05,0.5))});transform-origin:left">ВЫ</div>`)}</div>`;}
function render(t){let h='';
 for(const [a,b,fn] of SC){if(t<a-0.01||t>b+0.6)continue; const v=ease((t-a)/0.4)*(1-ease((t-b)/0.5)); if(v<=0.001)continue;
  h+=`<div style="position:absolute;inset:0;opacity:${v};transform:translateY(${(1-ease((t-a)/0.5))*16}px)">${fn(t)}</div>`;}
 document.getElementById('h').innerHTML=h;}
const WIN=SC.map(s=>[s[0],s[1]]);
