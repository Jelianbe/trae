import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.chapter_splitter import (
    ChapterSplitter, split_chapters, split_with_volumes,
    get_chapter_info, get_structure_info, Chapter, Volume, NovelStructure
)


class TestChapterSplitter:
    @pytest.fixture
    def splitter(self):
        return ChapterSplitter()

    def test_split_chinese_chapter(self, splitter):
        text = """第一章 开端

这是第一章的内容，讲述了一个故事的开始。

第二章 发展

这是第二章的内容，故事继续发展。

第三章 高潮

这是第三章的内容，故事达到了高潮。"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert chapters[0].title == "第一章 开端"
        assert chapters[1].title == "第二章 发展"
        assert chapters[2].title == "第三章 高潮"

    def test_split_numeric_chapter(self, splitter):
        text = """第1章 测试

内容1

第2章 测试2

内容2

第10章 测试10

内容10"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert chapters[0].title == "第1章 测试"
        assert chapters[1].title == "第2章 测试2"
        assert chapters[2].title == "第10章 测试10"

    def test_split_english_chapter(self, splitter):
        text = """Chapter 1: The Beginning

This is the first chapter.

Chapter 2: The Journey

This is the second chapter.

Chapter 3: The End

This is the third chapter."""
        
        chapters = splitter.split(text)
        assert len(chapters) == 3
        assert "Chapter 1" in chapters[0].title
        assert "Chapter 2" in chapters[1].title
        assert "Chapter 3" in chapters[2].title

    def test_split_bracket_chapter(self, splitter):
        text = """【第一章】序幕

内容一

【第二章】正篇

内容二"""
        
        chapters = splitter.split(text)
        assert len(chapters) == 2

    def test_no_chapters(self, splitter):
        text = "这是一段没有章节标题的普通文本。"
        chapters = splitter.split(text)
        assert len(chapters) == 1
        assert chapters[0].title == "全文"

    def test_get_chapter_count(self, splitter):
        text = """第一章

这是第一章的内容。

第二章

这是第二章的内容。"""
        
        count = splitter.get_chapter_count(text)
        assert count == 2

    def test_get_chapter_titles(self, splitter):
        text = """第一章 标题一

内容

第二章 标题二

内容"""
        
        titles = splitter.get_chapter_titles(text)
        assert len(titles) == 2
        assert titles[0] == "第一章 标题一"
        assert titles[1] == "第二章 标题二"

    def test_get_chapter_by_index(self, splitter):
        text = """第一章

这是第一章的内容。

第二章

这是第二章的内容。"""
        
        chapter = splitter.get_chapter_by_index(text, 0)
        assert chapter is not None
        assert chapter.title == "第一章"
        
        chapter = splitter.get_chapter_by_index(text, 10)
        assert chapter is None

    def test_get_chapter_range(self, splitter):
        text = """第一章

这是第一章的内容。

第二章

这是第二章的内容。

第三章

这是第三章的内容。"""
        
        chapters = splitter.get_chapter_range(text, 0, 2)
        assert len(chapters) == 2
        assert chapters[0].title == "第一章"
        assert chapters[1].title == "第二章"

    def test_chapter_content_extraction(self, splitter):
        text = """第一章 测试

这是第一章的正文内容，应该被正确提取。

第二章 测试2

这是第二章的正文内容。"""
        
        chapters = splitter.split(text)
        assert "这是第一章的正文内容" in chapters[0].content
        assert "这是第二章的正文内容" in chapters[1].content

    def test_min_chapter_length(self):
        splitter = ChapterSplitter(min_chapter_length=20)
        text = """第一章

短内容

第二章

这是一段足够长的内容，应该被保留。"""
        
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

这是卷一第一章的内容。

第二章 发展

这是卷一第二章的内容。

卷二 波澜壮阔

第一章 新的开始

这是卷二第一章的内容。

第二章 继续前行

这是卷二第二章的内容。"""
        
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

这是测试内容。"""
        
        structure = splitter.split_with_volumes(text)
        
        assert len(structure.chapters) == 1
        chapter = structure.chapters[0]
        
        assert chapter.volume_index == 0
        assert "卷一" in chapter.volume_title

    def test_chapter_index_reset_in_new_volume(self, splitter):
        text = """卷一

第一章

这是卷一第一章。

第二章

这是卷一第二章。

卷二

第一章

这是卷二第一章。

第二章

这是卷二第二章。"""
        
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

这是测试内容。

卷二 测试2

第一章

这是测试内容。"""
        
        info = splitter.get_structure_info(text)
        
        assert info['total_volumes'] == 2
        assert info['total_chapters'] == 2
        assert len(info['volumes']) == 2

    def test_no_volume_text(self, splitter):
        text = """第一章

这是内容一。

第二章

这是内容二。"""
        
        structure = splitter.split_with_volumes(text)
        
        assert structure.total_volumes == 1
        assert structure.total_chapters == 2
        assert structure.volumes[0].title == ""


class TestSplitChaptersFunction:
    def test_split_chapters_basic(self):
        text = """第一章

这是第一章的内容。

第二章

这是第二章的内容。"""
        
        chapters = split_chapters(text)
        assert len(chapters) == 2

    def test_get_chapter_info(self):
        text = """第一章 标题一

内容一

第二章 标题二

内容二"""
        
        info = get_chapter_info(text)
        assert info['total_chapters'] == 2
        assert len(info['titles']) == 2
        assert len(info['lengths']) == 2


class TestDataclasses:
    def test_chapter_creation(self):
        chapter = Chapter(
            index=0,
            title="测试章节",
            content="测试内容",
            start_pos=0,
            end_pos=100,
            volume_index=1,
            volume_title="卷一"
        )
        assert chapter.index == 0
        assert chapter.title == "测试章节"
        assert chapter.volume_index == 1
        assert chapter.volume_title == "卷一"

    def test_volume_creation(self):
        chapter = Chapter(index=0, title="测试", content="内容", start_pos=0, end_pos=10)
        volume = Volume(
            index=0,
            title="测试卷",
            chapters=[chapter],
            start_pos=0,
            end_pos=100
        )
        assert volume.index == 0
        assert volume.title == "测试卷"
        assert len(volume.chapters) == 1

    def test_novel_structure_creation(self):
        structure = NovelStructure()
        assert structure.total_volumes == 0
        assert structure.total_chapters == 0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
