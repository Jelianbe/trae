/**
 * api.js — NovellTTS-Engine API 客户端
 * 注意：当前后端 API 返回的 projects 和 chapters 路径为 /api/v1/projects/...
 * baseURL 解析优先级:
 *   1. 构造函数显式传入的 baseURL
 *   2. window.__API_BASE_URL__ 全局变量
 *   3. URL 参数 ?api_base=...
 *   4. localStorage 中的 api_base_url 配置
 *   5. 默认值 http://localhost:8000/api/v1
 */

function getApiBaseURLFromConfig() {
  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get('api_base');
  if (fromUrl) {
    try { localStorage.setItem('noveltts_api_base_url', fromUrl); } catch {}
    return fromUrl;
  }
  try {
    const fromStorage = localStorage.getItem('noveltts_api_base_url');
    if (fromStorage) return fromStorage;
  } catch {}
  return null;
}

export class ApiClient {
  constructor(baseURL) {
    const resolved = baseURL ||
      window.__API_BASE_URL__ ||
      getApiBaseURLFromConfig() ||
      'http://localhost:8000/api/v1';
    this._baseURL = resolved.replace(/\/+$/, '');
  }

  async _fetch(path, options = {}) {
    const url = `${this._baseURL}${path}`;
    const timeout = options.timeout || 120000; // 默认 2 分钟
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeout);

    let res;
    try {
      res = await fetch(url, { ...options, signal: controller.signal });
    } catch (err) {
      clearTimeout(timer);
      if (err.name === 'AbortError') {
        throw new Error(`请求超时 (${timeout/1000}s)`);
      }
      throw new Error(`网络请求失败: ${err.message}`);
    }
    clearTimeout(timer);
    let body = null;
    const ct = res.headers.get('content-type') || '';
    if (ct.includes('application/json')) {
      try { body = await res.json(); } catch {}
    }
    if (!res.ok) {
      throw new Error(body?.detail || body?.error || body?.message || `HTTP ${res.status}`);
    }
    return body;
  }

  async getHealth() { return this._fetch('/health'); }

  async listProjects() { return this._fetch('/projects'); }

  async deleteProject(id) {
    return this._fetch(`/projects/${encodeURIComponent(id)}`, { method: 'DELETE' });
  }

  async listVoices() { return this._fetch('/voices'); }

  async uploadProject(file) {
        const fd = new FormData();
        fd.append('file', file);
        return this._fetch('/projects/upload', { method: 'POST', body: fd });
    }

    async createProject(title, author, content) {
        return this._fetch('/projects/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, content, author: author || '' }),
        });
    }

  async getProject(id) { return this._fetch(`/projects/${encodeURIComponent(id)}`); }

  async getChapters(id) { return this._fetch(`/projects/${encodeURIComponent(id)}/chapters`); }

  async analyzeChapter(id, index) {
    return this._fetch(`/projects/${encodeURIComponent(id)}/chapters/${encodeURIComponent(String(index))}`);
  }

  async getCharacters(id) { return this._fetch(`/projects/${encodeURIComponent(id)}/characters`); }

  async generateTTS(params) {
    return this._fetch('/tts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(params),
      timeout: 300000,
    });
  }

  async synthesizeChapter(projectId, chapterIndex, segments) {
    return this._fetch(`/projects/${encodeURIComponent(projectId)}/chapters/${chapterIndex}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segments }),
      timeout: 300000,
    });
  }

  async synthesizeChapterDirect(segments) {
    return this._fetch('/tts/chapter', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ segments }),
      timeout: 300000,
    });
  }

  getAudioUrl(filename) { return `${this._baseURL}/audio/${encodeURIComponent(filename)}`; }
}
