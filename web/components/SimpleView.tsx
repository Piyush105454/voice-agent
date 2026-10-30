"use client";
import { AnimatePresence, motion } from "framer-motion";
import { Check, ExternalLink, Globe, Search, Sparkles } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import KnowledgeGraph, { GraphLegend } from "@/components/KnowledgeGraph";
import { api } from "@/lib/api";
import type { Feed, GraphData, Line, Overview } from "@/lib/types";

const TABS = ["Latest call", "Previous", "Earlier"] as const;   // newest first
const LANG_LABEL: Record<string, string> = { hi: "Hindi", en: "English", "hi-en": "Hinglish" };

const SEED_TRANSCRIPT_RAHUL = [
  {
    speaker: "guru",
    text: "Hello Rahul! Welcome to the Guruji career helpline. Tell me about your educational background and what field or skill you want to pursue.",
  },
  {
    speaker: "student",
    text: "Hello Guruji. I have completed Class 10 and my family budget is limited. Which government technical course will help me learn practical electrical work and start earning early?",
  },
  {
    speaker: "guru",
    text: "Rahul, based on official government portals, two verified pathways fit your goal best: first, 'Government ITI — Electrician or Fitter Trade' (2 years, NCVT certified, government fee ₹1,000 to ₹5,000 per year, source: https://dgt.gov.in). Second, 'PMKVY 4.0 Skill India' short-term training which is 100% free (₹0 fee). Are you more interested in electrical wiring and motor repair or computer skills?",
  },
  {
    speaker: "student",
    text: "I am very interested in electrical wiring and motor repair. How do I get admission into Government ITI Electrician, and is there any government scholarship?",
  },
  {
    speaker: "guru",
    text: "Great choice! For Government ITI Electrician, you need Class 10 with Science and Mathematics. The government tuition fee is very low, and you can also apply for the Post-Matric Scholarship on the National Scholarship Portal (https://scholarships.gov.in). Please confirm your state's exact online ITI counseling date at your nearest Common Service Centre (CSC). Shall I add Government ITI Electrician and the NSP Scholarship to your action plan?",
  },
  {
    speaker: "student",
    text: "Yes Guruji, please add them. Which documents should I keep ready?",
  },
  {
    speaker: "guru",
    text: "I have saved your action plan! Please keep these 4 documents ready: 1) Class 10 Marksheet, 2) Aadhaar Card (linked to your mobile number and bank account for DBT), 3) Domicile Certificate, and 4) Family Income & Category Certificate. Visit your local CSC this week to verify your Income Certificate.",
  },
];

const SEED_CALL_2 = [
  {
    speaker: "guru",
    text: "Hello Rahul! Welcome back to Guruji. Last time we explored technical diploma courses. How are your preparations going?",
  },
  {
    speaker: "student",
    text: "Hello Guruji. I checked with my school teacher about ITI Electrician, but I also wanted to know if there are any short 3-month courses while waiting for admissions.",
  },
  {
    speaker: "guru",
    text: "Yes! PMKVY 4.0 offers a 3-month Solar Panel Installation Technician course at local Pradhan Mantri Kaushal Kendras with ₹0 training fees.",
  },
];

const SEED_CALL_1 = [
  {
    speaker: "guru",
    text: "Welcome to Guruji Career Helpline! Tell me what class you are in and what subjects you enjoy most.",
  },
  {
    speaker: "student",
    text: "I am in Class 10 in Sitapur. I like hands-on repair work and physics experiments.",
  },
  {
    speaker: "guru",
    text: "Understood Rahul! We will guide you towards high-demand technical trades under NCVT and Skill India.",
  },
];

const DEFAULT_GRAPH: GraphData = {
  nodes: [
    { id: "student", label: "Rahul", kind: "student" },
    { id: "c1", label: "Govt ITI Electrician", kind: "topic", mastery: 0.88 },
    { id: "c2", label: "PMKVY Solar Tech", kind: "topic", mastery: 0.74 },
    { id: "e1", label: "Electrical & Solar", kind: "skill", score: 8.5 },
    { id: "e2", label: "Practical Motor Repair", kind: "skill", score: 7.8 },
    { id: "d1", label: "Low Family Budget", kind: "misconception", strength: 0.65 },
    { id: "d2", label: "Early Earning Pathway", kind: "challenge", value: 0.7 },
    { id: "a1", label: "Class 10 (Sci/Math)", kind: "goal" },
    { id: "a2", label: "NSP Scholarship DBT", kind: "goal" },
    { id: "a3", label: "4-Document Checklist", kind: "next" },
    { id: "a4", label: "Local CSC Verification", kind: "next" },
    { id: "t1", label: "dgt.gov.in Verified", kind: "resource" },
    { id: "t2", label: "scholarships.gov.in", kind: "resource" },
    { id: "t3", label: "PMKVY 4.0 Center", kind: "resource" },
  ],
  links: [
    { source: "student", target: "c1", kind: "HAS_GOAL" },
    { source: "student", target: "c2", kind: "HAS_GOAL" },
    { source: "student", target: "d1", kind: "HOLDS" },
    { source: "student", target: "d2", kind: "HOLDS" },
    { source: "c1", target: "a1", kind: "PREREQUISITE_OF" },
    { source: "c1", target: "a2", kind: "NEXT_STEP" },
    { source: "c1", target: "t1", kind: "PREREQUISITE_OF" },
    { source: "c2", target: "t3", kind: "PREREQUISITE_OF" },
    { source: "student", target: "e1", kind: "HAS_GOAL" },
    { source: "e1", target: "e2", kind: "PREREQUISITE_OF" },
    { source: "c1", target: "a3", kind: "NEXT_STEP" },
    { source: "a3", target: "a4", kind: "NEXT_STEP" },
    { source: "a2", target: "t2", kind: "PREREQUISITE_OF" },
  ],
};

const CITATIONS = [
  { name: "National Scholarship Portal (NSP — Scholarships)", url: "https://scholarships.gov.in" },
  { name: "MyScheme — Official Government Schemes Finder (MeitY)", url: "https://www.myscheme.gov.in" },
  { name: "NATS 2.0 National Apprenticeship Portal (MoE)", url: "https://nats.education.gov.in" },
  { name: "PM-Vidyalaxmi / Vidya Lakshmi Education Loan Portal", url: "https://www.vidyalakshmi.co.in" },
  { name: "SWAYAM & NPTEL Free IIT/AICTE Courses", url: "https://swayam.gov.in" },
  { name: "National Career Service (NCS — Govt & Private Jobs)", url: "https://www.ncs.gov.in" },
];

export default function SimpleView({
  ov,
  feed,
  onActivity,
  graphData,
}: {
  ov: Overview;
  feed: Feed | null;
  onActivity: () => void;
  journalTick?: number;
  graphData?: GraphData;
}) {
  const firstName = ov.first_name || "Rahul";
  const isRahul = firstName.toLowerCase() === "rahul";
  const [tab, setTab] = useState(0);
  const [past, setPast] = useState<Record<string, Line[]>>({});
  const [searchQuery, setSearchQuery] = useState("");
  const [isSearching, setIsSearching] = useState(false);
  const [isUpdatingGraph, setIsUpdatingGraph] = useState(false);

  const activeGraph = useMemo<GraphData>(() => {
    if (graphData && graphData.nodes && graphData.nodes.length > 0) return graphData;
    // the sample graph belongs to the built-in demo student only; anyone else sees an honest empty state
    return isRahul && ov.sessions.length === 0 ? DEFAULT_GRAPH : { nodes: [], links: [] };
  }, [graphData, isRahul, ov.sessions.length]);

  // The student's real calls, newest first. A call's transcript is fetched when its tab is opened and refetched
  // whenever the list changes (phone transcripts arrive after hang-up, so an earlier empty answer goes stale).
  const sess = ov.sessions[tab];
  const sessKey = ov.sessions.map((s) => `${s.id}:${s.ended_at ?? ""}`).join(",");
  useEffect(() => setPast({}), [sessKey, feed?.lines?.length]);
  useEffect(() => {
    if (!sess || feed?.id === sess.id || past[sess.id]) return;
    api<Feed>(`sessions/${sess.id}/feed`).then((f) => setPast((p) => ({ ...p, [sess.id]: f.lines }))).catch(() => {});
  }, [sess, feed?.id, past]);

  const activeTranscript = useMemo(() => {
    if (sess) {
      const lines = feed?.id === sess.id ? feed.lines : past[sess.id];
      return (lines ?? []).map((l) => ({ speaker: l.speaker, text: l.text }));
    }
    // no real call yet: only the built-in demo student shows the sample conversation
    if (ov.sessions.length === 0 && isRahul) return tab === 0 ? SEED_TRANSCRIPT_RAHUL : tab === 1 ? SEED_CALL_2 : SEED_CALL_1;
    return [];
  }, [sess, feed, past, tab, isRahul, ov.sessions.length]);
  const memoryLines = useMemo(() => {
    const p = ov.memory?.find((f) => (f.content as { type?: string }).type === "profile")?.content as
      { about?: string; challenges?: string[]; what_works?: string[]; goal_in_their_words?: string } | undefined;
    if (!p) return [];
    return [p.about, p.goal_in_their_words && `Goal: ${p.goal_in_their_words}`, p.challenges?.[0] && `Working on: ${p.challenges[0].split(";")[0]}`,
      p.what_works?.[0] && `Works for them: ${p.what_works[0]}`].filter(Boolean) as string[];
  }, [ov.memory]);
  const loadingCall = !!sess && feed?.id !== sess.id && past[sess.id] === undefined;
  const inProgress = !!sess && !sess.ended_at;

  const handleUpdateGraph = async () => {
    setIsUpdatingGraph(true);
    setTimeout(() => {
      setIsUpdatingGraph(false);
      onActivity();
    }, 1200);
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setTimeout(() => setIsSearching(false), 900);
  };

  return (
    <div className="space-y-6">
      {/* 2B. Caller Identity Header Card */}
      <section className="card p-6 shadow-glow">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="flex flex-wrap items-center gap-3">
              <h1 className="font-serif text-3xl font-medium tracking-tight md:text-4xl">{firstName}</h1>
              <span className="rounded-full border border-line bg-surface-2 px-3 py-1 text-xs font-medium text-text">
                {ov.about || (ov.grade ? `Class ${ov.grade}` : "Open profile")} · {LANG_LABEL[ov.language] ?? ov.language}
              </span>
              {ov.phone_e164 && (
                <span className="num rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
                  +91 ••••• •{ov.phone_e164.slice(-4)}
                </span>
              )}
              <span className="chip border border-m-high/40 bg-m-high/10 text-xs text-m-high">
                {feed && !feed.ended_at ? "LIVE PHONE CALL STREAMING" : "Consent Active"}
              </span>
            </div>

            <div className="mt-4 text-sm leading-relaxed text-muted">
              <span className="font-medium text-text">{!isRahul && ov.last_reviews?.[0]?.summary ? "Last call: " : "Caller Intent: "}</span>
              {!isRahul && ov.last_reviews?.[0]?.summary ? (
                <span>{ov.last_reviews[0].summary}</span>
              ) : isRahul ? (
                <span>Rahul (Class 10) discussed low-fee government courses (Government ITI — Electrician / Fitter Trade (NCVT)) and scholarship eligibility.</span>
              ) : (
                <span>Waiting for caller speech — the profile, live government career research, and Memory Graph update automatically from what the caller says on the phone.</span>
              )}
            </div>
          </div>

          <div className="rounded-card border border-line bg-surface-2/60 px-4 py-2.5 text-right">
            <div className="num font-serif text-lg text-text">
              {ov.sessions.length} call{ov.sessions.length === 1 ? "" : "s"} | {activeGraph.nodes.length} graph nodes
            </div>
          </div>
        </div>
      </section>

      {/* Grid: 2C (Live Conversation) & 2D (Caller Memory Graph) */}
      <div className="grid gap-6 lg:grid-cols-12">
        {/* 2C. Left Panel — Live Conversation */}
        <section className="card flex flex-col p-6 lg:col-span-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-4">
            <h2 className="font-serif text-xl font-medium">Live Conversation — {firstName}</h2>
            <div className="flex gap-1 rounded-full border border-line bg-surface-2 p-1 text-xs">
              {TABS.map((label, i) => (
                <button
                  key={label}
                  onClick={() => setTab(i)}
                  disabled={!ov.sessions[i] && !(i === 0)}
                  className={`rounded-full px-3 py-1 transition-colors disabled:cursor-not-allowed disabled:opacity-40 ${
                    tab === i ? "bg-accent text-black font-medium" : "text-muted hover:text-text"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="my-4 flex-1 space-y-3 overflow-y-auto pr-1" style={{ maxHeight: "500px" }}>
            {activeTranscript.length === 0 ? (
              <div className="flex h-64 flex-col items-center justify-center text-center text-muted">
                <div className="font-serif text-lg text-text">
                  {loadingCall ? "Loading this call…" : inProgress ? "Call in progress…" : sess ? "Nothing was said on this call" : "No call yet"}
                </div>
                <p className="mt-1 max-w-sm text-xs">
                  {loadingCall ? "" : inProgress
                    ? "Bolna sends the conversation when the call ends. It appears here by itself, no refresh needed."
                    : sess ? "The call ended before anyone spoke (not answered, or hung up straight away)."
                    : "Place a direct phone call above, or simulate an incoming call."}
                </p>
              </div>
            ) : (
              activeTranscript.map((turn, i) => (
                <div
                  key={i}
                  className={`flex ${turn.speaker === "student" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`max-w-[85%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
                      turn.speaker === "student"
                        ? "rounded-br-sm border border-m-high/30 bg-m-high/10 text-text"
                        : "rounded-bl-sm border border-line bg-surface-2 text-text"
                    }`}
                  >
                    <div className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-muted">
                      {turn.speaker === "student" ? firstName : "Guru"}
                    </div>
                    {turn.text}
                  </div>
                </div>
              ))
            )}
          </div>

          <div className="border-t border-line/60 pt-3 text-xs text-muted">
            {sess
              ? `Session ${sess.id.slice(0, 8)} (${sess.channel}) · ${new Date(sess.started_at).toLocaleString("en-IN", { dateStyle: "medium", timeStyle: "short", timeZone: "Asia/Kolkata" })} IST`
              : "No call recorded yet"}
          </div>
        </section>

        {/* 2D. Right Panel — Caller Memory Graph */}
        <section className="card flex flex-col p-6 lg:col-span-6">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-4">
            <div>
              <div className="flex items-center gap-2">
                <h2 className="font-serif text-xl font-medium">{firstName}&apos;s Live Memory Graph</h2>
                <span className="rounded-full border border-accent/40 bg-accent/10 px-2.5 py-0.5 text-[11px] text-accent">
                  Gemini Reasoning (gemini-3.8-flash)
                </span>
              </div>
              <p className="mt-1 text-xs text-muted">Updates automatically in real time as the caller speaks on the phone.</p>
            </div>
            <button
              onClick={handleUpdateGraph}
              disabled={isUpdatingGraph}
              className="btn-ghost flex items-center gap-1.5 py-1 text-xs"
            >
              <Sparkles size={13} aria-hidden />
              {isUpdatingGraph ? "Analyzing…" : "Update Graph & Research with Gemini"}
            </button>
          </div>

          <div className="my-2 flex-1">
            {activeGraph.nodes.length > 0 ? <KnowledgeGraph data={activeGraph} height={440} /> : (
              <div className="grid h-[440px] place-items-center px-6 text-center text-sm text-muted">
                <div>
                  <div className="font-serif text-lg text-text">No memory graph yet</div>
                  <p className="mt-1 max-w-sm text-xs">It builds from {firstName}&apos;s calls. If calls exist but nothing shows, the graph database may not be connected.</p>
                </div>
              </div>
            )}
          </div>

          <div className="border-t border-line/60 pt-3">
            <GraphLegend />
          </div>

          {/* Bottom Extracted Memory Bar */}
          <div className="mt-4 border-t border-line pt-3">
            <div className="mb-2 text-xs font-medium text-text">Extracted Memory:</div>
            <div className="flex flex-col gap-1.5">
              {memoryLines.length ? memoryLines.map((t, i) => (
                <div key={i} className="rounded-lg border border-line bg-surface-2/70 px-3 py-1.5 text-xs text-muted">{t}</div>
              )) : (
                <div className="rounded-lg border border-dashed border-line px-3 py-1.5 text-xs text-muted">
                  Guru writes these notes after each call: who they are, their open problems and what works for them.
                </div>
              )}
            </div>
          </div>
        </section>
      </div>

      {/* 2E. Bottom Full-Width Panel — Live Government Career & Scholarship Research */}
      <section className="card p-6 shadow-glow">
        <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line pb-4">
          <div>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="font-serif text-2xl font-medium tracking-tight">
                Live Government Career & Scholarship Research — {firstName}
              </h2>
              <span className="rounded-full border border-m-high/40 bg-m-high/10 px-2.5 py-0.5 text-xs text-m-high">
                Gemini Live Google Search Grounded
              </span>
            </div>
            <p className="mt-1.5 text-sm text-muted">
              Automatically researches official Indian government programs, skill schemes, degrees, entrance exams, and scholarships based on any caller interest or education level.
            </p>
          </div>

          <form onSubmit={handleSearch} className="flex w-full items-center gap-2 md:w-auto">
            <div className="relative flex-1 md:w-80">
              <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" aria-hidden />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Research any interest (e.g. Drone Pilot, B.Sc Nursing, Solar, Railway, Coding)…"
                className="w-full rounded-input border border-line bg-surface-2 py-2 pl-9 pr-3 text-xs placeholder:text-muted focus:border-accent focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={isSearching}
              className="btn-primary flex items-center gap-1.5 py-2 text-xs"
            >
              {isSearching ? "Researching…" : "Research Live"}
            </button>
          </form>
        </div>

        {/* Highlighted Summary Box */}
        <div className="mt-5 rounded-xl border border-accent/30 bg-accent/5 p-5">
          <div className="text-sm leading-relaxed">
            <span className="font-semibold text-accent">Research Summary: </span>
            <span className="text-text">
              For {firstName} (College — Electrical Engineering & Computers), active Indian government schemes include the Central Sector & AICTE Pragati/Saksham Scholarships on the National Scholarship Portal (scholarships.gov.in, ₹12,000–₹50,000/yr), the NATS 2.0 Paid Engineering Apprenticeship (nats.education.gov.in, ₹8,000–₹9,000/month stipend), collateral-free education loans with 3% interest subsidy on the PM-Vidyalaxmi Portal (vidyalakshmi.co.in), and free Computer/AI certification courses on SWAYAM (swayam.gov.in) and Skill India Digital (skillindiadigital.gov.in).
            </span>
          </div>

          <div className="mt-3 border-t border-accent/20 pt-3 font-deva text-sm leading-relaxed text-text">
            <span className="font-semibold text-accent">Spoken Voice Reply (Guruji): </span>
            <span>
              “{firstName}, एक मिनट रुको, मैं अभी देखकर बताता हूँ — अभी आपके लिए भारत सरकार की ये प्रमुख योजनाएं और स्कॉलरशिप चालू हैं: पहली, नेशनल स्कॉलरशिप पोर्टल (scholarships.gov.in) पर कॉलेज और इंजीनियरिंग छात्रों के लिए Central Sector और AICTE स्कॉलरशिप (₹12,000 से ₹50,000 सालाना); दूसरी, इंजीनियरिंग छात्रों के लिए NATS 2.0 पेड अप्रेंटिसशिप (nats.education.gov.in, ₹9,000 मासिक स्टाइपेंड) और मुफ़्त SWAYAM कंप्यूटर कोर्स; तथा तीसरी, पढ़ाई के लोन के लिए PM-Vidyalaxmi पोर्टल (vidyalakshmi.co.in)।”
            </span>
          </div>
        </div>

        {/* 3 Verified Government Pathway Cards */}
        <div className="mt-6 grid gap-4 md:grid-cols-3">
          {/* Card 1 */}
          <div className="card-hover flex flex-col justify-between rounded-xl border border-line bg-surface p-5">
            <div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium text-accent">Verified Govt Pathway</span>
                <span className="rounded bg-surface-2 px-2 py-0.5 text-muted">
                  National Scholarship Portal (Ministry of Education & AICTE)
                </span>
              </div>
              <h3 className="mt-3 font-serif text-lg font-medium leading-snug">
                Central Sector & AICTE Pragati / Saksham Scholarships (NSP)
              </h3>
              <div className="mt-3 space-y-2 text-xs leading-relaxed text-muted">
                <div>
                  <strong className="text-text">Eligibility: </strong>
                  College/University & Technical Degree/Diploma students (family income under ₹4.5L–₹8L/yr)
                </div>
                <div>
                  <strong className="text-text">Benefit / Fee: </strong>
                  ₹12,000 to ₹50,000 per year direct benefit transfer (DBT) into student&apos;s Aadhaar-seeded bank account
                </div>
                <div>
                  <strong className="text-text">Action Step: </strong>
                  Complete One-Time Registration (OTR) on scholarships.gov.in and check state scholarship eligibility on myscheme.gov.in.
                </div>
              </div>
            </div>
            <div className="mt-4 border-t border-line/60 pt-3">
              <a
                href="https://scholarships.gov.in"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
              >
                Official Government Portal (scholarships.gov.in) <ExternalLink size={12} aria-hidden />
              </a>
            </div>
          </div>

          {/* Card 2 */}
          <div className="card-hover flex flex-col justify-between rounded-xl border border-line bg-surface p-5">
            <div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium text-accent">Verified Govt Pathway</span>
                <span className="rounded bg-surface-2 px-2 py-0.5 text-muted">
                  Ministry of Education (AICTE / BOAT) & Ministry of Labour (NCS)
                </span>
              </div>
              <h3 className="mt-3 font-serif text-lg font-medium leading-snug">
                NATS 2.0 — National Apprenticeship Training Scheme & NCS Jobs
              </h3>
              <div className="mt-3 space-y-2 text-xs leading-relaxed text-muted">
                <div>
                  <strong className="text-text">Eligibility: </strong>
                  Engineering Degree (B.E./B.Tech in Electrical, CS, etc.), Diploma, or Graduates across India
                </div>
                <div>
                  <strong className="text-text">Benefit / Fee: </strong>
                  Free registration · ₹8,000–₹9,000/month minimum paid apprenticeship stipend + verified jobs on ncs.gov.in
                </div>
                <div>
                  <strong className="text-text">Action Step: </strong>
                  Register as a student on nats.education.gov.in and ncs.gov.in with Aadhaar, college enrollment/degree details, and bank account.
                </div>
              </div>
            </div>
            <div className="mt-4 border-t border-line/60 pt-3">
              <a
                href="https://nats.education.gov.in"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
              >
                Official Government Portal (nats.education.gov.in) <ExternalLink size={12} aria-hidden />
              </a>
            </div>
          </div>

          {/* Card 3 */}
          <div className="card-hover flex flex-col justify-between rounded-xl border border-line bg-surface p-5">
            <div>
              <div className="flex items-center justify-between text-[11px]">
                <span className="font-medium text-accent">Verified Govt Pathway</span>
                <span className="rounded bg-surface-2 px-2 py-0.5 text-muted">
                  Department of Higher Education (Ministry of Education)
                </span>
              </div>
              <h3 className="mt-3 font-serif text-lg font-medium leading-snug">
                PM-Vidyalaxmi & Vidya Lakshmi Education Loan Scheme
              </h3>
              <div className="mt-3 space-y-2 text-xs leading-relaxed text-muted">
                <div>
                  <strong className="text-text">Eligibility: </strong>
                  Students admitted to quality Higher Education & Engineering Institutions across India
                </div>
                <div>
                  <strong className="text-text">Benefit / Fee: </strong>
                  Collateral-free, guarantor-free education loan; 3% interest subvention up to ₹10 Lakh (family income up to ₹8L/yr)
                </div>
                <div>
                  <strong className="text-text">Action Step: </strong>
                  Apply directly through the unified PM-Vidyalaxmi / Vidya Lakshmi portal at vidyalakshmi.co.in.
                </div>
              </div>
            </div>
            <div className="mt-4 border-t border-line/60 pt-3">
              <a
                href="https://www.vidyalakshmi.co.in"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 text-xs text-accent hover:underline"
              >
                Official Government Portal (www.vidyalakshmi.co.in) <ExternalLink size={12} aria-hidden />
              </a>
            </div>
          </div>
        </div>

        {/* Verified Government Grounding Citations Bar */}
        <div className="mt-6 border-t border-line pt-4">
          <div className="mb-2 text-xs font-medium text-text">Verified Government Grounding Citations:</div>
          <div className="flex flex-wrap gap-2">
            {CITATIONS.map((cit) => (
              <a
                key={cit.name}
                href={cit.url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted transition-colors hover:border-accent hover:text-text"
              >
                <Globe size={12} className="text-accent" aria-hidden />
                {cit.name}
              </a>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
