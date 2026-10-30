import { chromium } from "playwright-core";
const OUT = new URL("./out/", import.meta.url).pathname.replace(/^\/([A-Z]:)/, "$1");
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
for (const [name, w, h, dark] of [["mobile", 390, 844, false], ["dark", 1531, 700, true]]) {
  const ctx = await b.newContext({ viewport: { width: w, height: h } });
  await ctx.addInitScript((d) => { if (d) localStorage.setItem("gl:theme", "dark"); }, dark);
  const page = await ctx.newPage();
  const errs = []; page.on("pageerror", (e) => errs.push(e.message));
  await page.goto("http://localhost:3000/", { waitUntil: "networkidle", timeout: 90000 });
  await page.waitForTimeout(3000);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  await page.screenshot({ path: `${OUT}landing-${name}.png` });
  console.log(name, "horizontal overflow:", overflow, "errors:", errs.length ? errs : "none");
}
await b.close();
