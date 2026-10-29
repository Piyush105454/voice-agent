from pathlib import Path
p = Path("web/app/live/page.tsx"); s = p.read_text(encoding="utf-8")
old = '''            <Panel title="Mastery">
              {overview?.topics.length ? (
                <div className="space-y-3">
                  {overview.topics.map((t) => <MasteryBar key={t.topic_id} label={t.name} value={t.p_known} />)}
                </div>
              ) : <EmptyState title="No topics practised yet" />}
            </Panel>
            <Panel title="Next review" className="demo-hide">
              <ul className="space-y-1.5 text-sm">
                {[...(overview?.topics ?? [])].sort((a, b) => a.p_now - b.p_now).slice(0, 4).map((t) => (
                  <li key={t.topic_id} className="flex justify-between gap-2">
                    <span className="truncate">{t.name}</span>
                    <span className="num text-muted">{t.p_now < 0.7 ? "due now" : `in ${dec(t.next_review_days, 1)} d`}</span>
                  </li>
                ))}
              </ul>
            </Panel>'''
new = '''            <Panel title="Mastery & skills">
              {overview?.topics.length || progress?.skills?.length ? (
                <div className="space-y-3">
                  {overview?.topics.map((t) => <MasteryBar key={t.topic_id} label={t.name} value={t.p_known} />)}
                  {/* coaching calls: AI-judged skill scores (0-10), latest, with change over 30 days */}
                  {progress?.skills?.map((k) => (
                    <MasteryBar key={k.skill} value={k.score / 10}
                      label={`${k.label}${Math.abs(k.trend) >= 0.5 ? (k.trend > 0 ? " ↑" : " ↓") : ""}`} />
                  ))}
                  {progress?.self_confidence && (
                    <p className="text-xs text-muted">Self-reported confidence <span className="num text-sky">{progress.self_confidence.value}/10</span></p>
                  )}
                </div>
              ) : <EmptyState title="No topics practised yet" />}
            </Panel>
            {!!progress?.next_steps?.length && (
              <Panel title="Next best steps" className="demo-hide">
                <ol className="space-y-3 text-sm">
                  {progress.next_steps.map((n, i) => (
                    <li key={i}>
                      <div className="font-medium">{i + 1}. {n.title}</div>
                      <p className="mt-0.5 text-xs text-muted">{n.why}</p>
                      <span className="mt-1 inline-block rounded-full border border-line px-2 py-0.5 text-[10px] text-accent">{n.principle}</span>
                    </li>
                  ))}
                </ol>
              </Panel>
            )}
            {!!overview?.topics.length && (
              <Panel title="Next review" className="demo-hide">
                <ul className="space-y-1.5 text-sm">
                  {[...overview.topics].sort((a, b) => a.p_now - b.p_now).slice(0, 4).map((t) => (
                    <li key={t.topic_id} className="flex justify-between gap-2">
                      <span className="truncate">{t.name}</span>
                      <span className="num text-muted">{t.p_now < 0.7 ? "due now" : `in ${dec(t.next_review_days, 1)} d`}</span>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}'''
assert old in s; s = s.replace(old, new)
s = s.replace('''<Panel title="Confidence vs accuracy" className="demo-hide">''',
              '''<Panel title="Confidence vs performance" className="demo-hide">''')
p.write_text(s, encoding="utf-8")
c = Path("web/components/Charts.tsx"); t = c.read_text(encoding="utf-8")
t = t.replace('name="quiz accuracy"', 'name="measured (quiz or AI skill score)"')
c.write_text(t, encoding="utf-8")
print("ok")
