// One-off patch: make components theme-aware (light sky default / dark).
const fs = require("fs");
const W = __dirname + "/../web/";
function patch(rel, pairs) {
  let s = fs.readFileSync(W + rel, "utf8");
  for (const [a, b] of pairs) { if (!s.includes(a)) throw new Error(rel + " missing: " + a.slice(0, 80)); s = s.split(a).join(b); }
  fs.writeFileSync(W + rel, s);
}

// headline accent words: italic serif in the accent colour (the shimmer stays available for other places)
patch("components/motion.tsx", [[
  `className={\`inline-block \${highlight.includes(w.replace(/[.,]/g, "")) ? "text-shimmer" : ""}\`}`,
  `className={\`inline-block \${highlight.includes(w.replace(/[.,]/g, "")) ? "hl" : ""}\`}`]]);

// orb: dark edge only in dark theme
patch("components/VoiceOrb.tsx", [[`${"${c.a}"}, #0b0c0e 85%)`, `${"${c.a}"}, var(--orb-edge) 85%)`]]);

// graph: student node uses page colours
patch("components/KnowledgeGraph.tsx", [
  [`ctx.fillStyle = "#07080A";`, `ctx.fillStyle = css("--bg") || "#07080A";`],
  [`ctx.strokeStyle = "#FFFFFF";`, `ctx.strokeStyle = colors.text;`],
]);

// how-it-works diagram
patch("components/landing/HowItWorks.tsx", [
  [`stroke="#3a4150"`, `stroke="var(--muted)" strokeOpacity={0.45}`],
  [`fill="#07080A" stroke="#fff"`, `fill="var(--bg)" stroke="var(--text)"`],
  [`fill="#F2F3F5" fontSize={11}`, `fill="var(--text)" fontSize={11}`],
  [`fill="#8B93A1" fontSize={10}`, `fill="var(--muted)" fontSize={10}`],
]);

// hero: dot grid colour + the phone always renders in the dark palette (phone screens are dark)
patch("app/page.tsx", [[`[background-image:radial-gradient(rgba(255,255,255,.07)_1px,transparent_1px)]`, `[background-image:radial-gradient(var(--dot)_1px,transparent_1px)]`]]);
patch("components/landing/HeroCall.tsx", [[
  `<div className="absolute left-1/2 top-1/2 h-[560px] w-[280px] -translate-x-1/2 -translate-y-1/2 rounded-[44px]`,
  `<div data-theme="dark" className="absolute left-1/2 top-1/2 h-[560px] w-[280px] -translate-x-1/2 -translate-y-1/2 rounded-[44px]`]]);

// parent language toggle: ink pill like the other primary actions
patch("app/parent/[id]/page.tsx", [[`lang === l ? "bg-accent text-black" : "text-muted"`, `lang === l ? "bg-[var(--btn-bg)] text-[var(--btn-fg)]" : "text-muted"`]]);

// practise top bar: glass, below the floating nav
patch("app/live/page.tsx", [[`<div className="card glass sticky top-[4.5rem] z-30 mb-6`, `<div className="liquid sticky top-[5.5rem] z-30 mb-6 rounded-2xl`]]);
console.log("patched");
