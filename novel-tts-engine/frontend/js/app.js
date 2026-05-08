import { ApiClient } from './api.js';
import { AppStore } from './store.js';
import * as V from './views.js';

class App {
  constructor() {
    this.api = new ApiClient();
    this.store = new AppStore();
    this.store.subscribe(state => this._onStateChange(state));
    this._initEventDelegation();
  }

  async init() {
    this._renderAll();
    this.navigate(location.hash.slice(1) || 'home');
    window.addEventListener('hashchange', () => {
      this.navigate(location.hash.slice(1) || 'home');
    });
    // Load projects and voices from backend
    try {
      await this.api.getHealth();
      console.log('[App] 后端就绪');
    } catch (e) {
      console.log('[App] 后端未连接:', e.message);
    }
    await this._loadProjects();
    await this._loadVoices();
  }

  async _loadProjects() {
    try {
      const projects = await this.api.listProjects();
      this.store.dispatch(s => ({ ...s, projects }));
    } catch (e) {
      console.log('[App] 加载项目失败:', e.message);
    }
  }

  async _loadVoices() {
    try {
      const voices = await this.api.listVoices();
      this.store.dispatch(s => ({ ...s, voices }));
      await this._preloadVoicePreviews(voices);
    } catch (e) {
      console.log('[App] 加载音色失败:', e.message);
    }
  }

  async _preloadVoicePreviews(voices) {
    // 使用预生成的静态音频文件，无需调用 TTS API
    // 文件位置: /audio/previews/{voiceName}.wav
    const cache = { ...this.store.state.voicePreviewCache };
    let preloadCount = 0;
    
    for (const v of voices) {
      if (cache[v.name]) continue;
      // 直接使用预生成的静态文件
      const previewUrl = `/audio/previews/${encodeURIComponent(v.name)}.wav`;
      cache[v.name] = previewUrl;
      preloadCount++;
    }
    
    if (preloadCount > 0) {
      this.store.dispatch(s => ({ ...s, voicePreviewCache: { ...s.voicePreviewCache, ...cache } }));
      console.log(`[App] 音色试听音频已加载: ${preloadCount} 个`);
    } else {
      console.log('[App] 音色试听音频已全部缓存，跳过预加载');
    }
  }

  // ==================== Event Delegation ====================

  _initEventDelegation() {
    document.body.addEventListener('click', e => {
      const el = e.target.closest('[data-action]');
      if (!el) return;
      e.stopPropagation();
      const action = el.dataset.action;
      const handler = this._actionHandlers[action];
      if (handler) handler.call(this, el, e);
    });

    document.body.addEventListener('change', e => {
      const el = e.target;
      if (el.id === 'file-input') {
        this.uploadProject(el.files[0]);
        el.value = '';
      }
    });

    document.body.addEventListener('click', e => {
      const bar = e.target.closest('#player-bar');
      if (bar) this._seekPlayer(e);
    });
  }

  get _actionHandlers() {
    return {
      'navigate': (el) => this.navigate(el.dataset.page || 'home'),
      'open-modal': (el) => this._openModal(el.dataset.modal),
      'close-modal': (el) => this._closeModal(el.dataset.modal),
      'open-project': (el) => this.openProject(el.dataset.pid),
      'delete-project': (el) => this._confirmDelete(el.dataset.pid),
      'confirm-delete': () => this._deleteProject(),
      'select-chapter': (el) => this.selectChapter(parseInt(el.dataset.index), el.dataset.title),
      'select-segment': (el, e) => this.selectSegment(parseInt(el.dataset.index), e),
      'toggle-edit-mode': () => this.toggleEditMode(),
      'change-font-size': (el) => this.changeFontSize(parseInt(el.dataset.delta)),
      'filter-chapters': (el) => this._filterChapters(el),
      'filter-voices': (el) => this._filterVoices(el),
      'filter-voices-cat': (el) => this._filterVoicesCat(el),
      'toggle-mobile-menu': () => document.getElementById('nav-links')?.classList.toggle('open'),
      'close-drawer': () => this._closeDrawer(),
      'open-drawer': (el) => this._openDrawer(el.dataset.drawer),
      'toggle-panel': (el) => this._togglePanel(el.dataset.panel),
      'toggle-play': () => this._togglePlay(),
      'undo': () => this._undo(),
      'redo': () => this._redo(),
      'toggle-batch': () => this._toggleBatch(),
      'batch-change-type': (el) => this._batchChangeType(el.dataset.type),
      'batch-delete': () => this._batchDelete(),
      'insert-segment-after': () => this.showToast('请先进入编辑模式', 'info'),
      'append-empty': () => this.showToast('请先进入编辑模式', 'info'),
      'trigger-sentence-split': () => this._triggerSentenceSplit(),
      'create-project': () => this._createProject(),
      'analyze-all': () => this._analyzeAll(),
      'synthesize-chapter': () => this._synthesizeChapter(),
      'export-data': () => this.showToast('数据导出成功', 'success'),
      'upload-project': () => document.getElementById('file-input')?.click(),
      'save-character': () => { this._closeModal('char-edit'); this.showToast('角色已保存', 'success'); },
      'preview-voice': (el) => this._previewVoice(el),
      'play-audio-segment': (el) => this._playAudioSegment(el),
      'play-segment': (el) => this._playOneSegment(el),
      'generate-segment': (el) => this._generateOneSegment(el),
      'toggle-active': (el) => el.classList.toggle('active'),
      'toggle-fullscreen': () => {
        if (!document.fullscreenElement) document.documentElement.requestFullscreen();
        else document.exitFullscreen();
      },
    };
  }

  // ==================== Navigation ====================

  navigate(page) {
    this.store.dispatch(s => ({ ...s, page }));
  }

  // ==================== Project Management ====================

  async uploadProject(file) {
    if (!file) return;
    try {
      const data = await this.api.uploadProject(file);
      const p = {
        id: data.project_id,
        project_id: data.project_id,
        title: data.book_title,
        author: '未知',
        total_chapters: data.total_chapters,
        chapters: data.total_chapters,
        total_words: 0,
        words: '--',
        status: 'pending',
        progress: 0,
      };
      this.store.dispatch(s => ({
        ...s,
        projects: [p, ...s.projects],
      }));
      this._closeModal('new-project');
      this.showToast('导入成功: ' + data.book_title, 'success');
    } catch (e) {
      this.showToast('导入失败: ' + e.message, 'error');
    }
  }

  async openProject(id) {
    this.store.dispatch(s => ({ ...s, loading: true }));
    try {
      const [project, chaptersData, charactersData] = await Promise.all([
        this.api.getProject(id),
        this.api.getChapters(id),
        this.api.getCharacters(id),
      ]);

      const contents = {};
      const chapters = [{ volume: '全部章节', chapters: chaptersData.map(ch => {
        contents[ch.index] = ch.content || '';
        return { id: ch.index, title: ch.title, status: 'pending' };
      }) }];
      const chars = charactersData.characters || [];
      const colors = {};
      const palette = ['#7ea8c8','#e8c87e','#d4727a','#7ec89b','#c89be8','#e8a87e'];
      chars.forEach((c, i) => { colors[c.name] = palette[i % 6]; });

      this.store.dispatch(s => ({
        ...s,
        currentProjectId: id,
        chapters,
        chapterContents: contents,
        characters: chars,
        speakerColors: colors,
        currentChapterIndex: null,
        segments: [],
        page: 'detail',
        loading: false,
      }));

      document.getElementById('detail-book-title').textContent = '《' + (project.book_title || '') + '》';
      document.getElementById('detail-tree-title').textContent = project.book_title || '';

      // 默认选中第1章（显示原文，不分析）
      if (chaptersData.length > 0) {
        await this.selectChapter(chaptersData[0].index, chaptersData[0].title);
      }
    } catch (e) {
      this.store.dispatch(s => ({ ...s, loading: false }));
      this.showToast('加载项目失败: ' + e.message, 'error');
    }
  }

  _confirmDelete(pid) {
    this._deleteTargetId = pid;
    this._openModal('confirm-delete');
  }

  _deleteProject() {
    const pid = this._deleteTargetId;
    if (!pid) return;
    (async () => {
      try {
        await this.api.deleteProject(pid);
      } catch (e) {
        // still remove from local list
      }
      this.store.dispatch(s => ({
        ...s,
        projects: s.projects.filter(p => {
          const pid = this._deleteTargetId;
          return (p.id !== pid) && (p.project_id !== pid);
        }),
      }));
      this._closeModal('confirm-delete');
      this.showToast('项目已删除', 'success');
    })();
  }

  async _createProject() {
    const title = document.getElementById('new-project-title')?.value || '';
    const content = document.getElementById('new-project-content')?.value || '';
    
    if (title.trim() && content.trim()) {
      // 使用手动输入方式创建项目
      try {
        const data = await this.api.createProject(title.trim(), content.trim());
        const p = {
          id: data.project_id,
          project_id: data.project_id,
          title: data.book_title,
          author: '未知',
          total_chapters: data.total_chapters,
          chapters: data.total_chapters,
          total_words: 0,
          words: '--',
          status: 'pending',
          progress: 0,
        };
        this.store.dispatch(s => ({
          ...s,
          projects: [p, ...s.projects],
        }));
        this._closeModal('new-project');
        // 清空输入框
        const titleEl = document.getElementById('new-project-title');
        if (titleEl) titleEl.value = '';
        const contentEl = document.getElementById('new-project-content');
        if (contentEl) contentEl.value = '';
        this.showToast('创建成功: ' + data.book_title, 'success');
      } catch (e) {
        this.showToast('创建失败: ' + e.message, 'error');
      }
    } else {
      // 使用文件上传方式
      document.getElementById('file-input')?.click();
    }
  }

  // ==================== Chapter Analysis ====================

  async selectChapter(index, title) {
    this._analysisGen = (this._analysisGen || 0) + 1;
    const gen = this._analysisGen;

    this.store.dispatch(s => ({
      ...s, currentChapterIndex: index,
      segments: [], selectedSegmentIndex: null, selectedFragmentIndex: null,
      audioSegments: [],
    }));
    document.getElementById('content-title').textContent = title || '';

    const pid = this.store.state.currentProjectId;
    if (!pid) return;
    const cacheKey = pid + '-' + index;
    const cached = this.store.state.analysisCache[cacheKey];

    if (cached) {
      // 有缓存：按 splitChapters 状态决定渲染模式
      if (gen !== this._analysisGen) return;
      this._applyAnalysis(cached, index);
      return;
    }

    // 无缓存：渲染原文纯文本（不触发分析，等用户点"句子拆分"）
    if (gen === this._analysisGen) {
      const content = this.store.state.chapterContents[index] || '';
      if (content) {
        const escaped = content
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/\n/g, '<br>');
        document.getElementById('content-body').innerHTML =
          '<div style="padding:24px;line-height:1.8;white-space:pre-wrap;color:var(--text-primary)">' + escaped + '</div>';
      } else {
        document.getElementById('content-body').innerHTML = '<div style="text-align:center;padding:60px 20px;color:var(--text-muted)"><i class="fa-solid fa-book-open" style="font-size:3rem;margin-bottom:16px;opacity:0.3"></i><p>暂无章节内容</p></div>';
      }
      this.store.dispatch(s => ({ ...s, segments: [] }));
    }
  }

  _applyAnalysis(data, index) {
    const segments = [];
    for (const sent of data.sentences) {
      segments.push({
        text: sent.text,
        type: sent.sentence_type || 'narration',
        speaker: sent.speaker || '',
        emotion: sent.emotion || 'neutral',
        emotion_class: sent.emotion_class || 'neutral',
        emotion_vector: sent.emotion_vector || null,
      });
    }

    this.store.dispatch(s => {
      const chapters = s.chapters.map(vol => ({
        ...vol,
        chapters: vol.chapters.map(ch => ch.id === index ? { ...ch, status: 'done' } : ch),
      }));
      return { ...s, segments, chapters };
    });

    this.showToast('分析完成: ' + segments.length + ' 个段落', 'success');
  }

  // ==================== Segment Interaction ====================

  selectSegment(index, event) {
    this.store.dispatch(s => ({
      ...s,
      selectedSegmentIndex: s.selectedSegmentIndex === index ? null : index,
    }));
  }

  toggleEditMode() {
    this.store.dispatch(s => ({ ...s, editMode: !s.editMode }));
  }

  changeFontSize(delta) {
    this.store.dispatch(s => ({ ...s, fontSize: Math.max(12, Math.min(24, s.fontSize + delta)) }));
  }

  // ==================== Rendering ====================

  _onStateChange(state) {
    this._renderNav(state);
    this._renderPageVisibility(state);
    this._renderContent(state);
  }

  _renderAll() {
    this._onStateChange(this.store.state);
  }

  _renderNav(state) {
    const el = document.getElementById('nav-links');
    if (!el) return;
    const pages = [
      { id: 'home', icon: 'fa-house', label: '首页' },
      { id: 'projects', icon: 'fa-folder', label: '项目管理' },
      { id: 'voices', icon: 'fa-microphone', label: '音色库' },
      { id: 'settings', icon: 'fa-gear', label: '系统设置' },
    ];
    el.innerHTML = pages.map(p => `
      <a class="nav-link ${state.page === p.id ? 'active' : ''}" data-action="navigate" data-page="${p.id}" href="#${p.id}">
        <i class="fa-solid ${p.icon}" style="margin-right:6px;font-size:0.8rem"></i>${p.label}
      </a>
    `).join('');
  }

  _renderPageVisibility(state) {
    document.querySelectorAll('.page').forEach(el => {
      el.classList.toggle('active', el.id === 'page-' + state.page);
    });
  }

  _renderContent(state) {
    if (state.page === 'home') {
      V.renderHomeProjects(state.projects);
    } else if (state.page === 'projects') {
      V.renderProjectsList(state.projects);
    } else if (state.page === 'detail') {
      const body = document.getElementById('content-body');
      if (body) {
        body.style.fontSize = state.fontSize + 'px';
        body.innerHTML = V.renderSegments(state.segments, state.selectedSegmentIndex, state.selectedFragmentIndex, state.splitChapters[state.currentChapterIndex], state.ttsCache, state.currentChapterIndex);
      }
      V.renderChapterTree(state.chapters, state.currentChapterIndex);
      this._renderAnalysisProgress(state);
      this._initWaveform();
    } else if (state.page === 'voices') {
      V.renderVoices(state.voices, 'all');
    }
  }

  _renderAnalysisProgress(state) {
    const el = document.getElementById('analysis-progress');
    if (!el) return;
    if (state.analysisProgress) {
      const p = state.analysisProgress;
      el.style.display = 'block';
      const fill = el.querySelector('.fill');
      const text = el.querySelector('.analysis-progress-text');
      if (fill) fill.style.width = (p.total > 0 ? (p.current / p.total) * 100 : 0) + '%';
      if (text) text.textContent = '分析中 ' + (p.current + 1) + '/' + p.total + ' - ' + p.label;
    } else {
      el.style.display = 'none';
    }
  }

  _initWaveform() {
    const bg = document.getElementById('waveform-bg');
    if (!bg) return;
    if (bg.children.length > 0) return;
    const n = 40;
    let html = '';
    for (let i = 0; i < n; i++) {
      const h = Math.floor(Math.random() * 60) + 20;
      html += `<div class="wf-bar" style="height:${h}%"></div>`;
    }
    bg.innerHTML = html;
  }

  // ==================== UI Helpers ====================

  _openModal(name) {
    document.getElementById('modal-' + name)?.classList.add('open');
  }

  _closeModal(name) {
    document.getElementById('modal-' + name)?.classList.remove('open');
  }

  _openDrawer(type) {
    const drawer = document.getElementById('right-drawer');
    const overlay = document.getElementById('drawer-overlay');
    const title = document.getElementById('drawer-title');
    const body = document.getElementById('drawer-body');
    if (!drawer || !overlay) return;
    if (type === 'characters') {
      if (title) title.textContent = '角色列表';
      if (body) body.innerHTML = V.renderCharacters(this.store.state.characters);
    } else if (type === 'stats') {
      if (title) title.textContent = '章节统计';
      const segs = this.store.state.segments;
      const total = segs.length;
      const dc = segs.filter(s => s.type === 'dialogue').length;
      const nc = segs.filter(s => s.type === 'narration').length;
      if (body) body.innerHTML = `<div style="padding:16px 20px"><div class="stats-grid">
        <div class="stat-item"><div class="val">${total}</div><div class="lbl">总句数</div></div>
        <div class="stat-item"><div class="val">${dc}</div><div class="lbl">对话</div></div>
        <div class="stat-item"><div class="val">${nc}</div><div class="lbl">旁白</div></div>
      </div></div>`;
    }
    drawer.classList.add('open');
    overlay.classList.add('open');
  }

  _filterChapters(el) {
    const q = el.value.toLowerCase();
    document.querySelectorAll('.chapter-item').forEach(item => {
      item.style.display = item.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  }

  _filterVoices(el) {
    const q = el.value.toLowerCase();
    document.querySelectorAll('.voice-card').forEach(card => {
      card.style.display = card.textContent.toLowerCase().includes(q) ? '' : 'none';
    });
  }

  _filterVoicesCat(el) {
    document.querySelectorAll('.voice-sidebar-item').forEach(item => item.classList.remove('active'));
    el.classList.add('active');
    const cat = el.dataset.cat;
    document.querySelectorAll('.voice-card').forEach(card => {
      card.style.display = cat === 'all' || card.dataset.cat === cat ? '' : 'none';
    });
  }

  _togglePlay() {
    if (this._previewAudio) {
      if (this._previewAudio.paused) {
        this._previewAudio.play();
        document.getElementById('play-btn').innerHTML = '<i class="fa-solid fa-pause"></i>';
      } else {
        this._previewAudio.pause();
        document.getElementById('play-btn').innerHTML = '<i class="fa-solid fa-play"></i>';
      }
    } else {
      this.showToast('点击音频列表中的片段试听', 'info');
    }
  }

  _seekPlayer(e) {
    const bar = document.getElementById('player-bar');
    const audio = this._previewAudio;
    if (!bar || !audio) return;
    const rect = bar.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.currentTime = pct * audio.duration;
  }

  _undo() {
    const s = this.store.state;
    if (s.undoStack.length === 0) return;
    const prev = s.undoStack.pop();
    this.store.dispatch(st => ({ ...st, redoStack: [...st.redoStack, JSON.parse(JSON.stringify(st.segments))], segments: prev }));
  }

  _redo() {
    const s = this.store.state;
    if (s.redoStack.length === 0) return;
    const next = s.redoStack.pop();
    this.store.dispatch(st => ({ ...st, undoStack: [...st.undoStack, JSON.parse(JSON.stringify(st.segments))], segments: next }));
  }

  _toggleBatch() {
    this.store.dispatch(s => ({ ...s, batchMode: !s.batchMode, batchSelected: s.batchMode ? new Set() : s.batchSelected }));
  }

  _batchChangeType(type) {
    this.store.dispatch(s => {
      const segs = [...s.segments];
      for (const i of s.batchSelected) {
        if (segs[i]) segs[i] = { ...segs[i], type };
      }
      return { ...s, segments: segs, batchMode: false, batchSelected: new Set() };
    });
  }

  _batchDelete() {
    this.store.dispatch(s => {
      const indices = [...s.batchSelected].sort((a, b) => b - a);
      const segs = [...s.segments];
      for (const i of indices) segs.splice(i, 1);
      return { ...s, segments: segs, batchMode: false, batchSelected: new Set() };
    });
  }

  _analyzeAll() {
    const pid = this.store.state.currentProjectId;
    if (!pid) { this.showToast('请先打开一个项目', 'warning'); return; }

    // 获取所有未分析章节
    const s = this.store.state;
    const flat = s.chapters.flatMap(v => v.chapters || []);
    const pending = flat.filter(ch => ch.status !== 'done');
    if (pending.length === 0) { this.showToast('所有章节已分析', 'info'); return; }

    const setStatus = (chId, status) => {
      this.store.dispatch(st => ({
        ...st,
        chapters: st.chapters.map(vol => ({
          ...vol,
          chapters: vol.chapters.map(c => c.id === chId ? { ...c, status } : c),
        })),
      }));
    };

    this.store.dispatch(st => ({ ...st, analysisProgress: { current: 0, total: pending.length, label: '准备分析…' } }));

    (async () => {
      const gen = ++this._analysisGen;
      for (let i = 0; i < pending.length; i++) {
        if (gen !== this._analysisGen) break;
        const ch = pending[i];
        this.store.dispatch(st => ({ ...st, analysisProgress: { current: i, total: pending.length, label: ch.title } }));
        setStatus(ch.id, 'processing');
        try {
          const data = await this.api.analyzeChapter(pid, ch.id);
          if (gen !== this._analysisGen) break;
          this.store.dispatch(st => ({
            ...st,
            analysisCache: { ...st.analysisCache, [pid + '-' + ch.id]: data },
            splitChapters: { ...st.splitChapters, [ch.id]: true },
          }));
          setStatus(ch.id, 'done');
        } catch (e) {
          if (gen === this._analysisGen) {
            setStatus(ch.id, 'pending');
            console.warn('章节分析失败:', ch.title, e.message);
          }
        }
      }
      this.store.dispatch(st => ({ ...st, analysisProgress: null }));
      if (gen === this._analysisGen) {
        this.showToast('分析完成: ' + pending.length + ' 章', 'success');
      }
    })();
  }

  _triggerSentenceSplit() {
    const index = this.store.state.currentChapterIndex;
    if (index == null) { this.showToast('请先选择一个章节', 'warning'); return; }

    const pid = this.store.state.currentProjectId;
    if (!pid) return;
    const cacheKey = pid + '-' + index;
    const cached = this.store.state.analysisCache[cacheKey];

    if (cached) {
      // 已有缓存：直接切换到拆分渲染
      this.store.dispatch(s => ({
        ...s, splitChapters: { ...s.splitChapters, [index]: true },
      }));
      this._applyAnalysis(cached, index);
      this.showToast('句子拆分完成', 'success');
      return;
    }

    // 无缓存：调 API 分析
    this.showToast('正在分析当前章节…', 'info');
    (async () => {
      const gen = ++this._analysisGen;
      try {
        const data = await this.api.analyzeChapter(pid, index);
        if (gen !== this._analysisGen) return;
        this.store.dispatch(s => ({
          ...s,
          analysisCache: { ...s.analysisCache, [cacheKey]: data },
          splitChapters: { ...s.splitChapters, [index]: true },
        }));
        this._applyAnalysis(data, index);
        this.showToast('句子拆分完成', 'success');
      } catch (e) {
        if (gen === this._analysisGen) {
          this.showToast('分析失败: ' + e.message, 'error');
        }
      }
    })();
  }

  _synthesizeChapter() {
    const segs = this.store.state.segments;
    if (!segs || segs.length === 0) { this.showToast('请先分析章节', 'warning'); return; }
    const chIdx = this.store.state.currentChapterIndex;
    if (chIdx == null) return;

    const ttsCache = this.store.state.ttsCache || {};
    const chCache = ttsCache[chIdx] || {};
    const pending = [];
    for (let i = 0; i < segs.length; i++) {
      if (!chCache[i]) pending.push(i);
    }
    if (pending.length === 0) { this.showToast('所有段落已生成', 'info'); return; }

    this._showTTSPregress(0, pending.length);
    (async () => {
      for (let i = 0; i < pending.length; i++) {
        if (this.store.state.page !== 'detail') { this._hideTTSPregress(); return; }
        const segIdx = pending[i];
        this._showTTSPregress(i + 1, pending.length);
        const seg = segs[segIdx];
        const frags = seg.fragments || [{ type: 'narration', text: seg.text, speaker: '' }];
        for (const f of frags) {
          if (!f.text || !f.text.trim()) continue;
          try {
            const result = await this.api.generateTTS({
              text: f.text,
              speaker: f.speaker || 'default',
              emotion: 'neutral',
              sentence_type: f.type === 'dialogue' ? 'dialogue' : 'narration',
            });
            this.store.dispatch(s => ({
              ...s,
              ttsCache: {
                ...s.ttsCache,
                [chIdx]: { ...(s.ttsCache[chIdx] || {}), [segIdx]: result.audio_url },
              },
            }));
            break;
          } catch (e) {
            console.warn('段' + segIdx + ' TTS失败:', e.message);
          }
        }
        await new Promise(r => setTimeout(r, 100));
      }
      this._hideTTSPregress();
      this.showToast('音频生成完成 (' + pending.length + ' 段)', 'success');
    })();
  }

  _showTTSPregress(current, total) {
    const el = document.getElementById('tts-progress');
    const fill = document.getElementById('tts-progress-fill');
    const text = document.getElementById('tts-progress-text');
    if (!el || !fill || !text) return;
    el.style.display = 'block';
    fill.style.width = (total > 0 ? (current / total) * 100 : 0) + '%';
    text.textContent = '生成中 ' + current + '/' + total;
  }

  _hideTTSPregress() {
    const el = document.getElementById('tts-progress');
    if (el) el.style.display = 'none';
  }

  _generateOneSegment(el) {
    const segIdx = parseInt(el.dataset.seg);
    if (isNaN(segIdx)) return;
    const chIdx = this.store.state.currentChapterIndex;
    if (chIdx == null) return;
    const segs = this.store.state.segments;
    if (!segs || !segs[segIdx]) return;

    this.showToast('正在生成…', 'info');
    const seg = segs[segIdx];
    const frags = seg.fragments || [{ type: 'narration', text: seg.text, speaker: '' }];
    (async () => {
      for (const f of frags) {
        if (!f.text || !f.text.trim()) continue;
        try {
          const result = await this.api.generateTTS({
            text: f.text,
            speaker: f.speaker || 'default',
            emotion: 'neutral',
            sentence_type: f.type === 'dialogue' ? 'dialogue' : 'narration',
          });
          this.store.dispatch(s => ({
            ...s,
            ttsCache: {
              ...s.ttsCache,
              [chIdx]: { ...(s.ttsCache[chIdx] || {}), [segIdx]: result.audio_url },
            },
          }));
          this._playAudioUrl(result.audio_url);
          return;
        } catch (e) {
          this.showToast('生成失败: ' + e.message, 'error');
        }
      }
    })();
  }

  _playOneSegment(el) {
    const segIdx = parseInt(el.dataset.seg);
    if (isNaN(segIdx)) return;
    const chIdx = this.store.state.currentChapterIndex;
    if (chIdx == null) return;
    const cache = this.store.state.ttsCache;
    const url = cache && cache[chIdx] && cache[chIdx][segIdx];
    if (url) {
      if (this._previewAudio) { this._previewAudio.pause(); }
      this._playAudioUrl(url);
    } else {
      this.showToast('请先生成该段落', 'info');
    }
  }

  _playAudioUrl(url) {
    if (this._previewAudio) { this._previewAudio.pause(); }
    const audio = new Audio(url);
    this._previewAudio = audio;
    audio.addEventListener('timeupdate', () => {
      const pct = audio.duration > 0 ? (audio.currentTime / audio.duration) * 100 : 0;
      const fill = document.getElementById('player-fill');
      if (fill) fill.style.width = pct + '%';
      document.getElementById('player-time-current').textContent = this._formatTime(audio.currentTime);
      document.getElementById('player-time-total').textContent = this._formatTime(audio.duration);
    });
    audio.play().then(() => {
      document.getElementById('play-btn').innerHTML = '<i class="fa-solid fa-pause"></i>';
    }).catch(() => {});
    audio.addEventListener('ended', () => {
      document.getElementById('play-btn').innerHTML = '<i class="fa-solid fa-play"></i>';
    });
  }

  _playAudioSegment(el) {
    const url = el.dataset.url;
    if (!url) return;
    this._playAudioUrl(url);
  }

  _formatTime(seconds) {
    if (!seconds || !isFinite(seconds)) return '00:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
  }

  _previewVoice(el) {
    const card = el.closest('.voice-card');
    if (!card) return;
    const name = card.querySelector('h3')?.textContent || '云深';
    const voiceName = name;

    if (this._previewAudio) { this._previewAudio.pause(); this._previewAudio = null; }

    const cachedUrl = this.store.state.voicePreviewCache[voiceName];
    if (cachedUrl) {
      this.showToast('试听: ' + voiceName, 'info');
      const audio = new Audio(cachedUrl);
      this._previewAudio = audio;
      audio.play();
      return;
    }

    this.showToast('试听: ' + voiceName + ' (生成中…)', 'info');
    (async () => {
      try {
        const result = await this.api.generateTTS({
          text: '你好，欢迎使用小说语音合成引擎。这是一段试听音频。',
          speaker: voiceName,
          emotion: 'neutral',
          sentence_type: 'narration',
        });
        this.store.dispatch(s => ({
          ...s,
          voicePreviewCache: { ...s.voicePreviewCache, [voiceName]: result.audio_url },
        }));
        const audio = new Audio(result.audio_url);
        this._previewAudio = audio;
        audio.play();
      } catch (e) {
        this.showToast('试听失败: ' + e.message, 'error');
      }
    })();
  }

  _closeDrawer() {
    document.getElementById('right-drawer')?.classList.remove('open');
    document.getElementById('drawer-overlay')?.classList.remove('open');
  }

  _togglePanel(side) {
    const el = document.getElementById(side === 'left' ? 'detail-left' : 'detail-right');
    if (el) el.classList.toggle('collapsed');
  }

  showToast(msg, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const icons = { info:'fa-circle-info', success:'fa-circle-check', error:'fa-circle-xmark', warning:'fa-triangle-exclamation' };
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.innerHTML = '<i class="fa-solid ' + (icons[type] || icons.info) + '"></i> <span>' + msg + '</span>';
    container.appendChild(el);
    setTimeout(() => el.remove(), 3000);
  }
}

const app = new App();
app.init();
