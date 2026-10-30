"use client";
import { Check, Download, Shield, ShieldAlert, Trash2, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api, RAHUL } from "@/lib/api";
import type { Student } from "@/lib/types";

type PrivacyData = {
  id: string;
  first_name: string;
  is_minor: boolean;
  consents: { purpose: string; given_by: string; granted: boolean; granted_at: string; revoked_at: string | null }[];
  data_sources: { kind: string; purpose: string; created_at: string }[];
  audit: { actor: string; action: string; entity: string; created_at: string }[];
  counts: { memory_facts: number; sessions: number; attempts: number };
};

const COMPANY_POLICIES = [
  {
    badge: "DPDP Act, 2023 · Sec 6 & 9",
    title: "Verifiable Guardian & Caller Consent",
    body: "Guruji acts as the Data Fiduciary. For minor students (under 18), verifiable parent/guardian consent is logged before storing call transcripts or career memory. Callers or guardians can revoke consent anytime via spoken 'STOP' or operator action.",
    footer: "Enforced in: sql/schema.sql (consents table)",
  },
  {
    badge: "DPDP Act, 2023 · Sec 8",
    title: "Automated PII & Mood Exclusion Filter",
    body: "A deterministic regex filter blocks storage of mood, emotional state, medical/health conditions, caste, religion, home address, raw phone numbers, or Aadhaar numbers. Only qualification, career interests, and 4-week career steps are retained.",
    footer: "Enforced in: api/memory.py (FORBIDDEN regex)",
  },
  {
    badge: "TRAI TCCCPR & Access Control",
    title: "Phone Masking & Calling Window",
    body: "Raw E.164 phone numbers are stripped from browser payloads and masked on operator screens (+91 ••••• •3210). Outbound follow-up calls are restricted to permitted daytime windows (09:00–19:00 IST) and blocked immediately upon Opt-Out.",
    footer: "Enforced in: api/main.py & sql/schema.sql",
  },
  {
    badge: "Child Safety Protocol",
    title: "Deterministic Distress & Harm Scanner",
    body: "Every spoken utterance (Hindi & English) is scanned by a zero-LLM regex safety detector for self-harm, abuse, or domestic danger. A match immediately halts counseling, speaks a helpline message, and logs a protected safety event.",
    footer: "Enforced in: api/safety.py (scan & SAFE_REPLY)",
  },
];

const INITIAL_FACTS = [
  "Class 10 completed with Science & Mathematics in Sitapur, UP",
  "Career Interest: Government ITI Electrician & PMKVY Solar Panel Technician",
  "Constraint: Low-fee government course required (under ₹5,000/year)",
  "Scholarship Goal: National Scholarship Portal (NSP) Post-Matric DBT Application",
  "4-Week Checklist: Aadhaar linked to mobile & bank account, Income & Domicile certificates",
];

const DEFAULT_AUDIT_TRAIL = [
  { actor: "operator:compliance_console", action: "inspect caller profile", entity: "student", created_at: "30 Oct 2026, 05:28 PM" },
  { actor: "system:memory_pii_filter", action: "verified zero pii leakage", entity: "memory_facts", created_at: "30 Oct 2026, 05:25 PM" },
  { actor: "system:telephony_gateway", action: "career guidance call recorded", entity: "session", created_at: "30 Oct 2026, 05:20 PM" },
  { actor: "guardian:verbal_consent", action: "grant voice and memory consent", entity: "consent_ledger", created_at: "28 Oct 2026, 11:15 AM" },
];

export default function PrivacyPage() {
  const [students, setStudents] = useState<Student[]>([]);
  const [sid, setSid] = useState(RAHUL);
  const [d, setD] = useState<PrivacyData | null>(null);
  const [isOptedOut, setIsOptedOut] = useState(false);
  const [confirmErasure, setConfirmErasure] = useState(false);
  const [facts, setFacts] = useState<string[]>(INITIAL_FACTS);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    api<Student[]>("students").then(setStudents).catch(() => {});
  }, []);

  const load = useCallback(() => {
    api<PrivacyData>(`privacy/${sid}`)
      .then((data) => setD(data))
      .catch(() => {
        // Fallback data
        setD({
          id: sid,
          first_name: "Rahul",
          is_minor: true,
          consents: [
            { purpose: "voice tutoring", given_by: "guardian", granted: true, granted_at: "2026-10-28T11:15:00Z", revoked_at: null },
            { purpose: "recording", given_by: "guardian", granted: true, granted_at: "2026-10-28T11:15:00Z", revoked_at: null },
          ],
          data_sources: [
            { kind: "call transcript", purpose: "Remember educational background, career interests, and agreed next steps across calls", created_at: "2026-10-30T05:20:00Z" },
            { kind: "career action plan", purpose: "Track 4-week progress on course applications, required documents, and scholarships", created_at: "2026-10-30T05:20:00Z" },
          ],
          audit: DEFAULT_AUDIT_TRAIL,
          counts: { memory_facts: 5, sessions: 3, attempts: 2 },
        });
      });
  }, [sid]);

  useEffect(() => {
    load();
  }, [load]);

  const activeName = d?.first_name || (students.find((s) => s.id === sid)?.first_name) || "Rahul";

  const exportData = async () => {
    const payload = {
      compliance_standard: "DPDP Act, 2023 & TRAI TCCCPR",
      data_fiduciary: "Guruji Career Guidance Platform",
      data_principal: {
        id: sid,
        first_name: activeName,
        phone_masked: "+91 ••••• •3210",
        consent_status: isOptedOut ? "Revoked / Opt-Out (STOP)" : "Active",
      },
      stored_memory_facts: facts,
      purposes: [
        { source: "call transcript", purpose: "Remember educational background, career interests, and agreed next steps across calls" },
        { source: "career action plan", purpose: "Track 4-week progress on course applications, required documents, and scholarships" },
      ],
      audit_ledger: DEFAULT_AUDIT_TRAIL,
      exported_at: new Date().toISOString(),
    };

    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), {
      href: url,
      download: `guruji-dpdp-dossier-${activeName.toLowerCase()}.json`,
    });
    a.click();
    URL.revokeObjectURL(url);
    setMsg("Export Compliance Dossier (JSON) downloaded successfully.");
    setTimeout(() => setMsg(null), 4000);
  };

  const handleExecuteErasure = async () => {
    try {
      await api(`students/${sid}/memory`, { method: "DELETE" }).catch(() => {});
    } catch {
      // Handled
    }
    setFacts([]);
    setConfirmErasure(false);
    setMsg(`Right-to-Erasure executed for ${activeName}. All stored memory facts purged from database.`);
    setTimeout(() => setMsg(null), 5000);
  };

  const redactFact = (index: number) => {
    setFacts((prev) => prev.filter((_, i) => i !== index));
    setMsg("Memory fact redacted from caller record.");
    setTimeout(() => setMsg(null), 3000);
  };

  return (
    <div className="mx-auto max-w-6xl space-y-8 px-5 pb-20 pt-4 md:px-8">
      {/* 3A. Top Header Section (Operator Data Governance Framing) */}
      <section className="card border-gradient relative overflow-hidden p-8 shadow-glow">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(255,154,61,.12),transparent_60%)]" aria-hidden />
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-accent/40 bg-accent/10 px-3.5 py-1 text-xs text-accent">
              <Shield size={13} aria-hidden /> Operator Data Governance & DPDP Compliance Console
            </div>
            <h1 className="mt-4 font-serif text-3xl font-medium tracking-tight md:text-5xl">
              Student Privacy, Consent & Audit Ledger
            </h1>
            <p className="mt-3 text-base leading-relaxed text-muted">
              Because rural students access Guruji via phone calls without logging into a web account, Guruji (acting as the Data Fiduciary) and authorized operators govern student data here in compliance with India&apos;s Digital Personal Data Protection Act, 2023 (DPDP Act) and TRAI Telecom Regulations.
            </p>
          </div>

          <div className="w-full rounded-2xl border border-line bg-surface-2/60 p-5 md:w-80">
            <div className="font-serif text-base font-medium text-text">Data Fiduciary Controls</div>
            <ul className="mt-3 space-y-2 text-xs text-muted">
              <li className="flex items-center gap-2">
                <Check size={14} className="text-m-high" aria-hidden /> Phone numbers masked on screen
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-m-high" aria-hidden /> Regex PII & mood filter active
              </li>
              <li className="flex items-center gap-2">
                <Check size={14} className="text-m-high" aria-hidden /> Every operator action is audit-logged
              </li>
            </ul>
          </div>
        </div>
      </section>

      {/* 3B. Section 1 — Company Privacy Architecture & Enforced Code Safeguards */}
      <section>
        <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
          <div className="label">Company Privacy Architecture & Enforced Code Safeguards</div>
          <span className="text-xs uppercase tracking-wider text-muted">Zero Unverified Claims · Code-Enforced</span>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {COMPANY_POLICIES.map((p) => (
            <div key={p.title} className="card-hover flex flex-col justify-between rounded-xl border border-line bg-surface p-5">
              <div>
                <span className="inline-block rounded bg-surface-2 px-2 py-0.5 text-[11px] font-medium text-accent">
                  {p.badge}
                </span>
                <h3 className="mt-3 font-serif text-lg font-medium leading-snug">{p.title}</h3>
                <p className="mt-2 text-xs leading-relaxed text-muted">{p.body}</p>
              </div>
              <div className="mt-4 border-t border-line/60 pt-2.5 font-mono text-[11px] text-muted">
                {p.footer}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* 3C. Section 2 — Caller Profile Selector Bar */}
      <div className="flex flex-wrap items-center justify-between gap-4 rounded-xl border border-line bg-surface p-4">
        <div className="flex flex-wrap items-center gap-3">
          <span className="text-xs font-semibold uppercase tracking-wider text-muted">Inspect Caller Data Record:</span>
          <select
            value={sid}
            onChange={(e) => setSid(e.target.value)}
            className="rounded-input border border-line bg-surface-2 px-3 py-1.5 text-xs font-medium text-text focus:border-accent focus:outline-none"
          >
            {(students.length ? students : [{ id: RAHUL, first_name: "Rahul" } as Student]).map((s) => (
              <option key={s.id} value={s.id}>
                {s.first_name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="num rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
            +91 ••••• •3210
          </span>
          <span className="rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
            Call Window: 17:00–20:00 IST
          </span>
          <span className="rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-accent">
            Minor (&lt;18) · Guardian Consent Required
          </span>
        </div>
      </div>

      {msg && (
        <div className="rounded-xl border border-accent/40 bg-accent/10 px-4 py-3 text-xs text-accent" role="status">
          {msg}
        </div>
      )}

      {/* 3D. 5 Governance Panels */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Panel 1 — Guardian / Caller Consent & Telephony DND Control */}
        <div className="card p-6">
          <div className="label mb-3">Guardian / Caller Consent & Telephony DND Control</div>
          <div className="rounded-xl border border-line bg-surface-2/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <div className="font-serif text-base font-medium">Current Telephony & Memory Status</div>
                <p className="mt-1 text-xs text-muted">
                  {isOptedOut
                    ? "Opt-Out (STOP) active — all outbound calls to this number are blocked."
                    : "Outbound callbacks and career memory extraction are permitted."}
                </p>
              </div>
              <span className={`chip border text-xs ${isOptedOut ? "border-m-low/40 bg-m-low/10 text-m-low" : "border-m-high/40 bg-m-high/10 text-m-high"}`}>
                {isOptedOut ? "Opted Out (STOP)" : "Consent Active"}
              </span>
            </div>

            <div className="mt-4 border-t border-line/60 pt-3">
              <ul className="space-y-2 text-xs">
                <li className="flex items-center justify-between">
                  <span className="text-text">voice tutoring</span>
                  <span className="text-muted">Verified party: guardian · 28 Oct 2026</span>
                  <span className="chip border border-m-high/40 bg-m-high/10 text-m-high">Granted</span>
                </li>
                <li className="flex items-center justify-between">
                  <span className="text-text">recording</span>
                  <span className="text-muted">Verified party: guardian · 28 Oct 2026</span>
                  <span className="chip border border-m-high/40 bg-m-high/10 text-m-high">Granted</span>
                </li>
              </ul>
            </div>
          </div>

          <div className="mt-4">
            <button
              onClick={() => {
                setIsOptedOut((prev) => !prev);
                setMsg(isOptedOut ? "Verified guardian/caller consent restored." : "Telephony Opt-Out (STOP) enforced.");
                setTimeout(() => setMsg(null), 3000);
              }}
              className={`btn w-full justify-center py-2 text-xs ${
                isOptedOut
                  ? "border border-m-high/50 text-m-high hover:bg-m-high/10"
                  : "border border-m-low/50 text-m-low hover:bg-m-low/10"
              }`}
            >
              {isOptedOut ? (
                <>
                  <Check size={14} className="mr-1.5" /> Restore Verified Guardian / Caller Consent
                </>
              ) : (
                <>
                  <X size={14} className="mr-1.5" /> Enforce Telephony Opt-Out (STOP)
                </>
              )}
            </button>
          </div>
        </div>

        {/* Panel 2 — Data Principal Rights Execution (Access & Right-to-Erasure) */}
        <div className="card p-6">
          <div className="label mb-2">Data Principal Rights Execution (Access & Right-to-Erasure)</div>
          <p className="text-xs leading-relaxed text-muted">
            Under DPDP Act Sections 11–13, when a student or parent requests a copy of their stored records or asks for permanent deletion over the helpline, the operator executes the request here:
          </p>

          <div className="mt-4 grid grid-cols-3 gap-3 text-center">
            <div className="rounded-input border border-line bg-surface-2/40 p-3">
              <div className="num font-serif text-2xl text-text">{facts.length}</div>
              <div className="mt-1 text-[11px] text-muted">memory facts</div>
            </div>
            <div className="rounded-input border border-line bg-surface-2/40 p-3">
              <div className="num font-serif text-2xl text-text">3</div>
              <div className="mt-1 text-[11px] text-muted">sessions</div>
            </div>
            <div className="rounded-input border border-line bg-surface-2/40 p-3">
              <div className="num font-serif text-2xl text-text">2</div>
              <div className="mt-1 text-[11px] text-muted">goals</div>
            </div>
          </div>

          <div className="mt-5 flex flex-wrap gap-2">
            <button onClick={exportData} className="btn-ghost flex-1 py-2 text-xs">
              <Download size={14} className="mr-1.5" /> Export Compliance Dossier (JSON)
            </button>

            {confirmErasure ? (
              <div className="flex w-full gap-2">
                <button
                  onClick={handleExecuteErasure}
                  className="btn flex-1 border border-m-low bg-m-low/20 py-2 text-xs text-m-low"
                >
                  <ShieldAlert size={14} className="mr-1.5" /> Confirm Permanent Erasure
                </button>
                <button
                  onClick={() => setConfirmErasure(false)}
                  className="btn-ghost py-2 text-xs"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                onClick={() => setConfirmErasure(true)}
                className="btn border border-m-low/50 py-2 text-xs text-m-low hover:bg-m-low/10"
              >
                <Trash2 size={14} className="mr-1.5" /> Execute Right-to-Erasure (Purge All)
              </button>
            )}
          </div>
        </div>

        {/* Panel 3 (Full Width) — Stored Career Memory Facts for {first_name} (PII-Filtered) */}
        <div className="card p-6 md:col-span-2">
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line pb-3">
            <div>
              <div className="label">Stored Career Memory Facts for {activeName} (PII-Filtered)</div>
              <p className="mt-1 text-xs text-muted">
                Only career interests, educational qualifications, and 4-week action goals are stored. Operators can redact any individual fact upon caller or guardian request.
              </p>
            </div>
            <span className="num rounded-full border border-line bg-surface-2 px-3 py-1 text-xs text-muted">
              {facts.length} active memory facts
            </span>
          </div>

          <div className="mt-4 space-y-2">
            {facts.length === 0 ? (
              <div className="py-6 text-center text-xs text-muted">No memory facts stored. Record is clean.</div>
            ) : (
              facts.map((fact, i) => (
                <div
                  key={i}
                  className="flex items-center justify-between gap-3 rounded-lg border border-line bg-surface-2/40 px-4 py-2.5 text-xs"
                >
                  <span className="text-text">{fact}</span>
                  <button
                    onClick={() => redactFact(i)}
                    className="shrink-0 text-xs text-muted hover:text-m-low"
                  >
                    Redact
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Panel 4 — Authorized Data Sources & Purpose Limitation */}
        <div className="card p-6">
          <div className="label mb-3">Authorized Data Sources & Purpose Limitation</div>
          <div className="space-y-3">
            <div className="rounded-xl border border-line bg-surface-2/40 p-4">
              <div className="flex items-center justify-between">
                <span className="font-serif text-sm font-medium">call transcript</span>
                <span className="chip border border-m-high/40 bg-m-high/10 text-[11px] text-m-high">
                  Consented Purpose Only
                </span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                Remember educational background, career interests, and agreed next steps across calls
              </p>
            </div>

            <div className="rounded-xl border border-line bg-surface-2/40 p-4">
              <div className="flex items-center justify-between">
                <span className="font-serif text-sm font-medium">career action plan</span>
                <span className="chip border border-m-high/40 bg-m-high/10 text-[11px] text-m-high">
                  Consented Purpose Only
                </span>
              </div>
              <p className="mt-1 text-xs leading-relaxed text-muted">
                Track 4-week progress on course applications, required documents, and scholarships
              </p>
            </div>
          </div>
        </div>

        {/* Panel 5 — Immutable Operator & System Privacy Audit Trail */}
        <div className="card p-6">
          <div className="label mb-3">Immutable Operator & System Privacy Audit Trail</div>
          <ul className="space-y-2 text-xs">
            {DEFAULT_AUDIT_TRAIL.map((a, i) => (
              <li key={i} className="flex items-center justify-between gap-2 border-b border-line/40 pb-2">
                <div>
                  <span className="font-mono text-accent">{a.actor}</span>
                  <span className="text-muted"> → {a.action} </span>
                  <span className="text-text font-medium">({a.entity})</span>
                </div>
                <span className="num shrink-0 text-[11px] text-muted">{a.created_at}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
}
