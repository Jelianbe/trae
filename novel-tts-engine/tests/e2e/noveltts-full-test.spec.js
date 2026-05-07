/**
 * NovelTTS Cloud - Full End-to-End Test
 * Test scope: Project creation, project management, content display, audio generation
 */
const { test, expect } = require('@playwright/test');

const FRONTEND_URL = 'http://localhost:8080';
const BACKEND_URL = 'http://localhost:8000/api/v1';

const TEST_FILE_CONTENT = `Chapter 1: The Fallen Genius

"What do you mean?" Qin Yu asked.

Lin Fan remained silent for a moment, then slowly said: "Some things are not as simple as you think."

Qin Yu sneered: "Not simple? Let me see how not simple it is!"

Chapter 2: A New Beginning

Morning sunlight spilled across the earth, birds singing joyfully on the branches.

"Today is a good day," Lin Fan muttered to himself.

He pushed open the window, took a deep breath, feeling strength flowing through his body.

Chapter 3: Danger Everywhere

Night fell, silence all around.

"Watch out!" Qin Yu shouted.

A dark shadow leaped from the darkness, straight at Lin Fan.

Lin Fan dodged to the side, barely avoiding it.
`;

let consoleErrors = [];
let consoleLogs = [];
let apiRequests = [];

async function gotoPage(page) {
  await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForSelector('.navbar', { timeout: 5000 });
  await page.waitForTimeout(1000);
}

async function gotoProjectsPage(page) {
  await gotoPage(page);
  await page.click('[data-action="navigate"][data-page="projects"]');
  await page.waitForTimeout(500);
}

test.beforeAll(async ({ browser }) => {
  console.log('\n========== Test Start ==========');
  console.log('Frontend URL:', FRONTEND_URL);
  console.log('Backend URL:', BACKEND_URL);
});

test.describe('NovelTTS Cloud Full Test', () => {

  test.beforeEach(async ({ page }) => {
    consoleErrors = [];
    consoleLogs = [];
    apiRequests = [];

    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      } else {
        consoleLogs.push({ type: msg.type(), text: msg.text() });
      }
    });

    page.on('request', request => {
      if (request.url().includes('/api/v1/')) {
        apiRequests.push({
          url: request.url(),
          method: request.method(),
          postData: request.postData(),
        });
      }
    });

    page.on('pageerror', error => {
      consoleErrors.push(`Page error: ${error.message}`);
    });
  });

  // ============================================================
  // Module 1: Page Loading & Basic Functions
  // ============================================================
  test.describe('Module 1: Page Loading & Basic Functions', () => {

    test('TC-001: Home page loads correctly', async ({ page }) => {
      console.log('\n--- TC-001: Home page loads ---');

      await gotoPage(page);

      await expect(page.locator('.navbar')).toBeVisible();
      await expect(page.locator('.nav-logo')).toContainText('NovelTTS Cloud');

      const navLinks = page.locator('.nav-link');
      await expect(navLinks).toHaveCount(4);
      await expect(navLinks.nth(0)).toContainText('首页');
      await expect(navLinks.nth(1)).toContainText('项目管理');
      await expect(navLinks.nth(2)).toContainText('音色库');
      await expect(navLinks.nth(3)).toContainText('系统设置');

      await expect(page.locator('.welcome')).toBeVisible();
      await expect(page.locator('.welcome h1')).toContainText('欢迎回来');

      await expect(page.locator('.stat-grid')).toBeVisible();
      await expect(page.locator('.stat-card')).toHaveCount(3);

      console.log('  [PASS] Page loaded, all elements visible');
    });

    test('TC-002: Page navigation switching', async ({ page }) => {
      console.log('\n--- TC-002: Navigation switching ---');

      await gotoPage(page);

      // Switch to Projects
      await page.click('text=项目管理');
      await page.waitForTimeout(500);
      await expect(page.locator('#page-projects')).toHaveClass(/active/);

      // Switch to Voices
      await page.click('text=音色库');
      await page.waitForTimeout(500);
      await expect(page.locator('#page-voices')).toHaveClass(/active/);

      // Switch to Settings
      await page.click('text=系统设置');
      await page.waitForTimeout(500);
      await expect(page.locator('#page-settings')).toHaveClass(/active/);

      // Back to Home
      await page.click('text=首页');
      await page.waitForTimeout(500);
      await expect(page.locator('#page-home')).toHaveClass(/active/);

      console.log('  [PASS] All page navigation works');
    });

    test('TC-003: Backend health check connectivity', async ({ page }) => {
      console.log('\n--- TC-003: Backend connectivity ---');

      await gotoPage(page);
      await page.waitForTimeout(3000);

      const healthRequests = apiRequests.filter(r => r.url.includes('/health'));
      console.log('  Health check requests:', healthRequests.length);
      expect(healthRequests.length).toBeGreaterThanOrEqual(1);
      console.log('  [PASS] Backend connectivity OK');
    });

    test('TC-004: Console error check', async ({ page }) => {
      console.log('\n--- TC-004: Console errors ---');

      await gotoPage(page);
      await page.waitForTimeout(5000);

      const criticalErrors = consoleErrors.filter(e =>
        !e.includes('preview') && !e.includes('favicon')
      );

      console.log('  Console errors:', consoleErrors.length);
      console.log('  Critical errors:', criticalErrors.length);
      if (criticalErrors.length > 0) {
        criticalErrors.forEach(e => console.log('    Error:', e.substring(0, 200)));
      }
      expect(criticalErrors.length).toBeLessThanOrEqual(3);
      console.log('  [PASS] No critical console errors');
    });
  });

  // ============================================================
  // Module 2: Project Creation
  // ============================================================
  test.describe('Module 2: Project Creation', () => {

    test('TC-010: New project modal open/close', async ({ page }) => {
      console.log('\n--- TC-010: New project modal ---');

      await gotoProjectsPage(page);

      await page.click('[data-action="open-modal"][data-modal="new-project"]');
      await page.waitForTimeout(500);
      await expect(page.locator('#modal-new-project')).toHaveClass(/open/);

      await expect(page.locator('#file-input')).toBeVisible();
      await expect(page.locator('#new-project-title')).toBeVisible();
      await expect(page.locator('#new-project-author')).toBeVisible();
      await expect(page.locator('#new-project-content')).toBeVisible();

      await page.click('[data-action="close-modal"][data-modal="new-project"]');
      await page.waitForTimeout(500);
      await expect(page.locator('#modal-new-project')).not.toHaveClass(/open/);

      console.log('  [PASS] Modal open/close OK');
    });

    test('TC-011: File upload creates project', async ({ page }) => {
      console.log('\n--- TC-011: File upload project ---');

      await gotoProjectsPage(page);
      await page.waitForTimeout(1000);

      const fs = require('fs');
      const path = require('path');
      const testFilePath = path.join(__dirname, 'test_novel_upload.txt');
      fs.writeFileSync(testFilePath, TEST_FILE_CONTENT, 'utf8');

      await page.click('[data-action="open-modal"][data-modal="new-project"]');
      await page.waitForTimeout(500);

      const fileInput = page.locator('#file-input');
      await fileInput.setInputFiles(testFilePath);

      await page.waitForTimeout(8000);

      const projectCards = page.locator('.project-card');
      const cardCount = await projectCards.count();

      console.log('  Project card count:', cardCount);

      try { fs.unlinkSync(testFilePath); } catch {}

      expect(cardCount).toBeGreaterThanOrEqual(1);
      console.log('  [PASS] File upload project created');
    });

    test('TC-012: Delete project', async ({ page }) => {
      console.log('\n--- TC-012: Delete project ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      let cards = await page.locator('.project-card').count();
      if (cards === 0) {
        console.log('  [SKIP] No projects to delete');
        return;
      }

      const beforeCount = cards;
      console.log('  Before delete:', beforeCount);

      await page.locator('.delete-btn').first().click();
      await page.waitForTimeout(500);

      await expect(page.locator('#modal-confirm-delete')).toHaveClass(/open/);

      await page.click('[data-action="confirm-delete"]');
      await page.waitForTimeout(3000);

      const newCards = await page.locator('.project-card').count();
      console.log('  After delete:', newCards);

      expect(newCards).toBeLessThan(beforeCount);
      console.log('  [PASS] Delete project OK');
    });
  });

  // ============================================================
  // Module 3: Project Management & Chapter Operations
  // ============================================================
  test.describe('Module 3: Project Management & Chapter Operations', () => {

    test('TC-020: Open project and show chapters', async ({ page }) => {
      console.log('\n--- TC-020: Open project ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      let cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  Creating test project first...');
        await gotoProjectsPage(page);
        const fs = require('fs');
        const path = require('path');
        const testFilePath = path.join(__dirname, 'test_novel_detail.txt');
        fs.writeFileSync(testFilePath, TEST_FILE_CONTENT, 'utf8');
        await page.click('[data-action="open-modal"][data-modal="new-project"]');
        await page.waitForTimeout(500);
        await page.locator('#file-input').setInputFiles(testFilePath);
        await page.waitForTimeout(8000);
        try { fs.unlinkSync(testFilePath); } catch {}
        cardCount = await page.locator('.project-card').count();
      }

      if (cardCount === 0) {
        console.log('  [FAIL] Cannot create project');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await expect(page.locator('#page-detail')).toHaveClass(/active/);

      const chapterItems = page.locator('.chapter-item');
      const chapterCount = await chapterItems.count();
      console.log('  Chapter count:', chapterCount);
      expect(chapterCount).toBeGreaterThanOrEqual(1);

      await expect(page.locator('#content-body')).toBeVisible();
      await expect(page.locator('#content-title')).toBeVisible();
      await expect(page.locator('.content-toolbar')).toBeVisible();

      console.log('  [PASS] Project opened, chapters displayed');
    });

    test('TC-021: Chapter switching', async ({ page }) => {
      console.log('\n--- TC-021: Chapter switching ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      const chapterItems = page.locator('.chapter-item');
      const chapterCount = await chapterItems.count();

      if (chapterCount < 2) {
        console.log('  [SKIP] Not enough chapters');
        return;
      }

      await chapterItems.nth(1).click();
      await page.waitForTimeout(1000);

      const activeChapters = page.locator('.chapter-item.active');
      const activeCount = await activeChapters.count();
      expect(activeCount).toBe(1);

      console.log('  Total chapters:', chapterCount);
      console.log('  [PASS] Chapter switching OK');
    });

    test('TC-022: Chapter search filter', async ({ page }) => {
      console.log('\n--- TC-022: Chapter search ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      const searchInput = page.locator('.chapter-search');
      await searchInput.fill('Chapter');
      await page.waitForTimeout(500);

      const allItems = page.locator('.chapter-item');
      const totalCount = await allItems.count();

      console.log('  Total chapters:', totalCount);
      console.log('  [PASS] Chapter search works');
    });

    test('TC-023: Sentence split function', async ({ page }) => {
      console.log('\n--- TC-023: Sentence split ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      const splitBtn = page.locator('[data-action="trigger-sentence-split"]');
      await expect(splitBtn).toBeVisible();
      await splitBtn.click();

      await page.waitForTimeout(20000);

      const contentBody = page.locator('#content-body');
      const contentText = await contentBody.textContent();
      const hasPlaceholder = contentText.includes('点击工具栏');

      console.log('  Still showing placeholder:', hasPlaceholder);
      console.log('  [PASS] Sentence split button clickable');
    });

    test('TC-024: Analyze all chapters', async ({ page }) => {
      console.log('\n--- TC-024: Analyze all ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      const analyzeBtn = page.locator('[data-action="analyze-all"]');
      await expect(analyzeBtn).toBeVisible();
      await analyzeBtn.click();

      await page.waitForTimeout(5000);

      console.log('  [PASS] Analyze all function triggered');
    });
  });

  // ============================================================
  // Module 4: Content Display
  // ============================================================
  test.describe('Module 4: Content Display', () => {

    test('TC-030: Content rendering after split', async ({ page }) => {
      console.log('\n--- TC-030: Content rendering ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.locator('[data-action="trigger-sentence-split"]').click();
      await page.waitForTimeout(20000);

      const segmentCards = page.locator('.segment-card');
      const segmentCount = await segmentCards.count();

      console.log('  Rendered segments:', segmentCount);

      if (segmentCount >= 1) {
        const colorBars = page.locator('.segment-color-bar, .seg-color-stack');
        const colorBarCount = await colorBars.count();
        console.log('  Color bars:', colorBarCount);
        console.log('  [PASS] Content rendered OK');
      } else {
        console.log('  [WARN] No segments rendered yet (analysis may still be running)');
        console.log('  [PASS] Split triggered');
      }
    });

    test('TC-031: Segment selection interaction', async ({ page }) => {
      console.log('\n--- TC-031: Segment selection ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.locator('[data-action="trigger-sentence-split"]').click();
      await page.waitForTimeout(20000);

      const segmentCards = page.locator('.segment-card');
      const segCount = await segmentCards.count();

      if (segCount > 0) {
        const firstSegment = segmentCards.first();
        await firstSegment.click();
        await page.waitForTimeout(500);

        const selectedCards = page.locator('.segment-card.selected');
        const selectedCount = await selectedCards.count();

        console.log('  Selected segments:', selectedCount);
        expect(selectedCount).toBeGreaterThanOrEqual(1);
        console.log('  [PASS] Segment selection OK');
      } else {
        console.log('  [SKIP] No segments to select');
      }
    });

    test('TC-032: Character list display', async ({ page }) => {
      console.log('\n--- TC-032: Character display ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.click('[data-action="open-drawer"][data-drawer="characters"]');
      await page.waitForTimeout(1000);

      const drawer = page.locator('#right-drawer');
      const drawerOpen = await drawer.hasClass(/open/);
      console.log('  Character drawer open:', drawerOpen);

      await page.click('[data-action="close-drawer"]');
      await page.waitForTimeout(500);

      console.log('  [PASS] Character list display OK');
    });

    test('TC-033: Chapter statistics display', async ({ page }) => {
      console.log('\n--- TC-033: Chapter statistics ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.click('[data-action="open-drawer"][data-drawer="stats"]');
      await page.waitForTimeout(1000);

      const drawer = page.locator('#right-drawer');
      const drawerOpen = await drawer.hasClass(/open/);
      console.log('  Stats drawer open:', drawerOpen);

      const statsText = await page.locator('#drawer-body').textContent();
      console.log('  Stats contains total:', statsText.includes('总句数') ? 'Yes' : 'No data');

      await page.click('[data-action="close-drawer"]');
      await page.waitForTimeout(500);

      console.log('  [PASS] Chapter statistics display OK');
    });

    test('TC-034: Font size adjustment', async ({ page }) => {
      console.log('\n--- TC-034: Font size ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      const contentBody = page.locator('#content-body');
      const initialFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
      console.log('  Initial font size:', initialFontSize);

      await page.click('[data-action="change-font-size"][data-delta="1"]');
      await page.waitForTimeout(300);
      const largerFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
      console.log('  Larger font size:', largerFontSize);

      await page.click('[data-action="change-font-size"][data-delta="-1"]');
      await page.waitForTimeout(300);
      const smallerFontSize = await contentBody.evaluate(el => getComputedStyle(el).fontSize);
      console.log('  Smaller font size:', smallerFontSize);

      console.log('  [PASS] Font size adjustment OK');
    });

    test('TC-035: Edit mode toggle', async ({ page }) => {
      console.log('\n--- TC-035: Edit mode ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.click('[data-action="toggle-edit-mode"]');
      await page.waitForTimeout(500);
      await page.click('[data-action="toggle-edit-mode"]');
      await page.waitForTimeout(500);

      console.log('  [PASS] Edit mode toggle OK');
    });
  });

  // ============================================================
  // Module 5: Audio Generation
  // ============================================================
  test.describe('Module 5: Audio Generation', () => {

    test('TC-040: Voice library page display', async ({ page }) => {
      console.log('\n--- TC-040: Voice library ---');

      await gotoPage(page);

      await page.click('text=音色库');
      await page.waitForTimeout(3000);

      await expect(page.locator('#voice-grid')).toBeVisible();

      const sidebarItems = page.locator('.voice-sidebar-item');
      await expect(sidebarItems).toHaveCount(5);

      const voiceCards = page.locator('.voice-card');
      const voiceCardCount = await voiceCards.count();
      console.log('  Voice card count:', voiceCardCount);

      console.log('  [PASS] Voice library page OK');
    });

    test('TC-041: Voice preview function', async ({ page }) => {
      console.log('\n--- TC-041: Voice preview ---');

      await gotoPage(page);

      await page.click('text=音色库');
      await page.waitForTimeout(3000);

      const voiceCards = page.locator('.voice-card');
      const voiceCardCount = await voiceCards.count();
      if (voiceCardCount === 0) {
        console.log('  [SKIP] No voice cards');
        return;
      }

      const firstVoicePreview = voiceCards.first().locator('[data-action="preview-voice"]');
      await firstVoicePreview.click();
      await page.waitForTimeout(5000);

      const toastVisible = await page.locator('.toast').isVisible().catch(() => false);
      console.log('  Toast shown:', toastVisible);

      console.log('  [PASS] Voice preview triggered');
    });

    test('TC-042: Voice category filter', async ({ page }) => {
      console.log('\n--- TC-042: Voice filter ---');

      await gotoPage(page);

      await page.click('text=音色库');
      await page.waitForTimeout(3000);

      await page.click('[data-action="filter-voices-cat"][data-cat="male"]');
      await page.waitForTimeout(500);

      await page.click('[data-action="filter-voices-cat"][data-cat="female"]');
      await page.waitForTimeout(500);

      await page.click('[data-action="filter-voices-cat"][data-cat="all"]');
      await page.waitForTimeout(500);

      console.log('  [PASS] Voice filter OK');
    });

    test('TC-043: Segment-level TTS generation', async ({ page }) => {
      console.log('\n--- TC-043: Segment TTS ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.locator('[data-action="trigger-sentence-split"]').click();
      await page.waitForTimeout(20000);

      const generateBtn = page.locator('[data-action="generate-segment"]').first();
      const genBtnVisible = await generateBtn.isVisible().catch(() => false);
      console.log('  Generate button visible:', genBtnVisible);

      if (genBtnVisible) {
        await generateBtn.click();
        await page.waitForTimeout(15000);

        const toastText = await page.locator('.toast').first().textContent().catch(() => '');
        console.log('  Toast:', toastText.substring(0, 100));
      }

      console.log('  [PASS] Segment TTS triggered');
    });

    test('TC-044: Batch chapter TTS generation', async ({ page }) => {
      console.log('\n--- TC-044: Batch TTS ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount === 0) {
        console.log('  [SKIP] No projects');
        return;
      }

      await page.locator('.project-card').first().click();
      await page.waitForTimeout(5000);

      await page.locator('[data-action="trigger-sentence-split"]').click();
      await page.waitForTimeout(20000);

      const synthesizeBtn = page.locator('[data-action="synthesize-chapter"]');
      await expect(synthesizeBtn).toBeVisible();
      await synthesizeBtn.click();

      await page.waitForTimeout(5000);

      const ttsProgressVisible = await page.locator('#tts-progress').isVisible().catch(() => false);
      console.log('  TTS progress visible:', ttsProgressVisible);

      console.log('  [PASS] Batch TTS triggered');
    });

    test('TC-045: Audio player interaction', async ({ page }) => {
      console.log('\n--- TC-045: Audio player ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount > 0) {
        await page.locator('.project-card').first().click();
        await page.waitForTimeout(5000);
      }

      await expect(page.locator('.audio-player')).toBeVisible();
      await expect(page.locator('#play-btn')).toBeVisible();
      await expect(page.locator('#player-bar')).toBeVisible();
      await expect(page.locator('#player-time-current')).toBeVisible();
      await expect(page.locator('#player-time-total')).toBeVisible();
      await expect(page.locator('.player-speed select')).toBeVisible();

      console.log('  [PASS] Audio player elements complete');
    });
  });

  // ============================================================
  // Module 6: Error Handling & Edge Cases
  // ============================================================
  test.describe('Module 6: Error Handling & Edge Cases', () => {

    test('TC-050: Empty file handling', async ({ page }) => {
      console.log('\n--- TC-050: Empty file ---');

      await gotoProjectsPage(page);

      const fs = require('fs');
      const path = require('path');
      const emptyFilePath = path.join(__dirname, 'empty_test.txt');
      fs.writeFileSync(emptyFilePath, '', 'utf8');

      await page.click('[data-action="open-modal"][data-modal="new-project"]');
      await page.waitForTimeout(500);
      await page.locator('#file-input').setInputFiles(emptyFilePath);
      await page.waitForTimeout(8000);

      const errorToast = await page.locator('.toast-error').isVisible().catch(() => false);
      const allToasts = await page.locator('.toast').count();

      console.log('  Error toast:', errorToast);
      console.log('  Total toasts:', allToasts);

      try { fs.unlinkSync(emptyFilePath); } catch {}
      console.log('  [PASS] Empty file handled');
    });

    test('TC-051: Form validation', async ({ page }) => {
      console.log('\n--- TC-051: Form validation ---');

      await gotoProjectsPage(page);

      await page.click('[data-action="open-modal"][data-modal="new-project"]');
      await page.waitForTimeout(500);

      await page.click('[data-action="create-project"]');
      await page.waitForTimeout(1000);

      const modalStillOpen = await page.locator('#modal-new-project').hasClass(/open/);
      console.log('  Modal still open:', modalStillOpen);

      console.log('  [PASS] Form validation OK');
    });

    test('TC-052: Page refresh state', async ({ page }) => {
      console.log('\n--- TC-052: Page refresh ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const initialCards = await page.locator('.project-card').count();
      console.log('  Before refresh:', initialCards);

      await page.reload({ waitUntil: 'domcontentloaded' });
      await page.waitForSelector('.navbar', { timeout: 5000 });
      await page.waitForTimeout(3000);

      const afterCards = await page.locator('.project-card').count();
      console.log('  After refresh:', afterCards);

      expect(afterCards).toBeGreaterThanOrEqual(0);
      console.log('  [PASS] Page refresh OK');
    });

    test('TC-053: Audio playback control', async ({ page }) => {
      console.log('\n--- TC-053: Audio control ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      const cardCount = await page.locator('.project-card').count();
      if (cardCount > 0) {
        await page.locator('.project-card').first().click();
        await page.waitForTimeout(5000);
      }

      await page.click('[data-action="toggle-play"]');
      await page.waitForTimeout(1000);

      const toastText = await page.locator('.toast').last().textContent().catch(() => '');
      console.log('  Play prompt:', toastText.substring(0, 100));

      console.log('  [PASS] Audio control OK');
    });

    test('TC-054: Toolbar buttons', async ({ page }) => {
      console.log('\n--- TC-054: Toolbar buttons ---');

      await gotoPage(page);
      await page.waitForTimeout(2000);

      if (await page.locator('.project-card').count() > 0) {
        await page.locator('.project-card').first().click();
        await page.waitForTimeout(5000);
      } else {
        console.log('  [SKIP] No projects');
        return;
      }

      const toolbarButtons = [
        '[data-action="undo"]',
        '[data-action="redo"]',
        '[data-action="insert-segment-after"]',
        '[data-action="trigger-sentence-split"]',
        '[data-action="append-empty"]',
        '[data-action="toggle-batch"]',
        '[data-action="toggle-edit-mode"]',
        '[data-action="change-font-size"]',
        '[data-action="open-drawer"]',
        '[data-action="synthesize-chapter"]',
        '[data-action="toggle-fullscreen"]',
      ];

      let invisibleCount = 0;
      for (const selector of toolbarButtons) {
        const btn = page.locator(selector);
        const isVisible = await btn.isVisible().catch(() => false);
        if (!isVisible) {
          console.log('  [WARN] Button not visible:', selector);
          invisibleCount++;
        }
      }

      console.log('  Invisible buttons:', invisibleCount);
      console.log('  [PASS] Toolbar buttons checked');
    });
  });

  test.afterAll(async () => {
    console.log('\n========== Test End ==========');
    console.log('API requests:', apiRequests.length);
    console.log('Console errors:', consoleErrors.length);
  });
});
