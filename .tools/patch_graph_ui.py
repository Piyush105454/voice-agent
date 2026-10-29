from pathlib import Path

t = Path("web/lib/types.ts"); s = t.read_text(encoding="utf-8")
old = '''  kind: "student" | "topic" | "misconception" | "strategy";
  mastery?: number | null;'''
new = '''  kind: "student" | "topic" | "misconception" | "strategy"
    // coaching side (after any call): goal, skill (0-10), self-reported confidence, mistake pattern,
    // topic practised, next step, suggested resource, what works for this student
    | "goal" | "skill" | "confidence" | "pattern" | "practice" | "next" | "resource" | "works";
  score?: number;
  trend?: number;
  value?: number | null;
  detail?: string;
  mastery?: number | null;'''
assert old in s; s = s.replace(old, new)
old = "export type Progress = { session_points: SessionPoint[] };"
new = '''export type SkillRow = { skill: string; label: string; score: number; trend: number; n: number; days_since: number };
export type NextStep = { kind: string; title: string; why: string; principle: string; priority: number };
export type Progress = {
  session_points: SessionPoint[];
  skills?: SkillRow[];
  self_confidence?: { value: number; trend: number; n: number } | null;
  next_steps?: NextStep[];
};'''
assert old in s; s = s.replace(old, new)
t.write_text(s, encoding="utf-8")

k = Path("web/components/KnowledgeGraph.tsx"); u = k.read_text(encoding="utf-8")
old = '''    if (node.kind === "student") r = 9;
    else if (node.kind === "topic") r = 6 + 6 * (node.mastery ?? 0.3);
    else if (node.kind === "misconception") r = 5 + 6 * (node.strength ?? 0.3);
    else r = 4;'''
new = '''    if (node.kind === "student") r = 9;
    else if (node.kind === "topic") r = 6 + 6 * (node.mastery ?? 0.3);
    else if (node.kind === "misconception") r = 5 + 6 * (node.strength ?? 0.3);
    else if (node.kind === "goal") r = 9;
    else if (node.kind === "skill") r = 5 + 0.7 * (node.score ?? 5);
    else if (node.kind === "confidence") r = 5 + 0.6 * (node.value ?? 5);
    else if (node.kind === "pattern") r = 6;
    else if (node.kind === "next") r = 6;
    else r = 4;'''
assert old in u; u = u.replace(old, new)
old = '''    ctx.beginPath();
    if (node.kind === "misconception") {'''
new = '''    ctx.beginPath();
    if (node.kind === "goal") {
      // five-point star: the student's own goal
      for (let i = 0; i < 10; i++) {
        const a = -Math.PI / 2 + (i * Math.PI) / 5, rr = i % 2 ? r * 0.45 : r;
        ctx[i ? "lineTo" : "moveTo"](node.x + rr * Math.cos(a), node.y + rr * Math.sin(a));
      }
      ctx.closePath();
      ctx.fillStyle = colors.accent;
      ctx.fill();
    } else if (node.kind === "resource" || node.kind === "works") {
      ctx.rect(node.x - r, node.y - r, 2 * r, 2 * r);
      ctx.fillStyle = node.kind === "resource" ? css("--sky") || "#4F8EF7" : resolve("var(--m-high)");
      ctx.globalAlpha = 0.8;
      ctx.fill();
      ctx.globalAlpha = 1;
    } else if (node.kind === "next" || node.kind === "confidence") {
      ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
      ctx.setLineDash(node.kind === "next" ? [3 / scale, 2 / scale] : []);
      ctx.lineWidth = 2 / scale;
      ctx.strokeStyle = node.kind === "next" ? colors.accent : css("--sky") || "#4F8EF7";
      ctx.stroke();
      ctx.setLineDash([]);
    } else if (node.kind === "misconception" || node.kind === "pattern") {'''
assert old in u; u = u.replace(old, new)
old = '''      } else if (node.kind === "topic") {
        ctx.fillStyle = resolve(masteryBand(node.mastery).color);
        ctx.fill();'''
new = '''      } else if (node.kind === "topic") {
        ctx.fillStyle = resolve(masteryBand(node.mastery).color);
        ctx.fill();
      } else if (node.kind === "skill") {
        ctx.fillStyle = resolve(masteryBand((node.score ?? 0) / 10).color);
        ctx.fill();
      } else if (node.kind === "practice") {
        ctx.fillStyle = resolve("var(--m-high)");
        ctx.globalAlpha = 0.55;
        ctx.fill();
        ctx.globalAlpha = 1;'''
assert old in u; u = u.replace(old, new)
old = '''      ctx.fillStyle = colors.misc;
      ctx.globalAlpha = 0.35 + 0.65 * (node.strength ?? 0.5);'''
new = '''      ctx.fillStyle = colors.misc;
      ctx.globalAlpha = node.kind === "pattern" ? 0.75 : 0.35 + 0.65 * (node.strength ?? 0.5);'''
assert old in u; u = u.replace(old, new)
old = '''      ctx.fillStyle = age < 1 ? colors.accent : node.kind === "misconception" ? colors.misc : colors.text;
      const val =
        node.kind === "topic" && node.mastery != null ? ` · ${node.mastery.toFixed(2)}`
        : node.kind === "misconception" && node.strength != null ? ` · ${node.strength.toFixed(2)}` : "";
      ctx.fillText(node.label + val, node.x, node.y + r + 3);'''
new = '''      ctx.fillStyle = age < 1 ? colors.accent
        : node.kind === "misconception" || node.kind === "pattern" ? colors.misc
        : node.kind === "practice" || node.kind === "works" || node.kind === "resource" ? colors.muted : colors.text;
      const arrow = (t?: number) => (t == null || Math.abs(t) < 0.5 ? "" : t > 0 ? " ↑" : " ↓");
      const val =
        node.kind === "topic" && node.mastery != null ? ` · ${node.mastery.toFixed(2)}`
        : node.kind === "misconception" && node.strength != null ? ` · ${node.strength.toFixed(2)}`
        : node.kind === "skill" && node.score != null ? ` · ${node.score.toFixed(1)}${arrow(node.trend)}` : "";
      ctx.fillText((node.id === hover && node.detail ? node.detail : node.label) + val, node.x, node.y + r + 3);'''
assert old in u; u = u.replace(old, new)
old = '''  const linkColor = (l: GraphLink) =>
    l.kind === "HOLDS" ? colors.misc : l.kind === "PREREQUISITE_OF" ? colors.muted : colors.line;'''
new = '''  const linkColor = (l: GraphLink) =>
    l.kind === "HOLDS" || l.kind === "HAS_PATTERN" || l.kind === "WEAKENS" ? colors.misc
    : l.kind === "NEXT_STEP" || l.kind === "HAS_GOAL" ? colors.accent
    : l.kind === "PREREQUISITE_OF" ? colors.muted : colors.line;'''
assert old in u; u = u.replace(old, new)
u = u.replace('''          linkLineDash={(l: any) => (l.kind === "PREREQUISITE_OF" ? [4, 3] : null)}
          linkDirectionalArrowLength={(l: any) => (l.kind === "PREREQUISITE_OF" ? 4 : 0)}''',
'''          linkLineDash={(l: any) => (l.kind === "PREREQUISITE_OF" || l.kind === "NEXT_STEP" || l.kind === "WEAKENS" ? [4, 3] : null)}
          linkDirectionalArrowLength={(l: any) => (l.kind === "PREREQUISITE_OF" || l.kind === "NEXT_STEP" || l.kind === "WEAKENS" ? 4 : 0)}''')
old = '''      {item(<span className="w-4 border-t border-dashed border-muted" />, "Prerequisite")}'''
new = '''      {item(<span className="w-4 border-t border-dashed border-muted" />, "Prerequisite")}
      {item(<span className="text-[11px] leading-none text-accent">★</span>, "Goal")}
      {item(<span className="h-2.5 w-2.5 rounded-full border border-dashed border-accent" />, "Next step")}
      {item(<span className="h-2.5 w-2.5 rounded-full border-2 border-sky" />, "Confidence (self-reported)")}
      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-high/60" />, "Practised")}
      {item(<span className="h-2.5 w-2.5 rotate-45 bg-misc/75" />, "Mistake pattern")}
      {item(<span className="h-2.5 w-2.5 bg-m-high/80" />, "Works for them")}
      {item(<span className="h-2.5 w-2.5 bg-sky/80" />, "Book / method")}'''
assert old in u; u = u.replace(old, new)
u = u.replace('''      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-low" />, "Topic: needs practice")}''',
              '''      {item(<span className="h-2.5 w-2.5 rounded-full bg-m-low" />, "Topic / skill: needs practice")}''')
k.write_text(u, encoding="utf-8")
print("ok")
