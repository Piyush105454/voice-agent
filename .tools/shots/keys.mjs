import { chromium } from "playwright-core";
const b = await chromium.launch({ executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
const p = await (await b.newContext({ viewport: { width: 1600, height: 1000 } })).newPage();
p.on("console", async (m) => {
  if (!m.text().includes("same key")) return;
  const args = await Promise.all(m.args().map((a) => a.jsonValue().catch(() => "?")));
  console.log("KEY:", JSON.stringify(args[1]), "|", String(args[2] ?? "").split("\n").slice(0, 6).join(" <- "));
});
await p.goto("http://localhost:3000/students/11111111-1111-4111-8111-111111111111");
await p.waitForTimeout(8000);
await b.close();
