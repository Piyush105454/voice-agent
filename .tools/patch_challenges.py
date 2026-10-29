from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:70])
        s = s.replace(old, new)
    p.write_text(s, encoding="utf-8")


edit("api/learning_graph.py", [
    ('''OWNED_KINDS = ("confidence", "pattern", "practice", "next", "resource", "works")''',
     '''OWNED_KINDS = ("confidence", "pattern", "practice", "next", "resource", "works", "challenge")


def challenge_status(text: str) -> tuple[str, float]:
    """'problem; root cause; next action; status improving' -> ('problem', 0.5). new 0, improving 0.5, solved 1."""
    low = text.lower()
    value = 1.0 if "solved" in low else 0.5 if "improving" in low else 0.0
    return text.split(";")[0].strip(), value'''),
    # follow-up on open problems comes first: that is what a mentor does
    ('''    for t in (prof.get("next_topics") or [])[:1]:''',
     '''    open_ch = [c for c in (prof.get("challenges") or []) if challenge_status(c)[1] < 1]
    for c in open_ch[:1]:
        problem, value = challenge_status(c)
        parts = [x.strip() for x in c.split(";")]
        step = parts[2] if len(parts) > 2 else ""
        steps.append({"kind": "follow_up", "title": f"Follow up: {_short(problem, 60)}", "priority": 0.9 - 0.1 * value,
                      "why": (f"Check the step agreed last time: {_short(step, 90)}. " if step else "")
                             + "Planning when and how, then checking back, makes people actually do it.",
                      "principle": "Implementation intentions and follow-up (Gollwitzer 1999)"})
    for t in (prof.get("next_topics") or [])[:1]:'''),
    ('''    for i, w in enumerate((prof.get("what_works") or [])[:3]):''',
     '''    for i, c in enumerate((prof.get("challenges") or [])[:4]):
        problem, value = challenge_status(c)
        node(f"ch:{sid}:{i}", "challenge", _short(problem), "FACES", value=value, detail=c)
    for i, w in enumerate((prof.get("what_works") or [])[:3]):'''),
])

# frontend: graph + journal card
edit("web/lib/types.ts", [
    ('''    | "goal" | "skill" | "confidence" | "pattern" | "practice" | "next" | "resource" | "works";''',
     '''    | "goal" | "skill" | "confidence" | "pattern" | "practice" | "next" | "resource" | "works" | "challenge";'''),
    ('''  what_works?: string[]; watch_outs?: string[]; direction?: string; next_call_plan?: string; updated_at?: string;''',
     '''  what_works?: string[]; watch_outs?: string[]; direction?: string; next_call_plan?: string; updated_at?: string;
  challenges?: string[]; solutions_tried?: string[]; goal_in_their_words?: string;'''),
])
edit("web/components/KnowledgeGraph.tsx", [
    ('''    else if (node.kind === "pattern") r = 6;''',
     '''    else if (node.kind === "pattern") r = 6;
    else if (node.kind === "challenge") r = 8;'''),
    ('''      } else if (node.kind === "skill") {''',
     '''      } else if (node.kind === "challenge") {
        // a problem the person brought: red new, amber improving, green solved
        ctx.fillStyle = resolve(masteryBand(node.value ?? 0).color);
        ctx.fill();
        ctx.lineWidth = 2 / scale;
        ctx.strokeStyle = colors.text;
        ctx.stroke();
      } else if (node.kind === "skill") {'''),
    ('''      {item(<span className="text-[11px] leading-none text-accent">★</span>, "Goal")}''',
     '''      {item(<span className="text-[11px] leading-none text-accent">★</span>, "Goal")}
      {item(<span className="h-2.5 w-2.5 rounded-full border border-text bg-m-low" />, "Problem: new / improving / solved")}'''),
])
edit("web/components/JournalPanel.tsx", [
    ('''  const rows: [string, string | string[] | undefined][] = [
    ["What drives you", p.motivation], ["Your confidence", p.confidence_pattern],
    ["What works for you", p.what_works], ["Keep fixing", p.recurring_mistakes],
  ];''',
     '''  const rows: [string, string | string[] | undefined][] = [
    ["What you are working on", p.challenges], ["Tried so far", p.solutions_tried],
    ["What drives you", p.motivation], ["Your confidence", p.confidence_pattern],
    ["What works for you", p.what_works], ["Keep fixing", p.recurring_mistakes],
  ];'''),
])
print("ok")
