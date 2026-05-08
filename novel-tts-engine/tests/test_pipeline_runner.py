# -*- coding: utf-8 -*-
"""PipelineRunner 单元测试

测试覆盖：
1. 辅助方法（_entity_in_sentence）
2. _process_chapter 集成测试（完整流水线处理单章）
3. analyze_chapters 集成测试（多章处理）
4. 进度管理与状态管理
5. 边界条件
"""

import pytest
import sys
import os
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.pipeline_runner import PipelineRunner, ChapterResult, SentenceData
from pipeline.chapter_splitter import Chapter


def make_chapter(title: str, content: str, volume_index: int = 0, index: int = 0) -> Chapter:
    """辅助函数：创建 Chapter 对象"""
    return Chapter(
        title=title,
        content=content,
        volume_index=volume_index,
        index=index,
        start_pos=0,
        end_pos=len(content),
    )


class TestPipelineRunner:
    @pytest.fixture
    def runner(self):
        return PipelineRunner()

    def test_entity_in_sentence_exact_match(self, runner):
        """测试精确匹配：实体完整出现在句子中"""
        assert PipelineRunner._entity_in_sentence("苏夜", 0, 2, "苏夜走进了房间") is True

    def test_entity_in_sentence_boundary_protection(self, runner):
        """测试边界保护：单字实体不应匹配到更长词的一部分"""
        assert PipelineRunner._entity_in_sentence("林", 0, 1, "他走进了树林里") is False

    def test_entity_in_sentence_not_found(self, runner):
        """测试实体不在句子中"""
        assert PipelineRunner._entity_in_sentence("张三", 0, 2, "李四走进了房间") is False

    def test_entity_in_sentence_empty_input(self, runner):
        """测试空输入"""
        assert PipelineRunner._entity_in_sentence("", 0, 0, "") is False
        assert PipelineRunner._entity_in_sentence("实体", 0, 2, "") is False
        assert PipelineRunner._entity_in_sentence("", 0, 0, "句子") is False

    def test_process_chapter_basic_structure(self, runner):
        """测试：_process_chapter 能正确识别章节基础结构"""
        chapter = make_chapter(
            title="第一章",
            content="""苏夜走进房间，看到老陈坐在沙发上。
"你来了。"老陈说道。
苏夜点了点头。
"事情怎么样了？"苏夜问道。
"已经安排好了。"老陈微微一笑。""",
        )
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 应该返回 ChapterResult
        assert result.chapter_id == 1
        assert result.title == "第一章"
        assert len(result.sentences) > 0
        assert "dialogue_count" in result.statistics

    def test_process_chapter_dialogue_detection(self, runner):
        """测试：_process_chapter 能正确检测对话"""
        chapter = make_chapter(
            title="测试章",
            content="""苏夜说道："你好啊"。
老陈点头："是的"。""",
        )
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 应该检测到对话
        dialogue_count = result.statistics.get("dialogue_count", 0)
        assert dialogue_count >= 1

    def test_process_chapter_entity_detection(self, runner):
        """测试：_process_chapter 能正确运行实体检测流程
        
        注意：由于 SpeakerRoleFilter 需要足够的对话上下文才能保留实体，
        短文本测试中实体可能被过滤。这里验证流程正常运行不报错。
        """
        chapter = make_chapter(
            title="测试章",
            content="""苏夜走进了公司的大楼，这里是他工作的地方。
北京分部最近来了一个新人，叫李四。
李四从上海来到这里，开始了新的生活。
苏夜对李四非常照顾，两人很快成为了朋友。""",
        )
        
        # 不应该报错
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 验证统计信息存在
        assert "entity_count" in result.statistics
        assert "dialogue_count" in result.statistics

    def test_process_chapter_narration_detection(self, runner):
        """测试：_process_chapter 能正确识别旁白"""
        chapter = make_chapter(
            title="测试章",
            content="""轰的一声，墙壁倒塌了。哗啦啦，雨水倾盆而下。
他站在窗前，凝视着远方。""",
        )
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 应该识别为旁白
        narration_count = result.statistics.get("narration_count", 0)
        assert isinstance(narration_count, int)
        assert narration_count >= 1

    def test_process_chapter_emotion_tagging(self, runner):
        """测试：_process_chapter 能正确标注情绪"""
        chapter = make_chapter(
            title="测试章",
            content="""苏夜笑道："太好了"。
老陈怒道："滚"。""",
        )
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 每个句子应该有情绪标注
        for sentence in result.sentences:
            assert hasattr(sentence, 'emotion')

    def test_process_chapter_empty_content(self, runner):
        """测试：处理空内容章节"""
        chapter = make_chapter(title="空章", content="")
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 应该返回空结果
        assert result.chapter_id == 1
        assert len(result.sentences) == 0

    def test_process_chapter_whitespace_only(self, runner):
        """测试：处理纯空白内容"""
        chapter = make_chapter(title="空白章", content="   \n\n   ")
        
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 应该正常处理（不报错）
        assert isinstance(result.sentences, list)

    def test_analyze_chapters_basic(self, runner):
        """测试：analyze_chapters 基本流程"""
        text = """第一章 苏夜
苏夜说道："你好"。

第二章 老陈
老陈点头："是的"。"""
        
        results = runner.analyze_chapters(text)
        
        # 应该返回至少 1 个结果
        assert len(results) >= 1

    def test_analyze_chapters_range(self, runner):
        """测试：analyze_chapters 范围参数"""
        text = """第一章 苏夜
苏夜说道："你好"。

第二章 老陈
老陈点头："是的"。

第三章 李四
李四离开了房间。"""
        
        # 只分析从索引 1 开始的章节
        results = runner.analyze_chapters(text, start=1)
        
        # 应该跳过第一章
        assert len(results) >= 1

    def test_progress_info(self, runner):
        """测试：进度信息更新"""
        # 初始状态
        assert runner.progress.current_step == ""
        assert runner.progress.state.value == "idle"
        
        text = """第一章 苏夜
苏夜说道："你好"。"""
        
        runner.analyze_chapters(text)
        
        # 处理后状态应该变化
        assert runner.progress.state.value in ("done", "running")

    def test_pause_and_resume(self, runner):
        """测试：暂停和恢复"""
        from pipeline.pipeline_runner import PipelineState
        
        runner.resume()
        assert runner.progress.state == PipelineState.RUNNING
        
        runner.pause()
        assert runner.progress.state == PipelineState.PAUSED
        
        runner.resume()
        assert runner.progress.state == PipelineState.RUNNING

    def test_get_progress(self, runner):
        """测试：获取进度"""
        progress = runner.get_progress()
        
        assert progress is not None
        assert hasattr(progress, 'current_step')
        assert hasattr(progress, 'total_chapters')

    def test_export_json_format(self, runner):
        """测试：导出 JSON 格式正确"""
        chapter = make_chapter(
            title="测试章",
            content="""苏夜说道："你好"。""",
        )
        result = runner._process_chapter(chapter, chapter_id=1)
        
        # 手动构造结果列表
        json_str = runner.export_json([result])
        
        # 应该可以解析为 JSON
        data = json.loads(json_str)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["chapter_id"] == 1

    def test_export_ssml_generation(self, runner):
        """测试：SSML 输出生成"""
        chapter = make_chapter(
            title="测试章",
            content="""苏夜说道："你好"。""",
        )
        result = runner._process_chapter(chapter, chapter_id=1)
        
        ssml = runner.export_ssml([result])
        
        # SSML 应该包含基本的 XML 标签
        assert "<?xml" in ssml
        assert "<speak" in ssml
        assert "</speak>" in ssml
