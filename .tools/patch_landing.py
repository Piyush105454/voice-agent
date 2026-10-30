from pathlib import Path

p = Path("web/app/page.tsx"); s = p.read_text(encoding="utf-8")


def rep(old, new, count=1):
    global s
    assert old in s, old[:70]
    s = s.replace(old, new, count)


# 1) compact hero: text column wider, no forced 700px height, tighter padding
rep('''<div className="mx-auto grid max-w-7xl items-center gap-10 px-5 pb-16 pt-10 md:px-8 lg:min-h-[700px] lg:grid-cols-[1.08fr_1fr] lg:pb-20 lg:pt-12">''',
    '''<div className="mx-auto grid max-w-7xl items-center gap-6 px-5 pb-4 pt-2 md:px-8 lg:grid-cols-[1.2fr_0.8fr] lg:gap-8">''')
rep('''className="mb-7 inline-flex items-center gap-2 rounded-full border border-accent/30''',
    '''className="mb-4 inline-flex items-center gap-2 rounded-full border border-accent/30''')
rep('''<h1 className="font-serif text-[clamp(44px,6vw,84px)] leading-[1.02] tracking-tight">''',
    '''<h1 className="font-serif text-[clamp(32px,3.7vw,54px)] leading-[1.05] tracking-tight">''')
rep('''className="mt-6 max-w-xl text-lg leading-relaxed text-muted md:text-xl">''',
    '''className="mt-4 max-w-2xl text-base leading-relaxed text-muted md:text-lg">''')
rep('''<div className="mt-6 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm text-muted">''',
    '''<div className="mt-4 inline-flex items-center gap-2 rounded-full border border-line px-3 py-1.5 text-sm text-muted">''')
rep('''className="mt-8 flex flex-wrap items-center gap-3">''', '''className="mt-4 flex flex-wrap items-center gap-3">''')
rep('''className="btn-primary group px-7 py-3.5 text-base shadow''', '''className="btn-primary group px-6 py-3 text-base shadow''')
rep('''<Link href="/privacy" className="btn-ghost px-6 py-3.5 text-base">Privacy & Audit</Link>
            </motion.div>''', '''<Link href="/privacy" className="btn-ghost px-5 py-3 text-base">Privacy & Audit</Link>
            </motion.div>''')
rep('''className="mt-8 flex flex-wrap gap-x-5 gap-y-2 text-sm text-muted">''', '''className="mt-4 flex flex-wrap gap-x-5 gap-y-1.5 text-sm text-muted">''')

# 2) phone mock-up scaled down on desktop so it shares the first screen with the text
rep('''            <HeroCall />
          </motion.div>
        </div>
      </section>''', '''            <div className="flex items-center justify-center lg:h-[470px]">
              <div className="w-full lg:origin-center lg:scale-[0.78]"><HeroCall /></div>
            </div>
          </motion.div>
        </div>

        {/* the four facts + portals now sit on the first screen, under the hero */}
        <div className="relative z-10 border-t border-line">
          <div className="mx-auto grid max-w-7xl grid-cols-2 gap-x-6 gap-y-3 px-5 py-4 md:grid-cols-4 md:px-8">
            {FACTS.map(([big, small], i) => (
              <motion.div key={small} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 1.2 + i * 0.08, duration: 0.45, ease }}>
                <div className="font-serif text-lg text-text md:text-xl">{big}</div>
                <div className="text-xs text-muted md:text-sm">{small}</div>
              </motion.div>
            ))}
          </div>
          <div className="mx-auto max-w-7xl px-5 pb-3 text-xs tracking-wide text-muted md:px-8">
            <span className="inline-block rounded-full border border-line bg-surface-2/60 px-3 py-1 text-muted">
              Live Grounding Across NCS (ncs.gov.in) · Skill India (PMKVY) · DGT / NCVT · AICTE / SWAYAM · National Scholarship Portal
            </span>
          </div>
        </div>
      </section>''')

# 3) remove the old facts section that sat below the fold
start = s.index("      {/* measured facts + stack */}")
end = s.index("      <HowItWorks />")
s = s[:start] + s[end:]

p.write_text(s, encoding="utf-8"); print("ok")
