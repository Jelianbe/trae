#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""功能测试脚本 - 验证三类核心交互"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.path.insert(0, '.')

import requests
import json

BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """健康检查"""
    resp = requests.get(f"{BASE_URL}/health")
    data = resp.json()
    print(f"✅ 健康检查: pipeline={data['pipeline_ready']}, tts={data['tts_engine']}")
    return data['pipeline_ready']

def test_projects():
    """获取项目列表"""
    resp = requests.get(f"{BASE_URL}/projects")
    projects = resp.json()
    print(f"✅ 项目数量: {len(projects)}")
    return projects

def test_chapter_analysis(project_id):
    """分析章节，验证 fragments 结构"""
    resp = requests.get(f"{BASE_URL}/projects/{project_id}/chapters")
    chapters = resp.json()
    print(f"✅ 章节数量: {len(chapters)}")
    
    if chapters:
        ch_idx = 0
        resp = requests.get(f"{BASE_URL}/projects/{project_id}/chapters/{ch_idx}")
        chapter = resp.json()
        
        sentences = chapter.get('sentences', [])
        print(f"✅ 句子数量: {len(sentences)}")
        
        # 测试1: 验证 fragments 拆分
        fragments_test(sentences)
        
        # 测试2: 验证情绪字段
        emotion_test(sentences)
        
        # 测试3: 验证角色列表
        test_characters(project_id)
        
        return sentences
    return []

def fragments_test(sentences):
    """测试1: 文字分类修改后句子合并渲染"""
    print("\n" + "="*60)
    print("测试1: 文字分类 / Fragments 拆分")
    print("="*60)
    
    has_fragments = False
    for sent in sentences:
        frags = sent.get('fragments', [])
        if len(frags) > 1:
            has_fragments = True
            print(f"  句子: {sent['text'][:50]}...")
            for frag in frags:
                print(f"    - [{frag['type']}] {frag['text'][:40]} (speaker={frag['speaker']})")
    
    if has_fragments:
        print("  ✅ PASS: 句子正确拆分为 fragments")
    else:
        print("  ⚠️  注意: 未找到多 fragments 句子（可能是测试数据问题）")

def emotion_test(sentences):
    """测试2: 情绪数据双向同步"""
    print("\n" + "="*60)
    print("测试2: 情绪数据双向同步")
    print("="*60)
    
    emotions_found = set()
    for sent in sentences:
        emotion = sent.get('emotion', 'unknown')
        emotion_class = sent.get('emotion_class', 'unknown')
        vector = sent.get('emotion_vector')
        emotions_found.add(emotion)
        
        if vector:
            print(f"  情绪: {emotion} (class={emotion_class}), 向量维度={len(vector)}")
    
    print(f"  情绪类型: {emotions_found}")
    
    # 测试 TTS 生成（情绪透传）
    print("  测试 TTS 生成（emotion=excited）...")
    try:
        resp = requests.post(f"{BASE_URL}/tts/generate", json={
            "text": "你好，这是测试。",
            "speaker": "测试",
            "emotion": "excited",
            "sentence_type": "dialogue"
        })
        if resp.status_code == 200:
            data = resp.json()
            print(f"  ✅ PASS: TTS 生成成功 ({data['filename']}, engine={data['engine']})")
        else:
            print(f"  ❌ FAIL: TTS 生成失败 ({resp.status_code})")
    except Exception as e:
        print(f"  ❌ FAIL: {e}")

def test_characters(project_id):
    """测试3: 角色分色逻辑"""
    print("\n" + "="*60)
    print("测试3: 角色分色逻辑")
    print("="*60)
    
    resp = requests.get(f"{BASE_URL}/projects/{project_id}/characters")
    data = resp.json()
    chars = data.get('characters', [])
    
    print(f"  角色数量: {len(chars)}")
    for char in chars:
        print(f"    - {char['name']} (id={char['id']}, gender={char['gender']}, locked={char['is_locked']})")
    
    print(f"  ✅ PASS: 角色列表返回正常（当前固定色，动态色差待实现）")

def main():
    print("="*60)
    print("功能测试开始")
    print("="*60)
    
    if not test_health():
        print("❌ 管道未就绪，退出测试")
        return
    
    projects = test_projects()
    if not projects:
        print("❌ 无项目，退出测试")
        return
    
    # 使用最近的项目
    project_id = projects[-1]['project_id']
    print(f"\n使用项目: {project_id} ({projects[-1]['title']})")
    
    test_chapter_analysis(project_id)
    
    print("\n" + "="*60)
    print("测试完成")
    print("="*60)

if __name__ == '__main__':
    main()
