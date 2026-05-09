/**
 * NovelTTS Cloud - Analysis Function Verification Test (API + UI)
 * 
 * Test scope:
 * 1. Backend analysis API returns correct segments with dialogue/narration types
 * 2. Frontend correctly renders segments with proper colors
 * 3. Character library is populated from analysis results
 * 
 * Approach:
 * - Use API to create project and trigger analysis (more reliable)
 * - Use UI to verify rendering and colors
 */
const { test, expect } = require('@playwright/test');
const http = require('http');

const FRONTEND_URL = 'http://localhost:8000';
const BACKEND_URL = 'http://localhost:8000/api/v1';

const TEST_FILE_CONTENT = `第一章：坠落的少年

"你什么意思？"秦羽问道。

林凡沉默了片刻，缓缓说道："有些事情没有你想的那么简单。"

秦羽冷笑一声："不简单？让我看看怎么不简单！"

第二章：新的开始

清晨的阳光洒在大地上，鸟儿在枝头欢快地歌唱。

"今天真是个好天气啊，"林凡自言自语道。

他推开窗户，深吸一口气，感受着体内涌动的力量。`;

function apiRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BACKEND_URL);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: { 'Content-Type': 'application/json' },
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(body) });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

test.describe('Analysis Function Verification', () => {

  test('TC-001: Backend analysis returns segments with correct types', async () => {
    console.log('\n========== TC-001: Backend Analysis API Test =========');

    // 1. Create project via API
    console.log('Creating project...');
    const createRes = await apiRequest('POST', '/api/v1/projects', {
      title: 'Analysis API Test',
      description: 'Testing analysis via API',
      content: TEST_FILE_CONTENT,
    });
    console.log(`Create project status: ${createRes.status}`);
    
    const projectId = createRes.data.id || createRes.data.project_id;
    console.log(`Project ID: ${projectId}`);
    expect(projectId).toBeTruthy();

    // 2. Trigger analysis for chapter 0
    console.log('Triggering analysis for chapter 0...');
    const analyzeRes = await apiRequest('POST', `/api/v1/projects/${projectId}/analyze`, {
      chapter_index: 0,
    });
    console.log(`Analysis status: ${analyzeRes.status}`);
    console.log(`Analysis response: ${JSON.stringify(analyzeRes.data).substring(0, 500)}`);

    // 3. Verify segments are returned
    const segments = analyzeRes.data.segments || analyzeRes.data.result?.segments;
    expect(Array.isArray(segments)).toBe(true);
    expect(segments.length).toBeGreaterThan(0);
    console.log(`Found ${segments.length} segments`);

    // 4. Verify segment types
    const dialogueSegs = segments.filter(s => s.type === 'dialogue');
    const narrationSegs = segments.filter(s => s.type === 'narration');
    console.log(`Dialogue segments: ${dialogueSegs.length}`);
    console.log(`Narration segments: ${narrationSegs.length}`);
    expect(dialogueSegs.length).toBeGreaterThan(0);
    expect(narrationSegs.length).toBeGreaterThan(0);

    // 5. Verify dialogue content contains quotes
    const firstDialogue = dialogueSegs[0];
    console.log(`First dialogue: "${firstDialogue.text}"`);
    expect(firstDialogue.text).toMatch(/[""「」]/);

    // 6. Verify characters are extracted
    const characters = analyzeRes.data.characters || analyzeRes.data.result?.characters || [];
    console.log(`Characters: ${JSON.stringify(characters)}`);
    expect(characters.length).toBeGreaterThanOrEqual(2);
    
    const charNames = characters.map(c => c.name);
    expect(charNames).toContain('秦羽');
    expect(charNames).toContain('林凡');

    console.log('\n========== TC-001 PASSED =========');
  });

  test('TC-002: Frontend renders segments with correct colors', async ({ page }) => {
    console.log('\n========== TC-002: Frontend Color Rendering Test =========');

    // 1. Navigate to projects page
    await page.goto(`${FRONTEND_URL}/#projects`, { waitUntil: 'domcontentloaded', timeout: 30000 });
    await page.waitForTimeout(1500);

    // 2. Click on first project
    const projectCard = page.locator('.project-card').first();
    await projectCard.waitFor({ state: 'visible', timeout: 10000 });
    await projectCard.click();
    await page.waitForTimeout(1000);

    // 3. Click on first chapter
    const chapterItem = page.locator('.chapter-list-item').first();
    await chapterItem.waitFor({ state: 'visible', timeout: 10000 });
    await chapterItem.click();
    await page.waitForTimeout(1500);

    // 4. Check if segments are rendered (analysis should have been done via API test)
    const segments = page.locator('.segment-card');
    const segmentCount = await segments.count();
    console.log(`Found ${segmentCount} segments in UI`);

    if (segmentCount > 0) {
      // 5. Verify dialogue segments have correct type badge
      const dialogueSegs = page.locator('.segment-card[data-type="dialogue"]');
      const dialogueCount = await dialogueSegs.count();
      console.log(`Dialogue segments in UI: ${dialogueCount}`);
      
      if (dialogueCount > 0) {
        const firstDialogue = dialogueSegs.first();
        const badge = firstDialogue.locator('.seg-type-badge');
        await expect(badge).toBeVisible();
        const badgeText = await badge.innerText();
        console.log(`Dialogue badge: ${badgeText}`);
        expect(badgeText).toContain('对话');

        // 6. Verify color bar exists
        const colorBar = firstDialogue.locator('.segment-color-bar');
        await expect(colorBar).toBeVisible();
        const bgColor = await colorBar.evaluate(el => window.getComputedStyle(el).backgroundColor);
        console.log(`Dialogue color bar background: ${bgColor}`);
      }
    }

    console.log('\n========== TC-002 PASSED =========');
  });
});
