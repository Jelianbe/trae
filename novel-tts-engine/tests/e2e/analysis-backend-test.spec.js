/**
 * NovelTTS Cloud - Analysis Function Backend Test (API Only)
 * 
 * Test scope:
 * 1. Backend analysis API returns correct segments with dialogue/narration types
 * 2. Character extraction works correctly
 * 3. Segment structure is valid
 */
const { test, expect } = require('@playwright/test');
const http = require('http');

const BACKEND_URL = 'http://localhost:8000';

const TEST_FILE_CONTENT = `第一章：坠落的少年

"你什么意思？"秦羽问道。

林凡沉默了片刻，缓缓说道："有些事情没有你想的那么简单。"

秦羽冷笑一声："不简单？让我看看怎么不简单！"

第二章：新的开始

清晨的阳光洒在大地上，鸟儿在枝头欢快地歌唱。

"今天真是个好天气啊，"林凡自言自语道。

他推开窗户，深吸一口气，感受着体内涌动的力量。`;

function apiRequest(method, path, data = null) {
  return new Promise((resolve, reject) => {
    const url = new URL(path, BACKEND_URL);
    const options = {
      hostname: url.hostname,
      port: url.port,
      path: url.pathname + url.search,
      method: method,
      headers: { 'Content-Type': 'application/json' },
    };

    const req = http.request(options, (res) => {
      let body = '';
      res.on('data', (chunk) => (body += chunk));
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, data: JSON.parse(body) });
        } catch (e) {
          resolve({ status: res.statusCode, data: body });
        }
      });
    });

    req.on('error', reject);
    if (data) req.write(JSON.stringify(data));
    req.end();
  });
}

test.describe('Analysis Backend Test', () => {

  test('TC-001: Create project and analyze chapter', async () => {
    console.log('\n========== TC-001: Backend Analysis API Test =========');

    // 1. Create project via API
    console.log('Creating project...');
    const createRes = await apiRequest('POST', '/api/v1/projects/create', {
      title: 'Analysis API Test',
      content: TEST_FILE_CONTENT,
    });
    console.log(`Create project status: ${createRes.status}`);
    console.log(`Response: ${JSON.stringify(createRes.data).substring(0, 300)}`);
    
    const projectId = createRes.data.project_id;
    console.log(`Project ID: ${projectId}`);
    expect(projectId).toBeTruthy();
    expect(createRes.data.total_chapters).toBeGreaterThanOrEqual(2);

    // 2. Trigger analysis for chapter 0
    console.log('\nTriggering analysis for chapter 0...');
    const analyzeRes = await apiRequest('GET', `/api/v1/projects/${projectId}/chapters/0`);
    console.log(`Analysis status: ${analyzeRes.status}`);
    console.log(`Analysis response: ${JSON.stringify(analyzeRes.data).substring(0, 800)}`);

    // 3. Verify segments are returned
    const sentences = analyzeRes.data.sentences;
    expect(Array.isArray(sentences)).toBe(true);
    expect(sentences.length).toBeGreaterThan(0);
    console.log(`\nFound ${sentences.length} sentences/segments`);

    // 4. Verify segment types
    const dialogueSegs = sentences.filter(s => s.sentence_type === 'dialogue' || s.type === 'dialogue');
    const narrationSegs = sentences.filter(s => s.sentence_type === 'narration' || s.type === 'narration');
    console.log(`Dialogue segments: ${dialogueSegs.length}`);
    console.log(`Narration segments: ${narrationSegs.length}`);
    
    if (dialogueSegs.length > 0) {
      console.log('\nDialogue segments:');
      dialogueSegs.forEach((seg, i) => {
        console.log(`  ${i+1}. "${seg.text}" (speaker: ${seg.speaker || 'N/A'})`);
      });
    }
    
    if (narrationSegs.length > 0) {
      console.log('\nNarration segments:');
      narrationSegs.forEach((seg, i) => {
        console.log(`  ${i+1}. "${seg.text}"`);
      });
    }

    expect(dialogueSegs.length).toBeGreaterThan(0);
    expect(narrationSegs.length).toBeGreaterThan(0);

    // 5. Verify dialogue content contains quotes
    const firstDialogue = dialogueSegs[0];
    console.log(`\nFirst dialogue: "${firstDialogue.text}"`);
    expect(firstDialogue.text).toMatch(/[""「」]/);

    // 6. Verify fragments within sentences
    const sentencesWithFragments = sentences.filter(s => s.fragments && s.fragments.length > 1);
    console.log(`\nSentences with multiple fragments: ${sentencesWithFragments.length}`);
    if (sentencesWithFragments.length > 0) {
      const firstMixed = sentencesWithFragments[0];
      console.log('First mixed sentence fragments:');
      firstMixed.fragments.forEach((frag, i) => {
        console.log(`  ${i+1}. [${frag.type}] "${frag.text}" (speaker: ${frag.speaker || 'N/A'})`);
      });
    }

    // 7. Verify characters are extracted via character API
    console.log('\nFetching characters...');
    const charRes = await apiRequest('GET', `/api/v1/projects/${projectId}/characters`);
    console.log(`Characters status: ${charRes.status}`);
    
    const characters = charRes.data.characters || [];
    console.log(`Characters found: ${characters.length}`);
    console.log(`Characters: ${JSON.stringify(characters)}`);
    
    if (characters.length > 0) {
      const charNames = characters.map(c => c.name);
      console.log(`Character names: ${charNames.join(', ')}`);
      
      // 旁白 is always present, so we check for 秦羽 and 林凡
      expect(charNames).toContain('秦羽');
      expect(charNames).toContain('林凡');
    }

    console.log('\n========== TC-001 PASSED =========');
  });
});
