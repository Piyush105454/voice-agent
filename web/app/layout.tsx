import type { Metadata } from "next";
import { JetBrains_Mono, Newsreader, Noto_Sans_Devanagari, Plus_Jakarta_Sans } from "next/font/google";
import Nav from "@/components/Nav";
import "./globals.css";

// Editorial serif with a real italic for accent words + a friendly geometric sans for UI text.
const serif = Newsreader({ subsets: ["latin"], weight: ["400", "500"], style: ["normal", "italic"], variable: "--font-serif", display: "swap" });
const sans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-sans", display: "swap" });
const mono = JetBrains_Mono({ subsets: ["latin"], variable: "--font-mono", display: "swap" });
const deva = Noto_Sans_Devanagari({ subsets: ["devanagari"], weight: ["400", "500"], variable: "--font-deva", display: "swap" });

export const metadata: Metadata = {
  title: "Guru Line · A tutor on a normal phone call",
  description: "A phone-call AI tutor that remembers every misconception a student has, and proves they improved.",
};

// Applies the saved theme before first paint (no light->dark flash). Light is the default.
const THEME_BOOT = `try{var t=localStorage.getItem("gl:theme");document.documentElement.dataset.theme=t==="dark"?"dark":"light"}catch(e){document.documentElement.dataset.theme="light"}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning className={`${serif.variable} ${sans.variable} ${mono.variable} ${deva.variable}`}>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_BOOT }} />
      </head>
      <body className="min-h-screen font-sans">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 btn-primary">Skip to content</a>
        <div className="aurora" aria-hidden />
        <Nav />
        {/* the nav floats (fixed); this keeps page content clear of it */}
        <main id="main" className="pt-24">{children}</main>
      </body>
    </html>
  );
}
