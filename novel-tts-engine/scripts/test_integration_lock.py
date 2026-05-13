# -*- coding: utf-8 -*-
"""
完整集成测试：角色库 + 锁定功能 + 分析管线

测试流程：
1. 创建临时数据库，添加测试角色
2. 测试角色库是否能正常调用（get_all_characters）
3. 测试锁定/解锁功能（lock/unlock）
4. 测试 analyze_dialogue 正确使用角色库
5. 测试旁白排除 + 角色库优先匹配
"""

import os
import sys
import tempfile
import json
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
log = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from pipeline.character_manager import get_character_manager, CharacterManager
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.nlp_basics import get_nlp


TEST_PROJECT_ID = 'test_project_lock_001'
TEST_CHAPTER_ID = 1


def setup_database() -> str:
    """创建测试数据库"""
    db_path = os.path.join(tempfile.gettempdir(), f'test_lock_{os.urandom(4).hex()}.db')
    log.info(f"[SETUP] 测试数据库: {db_path}")
    return db_path


def create_test_characters(cm: CharacterManager):
    """创建测试角色"""
    log.info("=" * 60)
    log.info("[测试1] 创建测试角色")
    log.info("=" * 60)

    characters_data = [
        ('林轩', 'male', {'林公子', '轩儿'}),
        ('小翠', 'female', {'翠儿'}),
        ('药老', 'male', {'药尊者', '老先生'}),
        ('纳兰嫣然', 'female', {'嫣然'}),
        ('萧炎', 'male', {'炎儿', '萧家小子'}),
        ('萧薰儿', 'female', {'薰儿'}),
    ]

    for name, gender, aliases in characters_data:
        char = cm.add_character(name, gender=gender, project_id=TEST_PROJECT_ID)
        for alias in aliases:
            cm.add_alias(char.id, alias)
        log.info(f"  ✅ 创建角色: {name}({gender}), 别名: {aliases}")

    # 验证角色数量
    all_chars = cm.get_all_characters(TEST_PROJECT_ID)
    assert len(all_chars) == 6, f"期望6个角色，实际{len(all_chars)}"
    log.info(f"  ✅ 角色库角色数: {len(all_chars)}")

    # 验证 get_character_by_name 能正常调用
    for name, _, _ in characters_data:
        char = cm.get_character_by_name(name, TEST_PROJECT_ID)
        assert char is not None, f"角色 {name} 未找到"
        assert char.name == name
    log.info("  ✅ get_character_by_name 正常调用")

    return all_chars


def test_lock_unlock(cm: CharacterManager):
    """测试锁定/解锁功能"""
    log.info("\n" + "=" * 60)
    log.info("[测试2] 测试锁定/解锁功能")
    log.info("=" * 60)

    # 获取药老和林轩
    yao_lao = cm.get_character_by_name('药老', TEST_PROJECT_ID)
    lin_xuan = cm.get_character_by_name('林轩', TEST_PROJECT_ID)

    # 锁定药老
    result = cm.lock_character(yao_lao.id, TEST_PROJECT_ID)
    assert result == True, f"锁定药老失败"
    log.info(f"  ✅ 锁定药老 (id={yao_lao.id})")

    # 验证锁定状态
    locked_chars = cm.get_locked_characters(TEST_PROJECT_ID)
    locked_names = [c.name for c in locked_chars]
    assert '药老' in locked_names, f"药老应该在锁定列表中，实际: {locked_names}"
    log.info(f"  ✅ get_locked_characters 返回: {locked_names}")

    # 解锁药老
    result = cm.unlock_character(yao_lao.id, TEST_PROJECT_ID)
    assert result == True, f"解锁药老失败"

    locked_chars = cm.get_locked_characters(TEST_PROJECT_ID)
    assert '药老' not in [c.name for c in locked_chars], "药老不应该在锁定列表中"
    log.info(f"  ✅ 解锁药老成功")

    # 重新锁定药老
    cm.lock_character(yao_lao.id, TEST_PROJECT_ID)
    log.info(f"  ✅ 重新锁定药老")

    # 锁定林轩
    cm.lock_character(lin_xuan.id, TEST_PROJECT_ID)
    locked_chars = cm.get_locked_characters(TEST_PROJECT_ID)
    assert len(locked_chars) == 2, f"期望2个锁定角色，实际{len(locked_chars)}"
    log.info(f"  ✅ 两个锁定角色: {[c.name for c in locked_chars]}")


def test_analyze_with_character_library(cm: CharacterManager):
    """测试分析时角色库使用"""
    log.info("\n" + "=" * 60)
    log.info("[测试3] 测试分析时角色库使用")
    log.info("=" * 60)

    sm = SpeakerMatcher(cm)

    # ===== 测试场景1：旁白排除 =====
    log.info("\n--- 场景1: 对话内容中人名不误判（旁白排除） ---")
    text1 = '"萧炎，你这丹药炼得如何？"药老捋着胡须问道。'
    results1 = sm.analyze_dialogue(text1)
    log.info(f"  输入: {text1}")
    for d, c in results1:
        log.info(f"  对话: {d} -> 说话人: {c.name if c else '未知'}")
    # 期望：说话人应该是"药老"，不是"萧炎"
    if results1:
        speaker = results1[0][1]
        if speaker:
            log.info(f"  {'✅' if speaker.name == '药老' else '❌'} 说话人: {speaker.name} (期望: 药老)")
        else:
            log.info(f"  ❌ 说话人为空 (期望: 药老)")

    # ===== 测试场景2：角色库优先匹配 =====
    log.info("\n--- 场景2: 角色库优先匹配（锁定角色最高优先级） ---")
    text2 = '药老点头道："这丹药不错。"他捋了捋胡须。'
    results2 = sm.analyze_dialogue(text2)
    log.info(f"  输入: {text2}")
    for d, c in results2:
        log.info(f"  对话: {d} -> 说话人: {c.name if c else '未知'}")
    # 药老已锁定，应优先匹配

    # ===== 测试场景3：多角色交替对话 =====
    log.info("\n--- 场景3: 多角色交替对话 ---")
    text3 = '林轩说道："这件事你怎么看？"小翠回应道："我觉得可行。"林轩点了点头。'
    results3 = sm.analyze_dialogue(text3)
    log.info(f"  输入: {text3}")
    for d, c in results3:
        log.info(f"  对话: {d} -> 说话人: {c.name if c else '未知'}")

    # ===== 测试场景4：角色库中角色在旁白中出现 =====
    log.info("\n--- 场景4: 角色库角色在旁白中出现 ---")
    text4 = '纳兰嫣然走进大殿。她冷冷扫了众人一眼。'
    sm.reset_activity()
    results4 = sm.analyze_dialogue(text4)
    log.info(f"  输入: {text4}")
    for d, c in results4:
        log.info(f"  对话: {d} -> 说话人: {c.name if c else '未知'}")

    # ===== 测试场景5：锁定角色 v.s 未锁定角色 =====
    log.info("\n--- 场景5: 锁定角色在旁白中优先于未锁定角色 ---")
    sm.reset_activity()
    # 药老已锁定，萧炎未锁定
    text5 = '萧炎和药老一起走进房间。他开口道："我们来了。"'
    results5 = sm.analyze_dialogue(text5)
    log.info(f"  输入: {text5}")
    for d, c in results5:
        log.info(f"  对话: {d} -> 说话人: {c.name if c else '未知'}")


def test_narration_extraction(cm: CharacterManager):
    """测试旁白提取"""
    log.info("\n" + "=" * 60)
    log.info("[测试4] 测试旁白提取逻辑")
    log.info("=" * 60)

    sm = SpeakerMatcher(cm)

    test_cases = [
        # (文本, 期望说话人)
        ('"你好。"林轩说道。', '林轩'),
        ('林轩说道："你好。"', '林轩'),
        ('"你好。"他说道。', None),  # 旁白为空，返回未知
    ]

    for text, expected in test_cases:
        results = sm.analyze_dialogue(text)
        speaker = results[0][1].name if results and results[0][1] else None
        status = '✅' if speaker == expected else '❌'
        log.info(f"  {status} 输入: {text}")
        log.info(f"     说话人: {speaker} (期望: {expected})")


def main():
    log.info("🚀 开始角色库+锁定功能集成测试")
    log.info(f"项目根目录: {PROJECT_ROOT}")

    db_path = setup_database()
    cm = CharacterManager(db_path)

    try:
        # 测试1：创建角色 + 验证角色库
        create_test_characters(cm)

        # 测试2：锁定/解锁
        test_lock_unlock(cm)

        # 测试3：分析管线
        test_analyze_with_character_library(cm)

        # 测试4：旁白提取
        test_narration_extraction(cm)

        log.info("\n" + "=" * 60)
        log.info("🎉 所有测试完成!")
        log.info(f"    数据库: {db_path}")
        log.info("=" * 60)

    except Exception as e:
        log.error(f"❌ 测试失败: {e}", exc_info=True)
        raise
    finally:
        if os.path.exists(db_path):
            os.remove(db_path)
            log.info(f"  🧹 临时数据库已清理: {db_path}")


if __name__ == '__main__':
    main()
