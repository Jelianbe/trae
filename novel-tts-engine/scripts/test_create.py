import requests
import json

# 测试创建项目API
data = {
    'title': '测试小说2',
    'author': '测试作者',
    'content': '''第一章 初入江湖

清晨的阳光透过窗户洒进房间，李逍遥缓缓睁开了眼睛。

"今天是个好日子。"他喃喃自语道。

第二章 奇遇

就在他准备出门的时候，突然听到门外传来一阵奇怪的声音。'''
}

print("\n" + "="*50)
print("测试创建项目API...")
try:
    r = requests.post('http://localhost:8000/api/v1/projects/create', json=data)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.json()}")
except Exception as e:
    print(f"Error: {e}")
