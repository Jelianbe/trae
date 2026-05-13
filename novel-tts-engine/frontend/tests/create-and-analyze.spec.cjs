const { test, expect } = require('@playwright/test');

const BASE_URL = 'http://localhost:8000';
const MODAL = '#modal-new-project';

// 测试用的小说内容
const TEST_NOVEL_CONTENT = `第一卷 初入学院

第一章 入学测试

晨光洒在学院的青石路上，林轩背着行囊，独自站在测试大厅的门口。

"终于到了。"他抬头望着门匾上"星辰学院"四个大字，深吸了一口气。

大厅内已经站满了人，都是来自各地的年轻学子。一个身穿青色长袍的中年男子站在高台上，目光扫过台下众人，朗声说道："欢迎各位来到星辰学院。我是你们的主考官，纳兰导师。今天的入学测试只有一项——通过幻境试炼。"

台下顿时一片哗然。

林轩身旁的年轻人低声问道："你紧张吗？"

"有一点。"林轩老实回答。

年轻人笑了笑："我叫小翠，以后我们可能是同学了。"

"我叫林轩。"两人握了握手。

纳兰导师拍了拍手，示意众人安静。"幻境试炼会将你们传送到一个模拟战场，你们需要在里面坚持一炷香的时间。记住，这不是生死搏杀，而是测试你们在压力下的反应能力。准备好了吗？"

"准备好了！"众人齐声回答。

一道白光闪过，林轩感到脚下一空，整个人仿佛坠入了无底深渊。

第二章 幻境试炼

当林轩再次睁开眼时，发现自己站在一片荒芜的战场上。远处有喊杀声传来，空气中弥漫着硝烟的味道。

"这就是幻境吗……也太真实了。"他喃喃自语。

一名全副武装的士兵跌跌撞撞地跑过来。"别发愣！敌人的骑兵正在逼近，快做好迎战准备！"

林轩来不及多想，拔出腰间佩剑。地面开始震动，远处出现了一排黑甲骑兵的身影。

"所有人列阵！"一个威严的声音响起。林轩回头一看，是一名须发皆白的老将，正挥动着令旗。

"你是新兵？"老兵瞥了他一眼。

"是……是的，长官！"

"跟紧我。活命的第一个规则：不要慌张。"老兵拍了拍他的肩膀。

黑甲骑兵的冲锋开始了。

第三章 突破

刀光剑影中，林轩几乎是本能地挥剑格挡。起初的慌乱逐渐被一种从未体验过的专注取代。

"好样的！"老兵在战斗间隙冲他点了点头。

林轩刚要回答，一柄长枪从侧面刺来。他侧身躲避，反手一剑击中了对手的手臂。黑甲骑兵痛呼一声，从马背上摔落。

一炷香的时间终于到了。周围的一切开始变得模糊，战场、士兵、硝烟都如同被水洗过的墨迹般慢慢散开。

"结束了。"林轩松了一口气，这才发现自己浑身都被汗水浸透了。

再次站在测试大厅里时，纳兰导师正微笑着看着他。

"林轩，你通过了。"

"我……通过了？"

"你的表现不错。"纳兰导师翻开手中的记录簿，"你在幻境中展现了合格的战斗直觉和压力应对能力。欢迎来到星辰学院。"

小翠从人群中挤过来，兴奋地拍着他的后背。"我就知道你能行！"

"谢谢。"林轩终于露出了笑容。

第四章 新的开始

办理完入学手续后，林轩跟着一个高年级学长来到了宿舍区。

"你的房间在二楼。食堂在楼下，训练场在学院东侧。"学长边走边介绍。

"有什么需要注意的吗？"林轩试探着问道，"比如……纳兰导师说的星辰塔？"

学长摇了摇头。"星辰塔可不是你现在该想的事。先在这里站稳脚跟，再考虑挑战塔。"

林轩默默点头。虽然没有得到回答，但他心里已经有了一个模糊的念头。

那天夜里，他独自躺在陌生的床上，望着天花板上投射的星光，久久没有入睡。

接下来的三个月，他要面对的是一个完全陌生的世界。一个比幻境更加真实的、属于修炼者的世界。

而他的故事，才刚刚开始。`;

test.describe('小说项目创建与分析验证', () => {

  test('创建小说项目并自动分章', async ({ page }) => {
    await page.goto(BASE_URL);
    
    // 导航到项目管理页面
    await page.locator('[data-page="projects"]').click();
    
    // 点击新建项目按钮
    await page.getByRole('button', { name: '新建项目' }).first().click();
    await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
    
    // 填写表单
    await page.fill('#new-project-title', '星辰学院');
    await page.fill('#new-project-author', '测试作者');
    await page.fill('#new-project-content', TEST_NOVEL_CONTENT);
    
    // 提交
    await page.locator('[data-action="create-project"]').click();
    
    // 等待模态框关闭
    await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
    
    // 等待进入详情页
    await page.waitForTimeout(3000);
    const detailPage = page.locator('#page-detail');
    expect(await detailPage.isVisible()).toBeTruthy();
    
    // 验证书名显示
    const bookTitle = await page.locator('#detail-book-title').textContent();
    expect(bookTitle).toContain('星辰学院');
    
    // 验证章节列表（应该有4章）
    const chapters = page.locator('.chapter-item:not(.add-chapter-btn)');
    const chapterCount = await chapters.count();
    expect(chapterCount).toBeGreaterThanOrEqual(4);
  });

  test('第一章自动分析并显示拆分结果', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('[data-page="projects"]').click();
    await page.getByRole('button', { name: '新建项目' }).first().click();
    await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
    await page.fill('#new-project-title', '自动分析测试');
    await page.fill('#new-project-author', '测试');
    await page.fill('#new-project-content', TEST_NOVEL_CONTENT);
    await page.locator('[data-action="create-project"]').click();
    await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
    
    // 动态等待分析完成（第一章自动分析）
    // 等待 segment-card 出现，超时 30 秒（分析API可能需要较长时间）
    const cards = page.locator('.segment-card');
    await cards.first().waitFor({ state: 'visible', timeout: 30000 }).catch(() => {
      console.log('等待 segment-card 超时，当前页面状态...');
    });
    
    const cardCount = await cards.count();
    console.log('segment-card 数量:', cardCount);
    
    // 分析完成后应该有多个卡片
    expect(cardCount).toBeGreaterThan(0);
    
    // 验证颜色条显示（不同类型有不同颜色）
    const colorBars = page.locator('.segment-color-bar, .seg-color-stack');
    expect(await colorBars.count()).toBeGreaterThan(0);
  });

  test('章节切换与内容缓存', async ({ page }) => {
    await page.goto(BASE_URL);
    await page.locator('[data-page="projects"]').click();
    await page.getByRole('button', { name: '新建项目' }).first().click();
    await page.waitForSelector(MODAL, { state: 'visible', timeout: 5000 });
    await page.fill('#new-project-title', '章节切换测试');
    await page.fill('#new-project-author', '测试');
    await page.fill('#new-project-content', TEST_NOVEL_CONTENT);
    await page.locator('[data-action="create-project"]').click();
    await page.waitForSelector(MODAL, { state: 'hidden', timeout: 15000 });
    await page.waitForTimeout(5000);
    
    // 点击第二章
    const chapter2 = page.locator('.chapter-item').nth(1);
    await chapter2.click();
    await page.waitForTimeout(2000);
    
    // 验证章节标题更新
    const title = await page.locator('#content-title').textContent();
    expect(title).toContain('第二章');
    
    // 返回第一章
    const chapter1 = page.locator('.chapter-item').first();
    await chapter1.click();
    await page.waitForTimeout(2000);
    
    const title2 = await page.locator('#content-title').textContent();
    expect(title2).toContain('第一章');
  });
});
