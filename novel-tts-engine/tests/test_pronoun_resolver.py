# -*- coding: utf-8 -*-
"""代词消解准确率测试集

目标：测量当前代词消解准确率的真实基线，为 T-007（代词消解强化）提供数据支持。

测试策略：
1. 构建包含不同场景的测试文本
2. 标注每个代词应该指向的真实说话人
3. 运行当前代词消解器，计算准确率
4. 分析误判案例，为 T-007 提供优化方向

测试场景覆盖：
- 场景A：单性别对话（简单）
- 场景B：双性别交替对话（中等）
- 场景C：三角色混合对话（困难）
- 场景D：长距离代词引用（困难）
- 场景E：性别冲突场景（边界）
"""

import pytest
import tempfile
import os
from pipeline.pronoun_resolver import PronounResolver, PRONOUNS
from pipeline.character_manager import CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher


class TestPronounResolverBaseline:
    """代词消解准确率基线测试"""

    @pytest.fixture
    def char_manager(self):
        """创建测试用角色管理器"""
        db_path = tempfile.mktemp(suffix='.db')
        cm = CharacterManager(db_path)
        
        # 添加测试角色
        cm.add_character('林轩', gender='male')
        cm.add_character('小翠', gender='female')
        cm.add_character('药老', gender='male')
        cm.add_character('纳兰嫣然', gender='female')
        cm.add_character('萧炎', gender='male')
        
        yield cm
        
        # 清理临时数据库
        if os.path.exists(db_path):
            os.remove(db_path)

    @pytest.fixture
    def resolver(self, char_manager):
        return PronounResolver(char_manager)

    @pytest.fixture
    def matcher(self, char_manager):
        return SpeakerMatcher(char_manager)

    # ========== 场景A: 单性别对话（简单） ==========

    def test_pronouns_exist(self):
        """验证PRONOUNS是封闭集合"""
        assert len(PRONOUNS) >= 5
        assert '他' in PRONOUNS
        assert '她' in PRONOUNS
        assert '它' in PRONOUNS
        assert PRONOUNS['他'] == 'male'
        assert PRONOUNS['她'] == 'female'

    def test_single_male_pronoun(self, resolver):
        """测试：单男性角色 + 男性代词"""
        # 文本中只有一个男性角色"林轩"和代词"他"
        text = '林轩说道："你好。"他转身离开了。'
        candidates = resolver.resolve(text)
        
        # 应该能识别到男性代词
        male_candidates = [c for c in candidates if '男性' in c[0]]
        assert len(male_candidates) >= 1

    def test_single_female_pronoun(self, resolver):
        """测试：单女性角色 + 女性代词"""
        text = '小翠笑道："知道了。"她拿起包裹走了。'
        candidates = resolver.resolve(text)
        
        female_candidates = [c for c in candidates if '女性' in c[0]]
        assert len(female_candidates) >= 1

    # ========== 场景B: 双性别交替对话（中等） ==========

    def test_two_gender_alternating(self, resolver):
        """测试：双性别交替对话中的代词消解"""
        text = '''林轩说道："你去哪里？"
小翠回应道："我去买东西。"她拿起包裹。
林轩点头道："我等你回来。"他坐在椅子上。'''
        
        candidates = resolver.resolve(text)
        
        # 应该能识别到男性和女性代词
        male_candidates = [c for c in candidates if '男性' in c[0]]
        female_candidates = [c for c in candidates if '女性' in c[0]]
        assert len(male_candidates) >= 1
        assert len(female_candidates) >= 1

    # ========== 场景C: 三角色混合对话（困难） ==========

    def test_three_characters_mixed(self, resolver):
        """测试：三角色混合对话中的代词消解"""
        text = '''萧炎说道："这件事交给我吧。"
药老点头道："你可以试试。"他捋了捋胡须。
纳兰嫣然冷声道："你们别太自信。"她转身离去。'''
        
        candidates = resolver.resolve(text)
        
        # 应该能识别到代词
        assert len(candidates) >= 2

    # ========== 场景D: 长距离代词引用（困难） ==========

    def test_long_distance_reference(self, resolver):
        """测试：长距离代词引用（超过5个说话人）"""
        text = '''林轩说道："今天天气不错。"
小翠笑道："是啊，适合出去玩。"
药老点头道："你们年轻人去吧。"
纳兰嫣然说道："我想去湖边。"
萧炎说道："我也想去。"
林轩说道："那我们走吧。"
小翠说道："好。"
药老说道："你们小心点。"
纳兰嫣然说道："知道了。"
萧炎说道："放心吧。"他拿起剑。'''
        
        # 最后一个"他"应该指向萧炎（最近的男性说话人）
        # 但当前窗口只有5，可能指向药老
        candidates = resolver.resolve(text)
        male_candidates = [c for c in candidates if '男性' in c[0]]
        assert len(male_candidates) >= 1

    # ========== 场景E: 边界案例 ==========

    def test_no_recent_speakers(self, resolver):
        """测试：无最近说话人时的处理"""
        text = '他走进来。'
        result = resolver.resolve_in_local_window('male', [])
        assert result is None

    def test_empty_text(self, resolver):
        """测试：空文本处理"""
        candidates = resolver.resolve('')
        assert len(candidates) == 0

    def test_neutral_pronoun(self, resolver):
        """测试：中性代词处理"""
        text = '它是一只猫。'
        candidates = resolver.resolve(text)
        neutral_candidates = [c for c in candidates if '未知' in c[0]]
        assert len(neutral_candidates) >= 1

    # ========== 准确率测量 ==========

    def test_measure_baseline_accuracy(self, matcher):
        """测量当前代词消解准确率基线
        
        使用 analyze_dialogue 方法测试完整的代词消解流程。
        """
        test_cases = [
            # (文本, 期望的说话人列表)
            (
                '林轩说道："你好。"他转身离开了。',
                ['林轩', '林轩']  # "他"应该指向林轩
            ),
            (
                '小翠笑道："知道了。"她拿起包裹。',
                ['小翠', '小翠']
            ),
            (
                '林轩说道："你去哪里？"小翠回应道："我去买东西。"她拿起包裹。',
                ['林轩', '小翠', '小翠']
            ),
            (
                '萧炎说道："这件事交给我吧。"药老点头道："你可以试试。"他捋了捋胡须。',
                ['萧炎', '药老', '药老']  # "他"应该指向药老
            ),
        ]
        
        correct = 0
        total = 0
        
        for text, expected_speakers in test_cases:
            results = matcher.analyze_dialogue(text)
            
            for i, (dialogue, char) in enumerate(results):
                if i < len(expected_speakers):
                    total += 1
                    if char and char.name == expected_speakers[i]:
                        correct += 1
        
        accuracy = correct / total if total > 0 else 0
        
        # 记录基线准确率（不做断言，仅用于测量）
        print(f"\n代词消解基线准确率: {accuracy:.2%} ({correct}/{total})")
        
        # 当前预期准确率约 55%（估算值）
        # 此测试仅用于记录，不强制要求通过率
        assert accuracy >= 0.0  # 总是通过，仅记录数据


class TestPronounResolverEdgeCases:
    """代词消解边界案例测试"""

    @pytest.fixture
    def char_manager(self):
        db_path = tempfile.mktemp(suffix='.db')
        cm = CharacterManager(db_path)
        cm.add_character('张三', gender='male')
        cm.add_character('李四', gender='male')
        cm.add_character('王五', gender='female')
        yield cm
        if os.path.exists(db_path):
            os.remove(db_path)

    def test_same_gender_conflict(self, char_manager):
        """测试：同性别冲突（多个男性角色）"""
        resolver = PronounResolver(char_manager)
        text = '张三说道："你好。"李四回应道："你好。"他转身离开了。'
        
        # "他"可能指向张三或李四，取决于上下文
        candidates = resolver.resolve(text)
        male_candidates = [c for c in candidates if '男性' in c[0]]
        assert len(male_candidates) >= 1

    def test_plural_pronoun(self, char_manager):
        """测试：复数代词处理"""
        resolver = PronounResolver(char_manager)
        text = '他们一起走了。'
        
        candidates = resolver.resolve(text)
        plural_candidates = [c for c in candidates if 'male_plural' in str(c)]
        assert len(candidates) >= 1

    def test_window_size_current(self, char_manager):
        """测试：当前窗口大小（5个说话人）"""
        resolver = PronounResolver(char_manager)
        
        # 创建7个说话人的序列
        speakers = ['张三', '李四', '王五', '张三', '李四', '王五', '张三']
        
        # 使用当前窗口（5）
        result = resolver.resolve_in_local_window('male', speakers)
        
        # 应该找到窗口内的男性说话人
        assert result is not None
        # 窗口内最后一个男性应该是"张三"
        # （因为窗口是5，所以看最后5个：李四, 王五, 张三, 李四, 王五, 张三 -> 倒数第5个是李四）
        # 实际上窗口是 reversed(recent_speakers[-5:])，所以从后往前找
        # 最后5个是：王五, 张三, 李四, 王五, 张三
        # 从后往前找男性：张三(7) -> 匹配
        assert result.character.name == '张三'
