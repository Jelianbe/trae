import sys, os
sys.path.insert(0, '.')

print("=== 角色识别率回退诊断 ===\n")

# 直接对比 v4 备份和当前代码的关键方法
v4_path = 'backups/v4_release_2026-05-10_准确率76.4%/pipeline/speaker_matcher.py'
curr_path = 'pipeline/speaker_matcher.py'

with open(v4_path, 'r', encoding='utf-8') as f:
    v4_lines = f.readlines()
with open(curr_path, 'r', encoding='utf-8') as f:
    curr_lines = f.readlines()

print(f"v4 行数: {len(v4_lines)}")
print(f"当前行数: {len(curr_lines)}")
print(f"差异: +{len(curr_lines)-len(v4_lines)}行\n")

# 对比 match_speaker 方法的关键差异
# 1. 查找 match_speaker 方法在两个版本中的位置
v4_match_start = None
curr_match_start = None
for i, line in enumerate(v4_lines):
    if 'def match_speaker(' in line:
        v4_match_start = i
        break
for i, line in enumerate(curr_lines):
    if 'def match_speaker(' in line:
        curr_match_start = i
        break

if v4_match_start and curr_match_start:
    print(f"v4 match_speaker 起始行: {v4_match_start+1}")
    print(f"当前 match_speaker 起始行: {curr_match_start+1}\n")
    
    # 对比方法的前100行
    v4_method = ''.join(v4_lines[v4_match_start:v4_match_start+100])
    curr_method = ''.join(curr_lines[curr_match_start:curr_match_start+100])
    
    if v4_method != curr_method:
        print("match_speaker 方法有差异")
        # 找出具体差异行
        for i, (v4_line, curr_line) in enumerate(zip(v4_method.split('\n'), curr_method.split('\n'))):
            if v4_line.strip() != curr_line.strip():
                print(f"  行{i+1}: v4={v4_line.strip()[:60]}")
                print(f"         curr={curr_line.strip()[:60]}")
                if i > 20:
                    print("  ... (省略后续差异)")
                    break
