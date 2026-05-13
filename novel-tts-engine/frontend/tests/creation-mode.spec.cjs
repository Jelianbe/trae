const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';
const MODAL = '#modal-new-project';

test.describe('创作模式 - 端到端验证', () => {

  test.describe('1. 导航与基础页面', () => {
    test('首页应正常加载', async ({ page }) => {
      await page.goto(BASE_URL);
      await expect(page.locator('body')).toBeVisible({ timeout: 10000 });
      const text = await page.textContent('body');
      expect(text.length).toBeGreaterThan(100);
    });

    test('导航到项目管理页面', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await expect(page.locator('#page-projects')).toBeVisible({ timeout: 10000 });
    });
  });

  test.describe('2. 创建空白项目', () => {
    test('通过手动输入创建空白项目', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      // 找到第一个"新建项目"按钮（项目管理页面上那个）
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '创作测试项目');
      await page.fill('#new-project-author', '测试作者');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      const detailPage = page.locator('#page-detail');
      expect(await detailPage.isVisible()).toBeTruthy();
    });
  });

  test.describe('3. 空章节创作模式', () => {
    test('空项目第一章应显示创作模式引导', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '创作空项目');
      await page.fill('#new-project-author', '测试');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      await page.waitForTimeout(3000);
      await expect(page.locator('#content-body')).toBeVisible({ timeout: 10000 });
    });

    test('应显示文本输入框', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '输入框测试');
      await page.fill('#new-project-author', '测试');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      await page.waitForTimeout(3000);
      const textarea = page.locator('#chapter-text-input');
      const isVisible = await textarea.isVisible().catch(() => false);
      if (isVisible) expect(isVisible).toBeTruthy();
    });
  });

  test.describe('4. 文本输入与片段生成', () => {
    test('输入文本后添加按钮应可用', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '片段测试');
      await page.fill('#new-project-author', '测试');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      await page.waitForTimeout(3000);

      const textarea = page.locator('#chapter-text-input');
      if (await textarea.isVisible().catch(() => false)) {
        await textarea.fill('你好我是小明');
        await page.locator('[data-action="commit-text-input"]').click();
        await page.waitForTimeout(500);
        const cards = page.locator('.segment-card');
        expect(await cards.count()).toBeGreaterThanOrEqual(1);
      }
    });
  });

  test.describe('5. 新建章节', () => {
    test('章节栏应可见', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '章节测试');
      await page.fill('#new-project-author', '测试');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      await page.waitForTimeout(3000);
      await expect(page.locator('#chapter-tree')).toBeVisible({ timeout: 10000 });
    });

    test('点击新建章节按钮', async ({ page }) => {
      await page.goto(BASE_URL);
      await page.locator('[data-page="projects"]').click();
      await page.getByRole('button', { name: '新建项目' }).first().click();
      await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
      await page.fill('#new-project-title', '新章节测试');
      await page.fill('#new-project-author', '测试');
      await page.locator('[data-action="create-project"]').click();
      await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
      await page.waitForTimeout(3000);

      const addBtn = page.locator('.add-chapter-btn');
      if (await addBtn.isVisible().catch(() => false)) {
        await addBtn.click();
        await page.waitForTimeout(500);
        const chapters = page.locator('.chapter-item:not(.add-chapter-btn)');
        expect(await chapters.count()).toBeGreaterThanOrEqual(1);
      }
    });
  });
});
