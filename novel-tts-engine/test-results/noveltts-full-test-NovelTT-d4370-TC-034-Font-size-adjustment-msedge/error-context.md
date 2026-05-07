# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: noveltts-full-test.spec.js >> NovelTTS Cloud Full Test >> Module 4: Content Display >> TC-034: Font size adjustment
- Location: tests\e2e\noveltts-full-test.spec.js:556:5

# Error details

```
TimeoutError: page.goto: Timeout 15000ms exceeded.
Call log:
  - navigating to "http://localhost:8080/", waiting until "domcontentloaded"

```

# Test source

```ts
  1   | /**
  2   |  * NovelTTS Cloud - Full End-to-End Test
  3   |  * Test scope: Project creation, project management, content display, audio generation
  4   |  */
  5   | const { test, expect } = require('@playwright/test');
  6   | 
  7   | const FRONTEND_URL = 'http://localhost:8080';
  8   | const BACKEND_URL = 'http://localhost:8000/api/v1';
  9   | 
  10  | const TEST_FILE_CONTENT = `Chapter 1: The Fallen Genius
  11  | 
  12  | "What do you mean?" Qin Yu asked.
  13  | 
  14  | Lin Fan remained silent for a moment, then slowly said: "Some things are not as simple as you think."
  15  | 
  16  | Qin Yu sneered: "Not simple? Let me see how not simple it is!"
  17  | 
  18  | Chapter 2: A New Beginning
  19  | 
  20  | Morning sunlight spilled across the earth, birds singing joyfully on the branches.
  21  | 
  22  | "Today is a good day," Lin Fan muttered to himself.
  23  | 
  24  | He pushed open the window, took a deep breath, feeling strength flowing through his body.
  25  | 
  26  | Chapter 3: Danger Everywhere
  27  | 
  28  | Night fell, silence all around.
  29  | 
  30  | "Watch out!" Qin Yu shouted.
  31  | 
  32  | A dark shadow leaped from the darkness, straight at Lin Fan.
  33  | 
  34  | Lin Fan dodged to the side, barely avoiding it.
  35  | `;
  36  | 
  37  | let consoleErrors = [];
  38  | let consoleLogs = [];
  39  | let apiRequests = [];
  40  | 
  41  | async function gotoPage(page) {
> 42  |   await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
      |              ^ TimeoutError: page.goto: Timeout 15000ms exceeded.
  43  |   await page.waitForSelector('.navbar', { timeout: 5000 });
  44  |   await page.waitForTimeout(1000);
  45  | }
  46  | 
  47  | test.beforeAll(async ({ browser }) => {
  48  |   console.log('\n========== Test Start ==========');
  49  |   console.log('Frontend URL:', FRONTEND_URL);
  50  |   console.log('Backend URL:', BACKEND_URL);
  51  | });
  52  | 
  53  | test.describe('NovelTTS Cloud Full Test', () => {
  54  | 
  55  |   test.beforeEach(async ({ page }) => {
  56  |     consoleErrors = [];
  57  |     consoleLogs = [];
  58  |     apiRequests = [];
  59  | 
  60  |     page.on('console', msg => {
  61  |       if (msg.type() === 'error') {
  62  |         consoleErrors.push(msg.text());
  63  |       } else {
  64  |         consoleLogs.push({ type: msg.type(), text: msg.text() });
  65  |       }
  66  |     });
  67  | 
  68  |     page.on('request', request => {
  69  |       if (request.url().includes('/api/v1/')) {
  70  |         apiRequests.push({
  71  |           url: request.url(),
  72  |           method: request.method(),
  73  |           postData: request.postData(),
  74  |         });
  75  |       }
  76  |     });
  77  | 
  78  |     page.on('pageerror', error => {
  79  |       consoleErrors.push(`Page error: ${error.message}`);
  80  |     });
  81  |   });
  82  | 
  83  |   // ============================================================
  84  |   // Module 1: Page Loading & Basic Functions
  85  |   // ============================================================
  86  |   test.describe('Module 1: Page Loading & Basic Functions', () => {
  87  | 
  88  |     test('TC-001: Home page loads correctly', async ({ page }) => {
  89  |       console.log('\n--- TC-001: Home page loads ---');
  90  | 
  91  |       await gotoPage(page);
  92  | 
  93  |       await expect(page.locator('.navbar')).toBeVisible();
  94  |       await expect(page.locator('.nav-logo')).toContainText('NovelTTS Cloud');
  95  | 
  96  |       const navLinks = page.locator('.nav-link');
  97  |       await expect(navLinks).toHaveCount(4);
  98  |       await expect(navLinks.nth(0)).toContainText('首页');
  99  |       await expect(navLinks.nth(1)).toContainText('项目管理');
  100 |       await expect(navLinks.nth(2)).toContainText('音色库');
  101 |       await expect(navLinks.nth(3)).toContainText('系统设置');
  102 | 
  103 |       await expect(page.locator('.welcome')).toBeVisible();
  104 |       await expect(page.locator('.welcome h1')).toContainText('欢迎回来');
  105 | 
  106 |       await expect(page.locator('.stat-grid')).toBeVisible();
  107 |       await expect(page.locator('.stat-card')).toHaveCount(3);
  108 | 
  109 |       console.log('  [PASS] Page loaded, all elements visible');
  110 |     });
  111 | 
  112 |     test('TC-002: Page navigation switching', async ({ page }) => {
  113 |       console.log('\n--- TC-002: Navigation switching ---');
  114 | 
  115 |       await gotoPage(page);
  116 | 
  117 |       // Switch to Projects
  118 |       await page.click('text=项目管理');
  119 |       await page.waitForTimeout(500);
  120 |       await expect(page.locator('#page-projects')).toHaveClass(/active/);
  121 | 
  122 |       // Switch to Voices
  123 |       await page.click('text=音色库');
  124 |       await page.waitForTimeout(500);
  125 |       await expect(page.locator('#page-voices')).toHaveClass(/active/);
  126 | 
  127 |       // Switch to Settings
  128 |       await page.click('text=系统设置');
  129 |       await page.waitForTimeout(500);
  130 |       await expect(page.locator('#page-settings')).toHaveClass(/active/);
  131 | 
  132 |       // Back to Home
  133 |       await page.click('text=首页');
  134 |       await page.waitForTimeout(500);
  135 |       await expect(page.locator('#page-home')).toHaveClass(/active/);
  136 | 
  137 |       console.log('  [PASS] All page navigation works');
  138 |     });
  139 | 
  140 |     test('TC-003: Backend health check connectivity', async ({ page }) => {
  141 |       console.log('\n--- TC-003: Backend connectivity ---');
  142 | 
```