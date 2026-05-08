import { test, expect, Page, Locator } from '@playwright/test';

const FRONTEND_URL = 'http://localhost:8000';
const TEST_FILE_PATH = 'C:\\Users\\月笙如歌\\Downloads\\P5R.txt';

async function gotoPage(page: Page): Promise<void> {
  await page.goto(FRONTEND_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await page.waitForSelector('.navbar', { timeout: 5000 });
  await page.waitForTimeout(1000);
}

async function navigateToProjects(page: Page): Promise<void> {
  await gotoPage(page);
  await page.click('text=项目管理');
  await page.waitForTimeout(500);
}

test.describe('上传功能专项测试', () => {

  test('TC-U001: 使用P5R.txt文件上传创建项目', async ({ page }) => {
    console.log('\n--- TC-U001: P5R.txt 文件上传 ---');
    
    await navigateToProjects(page);

    await page.click('[data-action="open-modal"][data-modal="new-project"]');
    await page.waitForTimeout(500);
    await expect(page.locator('#modal-new-project')).toHaveClass(/open/);

    const fileInput: Locator = page.locator('#file-input');
    await expect(fileInput).toBeVisible();
    
    await fileInput.setInputFiles(TEST_FILE_PATH);
    console.log('  文件已选择');
    
    await page.waitForTimeout(15000);

    const projectCards: Locator = page.locator('.project-card');
    const cardCount: number = await projectCards.count();
    console.log('  项目卡片数量:', cardCount);

    expect(cardCount).toBeGreaterThan(0);
    console.log('  [PASS] 文件上传成功');
  });

  test('TC-U002: 手动输入创建项目', async ({ page }) => {
    console.log('\n--- TC-U002: 手动输入创建项目 ---');
    
    await navigateToProjects(page);

    await page.click('[data-action="open-modal"][data-modal="new-project"]');
    await page.waitForTimeout(500);

    await page.locator('#new-project-title').fill('手动创建测试小说');
    await page.locator('#new-project-content').fill(`第一章 初入江湖

清晨的阳光透过窗户洒进房间，李逍遥缓缓睁开了眼睛。

"今天是个好日子。"他喃喃自语道。

第二章 奇遇

就在他准备出门的时候，突然听到门外传来一阵奇怪的声音。`);

    await page.click('[data-action="create-project"]');
    await page.waitForTimeout(8000);

    const projectCards: Locator = page.locator('.project-card');
    const cardCount: number = await projectCards.count();
    console.log('  项目卡片数量:', cardCount);

    expect(cardCount).toBeGreaterThan(0);
    console.log('  [PASS] 手动创建项目成功');
  });

  test('TC-U003: 打开项目查看章节', async ({ page }) => {
    console.log('\n--- TC-U003: 打开项目查看章节 ---');
    
    await gotoPage(page);
    await page.waitForTimeout(2000);

    const cardCount: number = await page.locator('.project-card').count();
    if (cardCount === 0) {
      console.log('  [SKIP] 没有项目可测试');
      return;
    }

    await page.locator('.project-card').first().click();
    await page.waitForTimeout(5000);

    await expect(page.locator('#page-detail')).toHaveClass(/active/);

    const chapterItems: Locator = page.locator('.chapter-item');
    const chapterCount: number = await chapterItems.count();
    console.log('  章节数量:', chapterCount);

    expect(chapterCount).toBeGreaterThanOrEqual(1);
    console.log('  [PASS] 项目打开成功，章节显示正常');
  });

  test('TC-U004: 句子分割功能', async ({ page }) => {
    console.log('\n--- TC-U004: 句子分割功能 ---');
    
    await gotoPage(page);
    await page.waitForTimeout(2000);

    const cardCount: number = await page.locator('.project-card').count();
    if (cardCount === 0) {
      console.log('  [SKIP] 没有项目可测试');
      return;
    }

    await page.locator('.project-card').first().click();
    await page.waitForTimeout(5000);

    const splitBtn: Locator = page.locator('[data-action="trigger-sentence-split"]');
    await expect(splitBtn).toBeVisible();
    await splitBtn.click();

    await page.waitForTimeout(30000);

    const segmentCards: Locator = page.locator('.segment-card');
    const segmentCount: number = await segmentCards.count();
    console.log('  分割后的片段数量:', segmentCount);

    expect(segmentCount).toBeGreaterThanOrEqual(1);
    console.log('  [PASS] 句子分割功能正常');
  });
});
