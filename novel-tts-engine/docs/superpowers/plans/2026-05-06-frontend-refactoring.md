# 前端重构实施计划

> **For agentic workers:** Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将单体 `noveltts-v2.html` 拆分为 api.js / store.js / views.js 三层架构，保持所有现有功能不受影响。

**架构:** 纯 JS 模块化重构，不引入框架。ApiClient 封装后端 8 个端点，AppStore 管理所有可变状态并通知订阅者，view 函数为纯渲染函数（数据入→HTML出）。

**Tech Stack:** 原生 JavaScript (ES Modules)，DOM API

---

## 文件结构

```
frontend/
├── noveltts-v2.html       ← 修改：保留 <style> + <body>，替换 <script> 为 import
├── js/
│   ├── api.js             ← 新建：API 客户端
│   ├── store.js           ← 新建：状态管理
│   ├── views.js           ← 新建：DOM 渲染
│   └── app.js             ← 新建：组装入口
```

---

### 全局状态迁移映射

| 旧全局变量 | 新 store.state 字段 | 说明 |
|---|---|---|
| `projects` | `projects` | 项目列表 |
| `currentProjectId` | `currentProjectId` | 当前项目 ID |
| `chapters` | `chapters` | 章节树数据 |
| `currentChapter` | `currentChapterIndex` | 当前章节索引 |
| `segments` | `segments` | 当前显示的片段列表 |
| `characters` | `characters` | 角色列表 |
| `selectedSegment` | `selectedSegmentIndex` | 选中片段索引 |
| `editMode` | `editMode` | 编辑模式开关 |
| `fontSize` | `fontSize` | 字体大小 |
| `batchMode` | `batchMode` | 批量模式开关 |
| `batchSelected` | `batchSelected` | Set<number> 批量选中 |
| `undoStack` / `redoStack` | `undoStack` / `redoStack` | 撤销栈 |
| `currentPage` | `page` | 'home' \| 'detail' |
| `currentVoiceCat` | `voiceFilter` | 音色分类筛选 |
| `loading` | `loading` | 全局加载状态 |

---

### Task 1: 创建 api.js

**文件:** 新建 `frontend/js/api.js`

API 客户端封装所有后端调用，统一错误处理。

- [ ] **Step 1: 创建文件骨架**

```javascript
// js/api.js
export class ApiClient {
  constructor(baseURL) {
    this.baseURL = baseURL;
  }

  async _fetch(path, options = {}) {
    const url = this.baseURL + path;
    const res = await fetch(url, {
      headers: { 'Accept': 'application/json', ...options.headers },
      ...options,
    });
    if (!res.ok) {
      let detail = '';
      try {
        const body = await res.json();
        detail = body.detail || body.error || res.statusText;
      } catch {
        detail = res.statusText;
      }
      throw new Error(detail || `HTTP ${res.status}`);
    }
    return res.json();
  }

  async getHealth() {
    return this._fetch('/health');
  }

  async uploadProject(file) {
    const form = new FormData();
    form.append('file', file);
    return this._fetch('/projects/upload', { method: 'POST', body: form });
  }

  async getProject(id) {
    return this._fetch(`/projects/${id}`);
  }

  async getChapters(id) {
    return this._fetch(`/projects/${id}/chapters`);
  }

  async analyzeChapter(id, index) {
    return this._fetch(`/projects/${id}/chapters/${index}`);
  }

  async getCharacters(id) {
    return this._fetch(`/projects/${id}/characters`);
  }

  async generateTTS(params) {
    return this._fetch('/tts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
    });
  }

  getAudioUrl(filename) {
    return `${this.baseURL}/audio/${filename}`;
  }
}
```

- [ ] **Step 2: 验证文件语法**

Run: `node --check frontend/js/api.js`
Expected: 无错误输出

---

### Task 2: 创建 store.js

**文件:** 新建 `frontend/js/store.js`

状态管理：单一 state 对象 + dispatch/subscribe 模式。

- [ ] **Step 1: 创建文件**

```javascript
// js/store.js
export class AppStore {
  constructor(initialState = {}) {
    this.state = {
      // 项目
      projects: [],
      currentProjectId: null,
      // 章节
      chapters: [],
      currentChapterIndex: null,
      // 分析结果（按章节索引缓存）
      analysisCache: {},
      // 片段
      segments: [],
      // 角色
      characters: [],
      // 角色颜色映射
      speakerColors: {},
      // UI 状态
      page: 'home',
      loading: false,
      error: null,
      selectedSegmentIndex: null,
      editMode: false,
      fontSize: 14,
      batchMode: false,
      batchSelected: new Set(),
      voiceFilter: 'all',
      undoStack: [],
      redoStack: [],
      // 音色列表
      voices: [],
      ...initialState,
    };
    this._listeners = new Set();
  }

  getState() {
    return this.state;
  }

  dispatch(updater) {
    this.state = updater(this.state);
    for (const fn of this._listeners) {
      fn(this.state);
    }
  }

  subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }
}
```

- [ ] **Step 2: 验证文件语法**

Run: `node --check frontend/js/store.js`
Expected: 无错误输出

---

### Task 3: 创建 views.js

**文件:** 新建 `frontend/js/views.js`

纯渲染函数。每个函数接受数据，返回 HTML 字符串。不调 fetch，不调 store。

这是最大的文件，按功能拆分为子函数。

- [ ] **Step 1: 创建骨架和常量**

```javascript
// js/views.js
export const TYPE_ICONS = {
  narration: '<i class="fa-solid fa-book-open"></i>',
  dialogue: '<i class="fa-solid fa-comment"></i>',
  onomatopoeia: '<i class="fa-solid fa-volume-high"></i>',
};
```

- [ ] **Step 2: 渲染首页项目列表**

```javascript
export function renderNav(page) {
  return `
    <div class="nav-link ${page === 'home' ? 'active' : ''}" onclick="window.__app.navigate('home')"><i class="fa-solid fa-home"></i> 首页</div>
    <div class="nav-link ${page === 'detail' ? 'active' : ''}" onclick="window.__app.navigate('detail')"><i class="fa-solid fa-book"></i> 当前项目</div>
  `;
}

export function renderProjectCard(project) {
  const ch = project.total_chapters || 0;
  return `
    <div class="project-card" onclick="window.__app.openProject('${project.project_id}')">
      <div class="project-icon"><i class="fa-solid fa-book"></i></div>
      <div class="project-info">
        <h3>${project.book_title || project.title}</h3>
        <div class="project-meta">
          <span>${ch} 章</span>
          <span>${project.total_words || '--'} 字</span>
        </div>
      </div>
    </div>
  `;
}

export function renderHomePage(projects) {
  if (projects.length === 0) {
    return '<div class="empty-state"><i class="fa-solid fa-book-open" style="font-size:3rem;opacity:0.3"></i><p>导入一本小说开始</p></div>';
  }
  return projects.map(p => renderProjectCard(p)).join('');
}
```

- [ ] **Step 3: 渲染章节树**

```javascript
export function renderChapterTree(chapters, currentIndex) {
  const analyzedCount = chapters.reduce((s, v) => s + v.chapters.filter(ch => ch.status === 'done').length, 0);
  const totalCount = chapters.reduce((s, v) => s + v.chapters.length, 0);
  const progress = totalCount > 0 ? `<div style="font-size:0.72rem;color:var(--text-muted);padding:2px 12px 6px">${analyzedCount}/${totalCount} 章已分析</div>` : '';

  const vols = chapters.map(vol => `
    <div class="volume-group">
      <div class="volume-header">${vol.volume || '全部章节'}</div>
      ${vol.chapters.map(ch => `
        <div class="chapter-item ${ch.id === currentIndex ? 'active' : ''} ${ch.status === 'done' ? 'done' : ''}"
             onclick="window.__app.selectChapter(${ch.id}, '${ch.title.replace(/'/g, "\\'").replace(/"/g, '&quot;')}')">
          <i class="fa-solid ${ch.status === 'done' ? 'fa-check-circle' : 'fa-circle'}"></i>
          <span>${ch.title}</span>
        </div>
      `).join('')}
    </div>
  `).join('');

  return progress + vols;
}
```

- [ ] **Step 4: 渲染片段列表（核心变更：利用 backend fragments）**

```javascript
export function renderSegments(segments, selectedIndex, editMode, batchMode, batchSelected, characters, speakerColors) {
  if (segments.length === 0) {
    return '<div class="empty-state"><i class="fa-solid fa-book-open" style="font-size:3rem;opacity:0.3"></i><p>点击左侧章节查看分析结果</p></div>';
  }

  const typeIcons = TYPE_ICONS;
  let html = '';

  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    const isSelected = selectedIndex === i;
    const isBatchChecked = batchSelected.has(i);

    // Insert zone before each segment
    html += `<div class="seg-insert-zone" data-insert-index="${i}">
      <div class="insert-btn" onclick="window.__app.insertSegment(${i})"><i class="fa-solid fa-plus"></i></div>
    </div>`;

    // Speaker info
    let speakerHtml = '';
    if (seg.type === 'dialogue' && seg.speaker) {
      speakerHtml = `<div class="seg-speaker">
        <span class="speaker-dot" style="background:${speakerColors[seg.speaker] || 'var(--text-muted)'}"></span>
        <span style="color:${speakerColors[seg.speaker] || 'var(--text-secondary)'}">${seg.speaker}</span>
        ${seg.emotion_class && seg.emotion_class !== 'neutral' ? `<span style="font-size:0.72rem;color:var(--text-muted);margin-left:4px">[${seg.emotion}]</span>` : ''}
      </div>`;
    } else if (seg.type === 'dialogue' && !seg.speaker) {
      speakerHtml = '<div class="seg-speaker"><span style="color:var(--text-muted)">未分配角色</span></div>';
    }

    // Text
    const textHtml = `<div class="seg-text" ${editMode ? 'contenteditable="true"' : ''} data-index="${i}">${seg.text}</div>`;

    // Checkbox
    const cbHtml = `<div class="seg-checkbox ${batchMode ? 'visible' : ''} ${isBatchChecked ? 'checked' : ''}" onclick="event.stopPropagation();window.__app.toggleBatchSelect(${i})"><i class="fa-solid fa-check"></i></div>`;

    // Drag
    const dragHtml = `<div class="seg-drag-handle seg-action-btn" draggable="true" ondragstart="window.__app.dragStart(event,${i})" ondragend="window.__app.dragEnd(event)" title="拖拽排序"><i class="fa-solid fa-grip-vertical"></i></div>`;

    // Hover actions
    const actionsHtml = `<div class="seg-actions">
      ${dragHtml}
      <button class="seg-action-btn" onclick="event.stopPropagation();window.__app.previewSegment(${i})" title="试听"><i class="fa-solid fa-headphones"></i></button>
      <button class="seg-action-btn" onclick="event.stopPropagation();window.__app.duplicateSegment(${i})" title="复制"><i class="fa-solid fa-copy"></i></button>
      <button class="seg-action-btn" onclick="event.stopPropagation();window.__app.deleteSegment(${i})" title="删除"><i class="fa-solid fa-trash"></i></button>
    </div>`;

    // Type capsules
    const typeCaps = `
      <button class="type-capsule ${seg.type === 'narration' ? 'active-narration' : ''}" onclick="event.stopPropagation();window.__app.changeSegType(${i},'narration')"><i class="fa-solid fa-book-open" style="font-size:0.7rem"></i> 旁白</button>
      <button class="type-capsule ${seg.type === 'dialogue' ? 'active-dialogue' : ''}" onclick="event.stopPropagation();window.__app.changeSegType(${i},'dialogue')"><i class="fa-solid fa-comment" style="font-size:0.7rem"></i> 对话</button>
      <button class="type-capsule ${seg.type === 'onomatopoeia' ? 'active-onomatopoeia' : ''}" onclick="event.stopPropagation();window.__app.changeSegType(${i},'onomatopoeia')"><i class="fa-solid fa-volume-high" style="font-size:0.7rem"></i> 拟声</button>
    `;

    // Speaker select
    const speakerOpts = characters.map(c => `<option value="${c.name}" ${seg.speaker === c.name ? 'selected' : ''}>${c.name}</option>`).join('');
    const speakerSelect = `<div class="slider-group"><label>说话人</label><select onchange="event.stopPropagation();window.__app.changeSpeaker(${i}, this.value)"><option value="">未分配</option>${speakerOpts}</select></div>`;

    // Edit panel
    const editPanel = `<div class="segment-edit-panel ${isSelected ? 'open' : ''}" id="seg-edit-${i}">
      <div class="segment-edit-inner">
        <div class="edit-row"><div style="flex:1;min-width:200px"><div style="font-size:0.78rem;color:var(--text-secondary);margin-bottom:8px">段落类型</div>${typeCaps}</div></div>
        <div class="edit-row" style="margin-top:12px">
          ${seg.type === 'dialogue' ? speakerSelect : ''}
          <div class="slider-group"><label>语速 <span class="slider-val">${seg.speed ?? 50}</span></label><input type="range" min="0" max="100" value="${seg.speed ?? 50}" oninput="window.__app.updateSegParam(${i},'speed',this.value)"></div>
          <div class="slider-group"><label>音量 <span class="slider-val">${seg.volume ?? 75}</span></label><input type="range" min="0" max="100" value="${seg.volume ?? 75}" oninput="window.__app.updateSegParam(${i},'volume',this.value)"></div>
          <div class="slider-group"><label>音调 <span class="slider-val">${seg.pitch ?? 50}</span></label><input type="range" min="0" max="100" value="${seg.pitch ?? 50}" oninput="window.__app.updateSegParam(${i},'pitch',this.value)"></div>
          <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();window.__app.previewSegment(${i})"><i class="fa-solid fa-headphones"></i> 试听</button>
        </div>
      </div>
    </div>`;

    html += `<div class="segment-card ${isSelected ? 'selected' : ''} ${isBatchChecked ? 'batch-selected' : ''}" data-index="${i}" data-type="${seg.type}" onclick="window.__app.selectSegment(${i})" ondragover="window.__app.dragOver(event)" ondragleave="window.__app.dragLeave(event)" ondrop="window.__app.drop(event,${i})">
      <div class="segment-color-bar"></div>
      <div class="segment-header">
        ${cbHtml}
        <div class="seg-type-icon">${typeIcons[seg.type]}</div>
        <div class="seg-content">
          ${speakerHtml}
          ${textHtml}
        </div>
        ${actionsHtml}
      </div>
      ${editPanel}
    </div>`;
  }

  html += `<div class="seg-insert-zone" data-insert-index="${segments.length}">
    <div class="insert-btn" onclick="window.__app.insertSegment(${segments.length})"><i class="fa-solid fa-plus"></i></div>
  </div>`;

  return html;
}
```

- [ ] **Step 5: 渲染角色列表**

```javascript
export function renderCharacterList(characters) {
  return characters.map(c => `
    <div class="char-lib-card">
      <div class="char-dot" style="background:${c.color || '#6b7b8d'}"></div>
      <div class="char-name">${c.name}</div>
      <div style="font-size:0.75rem;color:var(--text-muted);margin-top:4px">${c.voice || ''}</div>
    </div>
  `).join('');
}
```

- [ ] **Step 6: 渲染音色列表**

```javascript
export function renderVoiceList(voices, filter) {
  const filtered = filter === 'all' ? voices : voices.filter(v => v.cat === filter);
  const genderIcon = { male: 'fa-mars', female: 'fa-venus', neutral: 'fa-genderless' };
  return filtered.map(v => `
    <div class="voice-card">
      <div class="voice-card-header">
        <div class="voice-avatar"><i class="fa-solid ${genderIcon[v.gender]}"></i></div>
        <div><h3>${v.name}</h3><div class="gender">${v.gender === 'male' ? '男声' : v.gender === 'female' ? '女声' : '中性'}</div></div>
      </div>
      <div class="desc">${v.desc}</div>
      <div class="voice-tags">${(v.tags || []).map(t => `<span class="voice-tag">${t}</span>`).join('')}</div>
      <div class="waveform">${(v.bars || []).map(h => `<div class="bar" style="height:${h}%"></div>`).join('')}</div>
      <button class="btn btn-ghost btn-sm" onclick="window.__app.previewVoice('${v.name}')"><i class="fa-solid fa-play"></i> 试听</button>
    </div>
  `).join('');
}
```

- [ ] **Step 7: 渲染 Toast**

```javascript
export function renderToast(message, type = 'info') {
  const icons = { info: 'fa-circle-info', success: 'fa-circle-check', error: 'fa-circle-xmark', warning: 'fa-triangle-exclamation' };
  return `<div class="toast toast-${type}"><i class="fa-solid ${icons[type] || icons.info}"></i> ${message}</div>`;
}
```

- [ ] **Step 8: 验证文件语法**

Run: `node --check frontend/js/views.js`
Expected: 无错误输出

---

### Task 4: 创建 app.js（组装入口）

**文件:** 新建 `frontend/js/app.js`

- [ ] **Step 1: 创建组装逻辑**

```javascript
// js/app.js
import { ApiClient } from './api.js';
import { AppStore } from './store.js';
import * as Views from './views.js';

class App {
  constructor() {
    this.api = new ApiClient('http://localhost:8000/api/v1');
    this.store = new AppStore();
    this.store.subscribe(state => this._render(state));
  }

  async init() {
    // 加载音色列表
    const voices = [...]; // 从原文件保留的静态音色数据
    this.store.dispatch(s => ({ ...s, voices }));
    this._renderAll();
  }

  _render(state) {
    this._renderNav(state);
    this._renderContent(state);
  }

  _renderNav(state) {
    const el = document.getElementById('nav-links');
    if (el) el.innerHTML = Views.renderNav(state.page);
  }

  _renderContent(state) {
    if (state.page === 'home') {
      document.getElementById('content-body').innerHTML = Views.renderHomePage(state.projects);
    } else {
      document.getElementById('content-body').innerHTML = Views.renderSegments(
        state.segments, state.selectedSegmentIndex, state.editMode,
        state.batchMode, state.batchSelected, state.characters, state.speakerColors
      );
    }
  }

  _renderChapterTree() {
    const el = document.getElementById('chapter-tree');
    if (el) el.innerHTML = Views.renderChapterTree(this.store.state.chapters, this.store.state.currentChapterIndex);
  }

  _renderCharacterList() {
    const el = document.getElementById('char-lib-grid');
    if (el) el.innerHTML = Views.renderCharacterList(this.store.state.characters);
  }

  // === 行为方法（保持可调试，绑定到 window.__app）===
  navigate(page) {
    this.store.dispatch(s => ({ ...s, page }));
  }

  async openProject(id) {
    try {
      this.store.dispatch(s => ({ ...s, loading: true }));
      const project = await this.api.getProject(id);
      const chaptersData = await this.api.getChapters(id);
      const charactersData = await this.api.getCharacters(id);

      const chapters = [{ volume: '全部章节', chapters: chaptersData.map(ch => ({ id: ch.index, title: ch.title, status: 'pending' })) }];
      const chars = charactersData.characters || charactersData || [];
      const colors = {};
      chars.forEach((c, i) => { colors[c.name] = ['#7ea8c8','#e8c87e','#d4727a','#7ec89b','#c89be8','#e8a87e'][i % 6]; });

      this.store.dispatch(s => ({ ...s,
        currentProjectId: id,
        projects: s.projects,
        chapters,
        characters: chars,
        speakerColors: colors,
        currentChapterIndex: null,
        segments: [],
        page: 'detail',
        loading: false,
      }));
      this._renderChapterTree();

      // 自动选择第一章
      if (chaptersData.length > 0) {
        await this.selectChapter(chaptersData[0].index, chaptersData[0].title);
      }
    } catch (err) {
      this.store.dispatch(s => ({ ...s, loading: false, error: err.message }));
      showToast(err.message, 'error');
    }
  }

  async selectChapter(index, title) {
    this.store.dispatch(s => ({ ...s, currentChapterIndex: index, loading: true }));
    document.getElementById('content-title').textContent = title;
    document.getElementById('content-body').innerHTML = '<div class="loading-state"><i class="fa-solid fa-spinner fa-spin" style="font-size:2rem"></i><p>正在分析...</p></div>';

    // 检查缓存
    const cached = this.store.state.analysisCache[index];
    if (cached) {
      this._applyAnalysis(cached);
      this.store.dispatch(s => ({ ...s, loading: false }));
      return;
    }

    try {
      const data = await this.api.analyzeChapter(this.store.state.currentProjectId, index);
      this.store.dispatch(s => ({
        ...s,
        analysisCache: { ...s.analysisCache, [index]: data },
      }));
      this._applyAnalysis(data);
    } catch (err) {
      this.store.dispatch(s => ({ ...s, loading: false }));
      document.getElementById('content-body').innerHTML = `<div class="error-state"><i class="fa-solid fa-triangle-exclamation"></i><p>分析失败: ${err.message}</p></div>`;
    }
  }

  _applyAnalysis(data) {
    const segments = [];
    for (const sent of data.sentences) {
      if (sent.fragments && sent.fragments.length > 1) {
        for (const frag of sent.fragments) {
          segments.push({
            type: frag.type,
            text: frag.text,
            speaker: frag.speaker || '',
            speakerColor: '',
            emotion: sent.emotion || 'neutral',
            emotion_class: sent.emotion_class || 'neutral',
            quotation_type: frag.type === 'dialogue' ? 'dialogue' : 'none',
            speed: 50, volume: 75, pitch: 50,
          });
        }
      } else {
        segments.push({
          type: sent.sentence_type === 'dialogue' ? 'dialogue' : sent.sentence_type === 'onomatopoeia' ? 'onomatopoeia' : 'narration',
          text: sent.text,
          speaker: sent.speaker || '',
          speakerColor: '',
          emotion: sent.emotion || 'neutral',
          emotion_class: sent.emotion_class || 'neutral',
          quotation_type: sent.quotation_type || 'none',
          speed: 50, volume: 75, pitch: 50,
        });
      }
    }

    this.store.dispatch(s => ({ ...s, segments, currentChapterIndex: s.currentChapterIndex, loading: false }));

    // 更新章节状态
    this.store.dispatch(s => {
      const chapters = s.chapters.map(vol => ({
        ...vol,
        chapters: vol.chapters.map(ch => ch.id === s.currentChapterIndex ? { ...ch, status: 'done' } : ch),
      }));
      return { ...s, chapters };
    });
    this._renderChapterTree();

    showToast(`分析完成: ${segments.length} 个段落`, 'success');
  }

  selectSegment(index) {
    this.store.dispatch(s => ({
      ...s,
      selectedSegmentIndex: s.selectedSegmentIndex === index ? null : index,
    }));
  }

  changeSegType(index, type) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs[index] = { ...segs[index], type,
        speaker: type === 'dialogue' ? (s.characters[0]?.name || '未知角色') : '',
        speakerColor: type === 'dialogue' ? (s.speakerColors[s.characters[0]?.name] || '#6b7b8d') : '',
      };
      return { ...s, segments: segs, selectedSegmentIndex: index };
    });
  }

  changeSpeaker(index, name) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs[index] = { ...segs[index], speaker: name, speakerColor: s.speakerColors[name] || '' };
      return { ...s, segments: segs, selectedSegmentIndex: index };
    });
  }

  updateSegParam(index, param, value) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs[index] = { ...segs[index], [param]: parseInt(value) };
      return { ...s, segments: segs };
    });
  }

  insertSegment(index) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs.splice(index, 0, { type: 'narration', text: '', speed: 50, volume: 75, pitch: 50 });
      return { ...s, segments: segs, selectedSegmentIndex: index };
    });
  }

  duplicateSegment(index) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs.splice(index + 1, 0, { ...segs[index] });
      return { ...s, segments: segs };
    });
  }

  deleteSegment(index) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      segs.splice(index, 1);
      return { ...s, segments: segs, selectedSegmentIndex: s.selectedSegmentIndex === index ? null : s.selectedSegmentIndex > index ? s.selectedSegmentIndex - 1 : s.selectedSegmentIndex };
    });
  }

  toggleBatchSelect(index) {
    this.store.dispatch(s => {
      const set = new Set(s.batchSelected);
      set.has(index) ? set.delete(index) : set.add(index);
      return { ...s, batchSelected: set };
    });
  }

  toggleEditMode() {
    this.store.dispatch(s => ({ ...s, editMode: !s.editMode }));
  }

  changeFontSize(delta) {
    this.store.dispatch(s => ({ ...s, fontSize: Math.max(12, Math.min(20, s.fontSize + delta)) }));
  }

  previewSegment(index) {
    showToast(`试听第 ${index + 1} 段...`, 'info');
  }

  previewVoice(name) {
    showToast(`正在播放 ${name} 的示例`, 'info');
  }

  showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const el = document.createElement('div');
    el.innerHTML = Views.renderToast(msg, type);
    container.appendChild(el.firstElementChild);
    setTimeout(() => { if (el.parentNode) el.remove(); }, 3000);
  }
}

// 挂载全局，事件绑定通过 window.__app 访问
const app = new App();
window.__app = app;
app.init();
```

- [ ] **Step 2: 验证文件语法**

Run: `node --check frontend/js/app.js`
Expected: 无错误输出

---

### Task 5: 修改 noveltts-v2.html

**文件:** 修改 `frontend/noveltts-v2.html`

保留 CSS 和 HTML 结构，替换 `<script>` 块。

- [ ] **Step 1: 定位并替换 script 块**

找到 `<script>` 标记（~998 行），将其下所有 JS 代码替换为 ES Module 导入：

```html
<script type="module">
import './js/app.js';
</script>
```

同时将所有 `<script>` 的 `onclick` 等内联事件绑定从全局函数名改为 `window.__app.xxx()`。

- [ ] **Step 2: 将原来 HTML 中的 `onclick="functionName(...)"` 改为 `onclick="window.__app.functionName(...)"`**

全局搜索替换：
```
onclick="openDetail( → onclick="window.__app.openProject(
onclick="selectChapter( → onclick="window.__app.selectChapter(
onclick="selectSegment( → onclick="window.__app.selectSegment(
...
```

实际需要替换的 onclick 绑定：
- `openDetail(id)` → `window.__app.openProject(id)`  
- `selectChapter(id, title)` → `window.__app.selectChapter(id, title)`
- `selectSegment(i)` → `window.__app.selectSegment(i)`
- `insertSegmentAt(idx)` → `window.__app.insertSegment(idx)`
- `duplicateSegment(i)` → `window.__app.duplicateSegment(i)`
- `deleteSegment(i)` → `window.__app.deleteSegment(i)`
- `toggleEditMode()` → `window.__app.toggleEditMode()`
- `changeFontSize(delta)` → `window.__app.changeFontSize(delta)`
- `changeSegType(i, type)` → `window.__app.changeSegType(i, type)`
- `changeSpeaker(i, val)` → `window.__app.changeSpeaker(i, val)`
- `toggleBatchSelect(i)` → `window.__app.toggleBatchSelect(i)`
- `previewSegment(i)` → `window.__app.previewSegment(i)`
- `showToast(msg, type)` → `window.__app.showToast(msg, type)`
- `uploadProject()` → `window.__app.uploadProject()`

- [ ] **Step 3: 调整 upload 事件**

原 `uploadProject` 函数需迁移到 `App` 类。在 `app.js` 中添加：

```javascript
async uploadProject() {
  const fileInput = document.getElementById('file-input');
  const file = fileInput?.files?.[0];
  if (!file) { this.showToast('请选择文件', 'warning'); return; }

  try {
    this.store.dispatch(s => ({ ...s, loading: true }));
    const result = await this.api.uploadProject(file);
    this.store.dispatch(s => ({
      ...s,
      projects: [...s.projects, {
        id: result.project_id,
        project_id: result.project_id,
        title: result.book_title,
        total_chapters: result.total_chapters,
        total_volumes: result.total_volumes,
        author: '未知',
      }],
      loading: false,
    }));
    this.showToast(`导入成功: ${result.book_title}`, 'success');
    this._renderAll();
  } catch (err) {
    this.store.dispatch(s => ({ ...s, loading: false }));
    this.showToast('导入失败: ' + err.message, 'error');
  }
}
```

- [ ] **Step 4: 添加 upload HTML 的事件绑定**

HTML 中文件输入框的 `onchange` 绑定改为 `window.__app.onFileSelected(event)`：

```javascript
onFileSelected(event) {
  // 保持原来的 selectedUploadFile 逻辑
}
```

- [ ] **Step 5: 验证 HTML 加载**

启动后端，打开页面，确认：
1. 页面加载无控制台错误
2. 首页显示"导入一本小说开始"
3. 功能查看

---

### Task 6: 端到端验证

- [ ] **Step 1: 启动后端**

Run: `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000`

- [ ] **Step 2: 从文件系统直接打开 HTML**

在浏览器中打开 `frontend/noveltts-v2.html`

- [ ] **Step 3: 验证核心流程**

1. 上传修仙传.txt → 项目显示在首页 ✓
2. 点击项目 → 章节树加载 ✓
3. 自动分析第一章 → 段落正确显示 ✓
4. 混合句切分为独立 fragment ✓（如"对话"+"旁白"为两张卡片）
5. 点击片段 A 的编辑 → 只打开 A 的面板 ✓
6. 修改片段 B 的类型 → B 改变，A 不变 ✓

---

## 验收标准

| # | 标准 | 验证方式 |
|---|------|----------|
| 1 | `api.js` 8 个方法覆盖所有后端端点 | grep 或人工检查 |
| 2 | `store.js` 所有状态变更通过 dispatch | 无全局变量直接赋值 |
| 3 | `views.js` 所有函数为纯函数（数据入→HTML出） | 无 fetch/无 store.dispatch |
| 4 | 所有 onclick 使用 `window.__app.xxx()` | 无直接函数引用 |
| 5 | 混合句 fragment 切分为独立卡片 | 肉眼验证 |
| 6 | 无控制台错误 | Chrome DevTools |
| 7 | 加载/错误/空三态均有展示 | 测试每种状态 |
