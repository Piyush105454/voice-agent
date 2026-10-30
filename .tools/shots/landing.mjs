// First screen of the landing page at a laptop-sized viewport (no scrolling). Usage: node landing.mjs [dark]
import { chromium } from "playwright-core";
import fs from "node:fs";

const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const ctx = await browser.newContext({ viewport: { width: 1531, height: 700 } });
await ctx.addInitScript((dark) => { if (dark) localStorage.setItem("gl:theme", "dark"); }, process.argv[2] === "dark");
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(`PAGEERROR ${e.message}`));
await page.goto("http://localhost:3000/", { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(3500);
await page.screenshot({ path: `${OUT}landing-first-screen.png` });
const inView = await page.evaluate(() => {
  const h = window.innerHeight;
  const q = (t) => [...document.querySelectorAll("*")].find((e) => e.children.length === 0 && e.textContent.trim().startsWith(t));
  return Object.fromEntries(["Open Operator Console", "No app needed", "Any Qualification", "Memory Graph", "Live Grounding"]
    .map((t) => [t, Math.round(q(t)?.getBoundingClientRect().bottom ?? -1) + " / " + h]));
});
console.log("bottom edge vs viewport:", inView);
await page.setViewportSize({ width: 1531, height: 1000 });
await page.waitForTimeout(500);
await page.screenshot({ path: `${OUT}landing-tall.png`, fullPage: false });
console.log("errors:", errors.length ? errors : "none");
await browser.close();
