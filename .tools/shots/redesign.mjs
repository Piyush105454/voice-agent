// Screenshots for the redesign: landing (hero, facts, each scrollytelling step, CTA) + /live student (idle, in call).
import { chromium } from "playwright-core";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const FAKE = new URL("./fake-mic.wav", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const b = await chromium.launch({
  executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe",
  args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", `--use-file-for-fake-audio-capture=${FAKE}`, "--autoplay-policy=no-user-gesture-required"],
});
const ctx = await b.newContext({ viewport: { width: 1440, height: 900 }, permissions: ["microphone"] });
await ctx.addInitScript(() => localStorage.setItem("gl:view", "simple"));
const p = await ctx.newPage();
const errs = [];
p.on("pageerror", (e) => errs.push("PAGEERROR " + e.message));
p.on("console", (m) => m.type() === "error" && errs.push(m.text()));
const shot = async (n) => { await p.screenshot({ path: `${OUT}${n}.png` }); console.log("shot", n); };

await p.goto("http://localhost:3000/", { waitUntil: "networkidle" });
await p.waitForTimeout(2500); await shot("r-hero");
await p.mouse.wheel(0, 700); await p.waitForTimeout(1200); await shot("r-facts");
const sec = await p.locator('section[aria-label="How it works"] > div').first().boundingBox();
const top = await p.evaluate(() => window.scrollY) + (sec?.y ?? 0);
for (const [i, f] of [[0, 0.05], [1, 0.32], [2, 0.57], [3, 0.82]]) {
  await p.evaluate((y) => window.scrollTo(0, y), top + (sec?.height ?? 2700) * f);
  await p.waitForTimeout(900); await shot(`r-step${i + 1}`);
}
await p.evaluate(() => window.scrollTo(0, document.body.scrollHeight - 1700)); await p.waitForTimeout(1200); await shot("r-cta");

await p.goto("http://localhost:3000/live", { waitUntil: "networkidle" });
await p.getByRole("button", { name: /^Start call$/ }).waitFor({ timeout: 90000 });
await p.waitForTimeout(1500); await shot("r-live-idle");
await p.getByRole("tab", { name: /English speaking/ }).click(); await p.waitForTimeout(600);
await p.getByRole("button", { name: /^Start call$/ }).click();
await p.waitForTimeout(4500); await shot("r-live-call-1");
await p.waitForTimeout(7000); await shot("r-live-call-2");
await p.waitForTimeout(8000); await shot("r-live-call-3");
await p.getByRole("button", { name: /^End$/ }).click().catch(() => {});
await p.getByRole("tab", { name: /Advanced/ }).click(); await p.waitForTimeout(2500); await shot("r-live-advanced");
console.log(errs.length ? "ERRORS:\n" + errs.join("\n") : "no console errors");
await b.close();
