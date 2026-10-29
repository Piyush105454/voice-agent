// Sign-up flow: /start form -> submit -> lands in the new student's own /live space.
import { chromium } from "playwright-core";
import fs from "node:fs";

const BASE = "http://localhost:3000";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const page = await (await browser.newContext({ viewport: { width: 1440, height: 900 } })).newPage();
const errors = [];
page.on("pageerror", (e) => errors.push(`PAGEERROR ${e.message}`));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

await page.goto(`${BASE}/start`, { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(1200);
await page.screenshot({ path: `${OUT}start-empty.png` });
await page.getByRole("button", { name: /Start talking/ }).click();
await page.waitForTimeout(400);
await page.screenshot({ path: `${OUT}start-error.png` });
await page.fill("#name", "Kiran");
await page.selectOption("#grade", "8");
await page.getByText(/agrees that my calls/).click();
await page.getByRole("button", { name: /Start talking/ }).click();
await page.waitForURL(/\/live\?student=/, { timeout: 30000 });
await page.waitForTimeout(5000);
await page.screenshot({ path: `${OUT}live-new-student.png` });
console.log("landed:", page.url());
console.log("picker:", await page.locator("select").first().evaluate((s) => s.options[s.selectedIndex]?.text).catch(() => "?"));
await page.goto(`${BASE}/start`, { waitUntil: "networkidle" });
console.log("continue link:", await page.getByText(/Continue as/).textContent().catch(() => "missing"));
console.log("errors:", errors.length ? errors : "none");
await browser.close();
