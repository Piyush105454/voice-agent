import { chromium } from "playwright-core";
import fs from "node:fs";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
for (const [w, h] of [[1446, 746], [1531, 700], [1920, 1000], [1366, 640]]) {
  const page = await (await b.newContext({ viewport: { width: w, height: h } })).newPage();
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForTimeout(2800);
  const r = await page.evaluate(() => {
    const how = [...document.querySelectorAll("*")].find((e) => e.children.length === 0 && /^HOW GURUJI WORKS/i.test(e.textContent.trim()));
    const portals = [...document.querySelectorAll("*")].find((e) => e.children.length === 0 && e.textContent.trim().startsWith("Live Grounding"));
    return { howTop: Math.round(how.getBoundingClientRect().top), portalsBottom: Math.round(portals.getBoundingClientRect().bottom),
             helpline: document.body.innerText.includes("Helpline") };
  });
  console.log(`${w}x${h}: next-section label at y=${r.howTop} (hidden: ${r.howTop >= h}), portals line ends y=${r.portalsBottom} (visible: ${r.portalsBottom <= h}), helpline present: ${r.helpline}`);
  if (w === 1446) await page.screenshot({ path: `${OUT}landing-fold.png` });
}
await b.close();
