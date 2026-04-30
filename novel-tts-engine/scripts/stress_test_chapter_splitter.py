import sys
import time
import random

sys.path.insert(0, r'D:\trae\novel-tts-engine')

from pipeline.chapter_splitter import ChapterSplitter, split_chapters, get_chapter_info


def generate_test_novel(num_chapters: int, content_length: int = 500) -> str:
    chapters = []
    for i in range(1, num_chapters + 1):
        title = f"第{chinese_number(i)}章 测试章节{i}"
        content = generate_content(content_length)
        chapters.append(f"{title}\n\n{content}")
    return "\n\n".join(chapters)


def chinese_number(n: int) -> str:
    digits = "零一二三四五六七八九十"
    if n <= 10:
        return digits[n]
    elif n < 20:
        return "十" + (digits[n - 10] if n > 10 else "")
    elif n < 100:
        return digits[n // 10] + "十" + (digits[n % 10] if n % 10 > 0 else "")
    else:
        return str(n)


def generate_content(length: int) -> str:
    sentences = [
        "这是一个测试句子，用于生成测试内容。",
        "故事继续发展，主角遇到了新的挑战。",
        "经过一番努力，问题终于得到了解决。",
        "时光飞逝，转眼间已经过去了很长时间。",
        "这是一个充满悬念的情节，让人期待后续发展。",
        "角色之间的对话揭示了更多细节。",
        "场景描写让读者仿佛身临其境。",
        "情节转折出乎意料，但又在情理之中。",
    ]
    result = []
    current_length = 0
    while current_length < length:
        sentence = random.choice(sentences)
        result.append(sentence)
        current_length += len(sentence)
    return "".join(result)


def run_stress_test():
    print("=" * 60)
    print("分章模块压力测试")
    print("=" * 60)
    
    test_cases = [
        (10, 500),
        (50, 500),
        (100, 500),
        (200, 500),
        (500, 500),
    ]
    
    splitter = ChapterSplitter()
    
    for num_chapters, content_length in test_cases:
        print(f"\n测试: {num_chapters}章, 每章约{content_length}字")
        
        novel = generate_test_novel(num_chapters, content_length)
        novel_length = len(novel)
        print(f"  总文本长度: {novel_length:,} 字符")
        
        start_time = time.time()
        chapters = splitter.split(novel)
        elapsed = time.time() - start_time
        
        print(f"  识别章节数: {len(chapters)}")
        print(f"  处理时间: {elapsed:.4f} 秒")
        print(f"  处理速度: {novel_length / elapsed:,.0f} 字符/秒")
        
        accuracy = len(chapters) / num_chapters * 100
        print(f"  识别准确率: {accuracy:.1f}%")
        
        if len(chapters) > 0:
            first_chapter = chapters[0]
            last_chapter = chapters[-1]
            print(f"  首章标题: {first_chapter.title}")
            print(f"  末章标题: {last_chapter.title}")
    
    print("\n" + "=" * 60)
    print("压力测试完成")
    print("=" * 60)


def test_accuracy():
    print("\n" + "=" * 60)
    print("准确性测试")
    print("=" * 60)
    
    test_patterns = [
        ("第一章", "第[一二三四五六七八九十百千万零\\d]+章"),
        ("第1章", "第[一二三四五六七八九十百千万零\\d]+章"),
        ("Chapter 1", "Chapter\\s*\\d+"),
        ("卷一", "卷[一二三四五六七八九十\\d]+"),
        ("【第一章】", "【第[一二三四五六七八九十百千万零\\d]+章】"),
    ]
    
    splitter = ChapterSplitter()
    
    for pattern_name, pattern_desc in test_patterns:
        text = f"{pattern_name}\n\n这是测试内容。\n\n{pattern_name.replace('一', '二').replace('1', '2')}\n\n这是第二部分内容。"
        chapters = splitter.split(text)
        found = len(chapters) >= 1
        status = "✓" if found else "✗"
        print(f"  {status} 模式 '{pattern_desc}': {'通过' if found else '失败'}")


if __name__ == "__main__":
    run_stress_test()
    test_accuracy()
