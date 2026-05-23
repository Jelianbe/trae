import re
from typing import List, Tuple, Optional


# SPEAKER_HINTS
#
# 用途：说话提示词集合，用于从文本中识别说话人提示
# 来源：中文标点规范 + 网文常见说话动词
# 边界：仅包含明确的说话/回应类提示词
# 更新日期：2026-05-14
# 维护者：内联自 speaker_hint_matcher.py
SPEAKER_HINTS = [
    '道', '说', '问', '喊', '叫', '答', '应', '笑', '叹', '怒',
    '喝', '哼', '嚷', '骂', '嘟', '喃', '吟', '斥', '骂道', '说道',
    '问道', '答道', '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
    '沉声道', '低声道', '高声道', '冷冷道', '淡淡道',
]

# 引号匹配模式
#
# 用途：识别中文引号内的对话文本
# 来源：中文标点规范 GB/T 15834-2011 规定的引号对
# 边界：仅包含标准中文引号对，不包含英文引号和特殊符号
_QUOTE_CHARS = '""\'\'「」『』'
_LEFT_QUOTES = '"「『'
_RIGHT_QUOTES = '"」』'


def _build_quote_patterns():
    """构建引号对话匹配正则

    仅捕获引号内的对话内容，不捕获引号前的前缀。
    前缀信息通过后续的位置计算获得。
    """
    patterns = []

    for lq, rq in [('「', '」'), ('『', '』'), ('"', '"'), ("'", "'")]:
        patterns.append(re.compile(
            rf'{re.escape(lq)}'
            rf'([^{re.escape(rq)}]+?)'
            rf'{re.escape(rq)}'
        ))

    return patterns


DIALOGUE_PATTERNS = _build_quote_patterns()

# SPEAKER_PATTERNS
#
# 用途：匹配"XX道"、"XX说"等格式，从"秦羽问道"中提取说话人名字"秦羽"
# 来源：中文句法结构（主语+谓语+引语），网文常见说话模式统计
# 边界：仅匹配"说话"类动词，不匹配"思考"类动词
#       名字长度限制1-12字，覆盖中文人名和长外国名（亚历山大·尼古拉耶维奇）
#       支持中点·以兼容外国名（哈利·波特）
# 更新日期：2026-05-23（修复：复合动词优先→X对Y说→单字兜底）
# 维护者：pipeline/matchers/speaker_hint_matcher.py
# 注意：按动词长度降序排列（长匹配优先），避免"问道"被"问"+"道"截断
#       长度从{1,6}→{1,12}→{1,20}以兼容超长外国名（2026-05-23 去上限{1,12}→{1,20}）
SPEAKER_PATTERNS = [
    # P0: X对Y说 → 只捕获 X（X对Y说中的X是说话人）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*对[\u4e00-\u9fa5\u2027·]{1,6}\s*(?:道|说|问)[：:，,。\s]'),
    # P1: 复合动词（4字+优先）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:回答说|喃喃道|催促道|大叫道|大喊道|大声喊道|回答道|回应道|询问道|自言自语|低声道|高声道|沉声道|冷冷道|淡淡道|厉声道|轻声道|轻声说|轻声地说|急切地喊道|小心翼翼地说|小心翼翼道)[：:，,。\s]'),
    # P2: 双字动词
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:问道|答道|笑道|叹道|怒道|喝道|哼道|嚷道|骂道|说道|叫道)[：:，,。\s]'),
    # P3: 单字动词（最后的兜底，仅保留高频独立使用的单字）
    re.compile(r'([\u4e00-\u9fa5\u2027·]{1,20})\s*(?:道|说|问|叫|答|应|笑|叹)[：:，,。\s]'),
]


def _clean_speaker_name(name: str, nlp=None) -> str:
    if not name:
        return name

    cleaned_by_fallback = name
    SPEECH_VERBS = [
        '冷冷道', '淡淡道', '沉声道', '低声道', '高声道',
        '说道', '问道', '答道', '笑道', '叹道', '怒道', '喝道', '哼道', '嚷道',
        '骂道', '回应道', '回答道', '接道', '续道',
        '轻声道', '低声说', '轻声说', '沉声说', '厉声道', '笑着道', '笑着说', '大叫道',
        '笑着',
        '道', '说', '问', '喊', '叫', '答', '应', '笑', '叹', '怒',
        '喝', '哼', '嚷', '骂', '回',
    ]
    for verb in sorted(SPEECH_VERBS, key=len, reverse=True):
        if cleaned_by_fallback.endswith(verb) and len(cleaned_by_fallback) > len(verb):
            cleaned_by_fallback = cleaned_by_fallback[:-len(verb)]
            break

    if cleaned_by_fallback.endswith('地') and len(cleaned_by_fallback) > 1:
        cleaned_by_fallback = cleaned_by_fallback[:-1]

    return cleaned_by_fallback


class SpeakerHintMatcher:
    """说话人提示词匹配器"""

    def __init__(self, name_validator, nlp=None):
        self.name_validator = name_validator
        self.nlp = nlp

    def extract_speaker_hint(self, text: str) -> Tuple[Optional[str], str]:
        if not text:
            return None, 'none'

        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(text)
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name, 'explicit_hint'

        for pattern in DIALOGUE_PATTERNS:
            for match in pattern.finditer(text):
                start = match.start()
                prefix = text[max(0, start - 30):start].strip()
                for sp in SPEAKER_PATTERNS:
                    pm = sp.search(prefix)
                    if pm:
                        name = _clean_speaker_name(pm.group(1).strip(), self.nlp)
                        if self.name_validator.is_valid_speaker_candidate(name):
                            return name, 'prefix_hint'

        return None, 'none'

    def extract_speech_patterns(self, text: str) -> List[Tuple[str, str]]:
        if not text:
            return []

        results = []
        for pattern in SPEAKER_PATTERNS:
            for match in pattern.finditer(text):
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                hint = match.group(0).strip()
                if self.name_validator.is_valid_speaker_candidate(name):
                    results.append((name, hint))

        return results

    def extract_post_dialogue_hint(self, suffix: str) -> Optional[str]:
        if not suffix:
            return None

        for pattern in SPEAKER_PATTERNS:
            match = pattern.search(suffix[:50])
            if match:
                name = _clean_speaker_name(match.group(1).strip(), self.nlp)
                if self.name_validator.is_valid_speaker_candidate(name):
                    return name

        return None

    def _is_address_pattern(self, text: str, prefix: str) -> bool:
        if not prefix:
            return False

        address_patterns = [
            re.compile(r'([\u4e00-\u9fa5]{2,6})[，,、\s]'),
            re.compile(r'([\u4e00-\u9fa5]{2,6})(?:啊|呀|呢|吧)[！!？?]?'),
        ]

        for pattern in address_patterns:
            match = pattern.search(prefix)
            if match:
                name = match.group(1).strip()
                if self.name_validator.is_valid_speaker_candidate(name):
                    return True

        return False
