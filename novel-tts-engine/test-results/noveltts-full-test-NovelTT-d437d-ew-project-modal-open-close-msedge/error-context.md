# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: noveltts-full-test.spec.js >> NovelTTS Cloud Full Test >> Module 2: Project Creation >> TC-010: New project modal open/close
- Location: tests\e2e\noveltts-full-test.spec.js:177:5

# Error details

```
Test timeout of 60000ms exceeded.
```

```
Error: page.click: Test timeout of 60000ms exceeded.
Call log:
  - waiting for locator('[data-action="open-modal"][data-modal="new-project"]')
    - locator resolved to <button class="btn btn-primary" data-action="open-modal" data-modal="new-project">…</button>
  - attempting click action
    2 × waiting for element to be visible, enabled and stable
      - element is not visible
    - retrying click action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and stable
      - element is not visible
    - retrying click action
      - waiting 100ms
    114 × waiting for element to be visible, enabled and stable
        - element is not visible
      - retrying click action
        - waiting 500ms

```

# Test source

```ts
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
  143 |       await gotoPage(page);
  144 |       await page.waitForTimeout(3000);
  145 | 
  146 |       const healthRequests = apiRequests.filter(r => r.url.includes('/health'));
  147 |       console.log('  Health check requests:', healthRequests.length);
  148 |       expect(healthRequests.length).toBeGreaterThanOrEqual(1);
  149 |       console.log('  [PASS] Backend connectivity OK');
  150 |     });
  151 | 
  152 |     test('TC-004: Console error check', async ({ page }) => {
  153 |       console.log('\n--- TC-004: Console errors ---');
  154 | 
  155 |       await gotoPage(page);
  156 |       await page.waitForTimeout(5000);
  157 | 
  158 |       const criticalErrors = consoleErrors.filter(e =>
  159 |         !e.includes('preview') && !e.includes('favicon')
  160 |       );
  161 | 
  162 |       console.log('  Console errors:', consoleErrors.length);
  163 |       console.log('  Critical errors:', criticalErrors.length);
  164 |       if (criticalErrors.length > 0) {
  165 |         criticalErrors.forEach(e => console.log('    Error:', e.substring(0, 200)));
  166 |       }
  167 |       expect(criticalErrors.length).toBeLessThanOrEqual(3);
  168 |       console.log('  [PASS] No critical console errors');
  169 |     });
  170 |   });
  171 | 
  172 |   // ============================================================
  173 |   // Module 2: Project Creation
  174 |   // ============================================================
  175 |   test.describe('Module 2: Project Creation', () => {
  176 | 
  177 |     test('TC-010: New project modal open/close', async ({ page }) => {
  178 |       console.log('\n--- TC-010: New project modal ---');
  179 | 
  180 |       await gotoPage(page);
  181 | 
> 182 |       await page.click('[data-action="open-modal"][data-modal="new-project"]');
      |                  ^ Error: page.click: Test timeout of 60000ms exceeded.
  183 |       await page.waitForTimeout(500);
  184 |       await expect(page.locator('#modal-new-project')).toHaveClass(/open/);
  185 | 
  186 |       await expect(page.locator('#file-input')).toBeVisible();
  187 |       await expect(page.locator('#new-project-title')).toBeVisible();
  188 |       await expect(page.locator('#new-project-author')).toBeVisible();
  189 |       await expect(page.locator('#new-project-content')).toBeVisible();
  190 | 
  191 |       await page.click('[data-action="close-modal"][data-modal="new-project"]');
  192 |       await page.waitForTimeout(500);
  193 |       await expect(page.locator('#modal-new-project')).not.toHaveClass(/open/);
  194 | 
  195 |       console.log('  [PASS] Modal open/close OK');
  196 |     });
  197 | 
  198 |     test('TC-011: File upload creates project', async ({ page }) => {
  199 |       console.log('\n--- TC-011: File upload project ---');
  200 | 
  201 |       await gotoPage(page);
  202 |       await page.waitForTimeout(1000);
  203 | 
  204 |       const fs = require('fs');
  205 |       const path = require('path');
  206 |       const testFilePath = path.join(__dirname, 'test_novel_upload.txt');
  207 |       fs.writeFileSync(testFilePath, TEST_FILE_CONTENT, 'utf8');
  208 | 
  209 |       await page.click('[data-action="open-modal"][data-modal="new-project"]');
  210 |       await page.waitForTimeout(500);
  211 | 
  212 |       const fileInput = page.locator('#file-input');
  213 |       await fileInput.setInputFiles(testFilePath);
  214 | 
  215 |       await page.waitForTimeout(8000);
  216 | 
  217 |       const projectCards = page.locator('.project-card');
  218 |       const cardCount = await projectCards.count();
  219 | 
  220 |       console.log('  Project card count:', cardCount);
  221 | 
  222 |       try { fs.unlinkSync(testFilePath); } catch {}
  223 | 
  224 |       expect(cardCount).toBeGreaterThanOrEqual(1);
  225 |       console.log('  [PASS] File upload project created');
  226 |     });
  227 | 
  228 |     test('TC-012: Delete project', async ({ page }) => {
  229 |       console.log('\n--- TC-012: Delete project ---');
  230 | 
  231 |       await gotoPage(page);
  232 |       await page.waitForTimeout(2000);
  233 | 
  234 |       let cards = await page.locator('.project-card').count();
  235 |       if (cards === 0) {
  236 |         console.log('  [SKIP] No projects to delete');
  237 |         return;
  238 |       }
  239 | 
  240 |       const beforeCount = cards;
  241 |       console.log('  Before delete:', beforeCount);
  242 | 
  243 |       await page.locator('.delete-btn').first().click();
  244 |       await page.waitForTimeout(500);
  245 | 
  246 |       await expect(page.locator('#modal-confirm-delete')).toHaveClass(/open/);
  247 | 
  248 |       await page.click('[data-action="confirm-delete"]');
  249 |       await page.waitForTimeout(3000);
  250 | 
  251 |       const newCards = await page.locator('.project-card').count();
  252 |       console.log('  After delete:', newCards);
  253 | 
  254 |       expect(newCards).toBeLessThan(beforeCount);
  255 |       console.log('  [PASS] Delete project OK');
  256 |     });
  257 |   });
  258 | 
  259 |   // ============================================================
  260 |   // Module 3: Project Management & Chapter Operations
  261 |   // ============================================================
  262 |   test.describe('Module 3: Project Management & Chapter Operations', () => {
  263 | 
  264 |     test('TC-020: Open project and show chapters', async ({ page }) => {
  265 |       console.log('\n--- TC-020: Open project ---');
  266 | 
  267 |       await gotoPage(page);
  268 |       await page.waitForTimeout(2000);
  269 | 
  270 |       let cardCount = await page.locator('.project-card').count();
  271 |       if (cardCount === 0) {
  272 |         console.log('  Creating test project first...');
  273 |         const fs = require('fs');
  274 |         const path = require('path');
  275 |         const testFilePath = path.join(__dirname, 'test_novel_detail.txt');
  276 |         fs.writeFileSync(testFilePath, TEST_FILE_CONTENT, 'utf8');
  277 |         await page.click('[data-action="open-modal"][data-modal="new-project"]');
  278 |         await page.waitForTimeout(500);
  279 |         await page.locator('#file-input').setInputFiles(testFilePath);
  280 |         await page.waitForTimeout(8000);
  281 |         try { fs.unlinkSync(testFilePath); } catch {}
  282 |         cardCount = await page.locator('.project-card').count();
```