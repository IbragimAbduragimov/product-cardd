// Общие функции анимации. Сцена задаёт render(t); время t — секунды от начала сцены.
const C = window.CUES || {};
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const easeOut = (x) => 1 - Math.pow(1 - clamp(x), 3);
const easeInOut = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const prog = (t, start, dur) => clamp((t - start) / dur);
const $ = (id) => document.getElementById(id);

// Появление блока: прозрачность + небольшой подъём
function appear(el, t, start, dur = 0.6, dy = 26) {
  const p = easeOut(prog(t, start, dur));
  el.style.opacity = p;
  el.style.transform = `translateY(${(1 - p) * dy}px)`;
  return p;
}

// «Прорисовка» SVG-пути по длине
function draw(path, p) {
  if (!path._len) path._len = path.getTotalLength();
  path.style.strokeDasharray = path._len;
  path.style.strokeDashoffset = path._len * (1 - clamp(p));
}

// Пунктир, который проявляется по длине (маскированием через clip-rect)
function reveal(clipRect, x0, x1, p) {
  clipRect.setAttribute("width", Math.max(0, (x1 - x0) * clamp(p)));
}

// Мягкое «дыхание» всей сцены, чтобы графика не была мёртвой
function breathe(el, t, dur) {
  const s = 1 + 0.012 * (t / Math.max(dur, 0.01));
  el.style.transform = `scale(${s})`;
  el.style.transformOrigin = "540px 900px";
}
window.renderAt = (t) => { render(t); };
