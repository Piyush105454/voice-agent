from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


edit("web/components/KnowledgeGraph.tsx", [
    # a tiny dependency-free "do not overlap" force (d3 forces are plain functions with an initialize hook)
    ('''export default function KnowledgeGraph(''',
     '''/** Pushes nodes apart when they sit closer than `min` px, so circles and their labels do not pile up. */
function spreadForce(min = 54) {
  let nodes: any[] = [];
  const force = (alpha: number) => {
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = (b.x ?? 0) - (a.x ?? 0), dy = (b.y ?? 0) - (a.y ?? 0);
        const d = Math.hypot(dx, dy) || 0.01;
        if (d >= min) continue;
        const k = ((min - d) / d) * 0.5 * Math.max(alpha, 0.1);
        a.vx -= dx * k; a.vy -= dy * k; b.vx += dx * k; b.vy += dy * k;
      }
    }
  };
  force.initialize = (n: any[]) => { nodes = n; };
  return force;
}

export default function KnowledgeGraph('''),
    ('''    g.d3Force("charge")?.strength(-340);
    g.d3Force("link")?.distance((l: any) => (l.kind === "PREREQUISITE_OF" ? 95 : 70));''',
     '''    const charge = g.d3Force("charge");
    charge?.strength(-320);
    charge?.distanceMax?.(240);   // far-away nodes stop repelling each other, so nothing drifts off and shrinks the fit
    g.d3Force("link")?.distance((l: any) => (l.kind === "PREREQUISITE_OF" ? 95 : l.kind === "HAS_GOAL" ? 110 : 78));
    g.d3Force("spread", spreadForce());'''),
    # refit whenever the canvas size changes, not only when the node set changes
    ('''  useEffect(() => {
    fg.current?.d3ReheatSimulation?.();
  }, [graph]);
''', '''  useEffect(() => {
    fg.current?.d3ReheatSimulation?.();
  }, [graph]);
  useEffect(() => {
    const t = setTimeout(() => fg.current?.zoomToFit?.(300, 50), 350);   // window resized / layout settled: refit
    return () => clearTimeout(t);
  }, [width]);
'''),
    ('''            if (fittedFor.current !== nodeKey) {
              fittedFor.current = nodeKey;
              fg.current?.zoomToFit?.(500, 50);
            }''', '''            const key = `${nodeKey}|${Math.round(width / 40)}`;
            if (fittedFor.current !== key) {
              fittedFor.current = key;
              fg.current?.zoomToFit?.(500, 50);
            }'''),
    ('''          enableNodeDrag={interactive}''', '''          enableNodeDrag={interactive}
          minZoom={0.45}'''),
])
edit("web/components/SimpleView.tsx", [
    ('''<KnowledgeGraph data={activeGraph} height={380} />''', '''<KnowledgeGraph data={activeGraph} height={440} />'''),
])
print("ok")
