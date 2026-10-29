"use client";
// In-page voice call with Guru (Sarvam STT/TTS behind the same tutor core as the Bolna phone agent).
// UI: an audio-reactive orb (mic level while listening, Guru's own audio level while speaking) + live chat.
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Mic, MicOff, PhoneCall, PhoneOff, Send, Square } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import VoiceOrb, { type OrbState } from "@/components/VoiceOrb";
import { api } from "@/lib/api";
import { Recorder } from "@/lib/recorder";

type Turn = {
  reply_text: string;
  audio_b64: string | null;
  audio_parts?: string[]; // one clip per sentence, synthesised in parallel: play in order
  audio_mime: string | null;
  tts_error?: string | null;
  stt_error?: string | null;
  user_text?: string;
  done: boolean;
  state: string;
};
type Msg = { who: "guru" | "me" | "note"; text: string; id: number };
type Phase = "idle" | "starting" | "guru" | "listening" | "thinking" | "ended";

const LABEL: Record<Phase, string> = {
  idle: "Talk to Guru",
  starting: "Connecting…",
  guru: "Guru is speaking",
  listening: "Listening — just talk",
  thinking: "Thinking…",
  ended: "Call ended",
};
const ORB: Record<Phase, OrbState> = {
  idle: "idle", starting: "connecting", guru: "speaking", listening: "listening", thinking: "thinking", ended: "ended",
};

export type Mode = "coach" | "maths" | "english" | "topic";

/** Guru's text appears word by word, roughly at speaking pace. */
function Typewriter({ text }: { text: string }) {
  const reduce = useReducedMotion();
  const words = text.split(" ");
  return (
    <span>
      {words.map((w, i) => (
        <motion.span key={i} initial={reduce ? false : { opacity: 0, filter: "blur(4px)" }} animate={{ opacity: 1, filter: "blur(0px)" }}
          transition={{ duration: 0.25, delay: Math.min(i * 0.11, 6) }}>
          {w}{i < words.length - 1 ? " " : ""}
        </motion.span>
      ))}
    </span>
  );
}

export default function CallPanel({ studentId, name, big = false, mode = "coach", onActivity, toolbar }: {
  studentId: string; name: string; big?: boolean; mode?: Mode; onActivity?: () => void; toolbar?: React.ReactNode;
}) {
  const [phase, setPhase] = useState<Phase>("idle");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [level, setLevel] = useState(0);
  const [speaking, setSpeaking] = useState(false);
  const [micOk, setMicOk] = useState<boolean | null>(null);
  const [typed, setTyped] = useState("");
  const token = useRef<string | null>(null);
  const rec = useRef<Recorder | null>(null);
  const alive = useRef(false);
  const playCtx = useRef<AudioContext | null>(null);
  const box = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  useEffect(() => () => hangUp(true), []); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" });
  }, [msgs, phase]);
  // switching student or mode mid-call ends the call
  useEffect(() => () => hangUp(true), [studentId, mode]); // eslint-disable-line react-hooks/exhaustive-deps

  const add = (m: Omit<Msg, "id">) => setMsgs((x) => [...x, { ...m, id: nextId.current++ }]);

  /** Play one clip and drive the orb from its real loudness. */
  const playClip = (src: string) => new Promise<void>((res) => {
    const a = new Audio(src);
    let raf = 0;
    try {
      const ctx = playCtx.current;
      if (ctx) {
        const an = ctx.createAnalyser();
        an.fftSize = 1024;
        ctx.createMediaElementSource(a).connect(an);
        an.connect(ctx.destination);
        const buf = new Float32Array(an.fftSize);
        const tick = () => {
          an.getFloatTimeDomainData(buf);
          let s = 0;
          for (let i = 0; i < buf.length; i++) s += buf[i] * buf[i];
          setLevel(Math.min(1, Math.sqrt(s / buf.length) * 6));
          raf = requestAnimationFrame(tick);
        };
        raf = requestAnimationFrame(tick);
      }
    } catch { /* analyser is decoration only */ }
    const done = () => { cancelAnimationFrame(raf); setLevel(0); res(); };
    a.onended = done;
    a.onerror = done;
    a.play().catch(done);
  });

  const speak = async (t: Turn) => {
    add({ who: "guru", text: t.reply_text });
    setPhase("guru");
    const clips = t.audio_parts?.length ? t.audio_parts : t.audio_b64 ? [t.audio_b64] : [];
    if (clips.length) {
      for (const clip of clips) {
        if (!alive.current) break;
        await playClip(`data:${t.audio_mime};base64,${clip}`);
      }
    } else if ("speechSynthesis" in window) {
      await new Promise<void>((res) => {
        const u = new SpeechSynthesisUtterance(t.reply_text);
        u.lang = mode === "english" ? "en-IN" : "hi-IN";
        u.onend = () => res();
        u.onerror = () => res();
        speechSynthesis.speak(u);
      });
    }
  };

  const send = async (audio: Blob | null, text?: string) => {
    if (!token.current) return;
    setPhase("thinking");
    const fd = new FormData();
    fd.append("token", token.current);
    if (audio) fd.append("audio", audio, "utterance.wav");
    if (text !== undefined) fd.append("text", text);
    const r = await fetch("/api/gl/web-call/turn", { method: "POST", body: fd });
    const t: Turn & { error?: string } = await r.json();
    if (!r.ok) throw new Error(t.error || `HTTP ${r.status}`);
    if (audio && t.user_text) add({ who: "me", text: t.user_text });
    if (t.stt_error) add({ who: "note", text: `Speech recognition problem: ${t.stt_error}. You can type below.` });
    onActivity?.();
    return t;
  };

  const loop = async (first: Turn) => {
    let t: Turn | undefined = first;
    while (alive.current && t) {
      await speak(t);
      if (t.done || !alive.current) break;
      if (!rec.current) { setPhase("listening"); return; } // no mic: wait for typed answers
      setPhase("listening");
      // A pause is not a turn: keep listening quietly (up to ~20 s) instead of making Guru say "I didn't hear you".
      let blob: Blob | null = null;
      for (let tries = 0; tries < 2 && !blob; tries++) {
        blob = await rec.current.listen((rms, sp) => { setLevel(Math.min(1, rms * 14)); setSpeaking(sp); });
        if (!alive.current || rec.current?.cancelled) return; // hung up, or a typed answer took over this turn
      }
      setLevel(0);
      setSpeaking(false);
      t = await send(blob);
    }
    if (alive.current) finish();
  };

  const start = async () => {
    setMsgs([]);
    setPhase("starting");
    alive.current = true;
    try {
      playCtx.current = playCtx.current ?? new AudioContext(); // created on the click so playback may start
      if (playCtx.current.state === "suspended") await playCtx.current.resume();
    } catch { playCtx.current = null; }
    try {
      rec.current = new Recorder();
      await rec.current.open();
      setMicOk(true);
    } catch {
      rec.current = null;
      setMicOk(false);
      add({ who: "note", text: "Microphone is blocked. Allow it from the 🔒 icon in the address bar, or type your answers below." });
    }
    try {
      const link = await api<{ token: string }>("voice/call", { method: "POST", body: { student_id: studentId, provider: "sarvam" } });
      token.current = link.token;
      const first = await api<Turn>("web-call/start", { method: "POST", body: { token: link.token, mode } });
      await loop(first);
    } catch (e) {
      add({ who: "note", text: `Could not continue: ${(e as Error).message}` });
      finish();
    }
  };

  const finish = () => {
    alive.current = false;
    rec.current?.close();
    rec.current = null;
    setLevel(0);
    setPhase("ended");
    onActivity?.();
  };

  function hangUp(silent = false) {
    if (!alive.current && !silent) return;
    const tok = token.current;
    alive.current = false;
    rec.current?.cancel();
    if ("speechSynthesis" in window) speechSynthesis.cancel();
    if (tok) api("web-call/end", { method: "POST", body: { token: tok } }).catch(() => {});
    token.current = null;
    if (!silent) finish();
    else { rec.current?.close(); rec.current = null; }
  }

  const sendTyped = async () => {
    const v = typed.trim();
    if (!v || phase === "thinking" || phase === "guru") return;
    setTyped("");
    rec.current?.cancel(); // stop the listener without sending audio
    add({ who: "me", text: v });
    try {
      const t = await send(null, v);
      if (t) await loop(t);
    } catch (e) {
      add({ who: "note", text: (e as Error).message });
    }
  };

  const inCall = !["idle", "ended"].includes(phase);
  const sub =
    phase === "idle" ? `Practise right here in the browser, ${name}. Allow the microphone when asked.`
    : phase === "listening" ? (speaking ? "I can hear you ✓" : "Speak normally — I'll wait until you finish.")
    : phase === "guru" ? "Listen, then answer out loud."
    : phase === "thinking" ? "Understanding what you said…"
    : phase === "ended" ? "Nice work. Tap Start to talk again."
    : "Setting up your call…";

  return (
    <section className={`card border-gradient relative overflow-hidden ${big ? "p-6 md:p-8" : "p-5"}`} aria-label="Talk to Guru">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(255,154,61,.08),transparent_60%)]" aria-hidden />
      {toolbar && <div className="relative mb-6 flex justify-center">{toolbar}</div>}

      <div className={`relative grid items-center gap-8 ${big ? "lg:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]" : "md:grid-cols-[auto_1fr]"}`}>
        {/* stage: orb + status + controls */}
        <div className="flex flex-col items-center text-center">
          <VoiceOrb state={ORB[phase]} level={level} size={big ? 240 : 140} />
          <AnimatePresence mode="wait">
            <motion.div key={phase} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.25 }} className="mt-4" aria-live="polite">
              <div className={`font-serif ${big ? "text-3xl" : "text-xl"}`}>{LABEL[phase]}</div>
              <div className="mx-auto mt-1 max-w-xs text-sm text-muted">{sub}</div>
            </motion.div>
          </AnimatePresence>
          <div className="mt-5 flex flex-wrap justify-center gap-2">
            {!inCall ? (
              <motion.button whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}
                className={`btn-primary ${big ? "px-8 py-3.5 text-base" : ""} shadow-[0_10px_40px_-10px_rgba(255,154,61,.6)]`} onClick={start}>
                <PhoneCall size={16} aria-hidden /> {phase === "ended" ? "Start again" : "Start call"}
              </motion.button>
            ) : (
              <>
                {phase === "listening" && rec.current && (
                  <button className="btn-ghost" onClick={() => rec.current?.finish()}><Square size={14} aria-hidden /> Done talking</button>
                )}
                <button className="btn border border-m-low/50 text-m-low hover:bg-m-low/10" onClick={() => hangUp()}>
                  <PhoneOff size={15} aria-hidden /> End
                </button>
              </>
            )}
          </div>
          {micOk === false && <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-m-low"><MicOff size={13} /> Mic blocked — type instead</p>}
          {micOk && inCall && <p className="mt-3 inline-flex items-center gap-1.5 text-xs text-muted"><Mic size={13} /> Mic on</p>}
        </div>

        {/* conversation */}
        <div className="glass flex min-h-[260px] flex-col rounded-card border border-line">
          <div ref={box} className={`flex-1 space-y-3 overflow-y-auto p-4 ${big ? "max-h-[420px]" : "max-h-72"}`} role="log" aria-live="polite">
            {msgs.length === 0 && phase === "idle" && (
              <div className="grid h-full min-h-[200px] place-items-center text-center text-sm text-muted">
                <div>
                  <div className="text-base text-text">Your conversation appears here</div>
                  <div className="mt-1">Speak in Hindi, English or a mix — Guru follows you.</div>
                </div>
              </div>
            )}
            <AnimatePresence initial={false}>
              {msgs.map((m) =>
                m.who === "note" ? (
                  <motion.p key={m.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center text-xs text-muted">{m.text}</motion.p>
                ) : (
                  <motion.div key={m.id} layout initial={{ opacity: 0, y: 12, scale: 0.97 }} animate={{ opacity: 1, y: 0, scale: 1 }}
                    transition={{ type: "spring", stiffness: 380, damping: 30 }} className={`flex flex-col ${m.who === "me" ? "items-end" : "items-start"}`}>
                    <span className="mb-1 px-1 text-[11px] uppercase tracking-wider text-muted">{m.who === "me" ? name : "Guru"}</span>
                    <div className={`max-w-[88%] rounded-2xl px-4 py-2.5 leading-relaxed ${big ? "text-[17px]" : "text-sm"} ${
                      m.who === "me" ? "rounded-br-md bg-accent/15 text-accent-2" : "rounded-bl-md bg-surface-2"}`}>
                      {m.who === "guru" ? <Typewriter text={m.text} /> : m.text}
                    </div>
                  </motion.div>
                ),
              )}
              {phase === "thinking" && (
                <motion.div key="typing" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="flex items-start">
                  <div className="typing rounded-2xl rounded-bl-md bg-surface-2 px-4 py-3" aria-label="Guru is thinking"><span /><span /><span /></div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          {inCall && (
            <form className="flex gap-2 border-t border-line p-3" onSubmit={(e) => { e.preventDefault(); sendTyped(); }}>
              <input value={typed} onChange={(e) => setTyped(e.target.value)} placeholder="Or type your answer…"
                className="min-w-0 flex-1 rounded-input border border-line bg-surface-2/70 px-3 py-2 text-sm" aria-label="Type your answer" />
              <button className="btn-ghost" type="submit" disabled={!typed.trim()}><Send size={14} aria-hidden /> Send</button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
