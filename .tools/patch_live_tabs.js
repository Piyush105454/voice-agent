// One-off patch: sliding-pill view tabs + animated cross-fade between Student and Advanced views on /live.
const fs = require("fs");
const p = __dirname + "/../web/app/live/page.tsx";
let s = fs.readFileSync(p, "utf8");
const rep = (a, b) => { if (!s.includes(a)) throw new Error("missing: " + a.slice(0, 80)); s = s.replace(a, b); };

rep(`        <div className="flex rounded-full border border-line p-1 text-sm" role="tablist" aria-label="View">
          {(["simple", "advanced"] as const).map((v) => (
            <button key={v} role="tab" aria-selected={view === v} onClick={() => pickView(v)}
              className={\`rounded-full px-3.5 py-1 \${view === v ? "bg-surface-2 text-text" : "text-muted hover:text-text"}\`}>
              {v === "simple" ? "Student" : "Advanced · graph"}
            </button>
          ))}
        </div>`,
`        <PillTabs id="view" label="View" size="sm" value={view} onChange={pickView}
          options={[{ value: "simple", label: <><GraduationCap size={14} aria-hidden /> Student</> },
                    { value: "advanced", label: <><Network size={14} aria-hidden /> Advanced · graph</> }]} />`);

rep(`      <div className="card mb-4 flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-3">`,
    `      <div className="card glass sticky top-[4.5rem] z-30 mb-6 flex flex-wrap items-center gap-x-5 gap-y-3 px-5 py-3">`);

rep(`      {view === "simple" ? (
        error && !loading ? <div className="card"><ErrorState message={error} retry={() => load(studentId)} /></div>
        : !overview ? <div className="mx-auto max-w-5xl space-y-4"><Skeleton className="h-28" /><Skeleton className="h-64" /></div>
        : <SimpleView ov={overview} feed={feed} onActivity={refresh} />
      ) : (<>`,
`      <AnimatePresence mode="wait" initial={false}>
      {view === "simple" ? (
        <motion.div key="simple" initial={{ opacity: 0, x: -24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 24 }}
          transition={{ duration: 0.35, ease: [0.2, 0.7, 0.2, 1] }}>
        {error && !loading ? <div className="card"><ErrorState message={error} retry={() => load(studentId)} /></div>
        : !overview ? <div className="mx-auto max-w-6xl space-y-4"><div className="skeleton-shimmer h-28 rounded-card" /><div className="skeleton-shimmer h-[420px] rounded-card" /></div>
        : <SimpleView ov={overview} feed={feed} onActivity={refresh} />}
        </motion.div>
      ) : (<motion.div key="advanced" initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -24 }}
          transition={{ duration: 0.35, ease: [0.2, 0.7, 0.2, 1] }}>`);

// close the advanced fragment + AnimatePresence
const idx = s.lastIndexOf("      </>)}");
if (idx < 0) throw new Error("advanced close missing");
s = s.slice(0, idx) + "      </motion.div>)}\n      </AnimatePresence>" + s.slice(idx + "      </>)}".length);

rep(`import { Check, Copy, Maximize2, Mic, Minimize2, Phone, Play, RotateCcw, Sparkles } from "lucide-react";`,
    `import { Check, Copy, GraduationCap, Maximize2, Mic, Minimize2, Network, Phone, Play, RotateCcw, Sparkles } from "lucide-react";`);
rep(`import KnowledgeGraph, { GraphLegend } from "@/components/KnowledgeGraph";`,
    `import KnowledgeGraph, { GraphLegend } from "@/components/KnowledgeGraph";\nimport { PillTabs } from "@/components/motion";`);
fs.writeFileSync(p, s);
console.log("patched");
