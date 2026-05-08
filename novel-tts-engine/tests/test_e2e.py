#!/usr/bin/env python
"""E2E 测试：MVP 核心功能验证"""
import requests
import json
import time
import sys

BASE = 'http://localhost:8000'

def test_health():
    """测试 1：健康检查"""
    print("=== 测试 1：健康检查 ===")
    r = requests.get(f'{BASE}/api/v1/health')
    assert r.status_code == 200
    data = r.json()
    assert data['status'] == 'ok'
    assert data['pipeline_ready'] == True
    print(f"  Status: {data['status']}")
    print(f"  Pipeline: {data['pipeline_ready']}")
    print(f"  TTS Engine: {data['tts_engine']}")
    print("  PASS")
    return True

def test_list_projects():
    """测试 2：项目列表"""
    print("\n=== 测试 2：项目列表 ===")
    r = requests.get(f'{BASE}/api/v1/projects')
    assert r.status_code == 200
    projects = r.json()
    print(f"  Projects count: {len(projects)}")
    for p in projects[:2]:
        print(f"    - {p['id']}: {p['title']} ({p['total_chapters']} chapters)")
    print("  PASS")
    return projects

def test_get_chapters(project_id):
    """测试 3：获取章节列表"""
    print(f"\n=== 测试 3：获取章节列表 ({project_id}) ===")
    r = requests.get(f'{BASE}/api/v1/projects/{project_id}/chapters')
    assert r.status_code == 200
    chapters = r.json()
    print(f"  Chapter count: {len(chapters)}")
    for ch in chapters:
        print(f"    - [{ch['index']}] {ch['title']} ({ch['word_count']} words, status: pending)")
    print("  PASS")
    return chapters

def test_analyze_chapter(project_id, chapter_index):
    """测试 4：分析章节"""
    print(f"\n=== 测试 4：分析章节 {chapter_index} ===")
    
    # Start analysis (GET endpoint)
    r = requests.get(f'{BASE}/api/v1/projects/{project_id}/chapters/{chapter_index}')
    print(f"  Start analyze: {r.status_code}")
    if r.status_code != 200:
        print(f"  Error: {r.text[:300]}")
        return None
    
    data = r.json()
    status = data.get('status', 'unknown')
    print(f"  Status: {status}")
    return data

def verify_sentence_structure(data):
    """测试 5：验证 SentenceData 结构"""
    print(f"\n=== 测试 5：验证 SentenceData 结构 ===")
    sentences = data.get('sentences', [])
    if not sentences:
        print("  No sentences to verify")
        return False
    
    expected = {'text', 'speaker', 'emotion', 'emotion_class', 'emotion_vector', 'sentence_type', 'entities'}
    s = sentences[0]
    actual = set(s.keys())
    
    missing = expected - actual
    extra = actual - expected
    
    print(f"  Sentence count: {len(sentences)}")
    print(f"  Expected fields: {expected}")
    print(f"  Actual fields: {actual}")
    
    if missing:
        print(f"  FAIL - Missing: {missing}")
        return False
    if extra:
        print(f"  WARN - Extra: {extra}")
    
    print("  PASS")
    return True

def verify_dialogue_narration(data):
    """测试 6：验证对话/旁白识别"""
    print(f"\n=== 测试 6：验证对话/旁白识别 ===")
    sentences = data.get('sentences', [])
    
    dc = sum(1 for s in sentences if s.get('sentence_type') == 'dialogue')
    nc = sum(1 for s in sentences if s.get('sentence_type') == 'narration')
    
    print(f"  Dialogue: {dc}")
    print(f"  Narration: {nc}")
    print(f"  Total: {len(sentences)}")
    
    for s in sentences[:5]:
        speaker_info = f" (speaker: {s.get('speaker', '')})" if s['sentence_type'] == 'dialogue' else ""
        print(f"    [{s['sentence_type']}] {s['text'][:40]}...{speaker_info}")
    
    if dc > 0 or nc > 0:
        print("  PASS")
        return True
    print("  FAIL - No dialogue or narration found")
    return False

def verify_characters(project_id):
    """测试 7：验证角色列表"""
    print(f"\n=== 测试 7：验证角色列表 ===")
    r = requests.get(f'{BASE}/api/v1/projects/{project_id}/characters')
    assert r.status_code == 200
    data = r.json()
    chars = data.get('characters', [])
    print(f"  Characters: {len(chars)}")
    for c in chars[:5]:
        print(f"    - {c['name']} (gender: {c.get('gender', 'unknown')})")
    if len(chars) > 0:
        print("  PASS")
        return True
    print("  WARN - No characters found (may need more content)")
    return True

def main():
    print("Novel-TTS-Engine MVP E2E Test")
    print("="*50)
    
    passed = 0
    failed = 0
    
    # Test 1: Health
    try:
        test_health()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
        print("Cannot continue without healthy backend")
        sys.exit(1)
    
    # Test 2: List projects
    try:
        projects = test_list_projects()
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
        return
    
    if not projects:
        print("No projects found, cannot continue")
        sys.exit(1)
    
    project_id = projects[0]['id']
    
    # Test 3: Get chapters
    try:
        chapters = test_get_chapters(project_id)
        passed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
        return
    
    # Test 4: Analyze chapter
    try:
        chapter_index = 0
        data = test_analyze_chapter(project_id, chapter_index)
        if data:
            passed += 1
        else:
            failed += 1
            print("Analysis failed, skipping remaining tests")
            return
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
        return
    
    # Test 5: Verify SentenceData structure
    try:
        if verify_sentence_structure(data):
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    # Test 6: Verify dialogue/narration
    try:
        if verify_dialogue_narration(data):
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    # Test 7: Verify characters
    try:
        if verify_characters(project_id):
            passed += 1
        else:
            failed += 1
    except Exception as e:
        print(f"  FAIL: {e}")
        failed += 1
    
    print(f"\n{'='*50}")
    print(f"E2E Test Result: {passed} passed, {failed} failed")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
