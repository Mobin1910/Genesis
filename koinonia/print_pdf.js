// Usage: node print_pdf.js <in.html> <out.pdf>
// Prints an HTML file to PDF with Chromium (A4, CSS @page margins honoured).
const path = require('path');
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');

(async () => {
  const [inHtml, outPdf] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.goto('file://' + path.resolve(inHtml), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: outPdf, preferCSSPageSize: true, printBackground: true });
  await browser.close();
})();
