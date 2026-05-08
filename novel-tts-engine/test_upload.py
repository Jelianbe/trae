import requests
import json

# 测试上传
test_content = """第一章 初入江湖

清晨的阳光透过窗户洒进房间，李逍遥缓缓睁开了眼睛。

"今天是个好日子。"他喃喃自语道。

第二章 奇遇

就在他准备出门的时候，突然听到门外传来一阵奇怪的声音。"""

# 使用文本内容直接测试
data = {
    'title': '测试小说',
    'author': '测试作者',
    'content': test_content
}

try:
    print("测试直接创建项目...")
    r = requests.post('http://localhost:8000/api/v1/projects/upload', data=data)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")

# 测试文件上传
print("\n" + "="*50)
print("测试文件上传...")
try:
    files = {'file': ('test.txt', test_content.encode('utf-8'), 'text/plain')}
    r = requests.post('http://localhost:8000/api/v1/projects/upload', files=files)
    print(f"Status: {r.status_code}")
    print(f"Response: {r.text}")
except Exception as e:
    print(f"Error: {e}")
