// Headless Chrome screenshots of the Guru Line dashboard. Usage: node shoot.mjs [replay]
import { chromium } from "playwright-core";
import fs from "node:fs";

const BASE = "http://localhost:3000";
const R = "11111111-1111-4111-8111-111111111111";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });

const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const page = await (await browser.newContext({ viewport: { width: 1600, height: 1000 }, deviceScaleFactor: 1 })).newPage();
const errors = [];
page.on("console", (m) => m.type() === "error" && errors.push(`${page.url()} :: ${m.text()}`));
page.on("pageerror", (e) => errors.push(`${page.url()} :: PAGEERROR ${e.message}`));

const shot = async (name, full = false) => {
  await page.screenshot({ path: `${OUT}${name}.png`, fullPage: full });
  console.log("shot", name);
};

if (process.argv[2] === "replay") {
  await page.goto(`${BASE}/live`, { waitUntil: "domcontentloaded" });
  await page.getByRole("button", { name: /Replay Rahul session/ }).waitFor({ timeout: 90000 });
  await page.waitForTimeout(3000);
  await shot("live-before");
  await page.getByRole("button", { name: /Replay Rahul session/ }).click();
  await page.waitForTimeout(9000);
  await shot("live-mid-1");
  await page.waitForTimeout(8000);
  await shot("live-mid-2");
  await page.getByText("After this call").waitFor({ timeout: 90000 });
  await page.waitForTimeout(2500);
  await shot("live-after");
  await page.getByRole("button", { name: /Demo mode/ }).click();
  await page.waitForTimeout(1500);
  await shot("live-demo-mode");
} else {
  for (const [name, path] of [
    ["landing", "/"], ["teacher", "/teacher"], ["student", `/students/${R}`],
    ["privacy", "/privacy"], ["proof", "/proof"],
  ]) {
    await page.goto(BASE + path, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 90000 }).catch(() => {});
    // scroll through so whileInView reveals fire, as they would for a real visitor
    for (let y = 0; y < 6000; y += 500) { await page.mouse.wheel(0, 500); await page.waitForTimeout(120); }
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.waitForTimeout(2500);
    await shot(name, true);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(`${BASE}/parent/${R}`, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 90000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await shot("parent-mobile", true);
}
console.log(errors.length ? "CONSOLE ERRORS:\n" + errors.join("\n") : "no console errors");
await browser.close();
