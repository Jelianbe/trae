import sys
sys.path.insert(0, 'd:/trae/novel-tts-engine')
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.character_manager import get_character_manager

content = """苏夜走进房间，看到老陈坐在沙发上。
"你来了。"老陈说道。
苏夜点了点头。
"事情怎么样了？"苏夜问道。
"已经安排好了。"老陈微微一笑。"""

cm = get_character_manager()
sm = SpeakerMatcher(cm)
results = sm.analyze_dialogue(content, chapter_id=1)
print(f'Dialogue results: {len(results)}')
for text, speaker in results:
    print(f'  "{text}" -> {speaker.name if speaker else "unknown"}')
