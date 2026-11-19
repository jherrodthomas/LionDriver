// Print why-liondriver-exists.html to a one-page US Letter PDF and a PNG of the same page.
//   node docs/liondriver/why/render.cjs
// Fails if the page does not fit on one sheet. Needs Playwright with Chromium.
const path = require("path");
const { chromium } = require("playwright");

(async () => {
  const dir = __dirname;
  const src = "file://" + path.join(dir, "why-liondriver-exists.html");
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 816, height: 1056 }, deviceScaleFactor: 2 });
  await page.goto(src, { waitUntil: "networkidle" });
  const over = await page.evaluate(() => {
    const p = document.querySelector(".page");
    return p.scrollHeight - p.clientHeight;
  });
  if (over > 0) {
    console.error(`one-pager overflows the sheet by ${over}px; shorten it`);
    process.exit(1);
  }
  await page.screenshot({ path: path.join(dir, "why-liondriver-exists.png"), clip: { x: 0, y: 0, width: 816, height: 1056 } });
  await page.emulateMedia({ media: "print" });
  await page.pdf({ path: path.join(dir, "why-liondriver-exists.pdf"), format: "Letter", printBackground: true,
                   margin: { top: 0, right: 0, bottom: 0, left: 0 }, pageRanges: "1" });
  await browser.close();
  console.log("wrote why-liondriver-exists.pdf and why-liondriver-exists.png");
})();
