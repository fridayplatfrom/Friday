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

  console.log('=== DeepSeek Harness Browser Live Control Test ===');
  console.log('1. Launching visible Google Chrome window...');

  const browser = await chromium.launch({
    executablePath: 'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    headless: false,
    args: ['--start-maximized']
  });

  const context = await browser.newContext({
    viewport: null // use window size
  });
  const page = await context.newPage();

  console.log('2. Navigating to DeepSeek Harness web interface:', harnessUrl);
  await page.goto(harnessUrl, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(3000);

  // Take screenshot 1: Ready state
  const shot1 = path.join(screenshotsDir, '01_harness_ready.png');
  await page.screenshot({ path: shot1 });
  console.log('-> Captured screenshot 1: Ready state ->', shot1);

  // Find the contenteditable input textbox
  const inputSelector = '[role="textbox"][contenteditable="true"]';
  await page.waitForSelector(inputSelector, { timeout: 10000 });
  const inputElem = await page.$(inputSelector);
  if (!inputElem) {
    throw new Error('Could not find prompt textbox in Harness UI');
  }

  const promptText = 'Calculate the kinetic energy of a 4 kg mass moving at 15 m/s and derive the governing principle.';
  console.log(`3. Typing prompt into DeepSeek Harness prompt box: "${promptText}"`);
  await inputElem.click();
  await page.waitForTimeout(500);

  // Type prompt characters
  await page.keyboard.type(promptText, { delay: 35 });
  await page.waitForTimeout(1000);

  // Take screenshot 2: Prompt typed
  const shot2 = path.join(screenshotsDir, '02_harness_prompt_typed.png');
  await page.screenshot({ path: shot2 });
  console.log('-> Captured screenshot 2: Prompt typed ->', shot2);

  // Click Send button or press Enter
  console.log('4. Submitting prompt to Tiny Expert OS engine...');
  const sendButton = await page.$('button[aria-label="Send message"], button.GRgSLq_primary');
  if (sendButton) {
    await sendButton.click();
  } else {
    await page.keyboard.press('Enter');
  }

  console.log('5. Waiting for streaming response from Tiny Expert OS...');
  // Wait a few seconds for thinking/reasoning trace to start streaming
  await page.waitForTimeout(3500);

  const shot3 = path.join(screenshotsDir, '03_harness_reasoning_streaming.png');
  await page.screenshot({ path: shot3 });
  console.log('-> Captured screenshot 3: Reasoning streaming ->', shot3);

  // Wait for completion (look for the answer sections or wait until reasoning completes)
  console.log('6. Streaming answer and citations...');
  let completed = false;
  for (let i = 0; i < 20; i++) {
    await page.waitForTimeout(2000);
    const bodyText = await page.evaluate(() => document.body.innerText);
    if (bodyText.includes('Exact Symbolic & Numerical Solution') || bodyText.includes('450') || bodyText.includes('Multi-Book SHA-256')) {
      completed = true;
      console.log(`-> Detected completed answer on iteration ${i + 1}!`);
      break;
    }
  }

  await page.waitForTimeout(3000);

  // Take screenshot 4: Completed answer
  const shot4 = path.join(screenshotsDir, '04_harness_answer_completed.png');
  await page.screenshot({ path: shot4 });
  console.log('-> Captured screenshot 4: Answer completed ->', shot4);

  // Extract the text of the conversation turn
  const conversationText = await page.evaluate(() => {
    const messages = Array.from(document.querySelectorAll('[class*="message"], [class*="turn"], [class*="item"]'));
    return document.body.innerText;
  });

  console.log('=== DeepSeek Harness Browser UI Output Summary ===');
  const lines = conversationText.split('\n').filter(l => l.trim().length > 0);
  console.log('Total text lines captured:', lines.length);
  console.log('Sample output (first 25 lines):');
  lines.slice(0, 25).forEach(l => console.log('  ', l));

  console.log('\nKeeping browser window open for 15 seconds for user to view live...');
  await page.waitForTimeout(15000);

  await browser.close();
  console.log('=== Test Complete ===');
}

main().catch(err => {
  console.error('Browser automation error:', err);
  process.exit(1);
});
