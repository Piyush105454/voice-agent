"use client";
// Audio-reactive orb for the voice call. level (0..1) comes from the mic while listening and from Guru's own
// audio while speaking, so the orb visibly "hears" and "talks". Pure CSS/DOM: cheap, no canvas/WebGL.
import { motion, useReducedMotion, useSpring } from "framer-motion";
import { useEffect } from "react";

export type OrbState = "idle" | "connecting" | "listening" | "speaking" | "thinking" | "ended";

const PALETTE: Record<OrbState, { a: string; b: string; glow: string }> = {
  idle: { a: "#FF9A3D", b: "#7C3AED", glow: "rgba(255,154,61,.28)" },
  connecting: { a: "#FFD08A", b: "#FF9A3D", glow: "rgba(255,208,138,.28)" },
  listening: { a: "#3DD68C", b: "#22D3EE", glow: "rgba(61,214,140,.35)" },
  speaking: { a: "#FF9A3D", b: "#FFD08A", glow: "rgba(255,154,61,.42)" },
  thinking: { a: "#B794F6", b: "#7DD3FC", glow: "rgba(183,148,246,.35)" },
  ended: { a: "#4B5563", b: "#1F2937", glow: "rgba(139,147,161,.15)" },
};

export default function VoiceOrb({ state, level = 0, size = 220 }: { state: OrbState; level?: number; size?: number }) {
  const reduce = useReducedMotion();
  const c = PALETTE[state];
  const react = state === "listening" || state === "speaking";
  // springs smooth the raw RMS so the orb breathes instead of jittering
  const scale = useSpring(1, { stiffness: 260, damping: 18, mass: 0.6 });
  const halo = useSpring(1, { stiffness: 120, damping: 20 });
  useEffect(() => {
    const l = react ? Math.min(1, level) : 0;
    scale.set(1 + l * 0.22);
    halo.set(1 + l * 0.6);
  }, [level, react, scale, halo]);

  const spin = state === "thinking" ? 2.2 : state === "connecting" ? 3 : 14;
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }} aria-hidden>
      {/* outer glow, grows with loudness */}
      <motion.div className="absolute inset-[-18%] rounded-full blur-2xl transition-colors duration-700"
        style={{ scale: halo, background: `radial-gradient(circle, ${c.glow}, transparent 65%)` }} />
      {/* rotating light ring */}
      <motion.div className="absolute inset-0 rounded-full opacity-80"
        style={{ background: `conic-gradient(from 0deg, transparent 0deg, ${c.a} 70deg, transparent 140deg, ${c.b} 230deg, transparent 300deg)`,
                 WebkitMask: "radial-gradient(circle, transparent 62%, #000 63%, #000 66%, transparent 67%)",
                 mask: "radial-gradient(circle, transparent 62%, #000 63%, #000 66%, transparent 67%)" }}
        animate={reduce ? undefined : { rotate: 360 }} transition={{ duration: spin, repeat: Infinity, ease: "linear" }} />
      {/* liquid core */}
      <motion.div className="relative rounded-full" style={{ width: size * 0.58, height: size * 0.58, scale }}>
        <motion.div className="absolute inset-0"
          style={{ background: `radial-gradient(circle at 32% 28%, #fff6, transparent 32%), radial-gradient(circle at 70% 75%, ${c.b}, transparent 60%), radial-gradient(circle at 40% 40%, ${c.a}, var(--orb-edge) 85%)`,
                   boxShadow: `inset 0 0 40px ${c.glow}, 0 0 60px ${c.glow}`, transition: "background 0.7s" }}
          animate={reduce ? { borderRadius: "50%" } : {
            borderRadius: ["50% 50% 50% 50%", "56% 44% 52% 48%", "46% 54% 44% 56%", "50% 50% 50% 50%"],
            rotate: [0, 8, -6, 0],
          }}
          transition={{ duration: state === "speaking" ? 2.4 : 6, repeat: Infinity, ease: "easeInOut" }} />
      </motion.div>
    </div>
  );
}
