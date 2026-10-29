// One-off patch: compact, view-aware top bar on /live (student = slim; advanced = full presenter tools).
const fs = require("fs");
const p = __dirname + "/../web/app/live/page.tsx";
let s = fs.readFileSync(p, "utf8");
const start = s.indexOf("      {/* top bar */}");
const end = s.indexOf("      {call && <CallBanner");
if (start < 0 || end < 0) throw new Error("top bar block not found");
const bar = `      {/* top bar: slim for students; session details + presenter tools only in the advanced view */}
      <div className="card glass sticky top-[4.5rem] z-30 mb-6 flex flex-wrap items-center gap-x-4 gap-y-2 px-4 py-2.5">
        <select aria-label="Student" value={studentId} onChange={(e) => setStudentId(e.target.value)}
          className="rounded-full border border-line bg-surface-2 px-3 py-1.5 text-sm font-medium">
          {(students.length ? students : [{ id: RAHUL, first_name: "Rahul" } as Student]).map((s) => (
            <option key={s.id} value={s.id}>{s.first_name}{s.consented === false ? " (no consent)" : ""}</option>
          ))}
        </select>
        <PillTabs id="view" label="View" size="sm" value={view} onChange={pickView}
          options={[{ value: "simple", label: <><GraduationCap size={14} aria-hidden /> Student</> },
                    { value: "advanced", label: <><Network size={14} aria-hidden /> Advanced · graph</> }]} />
        <AnimatePresence>
          {(live || view === "advanced") && feed && (
            <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -8 }}
              className="flex items-center gap-2 text-sm">
              <LiveBadge live={live} />
              {feed.topic && <span className="text-muted">{feed.topic}</span>}
              <span className="num text-muted">{clock(feed.started_at, feed.ended_at)}</span>
              <span className="chip border border-line text-muted">{feed.channel === "web" ? "Browser call" : feed.channel === "simulator" ? "Replay" : "Phone call"}</span>
              <Waveform active={live} />
            </motion.div>
          )}
        </AnimatePresence>
        <div className="ml-auto flex flex-wrap items-center gap-2">
          {view === "advanced" && (
            <>
              <span className="demo-hide text-xs text-muted" title="Realtime transport">{mode === "stream" ? "● realtime" : mode === "polling" ? "○ polling" : "…"}</span>
              <button className="btn-primary py-1.5" onClick={replay} disabled={!!busy}>
                <Play size={15} aria-hidden /> {busy === "replay" ? "Starting…" : "Replay Rahul session"}
              </button>
              <button className="btn-ghost demo-hide py-1.5" onClick={() => setBrowserCall((b) => !b)} aria-pressed={browserCall}>
                <Mic size={15} aria-hidden /> Talk in browser
              </button>
            </>
          )}
          <button className={\`demo-hide py-1.5 \${view === "simple" ? "btn-primary" : "btn-ghost"}\`} onClick={startCall} disabled={!!busy}
            title="Guru calls the student's phone (Bolna)">
            <Phone size={15} aria-hidden /> {busy === "call" ? "Calling…" : "Call my phone"}
          </button>
          {view === "advanced" && (
            <>
              <button className="btn-ghost demo-hide py-1.5" onClick={reset} disabled={!!busy} title="Reset demo data">
                <RotateCcw size={15} aria-hidden /> Reset
              </button>
              <button className="btn-ghost py-1.5" onClick={() => setDemo((d) => !d)} aria-pressed={demo}>
                {demo ? <Minimize2 size={15} aria-hidden /> : <Maximize2 size={15} aria-hidden />} Demo mode
              </button>
            </>
          )}
        </div>
      </div>

`;
s = s.slice(0, start) + bar + s.slice(end);
fs.writeFileSync(p, s);
console.log("patched");
