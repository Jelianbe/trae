# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: noveltts-full-test.spec.js >> NovelTTS Cloud Full Test >> Module 2: Project Creation >> TC-012: Delete project
- Location: tests\e2e\noveltts-full-test.spec.js:228:5

# Error details

```
Error: expect(received).toBeLessThan(expected)

Expected: < 4
Received:   4
```

# Test source

```ts
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
  182 |       await page.click('[data-action="open-modal"][data-modal="new-project"]');
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
> 254 |       expect(newCards).toBeLessThan(beforeCount);
      |                        ^ Error: expect(received).toBeLessThan(expected)
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
  283 |       }
  284 | 
  285 |       if (cardCount === 0) {
  286 |         console.log('  [FAIL] Cannot create project');
  287 |         return;
  288 |       }
  289 | 
  290 |       await page.locator('.project-card').first().click();
  291 |       await page.waitForTimeout(5000);
  292 | 
  293 |       await expect(page.locator('#page-detail')).toHaveClass(/active/);
  294 | 
  295 |       const chapterItems = page.locator('.chapter-item');
  296 |       const chapterCount = await chapterItems.count();
  297 |       console.log('  Chapter count:', chapterCount);
  298 |       expect(chapterCount).toBeGreaterThanOrEqual(1);
  299 | 
  300 |       await expect(page.locator('#content-body')).toBeVisible();
  301 |       await expect(page.locator('#content-title')).toBeVisible();
  302 |       await expect(page.locator('.content-toolbar')).toBeVisible();
  303 | 
  304 |       console.log('  [PASS] Project opened, chapters displayed');
  305 |     });
  306 | 
  307 |     test('TC-021: Chapter switching', async ({ page }) => {
  308 |       console.log('\n--- TC-021: Chapter switching ---');
  309 | 
  310 |       await gotoPage(page);
  311 |       await page.waitForTimeout(2000);
  312 | 
  313 |       const cardCount = await page.locator('.project-card').count();
  314 |       if (cardCount === 0) {
  315 |         console.log('  [SKIP] No projects');
  316 |         return;
  317 |       }
  318 | 
  319 |       await page.locator('.project-card').first().click();
  320 |       await page.waitForTimeout(5000);
  321 | 
  322 |       const chapterItems = page.locator('.chapter-item');
  323 |       const chapterCount = await chapterItems.count();
  324 | 
  325 |       if (chapterCount < 2) {
  326 |         console.log('  [SKIP] Not enough chapters');
  327 |         return;
  328 |       }
  329 | 
  330 |       await chapterItems.nth(1).click();
  331 |       await page.waitForTimeout(1000);
  332 | 
  333 |       const activeChapters = page.locator('.chapter-item.active');
  334 |       const activeCount = await activeChapters.count();
  335 |       expect(activeCount).toBe(1);
  336 | 
  337 |       console.log('  Total chapters:', chapterCount);
  338 |       console.log('  [PASS] Chapter switching OK');
  339 |     });
  340 | 
  341 |     test('TC-022: Chapter search filter', async ({ page }) => {
  342 |       console.log('\n--- TC-022: Chapter search ---');
  343 | 
  344 |       await gotoPage(page);
  345 |       await page.waitForTimeout(2000);
  346 | 
  347 |       const cardCount = await page.locator('.project-card').count();
  348 |       if (cardCount === 0) {
  349 |         console.log('  [SKIP] No projects');
  350 |         return;
  351 |       }
  352 | 
  353 |       await page.locator('.project-card').first().click();
  354 |       await page.waitForTimeout(5000);
```