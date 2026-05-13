export class AppStore {
  constructor(initialState = {}) {
    let savedVoiceCache = {};
    let savedDrafts = {};
    try {
      const raw = localStorage.getItem('noveltts_voice_preview_cache');
      if (raw) savedVoiceCache = JSON.parse(raw);
    } catch {}
    try {
      const raw = localStorage.getItem('noveltts_chapter_drafts');
      if (raw) savedDrafts = JSON.parse(raw);
    } catch {}

    this.state = {
      projects: [],
      currentProjectId: null,
      chapters: [],
      currentChapterIndex: null,
      analysisCache: {},
      segments: [],
      characters: [],
      speakerColors: {},
      page: 'home',
      loading: false,
      error: null,
      selectedSegmentIndex: null,
      selectedFragmentIndex: null,
      editMode: false,
      fontSize: 14,
      batchMode: false,
      batchSelected: new Set(),
      sentenceSplitMode: true,
      splitChapters: {},
      chapterContents: {}, // {chapterIndex: content}
      ttsCache: {}, // {chapterIdx: {segIdx: audioUrl}}
      audioSegments: [],
      analysisProgress: null,
      voiceFilter: 'all',
      voicePreviewCache: savedVoiceCache, // {voiceName: audioUrl} 持久化缓存
      chapterDrafts: savedDrafts, // {projectId-chapterIndex: segments[]} 章节草稿
      undoStack: [],
      redoStack: [],
      voices: [],
      ...initialState,
    };
    this._listeners = new Set();
  }

  getState() { return this.state; }

  dispatch(updater) {
    const newState = updater(this.state);
    this.state = newState;
    try {
      if (newState.voicePreviewCache && Object.keys(newState.voicePreviewCache).length > 0) {
        localStorage.setItem('noveltts_voice_preview_cache', JSON.stringify(newState.voicePreviewCache));
      }
    } catch {}
    try {
      if (newState.chapterDrafts) {
        localStorage.setItem('noveltts_chapter_drafts', JSON.stringify(newState.chapterDrafts));
      }
    } catch {}
    for (const fn of this._listeners) {
      try { fn(this.state); } catch (e) { console.warn('Store listener error:', e); }
    }
  }

  subscribe(fn) {
    this._listeners.add(fn);
    return () => this._listeners.delete(fn);
  }
}
