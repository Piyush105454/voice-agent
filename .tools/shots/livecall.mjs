// The Live Conversation panel for ashu (who has several real phone calls and no saved phone number).
import { chromium } from "playwright-core";
import fs from "node:fs";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const ASHU = "959275e6-cdcd-4e2b-b288-87ea872797e5";
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const page = await (await b.newContext({ viewport: { width: 1446, height: 900 } })).newPage();
const errs = []; page.on("pageerror", (e) => errs.push(e.message));
await page.goto(`http://localhost:3000/live?student=${ASHU}`, { waitUntil: "networkidle", timeout: 90000 });
await page.waitForTimeout(3500);
const panel = page.locator("section", { has: page.getByText(/Live Conversation/) });
console.log("heading:", (await panel.locator("h2").first().innerText()));
console.log("bubbles:", await panel.locator("div.rounded-2xl").count(), "| waiting text:", await page.getByText("Waiting for caller speech").count());
console.log("first bubble:", (await panel.locator("div.rounded-2xl").first().innerText()).replace(/\s+/g, " ").slice(0, 90));
console.log("footer:", (await panel.locator("div.border-t").last().innerText()).trim());
console.log("header chip:", (await page.locator("h1").first().locator("xpath=../span[1]").innerText().catch(() => "?")));
for (const tab of ["Previous", "Earlier"]) {
  await panel.getByRole("button", { name: tab }).click();
  await page.waitForTimeout(1200);
  console.log(tab, "-> bubbles:", await panel.locator("div.rounded-2xl").count(), "|", (await panel.locator("div.border-t").last().innerText()).trim());
}
await panel.getByRole("button", { name: "Latest call" }).click();
await page.waitForTimeout(600);
await panel.scrollIntoViewIfNeeded();
await page.screenshot({ path: `${OUT}livecall.png` });

// call feedback: a bad number is refused with a clear message, not silently ignored
await page.getByPlaceholder(/Enter verified/).fill("12345");
await page.getByRole("button", { name: "Call Number Now" }).click();
await page.waitForTimeout(1500);
console.log("bad number ->", (await page.getByRole("status").first().innerText().catch(() => "(none)")).trim());
console.log("errors:", errs.length ? errs : "none");
await b.close();
