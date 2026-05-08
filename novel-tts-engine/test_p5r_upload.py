import requests
import os

# 测试文件路径
TEST_FILE_PATH = r'C:\Users\月笙如歌\Downloads\P5R.txt'

def test_upload():
    print("="*60)
    print("测试上传功能")
    print("="*60)
    
    # 检查文件是否存在
    if not os.path.exists(TEST_FILE_PATH):
        print(f"❌ 文件不存在: {TEST_FILE_PATH}")
        return
    
    # 获取文件大小
    file_size = os.path.getsize(TEST_FILE_PATH)
    print(f"文件路径: {TEST_FILE_PATH}")
    print(f"文件大小: {file_size / 1024:.2f} KB")
    
    # 测试文件上传
    print("\n--- 测试1: 文件上传 ---")
    try:
        with open(TEST_FILE_PATH, 'rb') as f:
            files = {'file': ('P5R.txt', f, 'text/plain')}
            r = requests.post('http://localhost:8000/api/v1/projects/upload', files=files)
        
        print(f"状态码: {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            print(f"项目ID: {data.get('project_id')}")
            print(f"书名: {data.get('book_title')}")
            print(f"章节数: {data.get('total_chapters')}")
            print(f"卷数: {data.get('total_volumes')}")
            print("✅ 文件上传成功")
        else:
            print(f"❌ 上传失败: {r.text}")
    except Exception as e:
        print(f"❌ 上传异常: {e}")
    
    # 测试获取项目列表
    print("\n--- 测试2: 获取项目列表 ---")
    try:
        r = requests.get('http://localhost:8000/api/v1/projects')
        if r.status_code == 200:
            projects = r.json()
            print(f"项目数量: {len(projects)}")
            for p in projects[-3:]:  # 只显示最后3个项目
                print(f"  - {p.get('title')} (ID: {p.get('project_id')})")
            print("✅ 获取项目列表成功")
        else:
            print(f"❌ 获取失败: {r.text}")
    except Exception as e:
        print(f"❌ 获取异常: {e}")

if __name__ == '__main__':
    test_upload()
