const { chromium } = require('playwright-core');
const path = require('path');
const fs = require('fs');

async function main() {
  const harnessUrl = process.env.FRIDAY_HARNESS_URL;
  if (!harnessUrl) throw new Error('Set FRIDAY_HARNESS_URL to the current authenticated Harness URL.');
  const screenshotsDir = 'C:/Users/ankus/.gemini/antigravity/scratch/tiny_expert_system/harness_screenshots';
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  console.log('=== DeepSeek Harness Browser Live Test for Physics Queries ===');
  console.log('1. Launching Google Chrome...');

  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: false,
    args: ['--start-maximized']
  });

  const context = await browser.newContext({ viewport: null });
  const page = await context.newPage();

  console.log('2. Navigating to Harness Web UI:', harnessUrl);
  await page.goto(harnessUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  const inputSelector = '[role="textbox"][contenteditable="true"]';
  await page.waitForSelector(inputSelector, { timeout: 15000 });

  // Test Query 1: "what is motion?"
  console.log('\n--- Testing Query 1: "what is motion?" ---');
  let inputElem = await page.$(inputSelector);
  await inputElem.click();
  await page.waitForTimeout(300);
  await page.keyboard.type('what is motion?', { delay: 30 });
  await page.waitForTimeout(500);

  const sendBtn1 = await page.$('button[aria-label="Send message"], button.GRgSLq_primary');
  if (sendBtn1) await sendBtn1.click();
  else await page.keyboard.press('Enter');

  console.log('Waiting for response stream...');
  for (let i = 0; i < 25; i++) {
    await page.waitForTimeout(1000);
    const body = await page.evaluate(() => document.body.innerText);
    if (body.includes('Motion and Kinematics') || body.includes('displacement, velocity, and acceleration')) {
      console.log(`-> Motion answer appeared at second ${i + 1}!`);
      break;
    }
  }
  await page.waitForTimeout(3000);

  const shotMotion = path.join(screenshotsDir, '06_motion_browser_verified.png');
  await page.screenshot({ path: shotMotion });
  console.log('-> Saved screenshot:', shotMotion);

  // Test Query 2: "3rd law of gravity"
  console.log('\n--- Testing Query 2: "3rd law of gravity" ---');
  await page.waitForSelector(inputSelector, { timeout: 10000 });
  inputElem = await page.$(inputSelector);
  await inputElem.click();
  await page.waitForTimeout(300);
  await page.keyboard.type('3rd law of gravity', { delay: 30 });
  await page.waitForTimeout(500);

  const sendBtn2 = await page.$('button[aria-label="Send message"], button.GRgSLq_primary');
  if (sendBtn2) await sendBtn2.click();
  else await page.keyboard.press('Enter');

  console.log('Waiting for response stream...');
  for (let i = 0; i < 25; i++) {
    await page.waitForTimeout(1000);
    const body = await page.evaluate(() => document.body.innerText);
    if (body.includes('Third Law of Gravity') || body.includes('Kepler') || body.includes('Harmonic Law')) {
      console.log(`-> 3rd law of gravity answer appeared at second ${i + 1}!`);
      break;
    }
  }
  await page.waitForTimeout(3000);

  const shotGravity = path.join(screenshotsDir, '07_third_law_gravity_browser_verified.png');
  await page.screenshot({ path: shotGravity });
  console.log('-> Saved screenshot:', shotGravity);

  const fullText = await page.evaluate(() => document.body.innerText);
  console.log('\n=== Captured Harness Web UI Text Snippet ===');
  const relevantLines = fullText.split('\n')
    .filter(l => l.includes('Motion and Kinematics') || l.includes('Third Law of Gravity') || l.includes('Principle:') || l.includes('Canonical Equation:'))
    .slice(0, 10);
  relevantLines.forEach(l => console.log('  ', l.trim()));

  console.log('\nKeeping browser window open 5 seconds...');
  await page.waitForTimeout(5000);

  await browser.close();
  console.log('=== Browser Test Complete ===');
}

main().catch(err => {
  console.error('Error during browser test:', err);
  process.exit(1);
});
