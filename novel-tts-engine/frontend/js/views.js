export function escapeHtml(str) {
  if (str == null) return '';
  const d = document.createElement('div');
  d.appendChild(document.createTextNode(String(str)));
  return d.innerHTML;
}

export function renderProjectCard(p) {
  const title = escapeHtml(p.title || p.book_title || '未命名');
  const author = escapeHtml(p.author || '未知');
  const chapters = p.chapters ?? p.total_chapters ?? 0;
  const words = p.total_words ?? p.words ?? '--';
  const progress = p.progress ?? 0;
  const status = p.status ?? 'pending';
  const statusLabel = { completed:'已完成', analyzing:'分析中', pending:'未分析' };
  return `<div class="project-card" data-action="open-project" data-pid="${escapeHtml(p.id || p.project_id)}">
    <button class="delete-btn" data-action="delete-project" data-pid="${escapeHtml(p.id || p.project_id)}" title="删除"><i class="fa-solid fa-trash" style="font-size:0.8rem"></i></button>
    <h3>${title}</h3>
    <div class="author">${author}</div>
    <div class="meta">
      <span><i class="fa-solid fa-file-word"></i> ${words} 字</span>
      <span><i class="fa-solid fa-list"></i> ${chapters} 章</span>
      <span class="status-tag ${status}">${statusLabel[status] || status}</span>
    </div>
    <div class="progress-bar"><div class="fill" style="width:${progress}%"></div></div>
  </div>`;
}

export function renderHomeProjects(projects) {
  const el = document.getElementById('home-projects');
  if (!el) return;
  if (!projects || projects.length === 0) {
    el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)"><p>还没有项目，点击上方"新建项目"开始</p></div>';
    return;
  }
  el.innerHTML = projects.map(p => renderProjectCard(p)).join('');
}

export function renderProjectsList(projects) {
  const el = document.getElementById('projects-list');
  if (!el) return;
  if (!projects || projects.length === 0) {
    el.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted)"><p>还没有项目</p></div>';
    return;
  }
  el.innerHTML = projects.map(p => renderProjectCard(p)).join('');
}

export function renderChapterTree(chapters, currentIndex) {
  const tree = document.getElementById('chapter-tree');
  if (!tree) return;
  if (!chapters || chapters.length === 0) {
    tree.innerHTML = '<div style="padding:12px;color:var(--text-muted);font-size:0.85rem">暂无章节</div>';
    return;
  }
  let doneCount = 0, totalCount = 0;
  const vols = chapters.map(vol => {
    const chs = vol.chapters || [];
    totalCount += chs.length;
    doneCount += chs.filter(ch => ch.status === 'done').length;
    return `<div class="volume-group">
      <div class="volume-header">${escapeHtml(vol.volume || '全部章节')}</div>
      ${chs.map(ch => {
        const isActive = ch.id === currentIndex;
        let iconHtml = '';
        if (ch.status === 'done') {
          iconHtml = '<i class="fa-solid fa-check-circle ch-icon done"></i>';
        } else if (ch.status === 'processing') {
          iconHtml = '<span class="ch-ring processing" data-chapter="' + ch.id + '"></span>';
        } else {
          iconHtml = '<span class="ch-ring pending"></span>';
        }
        return `<div class="chapter-item ${isActive ? 'active' : ''} ${ch.status === 'done' ? 'done' : ''}"
             data-action="select-chapter" data-index="${ch.id}" data-title="${escapeHtml(ch.title || '').replace(/"/g, '&quot;')}">
          ${iconHtml}
          <span>${escapeHtml(ch.title || '')}</span>
        </div>`;
      }).join('')}
    </div>`;
  }).join('');
  const progress = `<div style="font-size:0.72rem;color:var(--text-muted);padding:2px 12px 6px">${doneCount}/${totalCount} 章已分析</div>`;
  tree.innerHTML = progress + vols;
}

export function renderSegments(segments, selectedIndex, selectedFragIndex, splitMode, ttsCache, chapterIndex) {
  if (!segments || segments.length === 0) {
    return '<div style="text-align:center;padding:60px 20px;color:var(--text-muted)"><i class="fa-solid fa-book-open" style="font-size:3rem;margin-bottom:16px;opacity:0.3"></i><p>点击章节查看分析结果</p></div>';
  }

  if (!splitMode) {
    // 原文模式：不渲染句子拆分
    const typeColors = { narration:'var(--type-narration)', dialogue:'var(--type-dialogue)', onomatopoeia:'var(--type-onomatopoeia)' };
    return '<div class="segments-stats"><span class="stat-segments"><i class="fa-solid fa-paragraph"></i> 段落 ' + segments.length + '</span></div>' +
      segments.map((seg, i) => {
        const sel = selectedIndex === i ? 'selected' : '';
        const mainType = (seg.fragments && seg.fragments.length > 0) ? seg.fragments[0].type : 'narration';
        return `<div class="segment-card ${sel}" data-index="${i}" data-action="select-segment">
          <div class="segment-color-bar" style="background:${typeColors[mainType] || 'var(--border)'}"></div>
          <div class="segment-header">
            <div class="seg-text-wrapper"><span class="seg-text">${escapeHtml(seg.text)}</span></div>
          </div>
        </div>`;
      }).join('');
  }

  // 记录片段统计
  const mixedCount = segments.filter(s => (s.fragments || []).length > 1).length;
  console.debug('[句子拆分] 段落=' + segments.length + ', 混合句=' + mixedCount);

  const totalFrags = segments.reduce((sum, s) => sum + (s.fragments || []).length, 0);
  let statsHTML = `<div class="segments-stats"><span class="stat-segments"><i class="fa-solid fa-paragraph"></i> 段落 ${segments.length}</span>`;
  if (mixedCount > 0) {
    statsHTML += `<span class="stat-mixed"><i class="fa-solid fa-scissors"></i> 句子拆分 ${mixedCount} 句 / ${totalFrags} 段</span>`;
  }
  statsHTML += '</div>';

  const typeColors = { narration:'var(--type-narration)', dialogue:'var(--type-dialogue)', onomatopoeia:'var(--type-onomatopoeia)' };
  const typeLabels = { narration:'旁白', dialogue:'对话', onomatopoeia:'拟声' };
  const typeIcons = { narration:'fa-book-open', dialogue:'fa-comment', onomatopoeia:'fa-volume-high' };
  let html = '';
  for (let i = 0; i < segments.length; i++) {
    const seg = segments[i];
    const sel = selectedIndex === i ? 'selected' : '';
    const frags = seg.fragments || [{ type: 'narration', text: seg.text, speaker: '' }];

    // 堆叠色条
    let barHTML = '';
    if (frags.length > 1) {
      const totalLen = seg.text.length || 1;
      barHTML = '<div class="seg-color-stack">';
      for (const f of frags) {
        const pct = Math.max(10, (f.text.length / totalLen) * 100);
        barHTML += `<div class="seg-color-strip" style="height:${pct}%;background:${typeColors[f.type] || 'var(--border)'}" title="${typeLabels[f.type] || f.type}"></div>`;
      }
      barHTML += '</div>';
    } else {
      barHTML = `<div class="segment-color-bar" style="background:${typeColors[frags[0].type] || 'var(--border)'}"></div>`;
    }

    // 原文 + 悬停方框（多 fragment 时包裹 span）
    let textHTML = '';
    if (frags.length > 1) {
      for (let j = 0; j < frags.length; j++) {
        const f = frags[j];
        const isFragSel = selectedFragIndex != null && selectedFragIndex === j && selectedIndex === i;
        textHTML += `<span class="frag-hover ${isFragSel ? 'frag-selected' : ''}" data-seg-index="${i}" data-frag-index="${j}" title="${typeLabels[f.type] || f.type}${f.speaker ? ' · ' + f.speaker : ''}">${escapeHtml(f.text)}</span>`;
      }
    } else {
      textHTML = `<span class="seg-text">${escapeHtml(seg.text)}</span>`;
    }

    // 说话人标签 + 音频按钮
    let speakerHTML = '';
    if (frags.length === 1 && frags[0].type === 'dialogue' && frags[0].speaker) {
      speakerHTML = `<span class="seg-speaker" style="color:${frags[0].speakerColor || 'var(--text-secondary)'}">${escapeHtml(frags[0].speaker)}</span>`;
    }

    const chKey = chapterIndex != null ? chapterIndex : '';
    const cacheForSeg = (ttsCache && ttsCache[chKey] && ttsCache[chKey][i]) ? ttsCache[chKey][i] : null;
    const audioBtn = cacheForSeg
      ? `<button class="btn btn-ghost btn-sm audio-card-btn" data-action="play-segment" data-seg="${i}" title="试听"><i class="fa-solid fa-play"></i> 试听</button>`
      : `<button class="btn btn-ghost btn-sm audio-card-btn" data-action="generate-segment" data-seg="${i}" title="生成音频"><i class="fa-solid fa-waveform-lines"></i> 生成</button>`;

    html += `<div class="segment-card ${sel}" data-index="${i}" data-action="select-segment">
      ${barHTML}
      <div class="segment-header">
        <div class="seg-text-wrapper">${textHTML}</div>
      </div>
      <div class="segment-meta">
        ${speakerHTML}
        ${audioBtn}
      </div>
    </div>`;
  }
  return statsHTML + html;
}

export function renderCharacters(chars) {
  if (!chars || chars.length === 0) return '<div style="padding:16px;color:var(--text-muted);font-size:0.85rem">暂无角色</div>';
  return chars.map(c => `
    <div class="character-card" data-action="filter-character" data-cname="${escapeHtml(c.name || '')}">
      <div class="char-color" style="background:${c.color || (c.name === '旁白' ? '#6e6a65' : '#6b7b8d')}"></div>
      <div class="char-info">
        <div class="name">${escapeHtml(c.name || '')}${c.name === '旁白' ? ' <span style="font-size:0.65rem;color:var(--text-muted);font-weight:400">(锁定)</span>' : ''}</div>
        <div class="count">${c.gender || ''}${c.name === '旁白' ? ' · 默认音色' : ''}</div>
      </div>
    </div>
  `).join('');
}

export function renderEmptyState(message) {
  return `<div style="text-align:center;padding:60px 20px;color:var(--text-muted)"><i class="fa-solid fa-book-open" style="font-size:3rem;margin-bottom:16px;opacity:0.3"></i><p>${escapeHtml(message)}</p></div>`;
}

const _voices = [
  { id:1, name:'云深', gender:'male', cat:'male', desc:'沉稳磁性，适合旁白和成熟男性角色', tags:['磁性','沉稳','旁白'], bars:[40,65,50,80,55,70,45,60,75,50,65,40,70,55,80,60,45,70,50,65] },
  { id:2, name:'凌风', gender:'male', cat:'male', desc:'清朗少年音，适合年轻男性角色', tags:['少年','清朗','热血'], bars:[60,40,75,50,80,45,70,55,40,65,80,50,60,75,40,55,70,45,80,60] },
  { id:3, name:'若水', gender:'female', cat:'female', desc:'温婉知性，适合女性角色和内心独白', tags:['温婉','知性','柔美'], bars:[30,50,40,60,35,55,45,50,30,60,40,55,35,50,60,45,40,55,30,50] },
  { id:4, name:'铁马', gender:'male', cat:'male', desc:'豪迈刚毅，适合武将和豪爽角色', tags:['豪迈','刚毅','霸气'], bars:[80,60,90,70,85,65,80,75,60,90,70,85,65,80,90,75,60,85,70,80] },
  { id:5, name:'素心', gender:'female', cat:'female', desc:'清冷空灵，适合仙侠女性角色', tags:['清冷','空灵','仙侠'], bars:[25,45,35,55,30,50,40,45,25,55,35,50,30,45,55,40,35,50,25,45] },
  { id:6, name:'墨言', gender:'neutral', cat:'neutral', desc:'中性沉稳，适合旁白和叙述', tags:['中性','沉稳','叙述'], bars:[50,55,45,60,50,55,45,60,50,55,45,60,50,55,45,60,50,55,45,60] },
];

export function getVoices() { return _voices; }

export function renderVoices(voices, cat) {
  const grid = document.getElementById('voice-grid');
  if (!grid) return;
  const filtered = cat === 'all' ? voices : voices.filter(v => v.cat === cat);
  const genderIcon = { male:'fa-mars', female:'fa-venus', neutral:'fa-genderless' };
  grid.innerHTML = filtered.map(v => `
    <div class="voice-card" data-cat="${v.cat}">
      <div class="voice-card-header">
        <div class="voice-avatar"><i class="fa-solid ${genderIcon[v.gender] || 'fa-genderless'}"></i></div>
        <div><h3>${escapeHtml(v.name)}</h3><div class="gender">${v.gender === 'male' ? '男声' : v.gender === 'female' ? '女声' : '中性'}</div></div>
      </div>
      <div class="desc">${escapeHtml(v.desc || '')}</div>
      <div class="voice-tags">${(v.tags || []).map(t => `<span class="voice-tag">${escapeHtml(t)}</span>`).join('')}</div>
      <div class="waveform">${(v.bars || []).map(h => `<div class="bar" style="height:${h}%"></div>`).join('')}</div>
      <button class="btn btn-ghost btn-sm" data-action="preview-voice"><i class="fa-solid fa-play"></i> 试听</button>
    </div>
  `).join('');
}
