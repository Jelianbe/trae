import requests
import os

# 创建测试文件
test_content = """第一章 初入江湖

清晨的阳光透过窗户洒进房间，李逍遥缓缓睁开了眼睛。

"今天是个好日子。"他喃喃自语道。

第二章 奇遇

就在他准备出门的时候，突然听到门外传来一阵奇怪的声音。"""

# 测试1: 文件上传方式
print("="*60)
print("测试1: 文件上传方式")
print("="*60)
try:
    with open('test_novel.txt', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    with open('test_novel.txt', 'rb') as f:
        files = {'file': ('test_novel.txt', f, 'text/plain')}
        r = requests.post('http://localhost:8000/api/v1/projects/upload', files=files)
    
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
    
    # 清理测试文件
    os.remove('test_novel.txt')
except Exception as e:
    print(f"错误: {e}")

# 测试2: 手动输入方式
print("\n" + "="*60)
print("测试2: 手动输入方式")
print("="*60)
try:
    data = {
        'title': '手动创建测试',
        'author': '测试作者',
        'content': test_content
    }
    r = requests.post('http://localhost:8000/api/v1/projects/create', json=data)
    
    print(f"状态码: {r.status_code}")
    print(f"响应: {r.json()}")
except Exception as e:
    print(f"错误: {e}")

# 测试3: 获取项目列表
print("\n" + "="*60)
print("测试3: 获取项目列表")
print("="*60)
try:
    r = requests.get('http://localhost:8000/api/v1/projects')
    print(f"状态码: {r.status_code}")
    projects = r.json()
    print(f"项目数量: {len(projects)}")
    for p in projects:
        print(f"  - {p['title']} (ID: {p['project_id']})")
except Exception as e:
    print(f"错误: {e}")
