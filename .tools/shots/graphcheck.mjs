// The memory graph at several window sizes: how much of the canvas do the nodes actually use?
import { chromium } from "playwright-core";
import fs from "node:fs";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
fs.mkdirSync(OUT, { recursive: true });
const ASHU = process.argv[2] || "959275e6-cdcd-4e2b-b288-87ea872797e5";
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
for (const [w, h] of [[1360, 668], [1700, 836], [1446, 900]]) {
  const page = await (await b.newContext({ viewport: { width: w, height: h } })).newPage();
  await page.goto(`http://localhost:3000/live?student=${ASHU}`, { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForTimeout(6500);
  const box = page.locator('[aria-label="Knowledge graph"]').first();
  await box.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  const info = await box.evaluate((el) => {
    const c = el.querySelector("canvas"); const r = el.getBoundingClientRect();
    return { canvas: c ? `${c.clientWidth}x${c.clientHeight}` : "none", box: `${Math.round(r.width)}x${Math.round(r.height)}` };
  });
  console.log(`${w}x${h}:`, info);
  await box.screenshot({ path: `${OUT}graph-${w}.png` });
}
await b.close();
