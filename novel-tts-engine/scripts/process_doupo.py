# -*- coding: utf-8 -*-
"""
《斗破苍穹》文本处理脚本
1. 使用分章系统自动分章
2. 提取前10章内容
3. 生成预标注文件
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from pipeline.chapter_splitter import ChapterSplitter
import json
import re

# 读取原文
text_file = Path(__file__).parent.parent / '《斗破苍穹》【爱上阅读_www.isyd.net】.txt'
text = text_file.read_text(encoding='utf-8')

print(f"原文大小: {len(text)} 字符")

# 使用分章系统
splitter = ChapterSplitter(min_chapter_length=10)
chapters = splitter.split(text)

print(f"检测到章节数: {len(chapters)}")
for i, ch in enumerate(chapters[:10]):
    print(f"  第{i+1}章: {ch.title} (长度: {len(ch.content)} 字符)")

# 提取前10章
first_10 = chapters[:10]

# 输出前10章到文件
output_dir = Path(__file__).parent.parent / 'tests'
output_dir.mkdir(parents=True, exist_ok=True)

output_file = output_dir / 'test_novel_doupo_ch1-10.txt'
content_parts = []
for ch in first_10:
    content_parts.append(ch.title)
    content_parts.append(ch.content.strip())

output_text = '\n\n'.join(content_parts)
output_file.write_text(output_text, encoding='utf-8')
print(f"\n前10章已保存至: {output_file}")
print(f"输出大小: {len(output_text)} 字符")

# 生成预标注文件（ground truth）
# 斗破苍穹第1-10章的关键信息
ground_truth = {
    "novel": "斗破苍穹_前10章",
    "style": "玄幻",
    "chapters": {
        "total_expected": 10,
        "volumes": 1,
        "chapter_titles": [ch.title for ch in first_10]
    },
    "entities": {
        "persons": [
            "萧炎", "萧媚", "萧薰儿", "萧战", "萧宁", "萧玉",
            "药老", "药尘", "加列毕", "加列奥", "奥托", "纳兰嫣然",
            "葛叶", "云山", "云韵"
        ],
        "speaking_persons": [
            "萧炎", "萧媚", "萧薰儿", "萧战", "萧宁", "萧玉",
            "药老", "加列毕", "加列奥", "奥托", "纳兰嫣然", "葛叶"
        ],
        "organizations": [
            "萧家", "加列家族", "云岚宗", "炼药师公会"
        ],
        "locations": [
            "乌坦城", "斗气大陆", "后山", "测验魔石碑", "广场",
            "萧家", "加列家族"
        ],
        "aliases": {
            "萧炎": ["炎儿"],
            "药老": ["药尘", "老者"],
            "萧战": ["族长", "父亲"],
            "萧薰儿": ["薰儿"],
            "纳兰嫣然": ["嫣然"]
        }
    },
    "dialogue_speakers": [
        {"text": "斗之力，三段！", "speaker": "测验魔石碑"},
        {"text": "萧炎，斗之力，三段！级别：低级！", "speaker": "中年男子"},
        {"text": "下一个，萧媚！", "speaker": "测验人"},
        {"text": "下一个，萧薰儿！", "speaker": "测试员"},
        {"text": "萧炎哥哥。", "speaker": "萧薰儿"},
        {"text": "我现在还有资格让你怎么叫么？", "speaker": "萧炎"},
        {"text": "萧炎哥哥，以前你曾经与薰儿说过，要能放下，才能拿起，提放自如，是自在人！", "speaker": "萧薰儿"},
        {"text": "呵呵，自在人？我也只会说而已，你看我现在的模样，象自在人吗？而且……这世界，本来就不属于我。", "speaker": "萧炎"},
        {"text": "萧炎哥哥，虽然并不知道你究竟是怎么回事，不过，薰儿相信，你会重新站起来，取回属于你的荣耀与尊严……", "speaker": "萧薰儿"},
        {"text": "当年的萧炎哥哥，的确很吸引人……", "speaker": "萧薰儿"},
    ],
    "sfx": {
        "sfx_words": [
            "轰", "咔嚓", "呼",
        ]
    },
    "对话分类": {
        "总对话数": 0  # 待统计
    }
}

# 统计对话数量
dialogue_count = len(re.findall(r'["「"]', output_text))
ground_truth["对话分类"]["总对话数"] = dialogue_count // 2  # 大约对话数

# 保存预标注文件
gt_file = output_dir / 'test_novel_doupo_ground_truth.json'
gt_file.write_text(json.dumps(ground_truth, ensure_ascii=False, indent=2), encoding='utf-8')
print(f"预标注文件已保存至: {gt_file}")

# 生成章节内容摘要
print("\n" + "="*80)
print("前10章内容摘要")
print("="*80)
for i, ch in enumerate(first_10):
    content_preview = ch.content[:200].replace('\n', ' ')
    print(f"\n第{i+1}章: {ch.title}")
    print(f"  长度: {len(ch.content)} 字符")
    print(f"  摘要: {content_preview}...")
