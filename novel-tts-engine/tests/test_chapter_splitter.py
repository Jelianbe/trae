import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.chapter_splitter import ChapterSplitter, split_chapters, get_chapter_info, split_with_volumes


class TestChapterSplitter:
    @pytest.fixture
    def splitter(self):
        return ChapterSplitter()

    def test_split_basic_chapters(self, splitter):
        text = """第一章 开端

这是第一章的内容，讲述了一个故事的开始。在这个章节中，我们将看到主角的初次登场。

第二章 发展

这是第二章的内容，故事开始进入正题。主角遇到了许多困难和挑战。

第三章 高潮

这是第三章的内容，故事达到了高潮部分。所有的矛盾都在这里爆发了。"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert chapters[0].title == "第一章 开端"
        assert chapters[1].title == "第二章 发展"
        assert chapters[2].title == "第三章 高潮"

    def test_split_numeric_chapter(self, splitter):
        text = """第1章 测试

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第2章 测试2

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。

第10章 测试10

这是第十章的详细内容，用于测试多位数字章节的识别能力。"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert chapters[0].title == "第1章 测试"
        assert chapters[1].title == "第2章 测试2"
        assert chapters[2].title == "第10章 测试10"

    def test_split_english_chapter(self, splitter):
        text = """Chapter 1: The Beginning

This is the first chapter with enough content to pass the minimum length requirement.

Chapter 2: The Journey

This is the second chapter with enough content to pass the minimum length requirement.

Chapter 3: The End

This is the third chapter with enough content to pass the minimum length requirement."""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert "Chapter 1" in chapters[0].title
        assert "Chapter 2" in chapters[1].title
        assert "Chapter 3" in chapters[2].title

    def test_split_bracket_chapter(self, splitter):
        text = """【第一章】序幕

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

【第二章】正篇

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 2

    def test_no_chapters(self, splitter):
        text = "这是一段没有章节标题的普通文本，长度足够被识别为独立章节。"
        chapters = splitter.split(text)
        assert len(chapters) == 1
        assert chapters[0].title == "全文"

    def test_get_chapter_count(self, splitter):
        text = """第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        count = splitter.get_chapter_count(text)
        assert count == 2

    def test_get_chapter_titles(self, splitter):
        text = """第一章 标题一

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章 标题二

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        titles = splitter.get_chapter_titles(text)
        assert len(titles) == 2
        assert titles[0] == "第一章 标题一"
        assert titles[1] == "第二章 标题二"

    def test_get_chapter_by_index(self, splitter):
        text = """第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        chapter = splitter.get_chapter_by_index(text, 0)
        assert chapter is not None
        assert chapter.title == "第一章"
        
        chapter = splitter.get_chapter_by_index(text, 10)
        assert chapter is None

    def test_get_chapter_range(self, splitter):
        text = """第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。

第三章

这是第三章的详细内容，用于测试章节范围提取功能。"""
        
        chapters = splitter.get_chapter_range(text, 0, 2)
        assert len(chapters) == 2
        assert chapters[0].title == "第一章"
        assert chapters[1].title == "第二章"

    def test_chapter_content_extraction(self, splitter):
        text = """第一章 测试

这是第一章的正文内容，应该被正确提取出来用于后续处理和分析。

第二章 测试2

这是第二章的正文内容，同样应该被正确提取出来用于后续处理和分析。"""
        
        chapters = splitter.split(text)
        assert "这是第一章的正文内容" in chapters[0].content
        assert "这是第二章的正文内容" in chapters[1].content

    def test_min_chapter_length(self):
        splitter = ChapterSplitter(min_chapter_length=20)
        text = """第一章

这段内容太短了，应该被过滤掉。

第二章

这是一段足够长的内容，超过了二十个字符的最小长度要求，应该被保留下来。"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 1
        assert "第二章" in chapters[0].title


class TestVolumeSupport:
    @pytest.fixture
    def splitter(self):
        return ChapterSplitter()

    def test_split_with_volumes(self, splitter):
        text = """卷一 风起云涌

第一章 开端

这是卷一第一章的内容，讲述了故事的开始部分，主角初次登场。

第二章 发展

这是卷一第二章的内容，故事开始进入正题，主角遇到了挑战。

卷二 波澜壮阔

第一章 新的开始

这是卷二第一章的内容，开始了新的篇章，故事进入新阶段。

第二章 继续前行

这是卷二第二章的内容，主角继续他的冒险旅程，面对新的挑战。"""
        
        structure = splitter.split_with_volumes(text)
        
        assert structure.total_volumes == 2
        assert structure.total_chapters == 4
        
        assert len(structure.volumes) == 2
        assert "卷一" in structure.volumes[0].title
        assert "卷二" in structure.volumes[1].title
        
        assert len(structure.volumes[0].chapters) == 2
        assert len(structure.volumes[1].chapters) == 2

    def test_chapter_volume_info(self, splitter):
        text = """卷一 测试卷

第一章 测试章

这是测试章节的详细内容，包含了足够的文字以满足最小长度要求。"""
        
        structure = splitter.split_with_volumes(text)
        
        assert len(structure.chapters) == 1
        chapter = structure.chapters[0]
        
        assert chapter.volume_index == 0
        assert "卷一" in chapter.volume_title

    def test_chapter_index_reset_in_new_volume(self, splitter):
        text = """卷一

第一章

这是卷一第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是卷一第二章的详细内容，同样包含了足够的文字来满足最小长度要求。

卷二

第一章

这是卷二第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是卷二第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        structure = splitter.split_with_volumes(text)
        
        vol1_chapters = structure.volumes[0].chapters
        vol2_chapters = structure.volumes[1].chapters
        
        assert vol1_chapters[0].index == 0
        assert vol1_chapters[1].index == 1
        assert vol2_chapters[0].index == 0
        assert vol2_chapters[1].index == 1

    def test_get_structure_info(self, splitter):
        text = """卷一 测试

第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

卷二 测试2

第一章

这是另一章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        info = splitter.get_structure_info(text)
        
        assert info['total_volumes'] == 2
        assert info['total_chapters'] == 2
        assert len(info['volumes']) == 2

    def test_no_volume_text(self, splitter):
        text = """第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        structure = splitter.split_with_volumes(text)
        
        assert structure.total_volumes == 1
        assert structure.total_chapters == 2
        assert structure.volumes[0].title == ""


class TestSplitChaptersFunction:
    def test_split_chapters_basic(self):
        text = """第一章

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        chapters = split_chapters(text)
        assert len(chapters) == 2

    def test_get_chapter_info(self):
        text = """第一章 标题一

这是第一章的详细内容，包含了足够的文字以满足最小长度要求。

第二章 标题二

这是第二章的详细内容，同样包含了足够的文字来满足最小长度要求。"""
        
        info = get_chapter_info(text)
        assert info['total_chapters'] == 2
