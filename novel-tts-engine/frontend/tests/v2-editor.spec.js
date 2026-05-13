import { test, expect } from '@playwright/test';

const BASE_URL = 'http://localhost:3000/noveltts-v2.html';

const INITIAL_COUNT = 19;
const INITIAL_NARRATION = 8;
const INITIAL_DIALOGUE = 10;
const INITIAL_ONOMATOPOEIA = 1;

test.describe('NovelTTS V2 - 内容编辑器全面测试', () => {

  test.beforeEach(async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('.project-card').first().click();
    await page.waitForSelector('.segment-card');
  });

  test.describe('1. 编辑器核心渲染', () => {
    test('应该渲染所有 segment 卡片', async ({ page }) => {
      const cards = page.locator('.segment-card');
      await expect(cards).toHaveCount(INITIAL_COUNT);
    });

    test('每个卡片应该包含正确的类型图标', async ({ page }) => {
      const narrationCards = page.locator('.segment-card[data-type="narration"]');
      await expect(narrationCards).toHaveCount(INITIAL_NARRATION);

      const dialogueCards = page.locator('.segment-card[data-type="dialogue"]');
      await expect(dialogueCards).toHaveCount(INITIAL_DIALOGUE);

      const onomatopoeiaCards = page.locator('.segment-card[data-type="onomatopoeia"]');
      await expect(onomatopoeiaCards).toHaveCount(INITIAL_ONOMATOPOEIA);
    });

    test('对话卡片应该显示说话人信息', async ({ page }) => {
      const firstDialogue = page.locator('.segment-card[data-type="dialogue"]').first();
      await expect(firstDialogue.locator('.seg-speaker')).toBeVisible();
    });

    test('旁白卡片不应该显示说话人信息', async ({ page }) => {
      const firstNarration = page.locator('.segment-card[data-type="narration"]').first();
      await expect(firstNarration.locator('.seg-speaker')).not.toBeVisible();
    });

    test('点击卡片应该选中并展开编辑面板', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      const firstCard = page.locator('.segment-card').first();
      await expect(firstCard).toHaveClass(/selected/);
      const editPanel = firstCard.locator('.segment-edit-panel');
      await expect(editPanel).toHaveClass(/open/);
    });

    test('再次点击已选中卡片应该取消选中', async ({ page }) => {
      const firstCard = page.locator('.segment-card').first();
      await firstCard.click();
      await expect(firstCard).toHaveClass(/selected/);
      await firstCard.click();
      await expect(firstCard).not.toHaveClass(/selected/);
    });
  });

  test.describe('2. 编辑功能（contenteditable）', () => {
    test('应该可以进入编辑模式', async ({ page }) => {
      const toggle = page.locator('#edit-toggle');
      await toggle.click();
      await expect(toggle).toHaveClass(/active/);
    });

    test('编辑模式下 seg-text 应该可编辑', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      const segText = page.locator('.seg-text').first();
      await expect(segText).toHaveAttribute('contenteditable', 'true');
    });

    test('非编辑模式下 seg-text 不可编辑', async ({ page }) => {
      const segText = page.locator('.seg-text').first();
      await expect(segText).not.toHaveAttribute('contenteditable', 'true');
    });

    test('编辑模式下修改文字内容应该更新数据', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      const firstSegText = page.locator('.seg-text').first();
      await firstSegText.click();
      await firstSegText.fill('这是测试修改后的内容');
      await expect(firstSegText).toHaveText('这是测试修改后的内容');
    });

    test('编辑模式下多个 segment 应该独立编辑', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      await page.locator('.seg-text').nth(0).click();
      await page.locator('.seg-text').nth(0).fill('第一段修改内容');
      await expect(page.locator('.seg-text').nth(0)).toHaveText('第一段修改内容');
      await page.locator('.seg-text').nth(1).click();
      await page.locator('.seg-text').nth(1).fill('第二段修改内容');
      await expect(page.locator('.seg-text').nth(0)).toHaveText('第一段修改内容');
      await expect(page.locator('.seg-text').nth(1)).toHaveText('第二段修改内容');
    });
  });

  test.describe('3. 段落类型切换', () => {
    test('应该可以将旁白切换为对话', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.locator('.segment-card').first().locator('.type-capsule', { hasText: '对话' }).click();
      const firstCard = page.locator('.segment-card').first();
      await expect(firstCard).toHaveAttribute('data-type', 'dialogue');
    });

    test('应该可以将对话切换为旁白', async ({ page }) => {
      await page.locator('.segment-card[data-type="dialogue"]').first().click();
      await page.locator('.segment-card.selected .type-capsule', { hasText: '旁白' }).click();
      const card = page.locator('.segment-card.selected');
      await expect(card).toHaveAttribute('data-type', 'narration');
    });

    test('应该可以将旁白切换为拟声', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.locator('.segment-card').first().locator('.type-capsule', { hasText: '拟声' }).click();
      await expect(page.locator('.segment-card').first()).toHaveAttribute('data-type', 'onomatopoeia');
    });

    test('切换为对话类型应该自动分配说话人', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.locator('.segment-card').first().locator('.type-capsule', { hasText: '对话' }).click();
      await expect(page.locator('.segment-card').first().locator('.seg-speaker')).toBeVisible();
    });

    test('切换为非对话类型应该清空说话人信息', async ({ page }) => {
      const firstDialogue = page.locator('.segment-card[data-type="dialogue"]').first();
      await firstDialogue.click();
      await page.locator('.segment-card.selected .type-capsule', { hasText: '旁白' }).click();
      const switchedCard = page.locator('.segment-card.selected');
      await expect(switchedCard).toHaveAttribute('data-type', 'narration');
      await expect(switchedCard.locator('.seg-speaker')).not.toBeVisible();
    });
  });

  test.describe('4. 说话人选择', () => {
    test('对话类型应该显示说话人下拉框', async ({ page }) => {
      await page.locator('.segment-card[data-type="dialogue"]').first().click();
      await expect(page.locator('.segment-edit-panel.open select')).toBeVisible();
    });

    test('切换说话人应该更新显示', async ({ page }) => {
      const firstDialogue = page.locator('.segment-card[data-type="dialogue"]').first();
      await firstDialogue.click();
      const select = firstDialogue.locator('.segment-edit-panel.open select');
      await select.selectOption({ index: 2 });
      await expect(firstDialogue.locator('.seg-speaker .speaker-dot')).toBeVisible();
    });

    test('选择"未分配"应该清空说话人', async ({ page }) => {
      const firstDialogue = page.locator('.segment-card[data-type="dialogue"]').first();
      await firstDialogue.click();
      const select = firstDialogue.locator('.segment-edit-panel.open select');
      await select.selectOption({ index: 0 });
      await expect(firstDialogue.locator('.seg-speaker')).toContainText('未分配角色');
    });
  });

  test.describe('5. 参数绑定（滑块）', () => {
    test('编辑面板应该显示语速滑块', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await expect(page.locator('.segment-edit-panel.open input[type="range"]').first()).toBeVisible();
    });

    test('滑块应该显示初始数值', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      const sliderVals = page.locator('.segment-edit-panel.open .slider-val');
      await expect(sliderVals.first()).toHaveText('50');
    });

    test('拖动滑块应该实时更新显示数值', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      const speedSlider = page.locator('.segment-edit-panel.open input[type="range"]').first();
      await speedSlider.fill('80');
      await speedSlider.dispatchEvent('input');
      const speedVal = page.locator('.segment-edit-panel.open label:has-text("语速") .slider-val');
      await expect(speedVal).toHaveText('80');
    });

    test('切换 segment 后参数应该保留', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      const speedSlider = page.locator('.segment-edit-panel.open input[type="range"]').first();
      await speedSlider.fill('90');
      await speedSlider.dispatchEvent('input');
      await page.locator('.segment-card').nth(1).click();
      await page.locator('.segment-card').first().click();
      const speedVal = page.locator('.segment-edit-panel.open label:has-text("语速") .slider-val');
      await expect(speedVal).toHaveText('90');
    });

    test('不同 segment 应该有独立的参数值', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.locator('.segment-edit-panel.open input[type="range"]').first().fill('70');
      await page.locator('.segment-edit-panel.open input[type="range"]').first().dispatchEvent('input');
      await page.locator('.segment-card').nth(1).click();
      await page.locator('.segment-card').nth(1).locator('.segment-edit-panel.open input[type="range"]').first().fill('40');
      await page.locator('.segment-card').nth(1).locator('.segment-edit-panel.open input[type="range"]').first().dispatchEvent('input');
      await page.locator('.segment-card').first().click();
      await expect(page.locator('.segment-edit-panel.open label:has-text("语速") .slider-val')).toHaveText('70');
    });
  });

  test.describe('6. 插入功能', () => {
    test('工具栏插入按钮应该添加新段落到末尾', async ({ page }) => {
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('#btn-insert').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount + 1);
    });

    test('插入的段落应该是旁白类型', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const lastCard = page.locator('.segment-card').last();
      await expect(lastCard).toHaveAttribute('data-type', 'narration');
    });

    test('插入的段落文本应该为空', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const lastCard = page.locator('.segment-card').last();
      await expect(lastCard.locator('.seg-text')).toHaveText('');
    });

    test('hover 插入按钮应该可见', async ({ page }) => {
      const insertZone = page.locator('.seg-insert-zone').first();
      const insertBtn = insertZone.locator('.insert-btn');
      await expect(insertBtn).toBeVisible();
    });

    test('点击插入按钮应该在指定位置插入段落', async ({ page }) => {
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('.seg-insert-zone').nth(1).locator('.insert-btn').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount + 1);
    });

    test('插入后应该自动选中新段落', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const lastCard = page.locator('.segment-card').last();
      await expect(lastCard).toHaveClass(/selected/);
    });
  });

  test.describe('7. 拆分功能', () => {
    test('光标处拆分应该将段落分为两段', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      const firstSegText = page.locator('.seg-text').first();
      await firstSegText.click();
      // 将光标定位到文本中间位置
      await page.evaluate(() => {
        const sel = window.getSelection();
        const textEl = document.querySelector('.seg-text');
        const textNode = textEl.firstChild;
        if (textNode) {
          const mid = Math.floor(textNode.textContent.length / 2);
          const range = document.createRange();
          range.setStart(textNode, mid);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      });
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('#btn-split').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount + 1);
    });

    test('页面加载时已自动按引号拆分段落', async ({ page }) => {
      const count = await page.locator('.segment-card').count();
      expect(count).toBe(INITIAL_COUNT);
      const dialogueCards = page.locator('.segment-card[data-type="dialogue"]');
      const narrationCards = page.locator('.segment-card[data-type="narration"]');
      await expect(dialogueCards).toHaveCount(INITIAL_DIALOGUE);
      await expect(narrationCards).toHaveCount(INITIAL_NARRATION);
    });

    test('自动拆分按钮对已拆分内容不做重复拆分', async ({ page }) => {
      const countBefore = await page.locator('.segment-card').count();
      await page.locator('#btn-auto-split').click();
      const countAfter = await page.locator('.segment-card').count();
      expect(countAfter).toBe(countBefore);
    });

    test('自动拆分后保留拟声类型的段落', async ({ page }) => {
      const onomatopoeiaCards = page.locator('.segment-card[data-type="onomatopoeia"]');
      await expect(onomatopoeiaCards).toHaveCount(INITIAL_ONOMATOPOEIA);
    });
  });

  test.describe('8. 换行功能', () => {
    test('换行按钮应该在末尾添加空段落', async ({ page }) => {
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('#btn-newline').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount + 1);
    });

    test('换行添加的段落文本应该为空', async ({ page }) => {
      await page.locator('#btn-newline').click();
      const lastCard = page.locator('.segment-card').last();
      await expect(lastCard.locator('.seg-text')).toHaveText('');
    });
  });

  test.describe('9. 撤销/重做', () => {
    test('撤销按钮应该回退上一步操作', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const countAfterInsert = await page.locator('.segment-card').count();
      await page.locator('#btn-undo').click();
      const countAfterUndo = await page.locator('.segment-card').count();
      expect(countAfterUndo).toBe(countAfterInsert - 1);
    });

    test('重做按钮应该恢复撤销的操作', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const countAfterInsert = await page.locator('.segment-card').count();
      await page.locator('#btn-undo').click();
      await page.locator('#btn-redo').click();
      const countAfterRedo = await page.locator('.segment-card').count();
      expect(countAfterRedo).toBe(countAfterInsert);
    });

    test('多次撤销应该回退多步操作', async ({ page }) => {
      await page.locator('#btn-insert').click();
      await page.locator('#btn-insert').click();
      const countAfterInserts = await page.locator('.segment-card').count();
      await page.locator('#btn-undo').click();
      await page.locator('#btn-undo').click();
      const countAfterUndos = await page.locator('.segment-card').count();
      expect(countAfterUndos).toBe(countAfterInserts - 2);
    });

    test('类型切换后撤销应该恢复原类型', async ({ page }) => {
      const narrationIndex = await page.locator('.segment-card[data-type="narration"]').first().getAttribute('data-index');
      const aNarration = page.locator(`.segment-card[data-index="${narrationIndex}"]`);
      await aNarration.click();
      await aNarration.locator('.type-capsule', { hasText: '对话' }).click();
      await expect(aNarration).toHaveAttribute('data-type', 'dialogue');
      await page.locator('#btn-undo').click();
      await expect(aNarration).toHaveAttribute('data-type', 'narration');
    });
  });

  test.describe('10. 键盘快捷键', () => {
    test('Space 应该切换播放状态', async ({ page }) => {
      await page.keyboard.press('Space');
      const playBtn = page.locator('#play-btn');
      await expect(playBtn.locator('i')).toHaveClass(/fa-pause/);
      await page.keyboard.press('Space');
      await expect(playBtn.locator('i')).toHaveClass(/fa-play/);
    });

    test('ArrowDown 应该向下导航', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.keyboard.press('ArrowDown');
      const selectedCard = page.locator('.segment-card.selected');
      await expect(selectedCard).toHaveAttribute('data-index', '1');
    });

    test('ArrowUp 应该向上导航', async ({ page }) => {
      await page.locator('.segment-card').nth(3).click();
      await page.keyboard.press('ArrowUp');
      const selectedCard = page.locator('.segment-card.selected');
      await expect(selectedCard).toHaveAttribute('data-index', '2');
    });

    test('1 键应该切换为旁白类型', async ({ page }) => {
      await page.locator('.segment-card[data-type="dialogue"]').first().click();
      await page.keyboard.press('1');
      await expect(page.locator('.segment-card.selected')).toHaveAttribute('data-type', 'narration');
    });

    test('2 键应该切换为对话类型', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.keyboard.press('2');
      await expect(page.locator('.segment-card.selected')).toHaveAttribute('data-type', 'dialogue');
    });

    test('3 键应该切换为拟声类型', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await page.keyboard.press('3');
      await expect(page.locator('.segment-card.selected')).toHaveAttribute('data-type', 'onomatopoeia');
    });

    test('Escape 应该取消选中', async ({ page }) => {
      await page.locator('.segment-card').first().click();
      await expect(page.locator('.segment-card').first()).toHaveClass(/selected/);
      await page.keyboard.press('Escape');
      await expect(page.locator('.segment-card').first()).not.toHaveClass(/selected/);
    });

    test('Ctrl+Z 应该撤销', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const countAfterInsert = await page.locator('.segment-card').count();
      await page.keyboard.press('Control+z');
      const countAfterUndo = await page.locator('.segment-card').count();
      expect(countAfterUndo).toBe(countAfterInsert - 1);
    });

    test('Ctrl+Y 应该重做', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const countAfterInsert = await page.locator('.segment-card').count();
      await page.locator('#btn-undo').click();
      await page.keyboard.press('Control+y');
      const countAfterRedo = await page.locator('.segment-card').count();
      expect(countAfterRedo).toBe(countAfterInsert);
    });

    test('编辑模式下快捷键不应该触发导航', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      await page.locator('.seg-text').first().click();
      await page.keyboard.press('ArrowDown');
      const selectedCard = page.locator('.segment-card.selected');
      await expect(selectedCard).not.toBeVisible();
    });
  });

  test.describe('11. 拖拽排序', () => {
    test('应该可以拖拽卡片', async ({ page }) => {
      const firstCard = page.locator('.segment-card').first();
      await expect(firstCard.locator('.seg-drag-handle')).toBeVisible();
      await expect(firstCard.locator('.seg-drag-handle')).toHaveAttribute('draggable', 'true');
    });
  });

  test.describe('12. 批量选择', () => {
    test('批量模式切换应该显示复选框', async ({ page }) => {
      await page.locator('#btn-batch').click();
      const checkboxes = page.locator('.seg-checkbox.visible');
      await expect(checkboxes).toHaveCount(INITIAL_COUNT);
    });

    test('批量选择应该更新计数', async ({ page }) => {
      await page.locator('#btn-batch').click();
      await page.locator('.seg-checkbox').first().click();
      await expect(page.locator('#batch-count')).toHaveText('已选 1 项');
    });

    test('批量更改类型应该更新选中段落', async ({ page }) => {
      await page.locator('#btn-batch').click();
      await page.locator('.seg-checkbox').nth(0).click();
      await page.locator('.seg-checkbox').nth(1).click();
      await page.locator('#batch-actions .btn:has-text("旁白")').click();
      // 初始 8 个 narration + 被选的改为 narration
      const narrationCards = page.locator('.segment-card[data-type="narration"]');
      await expect(narrationCards).toHaveCount(INITIAL_NARRATION + 1);
    });

    test('批量删除应该删除选中段落', async ({ page }) => {
      await page.locator('#btn-batch').click();
      await page.locator('.seg-checkbox').first().click();
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('#batch-actions .btn:has-text("删除")').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount - 1);
    });
  });

  test.describe('13. 段落操作', () => {
    test('删除段落应该减少数量', async ({ page }) => {
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('.segment-card').first().hover();
      await page.locator('.segment-card').first().locator('.seg-action-btn:has(.fa-trash)').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount - 1);
    });

    test('复制段落应该增加数量', async ({ page }) => {
      const initialCount = await page.locator('.segment-card').count();
      await page.locator('.segment-card').first().hover();
      await page.locator('.segment-card').first().locator('.seg-action-btn:has(.fa-copy)').click();
      const newCount = await page.locator('.segment-card').count();
      expect(newCount).toBe(initialCount + 1);
    });

    test('试听应该显示 toast', async ({ page }) => {
      await page.locator('.segment-card').first().hover();
      await page.locator('.segment-card').first().locator('.seg-action-btn:has(.fa-headphones)').click();
      await expect(page.locator('.toast')).toBeVisible();
    });
  });

  test.describe('14. 章节树', () => {
    test('应该渲染章节树', async ({ page }) => {
      await expect(page.locator('.volume-header')).toHaveCount(2);
    });

    test('点击章节应该高亮', async ({ page }) => {
      await page.locator('.chapter-item').first().click();
      await expect(page.locator('.chapter-item').first()).toHaveClass(/active/);
    });

    test('搜索应该过滤章节', async ({ page }) => {
      await page.locator('.chapter-search').fill('天才');
      const visibleChapters = page.locator('.chapter-item:not([style*="display: none"])');
      await expect(visibleChapters).toHaveCount(1);
    });
  });

  test.describe('15. 右侧抽屉', () => {
    test('角色列表抽屉应该可以打开', async ({ page }) => {
      await page.locator('.toolbar-actions .btn-icon:has(.fa-address-book)').click();
      await expect(page.locator('#right-drawer')).toHaveClass(/open/);
      await expect(page.locator('#drawer-title')).toHaveText('角色列表');
    });

    test('统计抽屉应该可以打开', async ({ page }) => {
      await page.locator('.toolbar-actions .btn-icon:has(.fa-chart-pie)').click();
      await expect(page.locator('#right-drawer')).toHaveClass(/open/);
      await expect(page.locator('#drawer-title')).toHaveText('章节统计');
    });

    test('点击遮罩应该关闭抽屉', async ({ page }) => {
      await page.locator('.toolbar-actions .btn-icon:has(.fa-address-book)').click();
      await page.locator('#drawer-overlay').click();
      await expect(page.locator('#right-drawer')).not.toHaveClass(/open/);
    });
  });

  test.describe('16. 字号控制', () => {
    test('A+ 应该增大字号', async ({ page }) => {
      await page.locator('.btn-icon:has-text("A+")').click();
      const contentBody = page.locator('#content-body');
      const fontSize = await contentBody.evaluate(el => window.getComputedStyle(el).fontSize);
      expect(parseInt(fontSize)).toBeGreaterThan(14);
    });

    test('A- 应该减小字号', async ({ page }) => {
      await page.locator('.btn-icon:has-text("A+")').click();
      await page.locator('.btn-icon:has-text("A-")').click();
      const contentBody = page.locator('#content-body');
      const fontSize = await contentBody.evaluate(el => window.getComputedStyle(el).fontSize);
      expect(parseInt(fontSize)).toBe(14);
    });
  });

  test.describe('17. Toast 通知', () => {
    test('操作成功应该显示 toast', async ({ page }) => {
      await page.locator('#btn-insert').click();
      await expect(page.locator('.toast')).toBeVisible();
    });

    test('toast 应该自动消失', async ({ page }) => {
      await page.locator('#btn-insert').click();
      await expect(page.locator('.toast')).toBeVisible();
      await page.waitForTimeout(2500);
      await expect(page.locator('.toast')).not.toBeVisible();
    });
  });

  test.describe('18. 左侧面板折叠', () => {
    test('应该可以折叠左侧面板', async ({ page }) => {
      await page.locator('#tb-toggle-left').click();
      await expect(page.locator('#detail-left')).toHaveClass(/collapsed/);
    });

    test('应该可以展开左侧面板', async ({ page }) => {
      await page.locator('#tb-toggle-left').click();
      await page.locator('#tb-toggle-left').click();
      await expect(page.locator('#detail-left')).not.toHaveClass(/collapsed/);
    });
  });

  test.describe('19. 播放器', () => {
    test('播放按钮应该切换状态', async ({ page }) => {
      await page.locator('#play-btn').click();
      await expect(page.locator('#play-btn i')).toHaveClass(/fa-pause/);
      await page.locator('#play-btn').click();
      await expect(page.locator('#play-btn i')).toHaveClass(/fa-play/);
    });

    test('播放时进度条应该前进', async ({ page }) => {
      await page.locator('#play-btn').click();
      const initialWidth = await page.locator('#player-fill').evaluate(el => el.style.width);
      await page.waitForTimeout(1000);
      const finalWidth = await page.locator('#player-fill').evaluate(el => el.style.width);
      expect(parseFloat(finalWidth)).toBeGreaterThan(parseFloat(initialWidth));
    });
  });

  test.describe('20. 综合场景', () => {
    test('插入 + 编辑 + 撤销完整流程', async ({ page }) => {
      await page.locator('#btn-insert').click();
      const lastCard = page.locator('.segment-card').last();
      await expect(lastCard).toHaveClass(/selected/);
      await expect(lastCard).toHaveAttribute('data-type', 'narration');
      await page.locator('#edit-toggle').click();
      await lastCard.locator('.seg-text').fill('测试新段落');
      await expect(lastCard.locator('.seg-text')).toHaveText('测试新段落');
      await page.locator('#btn-undo').click();
      const countAfterUndo = await page.locator('.segment-card').count();
      expect(countAfterUndo).toBe(INITIAL_COUNT);
    });

    test('拆分 + 类型切换 + 重做完整流程', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      await page.locator('.seg-text').first().click();
      await page.evaluate(() => {
        const sel = window.getSelection();
        const textEl = document.querySelector('.seg-text');
        const textNode = textEl.firstChild;
        if (textNode) {
          const mid = Math.floor(textNode.textContent.length / 2);
          const range = document.createRange();
          range.setStart(textNode, mid);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      });
      await page.locator('#btn-split').click();
      const countAfterSplit = await page.locator('.segment-card').count();
      expect(countAfterSplit).toBe(INITIAL_COUNT + 1);
      await page.locator('#btn-undo').click();
      await expect(page.locator('.segment-card')).toHaveCount(INITIAL_COUNT);
      await page.locator('#btn-redo').click();
      await expect(page.locator('.segment-card')).toHaveCount(INITIAL_COUNT + 1);
    });

    test('自动拆分后参数修改 + 撤销', async ({ page }) => {
      const dialogueCards = page.locator('.segment-card[data-type="dialogue"]');
      const dialogueCount = await dialogueCards.count();
      expect(dialogueCount).toBe(INITIAL_DIALOGUE);
      await dialogueCards.first().click();
      await page.locator('.segment-edit-panel.open input[type="range"]').first().fill('80');
      await page.locator('.segment-edit-panel.open input[type="range"]').first().dispatchEvent('input');
      await expect(page.locator('.segment-edit-panel.open label:has-text("语速") .slider-val')).toHaveText('80');
      await page.locator('#btn-undo').click();
      const countAfterUndo = await page.locator('.segment-card').count();
      expect(countAfterUndo).toBe(INITIAL_COUNT);
    });

    test('自动拆分 + 手动拆分 + 撤销完整流程', async ({ page }) => {
      await page.locator('#edit-toggle').click();
      await page.locator('.seg-text').first().click();
      await page.evaluate(() => {
        const sel = window.getSelection();
        const textEl = document.querySelector('.seg-text');
        const textNode = textEl.firstChild;
        if (textNode) {
          const mid = Math.floor(textNode.textContent.length / 2);
          const range = document.createRange();
          range.setStart(textNode, mid);
          range.collapse(true);
          sel.removeAllRanges();
          sel.addRange(range);
        }
      });
      await page.locator('#btn-split').click();
      const countAfterSplit = await page.locator('.segment-card').count();
      expect(countAfterSplit).toBe(INITIAL_COUNT + 1);
      await page.locator('#btn-undo').click();
      await expect(page.locator('.segment-card')).toHaveCount(INITIAL_COUNT);
    });
  });
});
