"use client";
// Realtime feed: SSE from the API (Postgres LISTEN/NOTIFY) via the proxy; falls back to polling /events.
import { useEffect, useRef, useState } from "react";
import { api } from "./api";
import type { LiveEvent } from "./types";

export function useLiveEvents(studentId: string | null, onEvent: (e: LiveEvent) => void) {
  const [mode, setMode] = useState<"connecting" | "stream" | "polling">("connecting");
  const cb = useRef(onEvent);
  cb.current = onEvent;

  useEffect(() => {
    if (!studentId) return;
    let closed = false;
    let es: EventSource | null = null;
    let poll: ReturnType<typeof setInterval> | null = null;
    let lastId = 0;

    const startPolling = async () => {
      setMode("polling");
      try {
        const latest = await api<LiveEvent[]>(`events?student_id=${studentId}`);
        lastId = latest[0]?.id ?? 0;
      } catch {}
      poll = setInterval(async () => {
        try {
          const evs = await api<LiveEvent[]>(`events?student_id=${studentId}&after_id=${lastId}`);
          for (const e of evs.reverse()) {
            lastId = Math.max(lastId, e.id);
            cb.current(e);
          }
        } catch {}
      }, 2000);
    };

    try {
      es = new EventSource(`/api/gl/events/stream?student_id=${studentId}`);
      es.onopen = () => !closed && setMode("stream");
      es.onmessage = (m) => {
        try {
          cb.current(JSON.parse(m.data) as LiveEvent);
        } catch {}
      };
      es.onerror = () => {
        if (closed) return;
        es?.close();
        es = null;
        if (!poll) startPolling();
      };
    } catch {
      startPolling();
    }
    return () => {
      closed = true;
      es?.close();
      if (poll) clearInterval(poll);
    };
  }, [studentId]);

  return mode;
}
