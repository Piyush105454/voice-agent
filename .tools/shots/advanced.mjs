// Advanced view (graph + panels) for a coaching student. Usage: node advanced.mjs <student_id> [dark]
import { chromium } from "playwright-core";
import fs from "node:fs";

const SID = process.argv[2];
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const ctx = await browser.newContext({ viewport: { width: 1500, height: 1000 } });
await ctx.addInitScript((dark) => {
  localStorage.setItem("gl:view", "advanced");
  if (dark) localStorage.setItem("gl:theme", "dark");
}, process.argv[3] === "dark");
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(`PAGEERROR ${e.message}`));
await page.goto(`http://localhost:3000/live?student=${SID}`, { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(6000);
await page.screenshot({ path: `${OUT}advanced.png` });
console.log("errors:", errors.length ? errors : "none");
await browser.close();
