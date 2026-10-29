"use client";
// Re-mounted on every navigation: gives each page a soft fade/rise entrance.
import { motion, useReducedMotion } from "framer-motion";

export default function Template({ children }: { children: React.ReactNode }) {
  const reduce = useReducedMotion();
  return (
    <motion.div initial={reduce ? false : { opacity: 0, y: 14, filter: "blur(6px)" }}
      animate={{ opacity: 1, y: 0, filter: "blur(0px)" }} transition={{ duration: 0.45, ease: [0.2, 0.7, 0.2, 1] }}>
      {children}
    </motion.div>
  );
}
