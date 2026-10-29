"use client";
// Voice call shown as a chat: Guru on the left, the student on the right (phone and browser calls alike).
import { motion } from "framer-motion";
import { useEffect, useRef } from "react";
import type { Line } from "@/lib/types";

export default function ChatTranscript({ lines, studentName, big = false, renderTag, maxHeight = 420 }: {
  lines: Line[];
  studentName: string;
  big?: boolean;
  renderTag?: (index: number) => React.ReactNode;
  maxHeight?: number;
}) {
  const box = useRef<HTMLDivElement>(null);
  useEffect(() => {
    box.current?.scrollTo({ top: box.current.scrollHeight, behavior: "smooth" });
  }, [lines.length]);

  return (
    <div ref={box} className="space-y-3 overflow-y-auto pr-1" style={{ maxHeight }} role="log" aria-live="polite">
      {lines.map((l, i) => {
        const me = l.speaker === "student";
        return (
          <motion.div key={i} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}
            className={`flex flex-col ${me ? "items-end" : "items-start"}`}>
            <span className="mb-1 px-1 text-[11px] uppercase tracking-wider text-muted">{me ? studentName : "Guru"}</span>
            <div className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 leading-relaxed ${big ? "text-lg" : "text-[15px]"} ${
              me ? "rounded-br-md bg-accent/15 text-accent-2" : "rounded-bl-md bg-surface-2"}`}>
              {l.text}
            </div>
            {renderTag?.(i)}
          </motion.div>
        );
      })}
    </div>
  );
}
