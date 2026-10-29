// Real in-browser voice test: Chrome with a WAV file as the microphone, driving the dashboard's in-page call.
// Usage: node voicetest.mjs [url]   (default: dashboard /live Student tab)
import { chromium } from "playwright-core";

const FAKE = new URL("./fake-mic.wav", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const url = process.argv[2] || "http://localhost:3000/live";

const browser = await chromium.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", `--use-file-for-fake-audio-capture=${FAKE}`,
         "--autoplay-policy=no-user-gesture-required"],
});
const ctx = await browser.newContext({ viewport: { width: 1400, height: 1000 }, permissions: ["microphone"] });
await ctx.addInitScript(() => localStorage.setItem("gl:view", "simple"));
const page = await ctx.newPage();
const errors = [];
page.on("pageerror", (e) => errors.push("PAGEERROR " + e.message));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

await page.goto(url, { waitUntil: "domcontentloaded" });
await page.getByRole("radio", { name: /Any topic/ }).waitFor({ timeout: 90000 });
await page.getByRole("radio", { name: /Any topic/ }).click();
const start = page.getByRole("button", { name: /^Start call$/ });
await start.waitFor({ timeout: 90000 });
await start.click();
console.log("clicked Start call");

// Wait until the student's own (transcribed) words appear twice, or a speech-recognition problem is shown.
const deadline = Date.now() + 120000;
let lastLog = "";
while (Date.now() < deadline) {
  const log = await page.locator('[role="log"]').innerText().catch(() => "");
  if (log !== lastLog) {
    console.log("--- call log ---\n" + log.trim());
    lastLog = log;
  }
  if (/Speech recognition problem|Could not continue|Microphone is blocked/.test(log)) break;
  const mine = await page.locator('[role="log"] .items-end').count();
  if (mine >= 2) break;
  await page.waitForTimeout(1500);
}
await page.waitForTimeout(2500);
console.log("HEADER:", (await page.locator(".card").first().innerText()).replace(/s+/g, " ").slice(0, 120));
await page.screenshot({ path: OUT + "voicetest.png" });
const mine = await page.locator('[role="log"] .items-end').count();
console.log(`\nRESULT: student turns transcribed = ${mine}`);
console.log(errors.length ? "CONSOLE ERRORS:\n" + errors.join("\n") : "no console errors");
await page.getByRole("button", { name: /^End$/ }).click().catch(() => {});
await browser.close();
process.exit(mine >= 1 ? 0 : 1);
