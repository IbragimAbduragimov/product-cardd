// t = FRONT-camera seconds. Word timings: "медицина" 5.59, "десять процентов" 7.23-7.95,
// "оставшиеся девяносто" 9.36-10.30, "каждый фактор" 11.72; next chapter starts 14.29.
const C={med:'#E9EEF7',life:'#2F6BFF',env:'#F2801E',her:'#2EAA55'};
const F=[{k:'med',name:'Медицина',v:10},{k:'life',name:'Образ жизни',v:50},{k:'env',name:'Окружающая среда',v:20},{k:'her',name:'Наследственность',v:20}];
const cl=(x,a=0,b=1)=>Math.min(b,Math.max(a,x));
const ease=u=>{u=cl(u);return u<.5?4*u*u*u:1-Math.pow(-2*u+2,3)/2};
const back=u=>{u=cl(u);const c1=1.4,c3=c1+1;return 1+c3*Math.pow(u-1,3)+c1*Math.pow(u-1,2)};
const prog=(t,a,d)=>ease((t-a)/d);
// global in/out
const IN=5.45, OUT=13.35;
function vis(t){return ease((t-IN)/0.45)*(1-ease((t-OUT)/0.5));}
// segment growth times
const GROW={med:[7.15,0.75],life:[9.40,0.70],env:[10.05,0.55],her:[10.55,0.55]};
const g=(k,t)=>prog(t,GROW[k][0],GROW[k][1]);
const ICON={
 med:`<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>`,
 life:`<circle cx="14.5" cy="4" r="2.2" fill="currentColor"/><path d="M8 21l3.2-6.2 3.3 2.7V22M6.5 11.5l3.5-3.2 4.2.6 2.3 3.6 3 .9M10 8.3l1.6 6.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>`,
 env:`<path d="M12 22v-7M12 15c-4.5 0-7-2.8-7-6.3S8 2 12 2s7 3.2 7 6.7-2.5 6.3-7 6.3z" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M12 15l-3-3M12 12.5l2.6-2.6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>`,
 her:`<path d="M7 2c0 5 10 5 10 10S7 17 7 22M17 2c0 5-10 5-10 10s10 5 10 10M8.5 5h7M8.5 19h7M10 9.2h4M10 14.8h4" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>`};
const icon=(k,s,col)=>`<svg width="${s}" height="${s}" viewBox="0 0 24 24" style="color:${col}">${ICON[k]}</svg>`;
