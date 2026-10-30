from pathlib import Path


def edit(path, pairs):
    p = Path(path); s = p.read_text(encoding="utf-8")
    for old, new in pairs:
        assert old in s, (path, old[:80])
        s = s.replace(old, new, 1)
    p.write_text(s, encoding="utf-8")


edit("web/components/SimpleView.tsx", [
    # real graph for real students; the sample graph only for the built-in demo student with no calls yet
    ('''  const activeGraph = useMemo(() => {
    if (graphData && graphData.nodes && graphData.nodes.length >= 5) {
      return graphData;
    }
    return DEFAULT_GRAPH;
  }, [graphData]);''',
     '''  const activeGraph = useMemo<GraphData>(() => {
    if (graphData && graphData.nodes && graphData.nodes.length > 0) return graphData;
    // the sample graph belongs to the built-in demo student only; anyone else sees an honest empty state
    return isRahul && ov.sessions.length === 0 ? DEFAULT_GRAPH : { nodes: [], links: [] };
  }, [graphData, isRahul, ov.sessions.length]);'''),
    ('''{ov.sessions.length > 0 ? ov.sessions.length : 3} calls | {activeGraph.nodes.length} graph nodes''',
     '''{ov.sessions.length} call{ov.sessions.length === 1 ? "" : "s"} | {activeGraph.nodes.length} graph nodes'''),
    ('''            <KnowledgeGraph data={activeGraph} height={440} />''',
     '''            {activeGraph.nodes.length > 0 ? <KnowledgeGraph data={activeGraph} height={440} /> : (
              <div className="grid h-[440px] place-items-center px-6 text-center text-sm text-muted">
                <div>
                  <div className="font-serif text-lg text-text">No memory graph yet</div>
                  <p className="mt-1 max-w-sm text-xs">It builds from {firstName}&apos;s calls. If calls exist but nothing shows, the graph database may not be connected.</p>
                </div>
              </div>
            )}'''),
    # "Extracted memory" from the student's real notes (the learner profile Guru writes after every call)
    ('''            <div className="flex flex-col gap-1.5">
              <div className="rounded-lg border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">
                Class 10 rural student in Sitapur, UP; interested in hands-on electrical/technical work; needs low-fee government course and early earning pathway.
              </div>
              <div className="rounded-lg border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">
                Government ITI — Electrician / Fitter Trade (NCVT) — Admission & NSP Scholarship
              </div>
              <div className="rounded-lg border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">
                Responds best when admission and scholarship steps are broken into a clear 3-document checklist
              </div>
            </div>''',
     '''            <div className="flex flex-col gap-1.5">
              {memoryLines.length ? memoryLines.map((t, i) => (
                <div key={i} className="rounded-lg border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">{t}</div>
              )) : (
                <div className="rounded-lg border border-dashed border-line px-3 py-1.5 text-xs text-muted">
                  Guru writes these notes after each call: who they are, their open problems and what works for them.
                </div>
              )}
            </div>'''),
    ('''  const loadingCall = !!sess''', '''  const memoryLines = useMemo(() => {
    const p = ov.memory?.find((f) => (f.content as { type?: string }).type === "profile")?.content as
      { about?: string; challenges?: string[]; what_works?: string[]; goal_in_their_words?: string } | undefined;
    if (!p) return [];
    return [p.about, p.goal_in_their_words && `Goal: ${p.goal_in_their_words}`, p.challenges?.[0] && `Working on: ${p.challenges[0].split(";")[0]}`,
      p.what_works?.[0] && `Works for them: ${p.what_works[0]}`].filter(Boolean) as string[];
  }, [ov.memory]);
  const loadingCall = !!sess'''),
])
print("ok")
