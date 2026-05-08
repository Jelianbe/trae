# UI 与功能逻辑问题验证报告

**日期**: 2026-05-08  
**来源**: 用户反馈 + 代码审查  
**状态**: 全部8项经代码审查确认存在  

---

## 问题1：章节进入后未自动显示拆分内容

### 验证结果：✅ 确认存在

**关键代码**: [app.js:314-328](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L314-L328)

`selectChapter()` 的流程：

```
selectChapter(index)
  ↓
有分析缓存？ → 是 → 渲染拆分结果
  ↓ 否
渲染原始文本（无拆分）
  ↓
等待用户点击"句子拆分"按钮
```

**问题**: 进入章节时，即使已有分析缓存（如第一章），如果 `splitChapters[index]` 标记不为 `true`，仍然会渲染原始文本而不是拆分后的内容。用户需要每次都手动点击"句子拆分"才能看到切分后的段落。

---

## 问题2：章节切换时未显示该章原文内容

### 验证结果：✅ 确认存在

**关键代码**: [app.js:291-330](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L291-L330)

`selectChapter()` 切换章节时会：
1. 清空 `segments: []`
2. 如果有缓存 → 渲染拆分结果
3. 没有缓存 → 渲染纯文本

但 `splitChapters` 标记是累加的——切换回已拆分的章节时，如果标记为 `true` 但缓存不存在，会显示"暂无章节内容"。

**根本原因**: 章节切换时没有独立维护每章的拆分状态和内容显示状态。

---

## 问题3：旁白位置与图标重叠

### 验证结果：✅ 确认存在

**关键代码**: [views.js:119-129](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L119-L129)

`segment-meta` 在 [views.js:124-128](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L124-L128) 中使用但在 **CSS 中没有定义任何样式**。`segment-color-bar`（左侧色条）通过 `position:absolute` 定位，而 `segment-meta` 使用默认文档流布局，两者无明确边界划分，导致在屏幕较窄时重叠。

**具体**: 左侧4px色条（`segment-color-bar`）与右侧 `segment-meta` 中的类型图标、说话人标签之间的间距未明确定义，在窄屏或内容较多时发生挤压叠加。

---

## 问题4：生成/试听功能层级位置错误

### 验证结果：✅ 确认存在

**关键代码**: [views.js:115-117](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L115-L117)

当前布局：

```
segment-card
  ├── segment-color-bar（左侧色条）
  ├── segment-header（文本内容）
  └── segment-meta
        ├── seg-type-badge ← 类型标签（旁白/对话）
        ├── seg-speaker    ← 说话人
        └── audio-card-btn ← "生成" / "试听" 按钮（在此！）
```

**问题**: 生成和试听按钮直接显示在段落卡片底部，没有按原设计放在"编辑功能"模块下。原设计是：

```
编辑功能模块
  ├── 情绪选择
  ├── 语速控制
  ├── 生成音频 ← 应该在这里
  └── 试听音频 ← 应该在这里
```

当前的"生成音频"按钮在工具栏中作为独立按钮（[index.html:138](file:///d:/trae/novel-tts-engine/frontend/index.html#L138)），"试听"按钮在段落卡片底部（[views.js:116](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L116)），两者都不在原设计位置。

---

## 问题5：开始分析功能无参数配置

### 验证结果：✅ 确认存在

**关键代码**: [app.js:572-622](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L572-L622)

`_analyzeAll()` 的逻辑：

```javascript
const pending = flat.filter(ch => ch.status !== 'done');
// 直接分析所有未完成的章节，没有任何选择参数
```

**问题**: 
- 没有"从第几章开始分析"的参数
- 没有"分析哪几章"的选择功能
- 没有分析范围的弹窗或配置界面
- 用户点击"开始分析"后直接跑全部未分析章节

---

## 问题6：底部播放器功能逻辑错误

### 验证结果：✅ 确认存在

**关键代码**: [app.js:512-524](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L512-L524), [app.js:665-713](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L665-L713)

**问题分析**:

| 问题 | 代码位置 | 说明 |
|------|---------|------|
| **单句播放器** | [app.js:514-523](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L514-L523) | `_togglePlay()` 只控制一个 `_previewAudio`，无章节拼接逻辑 |
| **生成即播放** | `_synthesizeChapter()` + TTS 生成后直接缓存 audio_url | 生成按钮和播放器之间直接关联，没有分离 |
| **任务重叠** | [app.js:512](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L512) | 唯一 `_previewAudio` 实例，多次生成后覆盖，导致多音频同时播放 |
| **无章节拼接** | 缺少 `concat()` 或排队播放逻辑 | 播放器不能连续播放整个章节的所有片段 |

原设计：播放器应该是**章节内容整体播放器**，将章节所有片段拼接后连续播放。当前实现是**每个片段的独立播放器**。

---

## 问题7：句子片段拆分系统缺失

### 验证结果：✅ 确认存在

**关键代码**: [views.js:85-132](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L85-L132)

当前 `renderSegments()` 只渲染**粗粒度的段落卡片**：

```html
<div class="segment-card">
  <div class="segment-header">文本内容</div>
  <div class="segment-meta">旁白 | 生成按钮</div>
</div>
```

**缺失**: 原设计的**细粒度片段拆分系统**：

```
句子-1：[整个句子的可选中方框]
  对话-1：[对话片段的可选中方框]  
  旁白-1：[旁白片段的可选中方框]
  句子-2：[...
```

每个片段应该是**独立可选中、可操作**的方框，带有自己的类型标签。当前的实现只做了段落级别的拆分，没有做片段级别的拆分和选择系统。

---

## 问题8：分析功能未实际应用

### 验证结果：✅ 确认存在

**关键代码**: [app.js:332-354](file:///d:/trae/novel-tts-engine/frontend/js/app.js#L332-L354)

`_applyAnalysis()` 确实处理了分析结果：

```javascript
segments.push({
  text: sent.text,
  type: sent.sentence_type || 'narration',  // 这里接收了 analysis 结果
  speaker: sent.speaker || '',
  emotion: sent.emotion || 'neutral',
});
```

但 `renderSegments()` 中**只使用了 `type` 和 `speaker`**，没有使用 `emotion`, `emotion_class`, `emotion_vector` 等分析结果。

**关键证据**: [views.js:85-132](file:///d:/trae/novel-tts-engine/frontend/js/views.js#L85-L132)

```javascript
const typeColors = { narration:'var(--type-narration)', dialogue:'var(--type-dialogue)' };
const typeLabels = { narration:'旁白', dialogue:'对话' };
const typeIcons = { narration:'fa-book-open', dialogue:'fa-comment' };
// 只用了 type，没用到 emotion 等分析字段
```

**结论**: 分析数据被保存了（`analysisCache`），但渲染层面只使用了 `type`（对话/旁白）这一项。情感分析、角色分配、情绪向量等结果在UI中完全不可见，导致分析功能显得"没有用"。

---

## 问题汇总表

| # | 问题 | 严重度 | 涉及文件 | 是否确认 |
|---|------|--------|---------|---------|
| 1 | 进入章节不自动拆分 | P1 | `app.js` | ✅ |
| 2 | 切换章节原文显示异常 | P1 | `app.js` | ✅ |
| 3 | 旁白位置与图标重叠 | P2 | `views.js`, `style.css` | ✅ |
| 4 | 生成/试听层级位置错误 | P2 | `views.js`, `index.html` | ✅ |
| 5 | 分析无参数配置 | P1 | `app.js`, `index.html` | ✅ |
| 6 | 播放器逻辑错误 | P1 | `app.js` | ✅ |
| 7 | 片段拆分系统缺失 | P1 | `views.js` | ✅ |
| 8 | 分析结果未在UI呈现 | P1 | `views.js`, `app.js` | ✅ |

**严重度定义**:
- **P1**: 核心功能缺失或错误，影响正常使用流程
- **P2**: 功能位置或UI布局不符合设计要求

---

## 代码引用索引

| 文件 | 关键函数/区域 | 行号 |
|------|-------------|------|
| [app.js](file:///d:/trae/novel-tts-engine/frontend/js/app.js) | `selectChapter()` | 291-330 |
| [app.js](file:///d:/trae/novel-tts-engine/frontend/js/app.js) | `_applyAnalysis()` | 332-354 |
| [app.js](file:///d:/trae/novel-tts-engine/frontend/js/app.js) | `_analyzeAll()` | 572-622 |
| [app.js](file:///d:/trae/novel-tts-engine/frontend/js/app.js) | `_synthesizeChapter()` | 665-713 |
| [app.js](file:///d:/trae/novel-tts-engine/frontend/js/app.js) | `_togglePlay()` | 512-524 |
| [views.js](file:///d:/trae/novel-tts-engine/frontend/js/views.js) | `renderSegments()` | 85-132 |
| [views.js](file:///d:/trae/novel-tts-engine/frontend/js/views.js) | `renderChapterTree()` | 49-83 |
| [index.html](file:///d:/trae/novel-tts-engine/frontend/index.html) | 工具栏 & 播放器 | 101-165 |
| [style.css](file:///d:/trae/novel-tts-engine/frontend/css/style.css) | Segment card & color bar | 180-270 |
