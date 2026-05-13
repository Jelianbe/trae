"""快速基线测试，只输出关键指标"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import subprocess
result = subprocess.run(
    [sys.executable, os.path.join(os.path.dirname(__file__), 'evaluate_v6_improvements.py')],
    capture_output=True, text=True, encoding='utf-8', errors='replace'
)

for line in result.stdout.split('\n'):
    stripped = line.strip()
    if any(k in stripped for k in [
        '模式A:', '模式B:', '总对话', '正确:', '未知:', '错误:', 
        '加权准确率', '对比总结', '指标', '准确率', '差值', '正确数'
    ]):
        print(stripped)
