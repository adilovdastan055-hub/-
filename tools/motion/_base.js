// Параметры приходят в window.PARAMS. vmin-подобная единица: u = 1% от меньшей стороны.
const P = window.PARAMS || {};
const W = P._w || innerWidth, H = P._h || innerHeight, U = Math.min(W, H) / 100;
const VERT = H > W;
function css(name, v) { document.documentElement.style.setProperty(name, v); }
css('--D', (P.duration || 3) + 's');
if (P.accent) css('--accent', P.accent);
if (P.color) css('--color', P.color);
if (P.font) css('--font', `'${P.font}'`);
const ease = { outExpo: x => x >= 1 ? 1 : 1 - Math.pow(2, -10 * x), outCubic: x => 1 - Math.pow(1 - x, 3) };
function el(tag, cls, parent, text) {
  const e = document.createElement(tag); if (cls) e.className = cls;
  if (text != null) e.textContent = text; (parent || document.getElementById('wrap')).appendChild(e); return e;
}
