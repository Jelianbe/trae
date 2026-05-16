# -*- coding: utf-8 -*-
"""
回归测试脚本 - 自动化对比基线准确率

使用方法：
1. 修改代码前：python regression_test.py baseline
2. 修改代码后：python regression_test.py current  
3. 对比结果：  python regression_test.py compare

输出格式：准确率 + 失败案例明细
"""
import sys, os, tempfile, uuid, json
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import CharacterManager
from pipeline.semantic_ranker import get_semantic_ranker

# ============================================================
# 测试数据集
# ============================================================

# 《修仙传》20句测试集
# 注意：paragraph是完整段落，系统会自行提取对话
XIUXIAN_TEST_CASES = [
    {
        'id': 'X01',
        'paragraph': '前方传来管事刻板的声音："孙项明！"',
        'dialogue': '孙项明！',
        'expected': '管事',
    },
    {
        'id': 'X02',
        'paragraph': '负责发放物资的是仓央洲林家的管事，一个面无表情的中年修士。"规矩都懂。出来之后，七成收获上交，林家自有灵晶丹药补偿。"',
        'dialogue': '规矩都懂。出来之后，七成收获上交，林家自有灵晶丹药补偿。',
        'expected': '管事',
    },
    {
        'id': 'X03',
        'paragraph': '管事眼皮都没抬，语气公式化。"明白。"',
        'dialogue': '明白。',
        'expected': '孙项明',
    },
    {
        'id': 'X04',
        'paragraph': '一个略显油滑的声音响起。"哟，老孙！你也来了啊！"',
        'dialogue': '哟，老孙！你也来了啊！',
        'expected': '郭垣',
    },
    {
        'id': 'X05',
        'paragraph': '孙项明回头，只见郭垣正笑嘻嘻地走过来。"郭道友。"',
        'dialogue': '郭道友。',
        'expected': '孙项明',
    },
    {
        'id': 'X06',
        'paragraph': '郭垣凑近了些，压低声音，"嘿，这次准备往哪边探？"',
        'dialogue': '嘿，这次准备往哪边探？',
        'expected': '郭垣',
    },
    {
        'id': 'X07',
        'paragraph': '孙项明心中冷笑，面上不动声色："我自知斤两，还是去老地方幽石林碰碰运气。"',
        'dialogue': '我自知斤两，还是去老地方幽石林碰碰运气。',
        'expected': '孙项明',
    },
    {
        'id': 'X08',
        'paragraph': '郭垣一拍大腿，笑得眼睛更眯了，"幽石林好啊，稳妥！"',
        'dialogue': '幽石林好啊，稳妥！',
        'expected': '郭垣',
    },
    {
        'id': 'X09',
        'paragraph': '郭垣一拍大腿，笑得眼睛更眯了，"那咱们……各凭机缘？"',
        'dialogue': '那咱们……各凭机缘？',
        'expected': '郭垣',
    },
    {
        'id': 'X10',
        'paragraph': '他最后四个字咬得有些重。"自然。"',
        'dialogue': '自然。',
        'expected': '孙项明',
    },
    {
        'id': 'X11',
        'paragraph': '他看到了——就在他刚才采集位置侧后方的几块怪石阴影下，郭垣那张圆脸上再无半点笑意，只剩下冰冷的狰狞和贪婪！"郭垣？！"',
        'dialogue': '郭垣？！',
        'expected': '孙项明',
    },
    {
        'id': 'X12',
        'paragraph': '郭垣见偷袭失败，索性不再隐藏，从阴影处走了出来，手中握着一把闪着寒光的淬毒短匕，"哼，反应倒快！"',
        'dialogue': '哼，反应倒快！',
        'expected': '郭垣',
    },
    {
        'id': 'X13',
        'paragraph': '孙项明眼中寒光一闪。既然撕破脸，唯有一战！"想要？自己来拿！"',
        'dialogue': '想要？自己来拿！',
        'expected': '孙项明',
    },
    {
        'id': 'X14',
        'paragraph': '郭垣狞笑一声，短匕化作一道毒蛇般的绿芒，直刺孙项明咽喉！"找死！"',
        'dialogue': '找死！',
        'expected': '郭垣',
    },
    {
        'id': 'X15',
        'paragraph': '郭垣找到一个破绽，毒匕划破了孙项明的左臂衣袖，衣裳撕裂，带起一溜血花，却少有痛楚，一阵麻痹感沿着伤口蔓延！"哈哈！中了老子的蛇涎毒，看你还能撑多久！"',
        'dialogue': '哈哈！中了老子的蛇涎毒，看你还能撑多久！',
        'expected': '郭垣',
    },
    {
        'id': 'X16',
        'paragraph': '郭垣早有防备，猛地甩手，又是三道乌黑的腐骨钉成品字形激射而出，彻底封死了孙项明所有可能逃脱的方向！"想跑？！"',
        'dialogue': '想跑？！',
        'expected': '郭垣',
    },
    {
        'id': 'X17',
        'paragraph': '郭垣同样被这突如其来的变故惊呆了，再次射出的三枚腐骨钉也被法坛散逸的吸力扭曲了轨迹，"什么鬼东西？！"',
        'dialogue': '什么鬼东西？！',
        'expected': '郭垣',
    },
    {
        'id': 'X18',
        'paragraph': '郭垣咬牙切齿在原地摸索半天，不得其门，又怕孙项明真活着出去乱说，一时间在那乱石林中踌躇不决。"该死的！"',
        'dialogue': '该死的！',
        'expected': '郭垣',
    },
    {
        'id': 'X19',
        'paragraph': '一股子意念从祭坛中心传递出来，被孙项明轻易捕获……或者说，这就是冲着他来的。"别看了，小子，上前来，助我摆脱封印，送你一场造化。"',
        'dialogue': '别看了，小子，上前来，助我摆脱封印，送你一场造化。',
        'expected': '前辈',
    },
    {
        'id': 'X20',
        'paragraph': '孙项明身影瞬间暴退出数十丈的距离，已经残破的法剑再次挡在身前，仅剩的神魂凝结起来，准备做殊死一搏。"谁！"',
        'dialogue': '谁！',
        'expected': '孙项明',
    },
]

# 角色库（测试集使用的所有角色）
TEST_CHARACTERS = {
    '孙项明': ('male', ['主角']),
    '郭垣': ('male', ['配角']),
    '管事': ('male', ['配角']),
    '前辈': ('male', ['配角']),
}


# ============================================================
# 测试执行引擎
# ============================================================

def create_test_environment():
    """创建测试环境（临时数据库 + 角色库）"""
    db_file = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
    db_path = db_file.name
    db_file.close()

    cm = CharacterManager(db_path=db_path)
    project_id = f'regression_test_{uuid.uuid4().hex[:8]}'

    # 预创建角色
    for name, (gender, tags) in TEST_CHARACTERS.items():
        cm.add_character(name, project_id, set(tags), gender)

    sm = SpeakerMatcher(character_manager=cm, semantic_ranker=get_semantic_ranker())
    sm._current_project_id = project_id

    return sm, db_path


def run_xiuxian_tests(sm):
    """运行《修仙传》测试集"""
    results = []
    correct = 0

    for case in XIUXIAN_TEST_CASES:
        sm.reset_activity()

        # 使用完整段落
        paragraph = case['paragraph']
        target_dialogue = case['dialogue']

        # analyze_dialogue 会提取段落中的所有对话
        analysis_results = sm.analyze_dialogue(paragraph, chapter_id=1)

        # 查找目标对话的说话人
        actual = '未知'
        for dialogue_text, speaker in analysis_results:
            if dialogue_text.strip() == target_dialogue.strip():
                actual = speaker.name if speaker else '未知'
                break

        is_correct = actual == case['expected']
        if is_correct:
            correct += 1

        results.append({
            'id': case['id'],
            'expected': case['expected'],
            'actual': actual,
            'correct': is_correct,
            'text': target_dialogue[:30],
        })

    return results, correct, len(XIUXIAN_TEST_CASES)


def print_results(results, correct, total, test_name):
    """打印测试结果"""
    print(f"\n{'='*60}")
    print(f"{test_name}")
    print(f"{'='*60}")
    print(f"准确率: {correct}/{total} ({correct/total*100:.1f}%)")
    print(f"正确: {correct} | 错误: {total - correct}")

    # 打印失败案例
    failed = [r for r in results if not r['correct']]
    if failed:
        print(f"\n失败案例明细:")
        print(f"{'ID':<6} {'期望':<8} {'实际':<12} {'对话内容'}")
        print(f"{'-'*50}")
        for r in failed:
            print(f"{r['id']:<6} {r['expected']:<8} {r['actual']:<12} {r['text']}")


def save_baseline(results, correct, total, filename='baseline_result.json'):
    """保存基线结果"""
    baseline = {
        'timestamp': datetime.now().isoformat(),
        'correct': correct,
        'total': total,
        'accuracy': correct / total,
        'results': results,
    }

    filepath = os.path.join(os.path.dirname(__file__), filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(baseline, f, ensure_ascii=False, indent=2)

    print(f"\n基线已保存到: {filepath}")
    return filepath


def load_baseline(filename='baseline_result.json'):
    """加载基线结果"""
    filepath = os.path.join(os.path.dirname(__file__), filename)
    if not os.path.exists(filepath):
        print(f"错误: 找不到基线文件 {filename}")
        print("请先运行: python regression_test.py baseline")
        return None

    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def compare_with_baseline(current_results, current_correct, current_total, baseline_data):
    """对比当前结果与基线"""
    baseline_acc = baseline_data['accuracy']
    current_acc = current_correct / current_total

    diff = current_acc - baseline_acc
    diff_pct = diff * 100

    print(f"\n{'='*60}")
    print("与基线对比")
    print(f"{'='*60}")
    print(f"基线准确率: {baseline_data['correct']}/{baseline_data['total']} ({baseline_acc*100:.1f}%)")
    print(f"当前准确率: {current_correct}/{current_total} ({current_acc*100:.1f}%)")
    print(f"变化: {diff_pct:+.1f}%", end='')

    if diff_pct > 0:
        print(" ✅ 提升")
    elif diff_pct == 0:
        print(" ➡️ 持平")
    else:
        print(" ❌ 下降")

    # 打印回归案例（基线通过但当前失败）
    baseline_passed = {r['id']: r for r in baseline_data['results'] if r['correct']}
    current_results_dict = {r['id']: r for r in current_results}
    
    regressions = []
    for case_id, baseline_result in baseline_passed.items():
        if case_id in current_results_dict:
            current_result = current_results_dict[case_id]
            if not current_result['correct']:
                regressions.append({
                    'id': case_id,
                    'baseline': baseline_result['actual'],
                    'current': current_result['actual'],
                    'expected': current_result['expected'],
                    'text': current_result['text'],
                })

    if regressions:
        print(f"\n回归案例（之前正确，现在错误）:")
        print(f"{'ID':<6} {'期望':<8} {'基线':<8} {'当前':<8} {'对话内容'}")
        print(f"{'-'*60}")
        for r in regressions:
            print(f"{r['id']:<6} {r['expected']:<8} {r['baseline']:<8} {r['current']:<8} {r['text']}")
    else:
        print(f"\n✅ 无回归案例")

    # 打印修复案例（基线失败但当前通过）
    baseline_failed = {r['id']: r for r in baseline_data['results'] if not r['correct']}
    fixes = []
    for case_id, baseline_result in baseline_failed.items():
        if case_id in current_results_dict:
            current_result = current_results_dict[case_id]
            if current_result['correct']:
                fixes.append({
                    'id': case_id,
                    'baseline': baseline_result['actual'],
                    'current': current_result['actual'],
                    'expected': current_result['expected'],
                    'text': current_result['text'],
                })

    if fixes:
        print(f"\n修复案例（之前错误，现在正确）:")
        print(f"{'ID':<6} {'期望':<8} {'基线':<12} {'当前':<12} {'对话内容'}")
        print(f"{'-'*60}")
        for r in fixes:
            print(f"{r['id']:<6} {r['expected']:<8} {r['baseline']:<12} {r['current']:<12} {r['text']}")


def main():
    if len(sys.argv) < 2:
        print("用法: python regression_test.py [baseline|current|compare]")
        print("  baseline  - 运行测试并保存为基线")
        print("  current   - 运行当前版本测试")
        print("  compare   - 对比当前结果与基线")
        sys.exit(1)

    mode = sys.argv[1]

    # 创建测试环境
    sm, db_path = create_test_environment()

    try:
        # 运行测试
        results, correct, total = run_xiuxian_tests(sm)

        # 打印结果
        print_results(results, correct, total, "《修仙传》测试集")

        # 根据模式执行不同操作
        if mode == 'baseline':
            save_baseline(results, correct, total)
            print("\n✅ 基线已保存")

        elif mode == 'current':
            print("\n✅ 当前版本测试完成")
            print("提示: 修改代码后可以再次运行此命令对比结果")

        elif mode == 'compare':
            baseline_data = load_baseline()
            if baseline_data:
                compare_with_baseline(results, correct, total, baseline_data)

    finally:
        # 清理临时数据库
        try:
            os.unlink(db_path)
        except:
            pass


if __name__ == '__main__':
    main()
