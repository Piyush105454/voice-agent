// The user's student page after phone calls: journal + "What Guru knows about you".
import { chromium } from "playwright-core";
import fs from "node:fs";

const SID = "85f498f8-7895-42ee-a6e2-f647631bd3cc";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 1000 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(`PAGEERROR ${e.message}`));
await page.goto(`http://localhost:3000/live?student=${SID}`, { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(2500);
const j = page.getByText("What Guru knows about you");
await j.scrollIntoViewIfNeeded();
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}journal-profile.png` });
await page.mouse.wheel(0, 650);
await page.waitForTimeout(1500);
await page.screenshot({ path: `${OUT}journal-days.png` });
console.log("errors:", errors.length ? errors : "none");
await browser.close();
