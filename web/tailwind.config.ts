import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: "var(--surface)",
        "surface-2": "var(--surface-2)",
        line: "var(--line)",
        text: "var(--text)",
        muted: "var(--muted)",
        accent: "var(--accent)",
        "accent-2": "var(--accent-2)",
        "m-low": "var(--m-low)",
        "m-mid": "var(--m-mid)",
        "m-high": "var(--m-high)",
        misc: "var(--misc)",
      },
      fontFamily: {
        serif: ["var(--font-serif)", "Georgia", "serif"],
        sans: ["var(--font-sans)", "var(--font-deva)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
        deva: ["var(--font-deva)", "var(--font-sans)", "sans-serif"],
      },
      borderRadius: { card: "16px", input: "10px" },
      boxShadow: { glow: "0 0 80px rgba(255,154,61,.08)" },
      keyframes: {
        rise: { from: { opacity: "0", transform: "translateY(12px)" }, to: { opacity: "1", transform: "none" } },
        livepulse: { "0%,100%": { opacity: "1" }, "50%": { opacity: ".35" } },
        wave: { "0%,100%": { transform: "scaleY(.35)" }, "50%": { transform: "scaleY(1)" } },
      },
      animation: {
        rise: "rise .4s cubic-bezier(.2,.7,.2,1) both",
        livepulse: "livepulse 1.4s ease-in-out infinite",
        wave: "wave 1s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};
export default config;
