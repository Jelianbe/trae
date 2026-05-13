import sys
sys.path.insert(0, '.')
sys.path.insert(0, './analysis_reports')

from analysis_reports.evaluate_v6_improvements import run_evaluation, load_test_data
from test_data_v6 import TEST_PARAGRAPHS
import json

data = load_test_data()

# Run both modes
result_a = run_evaluation(data, precreate_chars=None)
result_b = run_evaluation(data, precreate_chars=[
    ('林轩', 'male'), ('纳兰嫣然', 'female'), ('小翠', 'female'),
    ('苏夜', 'male'), ('林雪', 'female'), ('黑衣人', 'male'),
    ('药老', 'male'), ('萧炎', 'male'), ('赵天行', 'male'),
    ('艾德温', 'male'), ('伊莉雅', 'female'), ('博士', 'male'),
    ('骑士', 'male'), ('加尔文', 'male'), ('白发老者', 'male'),
    ('掌柜', 'male'), ('骑士队长', 'male'), ('首领', 'male'),
])

# Collect detailed error analysis
errors_a = [d for d in result_a['details'] if not d['is_correct']]
errors_b = [d for d in result_b['details'] if not d['is_correct']]

print("=" * 70)
print("当前测试结果摘要")
print("=" * 70)
print(f"模式A: 准确率={result_a['accuracy']:.1%}, 加权={result_a['weighted_accuracy']:.1%}, 错误={len(errors_a)}, 未知={result_a['unknown']}")
print(f"模式B: 准确率={result_b['accuracy']:.1%}, 加权={result_b['weighted_accuracy']:.1%}, 错误={len(errors_b)}, 未知={result_b['unknown']}")

# Save detailed data for documentation
output = {
    'result_a': result_a,
    'result_b': result_b,
    'errors_a': errors_a,
    'errors_b': errors_b,
    'paragraphs': TEST_PARAGRAPHS
}

with open('d:/trae/novel-tts-engine/analysis_reports/evaluation_data.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, ensure_ascii=False, indent=2)

print("\n详细数据已保存到 evaluation_data.json")
