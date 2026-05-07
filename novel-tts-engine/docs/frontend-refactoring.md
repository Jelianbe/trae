# 前端重构文档

## 一、现状与问题

### 1.1 核心问题：前后端关系倒置

当前前端 `noveltts-v2.html` 的问题不是代码质量，而是**架构方向错误**——前端在"假设"后端应该提供什么，然后后端被拖着适配前端期望。这违反了"后端是基础、前端是表面"的原则。

具体表现：
- 前端定义了 `ChapterAnalysisResponse` 的消费方式，后端被迫调整 `force=True` 等参数来匹配前端行为
- 前端在 `selectChapter` 中混合了"选择章节"和"触发分析"两个职责
- 前端逻辑层（API 调用、状态管理）与视图层（DOM 渲染）交织在同一个 2200+ 行 HTML 文件中

### 1.2 派生问题

| 问题 | 表现 |
|------|------|
| 状态扩散 | 章节分析状态 `status='done'` 由前端自行标记，与后端实际状态脱节 |
| 职责混杂 | `openDetail()` 同时做数据加载、项目列表切换、章节树渲染 |
| 无加载态 | API 请求期间 UI 无反馈，用户无法区分"正在加载"和"卡死" |
| 无错误恢复 | 网络错误、后端未就绪等情况无兜底 UI |
| 不可测试 | 所有逻辑耦合在 DOM 事件中，无法单独测试数据流 |

---

## 二、后端 API 契约（不可变）

> 前端必须基于以下 API 设计，**不能要求后端为新功能增加端点**。

| 方法 | 路径 | 请求 | 响应 |
|------|------|------|------|
| `GET` | `/api/v1/health` | — | `{status, pipeline_ready, tts_engine}` |
| `POST` | `/api/v1/projects/upload` | `multipart/form-data` (file) | `{project_id, book_title, chapters[]}` |
| `GET` | `/api/v1/projects/{id}` | — | `{project_id, book_title, total_chapters, total_words}` |
| `GET` | `/api/v1/projects/{id}/chapters` | — | `[{index, title, word_count}]` |
| `GET` | `/api/v1/projects/{id}/chapters/{idx}` | — | `{chapter_index, sentences[], statistics}` |
| `GET` | `/api/v1/projects/{id}/characters` | — | `{total, characters[]}` |
| `POST` | `/api/v1/tts/generate` | `{text, speaker, emotion}` | `{audio_url}` |
| `GET` | `/api/v1/audio/{filename}` | — | `audio/*` |

### 关键数据模型

```typescript
// 句子（后端决定结构，前端照单消费）
interface Sentence {
  text: string;
  speaker: string;        // "" 表示未识别到说话人
  sentence_type: "dialogue" | "narration";
  emotion: string;        // "neutral" | "joy" | "sadness" | ...
  emotion_class: string;  // "neutral" | "excited" | "subdued"
  quotation_type: "none" | "dialogue" | "written" | "thought";
  sentence_id: number;
  sfx_words: string[];
}
```

### 重要规则

1. **`speaker` 为空字符串是合法状态**——后端可能无法识别说话人，前端必须优雅展示
2. **`force=True` 是后端内部决策**——前端不关心缓存策略
3. **后端不分页**——单章分析结果一次返回，前端仅做渲染

---

## 三、前端架构

### 3.1 分层隔离

```
┌─────────────────────────────────────────┐
│  视图层 (DOM 渲染)                       │
│  - renderProjectList()                  │
│  - renderChapterTree()                  │
│  - renderSentenceList()                 │
├─────────────────────────────────────────┤
│  数据层 (API 客户端)                     │
│  - api.get('/projects')                 │
│  - api.post('/projects/upload', form)   │
│  - api.get('/projects/{id}/chapters')   │
├─────────────────────────────────────────┤
│  状态层                                  │
│  - 当前项目 ID                           │
│  - 当前章节索引                          │
│  - 分析结果缓存 {chapterIdx → Response}  │
│  - UI 状态 (loading / error / ready)     │
└─────────────────────────────────────────┘
```

各层之间通过**纯函数**通信，不直接操作 DOM 以外的全局变量。

### 3.2 数据流

```
用户操作 → 更新状态层 → 调用数据层 → 收到响应 → 更新状态层 → 触发视图层
```

**不允许的路径**：
- ❌ 视图层直接调用 `fetch()`
- ❌ 数据层修改 DOM
- ❌ 状态层存储 DOM 引用

### 3.3 状态设计

```typescript
interface AppState {
  // 项目
  projects: ProjectSummary[];
  currentProjectId: string | null;
  
  // 章节
  chapters: ChapterMeta[];
  currentChapterIndex: number | null;
  
  // 分析结果（按章节索引缓存）
  analysisCache: Map<number, ChapterAnalysisResponse>;
  
  // UI 状态
  loading: boolean;
  error: string | null;
  page: 'home' | 'detail';
}
```

---

## 四、重构计划

### 4.1 阶段一：抽取 API 客户端层（不影响现有 UI）

创建一个纯 JavaScript 模块，封装所有后端调用：

```javascript
// api.js — 纯数据层，不引用任何 DOM
class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async getProject(id) { ... }
  async uploadProject(file) { ... }
  async getChapters(id) { ... }
  async analyzeChapter(id, index) { ... }
  async getCharacters(id) { ... }
  async generateTTS(params) { ... }
  async health() { ... }
}
```

**验收标准**：
- 所有 8 个后端端点都有对应的封装方法
- 统一错误处理（网络错误 → 抛出 `ApiError`，业务错误 → 抛出 `ApiError`）
- 纯函数，不引用 `window`、`document` 或任何 DOM 元素

### 4.2 阶段二：抽取状态管理层

```javascript
// store.js — 纯状态管理，不引用任何 DOM
class AppStore {
  constructor() {
    this.state = { ... };
    this.listeners = new Set();
  }
  
  getState() { return this.state; }
  dispatch(action) { /* 更新状态 → 通知所有 listener */ }
  subscribe(fn) { this.listeners.add(fn); }
}
```

**验收标准**：
- 所有状态变更通过 `dispatch(action)` 进行
- `subscribe(listener)` 在状态变化时通知视图层
- 支持撤销/回退（可选，不做硬性要求）

### 4.3 阶段三：重写视图层

视图层按功能拆分为独立渲染函数，每个函数接收纯数据，返回 DOM 字符串或操作 DOM：

```javascript
// views.js — 纯视图层
function renderProjectCard(project) { /* 返回 HTML 字符串 */ }
function renderChapterTree(chapters, currentIndex) { /* ... */ }
function renderSentenceList(sentences, speakers) { /* ... */ }
function renderCharacterList(characters) { /* ... */ }
```

**验收标准**：
- 每个函数输入是纯数据，输出是 HTML（字符串或 DOM 节点）
- 不包含任何 `fetch()`、`apiFetch()` 等网络调用
- 不包含任何状态管理逻辑

### 4.4 阶段四：组装

主文件（`app.js` 或 `index.html` 中的 `<script>`）三行即完成装配：

```javascript
const api = new ApiClient('http://localhost:8000/api/v1');
const store = new AppStore();
store.subscribe(() => renderAll(store.getState()));
```

---

## 五、UI 行为规范

### 5.1 加载态

- API 请求期间，相关区域显示骨架屏或加载指示器
- 全局 loading 状态由 store 管理，不依赖单个请求的超时

### 5.2 错误态

- 后端返回错误 → 局部错误提示（不影响其他区域）
- 网络断开 → 全局 banner "后端服务未连接"
- 所有错误用户可关闭/重试

### 5.3 空态

- 无项目 → "导入一本小说开始"
- 无角色 → "分析章节后将自动识别角色"
- 无对话 → "当前章节尚未检测到对话"（接受后端返回的事实）

### 5.4 章节分析行为

```
用户点击章节 → 前端查缓存
  ├─ 有缓存 → 直接渲染
  └─ 无缓存 → 调用 GET /projects/{id}/chapters/{idx}
       ├─ 成功 → 存入缓存 → 渲染
       └─ 失败 → 显示错误（不阻断其他章节）
```

**关键约束**：
- 前端不维护 `status='done'` 这样的分析状态——后端每次返回完整数据
- 不自动预分析下一章——用户点击什么就请求什么

---

## 六、SRP 检查清单

每个函数/模块在重构后必须满足：

| 原则 | 检查项 |
|------|--------|
| 单一职责 | 一个函数只做一件事（渲染 / 请求 / 状态更新） |
| 无副作用 | 渲染函数不修改全局变量，不发起网络请求 |
| 纯数据输入 | 视图函数只接受 `JSON 对象` 参数 |
| 可测试 | API 客户端可 mock，状态管理可单测，视图函数可 snapshot |

---

## 七、非目标（本轮不做）

- 不引入 React/Vue 等框架——保持原生 JS，但用模块化模式
- 不修改后端 API——前端适配后端，而不是相反
- 不做 PWA / 离线缓存——仅在线使用
- 不做 TTS 播放器重构——保持现有音频播放逻辑

---

## 八、实施顺序

```
步骤 1: 创建 api.js（API 客户端层）
步骤 2: 创建 store.js（状态管理层）
步骤 3: 创建 views.js（视图渲染层）
步骤 4: 重写 index.html，引用三个模块
步骤 5: 删除旧代码，验证所有功能
```
