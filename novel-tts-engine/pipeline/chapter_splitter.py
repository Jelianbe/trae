import re
from typing import List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Chapter:
    index: int
    title: str
    content: str
    start_pos: int
    end_pos: int
    volume_index: int = 0
    volume_title: str = ""


@dataclass
class Volume:
    index: int
    title: str
    chapters: List[Chapter] = field(default_factory=list)
    start_pos: int = 0
    end_pos: int = 0


@dataclass
class NovelStructure:
    volumes: List[Volume] = field(default_factory=list)
    chapters: List[Chapter] = field(default_factory=list)
    total_volumes: int = 0
    total_chapters: int = 0


class ChapterSplitter:
    CHAPTER_PATTERNS = [
        re.compile(r'^第[一二三四五六七八九十百千万零\d]+[章节回卷].*$', re.MULTILINE),
        re.compile(r'^[第][0-9]+[章节回卷].*$', re.MULTILINE),
        re.compile(r'^Chapter\s*\d+.*$', re.MULTILINE | re.IGNORECASE),
        re.compile(r'^[一二三四五六七八九十\d]+[、.．].*$', re.MULTILINE),
        re.compile(r'^\d+[\.\s].*$', re.MULTILINE),
        re.compile(r'^【第[一二三四五六七八九十百千万零\d]+[章节回卷]】.*$', re.MULTILINE),
    ]
    
    VOLUME_PATTERNS = [
        re.compile(r'^卷[一二三四五六七八九十百千万零\d]+.*$', re.MULTILINE),
        re.compile(r'^【卷[一二三四五六七八九十百千万零\d]+】.*$', re.MULTILINE),
        re.compile(r'^Volume\s*\d+.*$', re.MULTILINE | re.IGNORECASE),
    ]

    def __init__(self, min_chapter_length: int = 10):
        self.min_chapter_length = min_chapter_length

    def split(self, text: str) -> List[Chapter]:
        structure = self.split_with_volumes(text)
        return structure.chapters

    def split_with_volumes(self, text: str) -> NovelStructure:
        volume_matches = self._find_volume_positions(text)
        chapter_matches = self._find_chapter_positions(text)
        
        if not chapter_matches:
            return NovelStructure(
                volumes=[Volume(index=0, title="全文", chapters=[
                    Chapter(index=0, title="全文", content=text, start_pos=0, end_pos=len(text))
                ])],
                chapters=[Chapter(index=0, title="全文", content=text, start_pos=0, end_pos=len(text))],
                total_volumes=1,
                total_chapters=1
            )
        
        if volume_matches:
            return self._split_by_volumes(text, volume_matches, chapter_matches)
        else:
            return self._split_without_volumes(text, chapter_matches)

    def _split_by_volumes(self, text: str, volume_matches: List[Tuple[str, int]], 
                          chapter_matches: List[Tuple[str, int]]) -> NovelStructure:
        volumes = []
        all_chapters = []
        
        pre_volume_chapters = []
        first_vol_start = volume_matches[0][1] if volume_matches else 0
        for ch_title, ch_start in chapter_matches:
            if ch_start < first_vol_start:
                pre_volume_chapters.append((ch_title, ch_start))
        
        if pre_volume_chapters:
            pre_volume = Volume(
                index=0,
                title="序卷",
                chapters=[],
                start_pos=0,
                end_pos=first_vol_start
            )
            for i, (ch_title, ch_start) in enumerate(pre_volume_chapters):
                if i < len(pre_volume_chapters) - 1:
                    ch_end = pre_volume_chapters[i + 1][1]
                else:
                    ch_end = first_vol_start
                
                content = self._extract_content(text, ch_start, ch_end, ch_title)
                
                if len(content) >= self.min_chapter_length:
                    chapter = Chapter(
                        index=len(pre_volume.chapters),
                        title=ch_title.strip(),
                        content=content,
                        start_pos=ch_start,
                        end_pos=ch_end,
                        volume_index=0,
                        volume_title="序卷"
                    )
                    pre_volume.chapters.append(chapter)
                    all_chapters.append(chapter)
            
            if pre_volume.chapters:
                volumes.append(pre_volume)
        
        volume_offset = len(volumes)
        
        for vol_idx, (vol_title, vol_start) in enumerate(volume_matches):
            actual_vol_idx = vol_idx + volume_offset
            if vol_idx < len(volume_matches) - 1:
                vol_end = volume_matches[vol_idx + 1][1]
            else:
                vol_end = len(text)
            
            vol_chapters_in_range = []
            for ch_title, ch_start in chapter_matches:
                if vol_start <= ch_start < vol_end:
                    vol_chapters_in_range.append((ch_title, ch_start))
            
            vol_chapters_in_range.sort(key=lambda x: x[1])
            
            vol_chapters = []
            for i, (ch_title, ch_start) in enumerate(vol_chapters_in_range):
                if i < len(vol_chapters_in_range) - 1:
                    ch_end = vol_chapters_in_range[i + 1][1]
                else:
                    ch_end = vol_end
                
                if ch_end > vol_end:
                    ch_end = vol_end
                
                content = self._extract_content(text, ch_start, ch_end, ch_title)
                
                if len(content) >= self.min_chapter_length:
                    chapter = Chapter(
                        index=len(vol_chapters),
                        title=ch_title.strip(),
                        content=content,
                        start_pos=ch_start,
                        end_pos=ch_end,
                        volume_index=actual_vol_idx,
                        volume_title=vol_title.strip()
                    )
                    vol_chapters.append(chapter)
                    all_chapters.append(chapter)
            
            volume = Volume(
                index=actual_vol_idx,
                title=vol_title.strip(),
                chapters=vol_chapters,
                start_pos=vol_start,
                end_pos=vol_end
            )
            volumes.append(volume)
        
        return NovelStructure(
            volumes=volumes,
            chapters=all_chapters,
            total_volumes=len(volumes),
            total_chapters=len(all_chapters)
        )

    def _split_without_volumes(self, text: str, chapter_matches: List[Tuple[str, int]]) -> NovelStructure:
        chapters = []
        
        for i, (title, start_pos) in enumerate(chapter_matches):
            if i < len(chapter_matches) - 1:
                end_pos = chapter_matches[i + 1][1]
            else:
                end_pos = len(text)
            
            content = self._extract_content(text, start_pos, end_pos, title)
            
            if len(content) >= self.min_chapter_length:
                chapters.append(Chapter(
                    index=len(chapters),
                    title=title.strip(),
                    content=content,
                    start_pos=start_pos,
                    end_pos=end_pos,
                    volume_index=0,
                    volume_title=""
                ))
        
        volume = Volume(
            index=0,
            title="",
            chapters=chapters,
            start_pos=0,
            end_pos=len(text)
        )
        
        return NovelStructure(
            volumes=[volume],
            chapters=chapters,
            total_volumes=1,
            total_chapters=len(chapters)
        )
    
    def _extract_content(self, text: str, start_pos: int, end_pos: int, title: str) -> str:
        line_end = text.find('\n', start_pos)
        title_len = len(title)
        
        if line_end != -1 and line_end < start_pos + title_len + 5:
            content_start = line_end + 1
        else:
            content_start = start_pos + title_len
        
        content = text[content_start:end_pos].strip()
        return content

    def _find_chapter_positions(self, text: str) -> List[Tuple[str, int]]:
        all_matches = []
        
        for pattern in self.CHAPTER_PATTERNS:
            for match in pattern.finditer(text):
                title = match.group().strip()
                start_pos = match.start()
                
                if self._is_volume_title(title):
                    continue
                
                is_duplicate = False
                for existing_title, existing_pos in all_matches:
                    if start_pos == existing_pos:
                        is_duplicate = True
                        break
                    if title == existing_title and abs(start_pos - existing_pos) < 100:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_matches.append((title, start_pos))
        
        all_matches.sort(key=lambda x: x[1])
        return all_matches

    def _find_volume_positions(self, text: str) -> List[Tuple[str, int]]:
        all_matches = []
        
        for pattern in self.VOLUME_PATTERNS:
            for match in pattern.finditer(text):
                title = match.group().strip()
                start_pos = match.start()
                
                is_duplicate = False
                for existing_title, existing_pos in all_matches:
                    if start_pos == existing_pos:
                        is_duplicate = True
                        break
                    if title == existing_title and abs(start_pos - existing_pos) < 100:
                        is_duplicate = True
                        break
                
                if not is_duplicate:
                    all_matches.append((title, start_pos))
        
        all_matches.sort(key=lambda x: x[1])
        return all_matches

    def _is_volume_title(self, title: str) -> bool:
        for pattern in self.VOLUME_PATTERNS:
            if pattern.match(title):
                return True
        return False

    def get_chapter_count(self, text: str) -> int:
        return len(self.split(text))

    def get_chapter_titles(self, text: str) -> List[str]:
        return [ch.title for ch in self.split(text)]

    def get_chapter_by_index(self, text: str, index: int) -> Optional[Chapter]:
        chapters = self.split(text)
        if 0 <= index < len(chapters):
            return chapters[index]
        return None

    def get_chapter_range(self, text: str, start: int, end: int) -> List[Chapter]:
        chapters = self.split(text)
        return chapters[start:end]

    def get_structure_info(self, text: str) -> dict:
        structure = self.split_with_volumes(text)
        return {
            'total_volumes': structure.total_volumes,
            'total_chapters': structure.total_chapters,
            'volumes': [
                {
                    'index': vol.index,
                    'title': vol.title,
                    'chapter_count': len(vol.chapters),
                    'chapters': [ch.title for ch in vol.chapters]
                }
                for vol in structure.volumes
            ]
        }


def split_chapters(text: str) -> List[Chapter]:
    splitter = ChapterSplitter()
    return splitter.split(text)


def split_with_volumes(text: str) -> NovelStructure:
    splitter = ChapterSplitter()
    return splitter.split_with_volumes(text)


def get_chapter_info(text: str) -> dict:
    splitter = ChapterSplitter()
    chapters = splitter.split(text)
    return {
        'total_chapters': len(chapters),
        'titles': [ch.title for ch in chapters],
        'lengths': [len(ch.content) for ch in chapters]
    }


def get_structure_info(text: str) -> dict:
    splitter = ChapterSplitter()
    return splitter.get_structure_info(text)
