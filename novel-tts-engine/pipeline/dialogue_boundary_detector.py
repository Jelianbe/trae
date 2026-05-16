# -*- coding: utf-8 -*-
"""对话边界检测器 — 区分真实对话与非对话引号内容

用途：判断引号内的文本是真实对话还是非对话内容（地名、物品名、拟声词、
内心独白、书本引用、碑文等）。

来源：
- 现代汉语句法结构（言说动词与引语的依存关系）
- 中文网文引号使用模式统计
- GB/T 15834-2011 中文标点规范（引号的多种用法）

设计原则：
1. 说话动词来自 speech_verb_detector（唯一权威源），不使用静态白名单
2. 基于语言学和结构特征判断，不依赖硬编码词表
3. 高置信度过滤非对话，不确定时默认放行（交给 speaker_matcher + LLM 兜底）

策略说明：
策略1 - 说话动词锚定：检查引号前后 15 字内是否存在说话动词
策略2 - 引号内容结构分析：纯名词短语、单字+叹号、无标点的单词应抑制
策略3 - 引号模式抑制：书本/碑文/书信等引用模式应抑制

边界：
  - 策略1：说话动词窗口为引号前后各 15 个字符
  - 策略2：内容长度 < 3 字且无标点符号，视为非对话
  - 策略3：书名号、引号与特定关键词组合时触发抑制
  - 三种策略任一命中即判定为非对话
  - 不处理嵌套引号（嵌套引号由外层决定）

更新日期：2026-05-13
维护者：对话边界检测器方案
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pipeline.speaker_matcher import ALL_SPEECH_VERBS
from utils.config import SPEECH_VERB_ANCHOR_WINDOW


@dataclass
class QuoteInfo:
    """引号内容信息"""
    text: str                    # 引号内的纯文本（不含引号）
    full_text: str               # 包含引号的完整文本
    quote_type: str              # 引号类型: 「」、『』、""、""
    start_pos: int               # 在原文中的起始位置（含左引号）
    end_pos: int                 # 在原文中的结束位置（含右引号）
    context_before: str = ""     # 引号前的上下文
    context_after: str = ""      # 引号后的上下文


@dataclass
class DialogueBoundaryResult:
    """对话边界检测结果"""
    quote_info: QuoteInfo
    is_dialogue: bool            # 是否为真实对话
    confidence: float            # 置信度 0.0 ~ 1.0
    reasons: List[str] = field(default_factory=list)     # 判定为对话的理由
    suppression_reasons: List[str] = field(default_factory=list)  # 判定为非对话的理由


# ============================================================
# 常量定义
# ============================================================

# 说话动词锚定窗口大小（引号前后各 N 个字符）
# 已从 utils.config.SPEECH_VERB_ANCHOR_WINDOW 导入
# 来源：经验值（中文网文对话通常在引号前后15字内出现说话人标记）
# 边界：过小会漏检，过大会误匹配无关文本
ANCHOR_WINDOW = SPEECH_VERB_ANCHOR_WINDOW

# _QUOTE_TYPES
#
# 用途：中文引号类型识别（用于提取引号内容）
# 来源：GB/T 15834-2011 标点符号用法——引号规范
# 边界：
#   - 包含中文全角引号（「」『』""）和Unicode弯引号
#   - 不包含英文半角引号（'）因为中文网文不用单引号
# 更新日期：2026-05-13
# 维护者：项目规则
_QUOTE_TYPES = [
    ('「', '」', '「」'),
    ('『', '』', '『』'),
    ('"', '"', '""'),
    ('\u201c', '\u201d', '""'),
]

# 构建说话动词正则（按长度降序，确保长词优先匹配）
_SPEECH_VERB_PATTERN = re.compile(
    '(?:' + '|'.join(re.escape(v) for v in sorted(ALL_SPEECH_VERBS, key=len, reverse=True)) + ')'
)

# _BOOK_QUOTE_KEYWORDS
#
# 用途：检测书本/碑文/书信引用模式（非实时对话）
# 来源：中文语言学引用标记词 + 网文高频非对话模式统计
# 边界：
#   - 包含书写类（写着/记载）、载体类（碑文/信中）、诵读类（背诵/朗读）
#   - 不包含实时说话动词（说/道/问）
# 更新日期：2026-05-13
# 维护者：项目规则
_BOOK_QUOTE_KEYWORDS = [
    '写着', '写道', '记载', '刻着', '刻有',
    '书上', '碑文', '信中', '纸条', '日记', '笔记',
    '名言', '格言', '警句', '谚语', '俗语',
    '标题', '扉页', '序言', '跋', '题词',
    '吟诵', '念道', '默念', '背诵', '朗读',
    '古籍', '古卷', '玉简', '典籍', '经书',
    '匾额', '对联', '牌匾', '石碑', '石刻',
]

# 策略3：书本引用模式正则
# 匹配模式：「...写着...」、「碑文：...」、「信中写道：...」
_BOOK_QUOTE_PATTERNS = [
    # 模式1：[关键词] + [冒号/逗号] + 引号
    # 例："石碑上写着：「...」"
    re.compile(
        r'(?:' + '|'.join(re.escape(kw) for kw in _BOOK_QUOTE_KEYWORDS) + r')\s*[：:，,]?\s*'
    ),
    # 模式2：引号 + [关键词] + [的] + [名词]
    # 例：「...」这句话刻在石碑上
    re.compile(
        r'[」"』]\s*(?:的)?(?:这句话|这行字|这些字|此句|此诗|此词)\s*'
        r'(?:刻|写|留|题|录|记|载)'
    ),
]

# 策略2：纯名词短语模式
# 匹配：纯汉字词组（无动词、无标点、无语气词）
_PURE_NOUN_PHRASE_PATTERN = re.compile(
    r'^[\u4e00-\u9fa5·\-—~～]{1,10}$'
)

# 策略2：单字 + 叹号模式（拟声词/惊呼）
# 匹配：单个汉字 + 叹号，如「杀！」、「走！」
_SINGLE_CHAR_EXCLAIM_PATTERN = re.compile(
    r'^[\u4e00-\u9fa5][！!]+$'
)

# 策略2：无标点的单/双字词（物品名/地名）
# 匹配：1-2 个汉字，无任何标点
_SINGLE_WORD_PATTERN = re.compile(
    r'^[\u4e00-\u9fa5]{1,2}$'
)

# _PROPER_NOUN_SUFFIXES
#
# 用途：识别专有名词（地名/建筑/物品名），用于判断引号内容是否为对话
# 来源：中文地名/建筑/物品命名模式——后缀词体系
# 边界：
#   - 包含建筑类（阁/楼/殿/宫/府/院）、地理类（峰/山/谷/湖/海）
#   - 包含组织类（宗/门/派/帮/教/会）、武器类（剑/刀/枪/弓/盾）
#   - 包含修仙类（丹/药/符/阵/诀/功/法）、典籍类（图/卷/册/谱）
#   - 不应往里加：动词/形容词/副词
# 更新日期：2026-05-13
# 维护者：项目规则
_PROPER_NOUN_SUFFIXES = [
    '阁', '楼', '殿', '宫', '府', '院', '庄', '堡', '城', '关',
    '峰', '山', '谷', '崖', '洞', '渊', '潭', '湖', '海', '江',
    '宗', '门', '派', '帮', '教', '会', '盟', '寨', '村', '镇',
    '剑', '刀', '枪', '棍', '杖', '弓', '箭', '盾', '甲', '袍',
    '丹', '药', '符', '阵', '诀', '功', '法', '术', '技',
    '图', '卷', '册', '谱', '录', '鉴', '碑', '印', '镜', '珠',
]


# ============================================================
# 核心检测器类
# ============================================================

class DialogueBoundaryDetector:
    """对话边界检测器

    使用多种策略判断引号内容是否为真实对话。

    使用示例：
        >>> detector = DialogueBoundaryDetector()
        >>> text = '他笑道：「你好啊。」'
        >>> results = detector.detect_all(text)
        >>> for r in results:
        ...     print(r.is_dialogue, r.quote_info.text)
        True 你好啊。
    """

    def __init__(
        self,
        anchor_window: int = ANCHOR_WINDOW,
        enable_strategy1: bool = True,
        enable_strategy2: bool = True,
        enable_strategy3: bool = True,
    ):
        """初始化检测器

        Args:
            anchor_window: 说话动词锚定窗口大小（字符数）
            enable_strategy1: 是否启用说话动词锚定策略
            enable_strategy2: 是否启用引号内容结构分析策略
            enable_strategy3: 是否启用引号模式抑制策略
        """
        self.anchor_window = anchor_window
        self.enable_strategy1 = enable_strategy1
        self.enable_strategy2 = enable_strategy2
        self.enable_strategy3 = enable_strategy3

    def detect_all(self, text: str) -> List[DialogueBoundaryResult]:
        """检测文本中所有引号内容的对话属性

        Args:
            text: 完整文本

        Returns:
            检测结果列表，按引号出现顺序排列
        """
        if not text:
            return []

        quotes = self._extract_all_quotes(text)
        results = []

        for quote_info in quotes:
            result = self._detect_single(quote_info, text)
            results.append(result)

        return results

    def is_dialogue(self, text: str, quote_text: str) -> bool:
        """判断指定引号内容是否为真实对话（简化接口）

        Args:
            text: 完整文本
            quote_text: 引号内的文本（不含引号）

        Returns:
            是否为真实对话
        """
        if not text or not quote_text:
            return False

        # 找到引号在文本中的位置
        for left_q, right_q, _ in _QUOTE_TYPES:
            full_quote = left_q + quote_text + right_q
            pos = text.find(full_quote)
            if pos >= 0:
                quote_info = QuoteInfo(
                    text=quote_text,
                    full_text=full_quote,
                    quote_type=left_q + right_q,
                    start_pos=pos,
                    end_pos=pos + len(full_quote),
                    context_before=text[max(0, pos - 50):pos],
                    context_after=text[pos + len(full_quote):pos + len(full_quote) + 50],
                )
                result = self._detect_single(quote_info, text)
                return result.is_dialogue

        # 如果找不到完整引号，使用默认逻辑
        return True

    def _extract_all_quotes(self, text: str) -> List[QuoteInfo]:
        """提取文本中所有引号内容"""
        quotes = []

        for left_q, right_q, qtype in _QUOTE_TYPES:
            start = 0
            while True:
                left_pos = text.find(left_q, start)
                if left_pos == -1:
                    break

                # 处理左右引号相同的情况（英文双引号）
                if left_q == right_q:
                    # 找配对的结束引号
                    depth = 1
                    pos = left_pos + 1
                    while pos < len(text) and depth > 0:
                        if text[pos] == right_q:
                            depth -= 1
                            if depth == 0:
                                break
                        elif text[pos] == left_q:
                            depth += 1
                        pos += 1
                    right_pos = pos if depth == 0 else -1
                else:
                    right_pos = text.find(right_q, left_pos + 1)

                if right_pos == -1:
                    break

                quote_text = text[left_pos + 1:right_pos]
                quote_info = QuoteInfo(
                    text=quote_text,
                    full_text=text[left_pos:right_pos + 1],
                    quote_type=qtype,
                    start_pos=left_pos,
                    end_pos=right_pos + 1,
                    context_before=text[max(0, left_pos - 50):left_pos],
                    context_after=text[right_pos + 1:right_pos + 51],
                )
                quotes.append(quote_info)
                start = right_pos + 1

        # 按位置排序，去重
        quotes.sort(key=lambda q: q.start_pos)
        return self._deduplicate_quotes(quotes)

    def _deduplicate_quotes(self, quotes: List[QuoteInfo]) -> List[QuoteInfo]:
        """去重引号（重叠的引号只保留一个）"""
        if not quotes:
            return []

        result = []
        last_end = -1

        for q in quotes:
            if q.start_pos >= last_end:
                result.append(q)
                last_end = q.end_pos

        return result

    def _detect_single(self, quote_info: QuoteInfo, full_text: str) -> DialogueBoundaryResult:
        """检测单个引号内容
        
        判定逻辑（修改后）：
        - 不轻易判定为非对话。只有明确拟声词或地名引用才判非对话。
        - 其余情况全部放行，交给 speaker_matcher + LLM 兜底。
        """
        result = DialogueBoundaryResult(
            quote_info=quote_info,
            is_dialogue=True,
            confidence=0.8,
        )

        score = 0.0
        max_score = 0.0

        # 特殊处理：空引号内容直接判定为非对话
        if not quote_info.text.strip():
            result.is_dialogue = False
            result.confidence = 0.0
            result.suppression_reasons.append("引号内容为空")
            return result

        # 策略1：说话动词锚定（决定性信号）
        if self.enable_strategy1:
            s1_score, s1_reasons, s1_suppressions = self._strategy1_speech_verb_anchor(
                quote_info, full_text
            )
            score += s1_score
            max_score += 1.0
            result.reasons.extend(s1_reasons)
            result.suppression_reasons.extend(s1_suppressions)

        # 策略2：内容结构分析
        if self.enable_strategy2:
            s2_score, s2_reasons, s2_suppressions = self._strategy2_content_structure(
                quote_info
            )
            score += s2_score
            max_score += 1.0
            result.reasons.extend(s2_reasons)
            result.suppression_reasons.extend(s2_suppressions)

        # 策略3：引号模式抑制
        if self.enable_strategy3:
            s3_score, s3_reasons, s3_suppressions = self._strategy3_quote_pattern_suppression(
                quote_info, full_text
            )
            score += s3_score
            max_score += 1.0
            result.reasons.extend(s3_reasons)
            result.suppression_reasons.extend(s3_suppressions)

        # 计算最终结果
        if max_score > 0:
            result.confidence = max(0.0, min(1.0, score / max_score))

        # 判定逻辑（修改后）：
        # 不轻易判定为非对话。只有以下情况才判非对话：
        # 1. 空引号内容（已在前面处理）
        # 2. 明确拟声词（策略2-检查4：单字+叹号）且无其他支持信号
        # 3. 明确地名引用（策略2-检查3：纯名词+专有后缀）且无标点、无语气词
        #
        # 其余情况全部放行，交给 speaker_matcher + LLM 兜底

        is_onomatopoeia = any("拟声" in r for r in result.suppression_reasons)
        is_place_name = any("物品/地名" in r for r in result.suppression_reasons)
        is_pure_noun_phrase = any("纯名词短语" in r for r in result.suppression_reasons)

        # 如果是单字+叹号模式（"嗤！"、"噗！"、"谁！"），
        # 句子结束标点和策略1后锚定的支持信号不予考虑
        text = quote_info.text.strip()
        is_single_exclaim = bool(_SINGLE_CHAR_EXCLAIM_PATTERN.match(text))
        reasons_to_ignore = set()
        if is_single_exclaim:
            reasons_to_ignore.add('策略2：含句子结束标点，倾向于对话')
            reasons_to_ignore.add('策略1-后锚定')
        effective_reasons = [
            r for r in result.reasons
            if not any(r.startswith(prefix) for prefix in reasons_to_ignore)
        ]
        has_support = len(effective_reasons) > 0

        if is_onomatopoeia and not has_support:
            result.is_dialogue = False
            result.confidence = 0.2
        elif is_place_name and not has_support:
            result.is_dialogue = False
            result.confidence = 0.3
        elif is_pure_noun_phrase and not has_support:
            result.is_dialogue = False
            result.confidence = 0.3
        else:
            # 其余情况全部放行，交给 speaker_matcher + LLM 兜底
            result.is_dialogue = True
            result.confidence = max(result.confidence, 0.5)

        return result

    def _strategy1_speech_verb_anchor(
        self,
        quote_info: QuoteInfo,
        full_text: str,
    ) -> Tuple[float, List[str], List[str]]:
        """策略1：说话动词锚定

        检查引号前后 N 个字符内是否存在说话动词。
        说话动词在引号前：通常是"XX道：「...」"
        说话动词在引号后：通常是"「...」XX道"

        Returns:
            (score, reasons, suppression_reasons)
        """
        reasons = []
        suppressions = []
        score = 0.0

        # 提取引号前后窗口
        before_window = quote_info.context_before[-self.anchor_window:]
        after_window = quote_info.context_after[:self.anchor_window]

        # 检查引号前窗口（从后往前找最近的说话动词）
        before_verb = None
        before_verb_end = 0
        for verb in sorted(ALL_SPEECH_VERBS, key=len, reverse=True):
            pos = before_window.rfind(verb)
            if pos >= 0:
                before_verb = verb
                before_verb_end = pos + len(verb)
                break

        if before_verb:
            # 检查动词和引号之间是否有冒号/逗号分隔（更可能是对话）
            between_text = before_window[before_verb_end:]
            # 动词必须在窗口后半部分（靠近引号），避免匹配远处的无关动词
            if len(between_text) <= 10:
                if re.search(r'[：:，,]\s*$', between_text):
                    score += 1.0
                    reasons.append(f"策略1-前锚定：说话动词'{before_verb}'+标点指向引号")
                elif between_text.strip() == '':
                    # 说话动词紧挨引号（如"笑道「...」"）也是强信号
                    score += 1.0
                    reasons.append(f"策略1-前锚定：说话动词'{before_verb}'紧挨引号")
                else:
                    score += 0.7
                    reasons.append(f"策略1-前锚定：说话动词'{before_verb}'在引号前{len(between_text)}字内")

        # 检查引号后窗口（从前往后找最近的说话动词）
        after_verb = None
        after_verb_start = len(after_window)
        for verb in sorted(ALL_SPEECH_VERBS, key=len, reverse=True):
            pos = after_window.find(verb)
            if pos >= 0 and pos < after_verb_start:
                after_verb = verb
                after_verb_start = pos

        if after_verb:
            between_text = after_window[:after_verb_start]
            # 动词必须在窗口前半部分（靠近引号）
            if len(between_text) <= 10:
                # 后锚定的说话动词可能是为后面的引号服务的，所以只给弱信号
                if re.search(r'^\s*[，,]', between_text):
                    score += 0.5
                    reasons.append(f"策略1-后锚定：引号后+说话动词'{after_verb}'")
                else:
                    score += 0.3
                    reasons.append(f"策略1-后锚定：说话动词'{after_verb}'在引号后{len(between_text)}字内")

        # 如果窗口内无说话动词，不扣分，不加抑制标签
        # 理由：15字窗口在网文语境下过短，说话动词经常距离引号较远。
        # 此策略只做加分（有动词=强信号），不做减分（无动词≠非对话）。
        if not before_verb and not after_verb:
            score += 0.3

        return score, reasons, suppressions

    def _strategy2_content_structure(
        self,
        quote_info: QuoteInfo,
    ) -> Tuple[float, List[str], List[str]]:
        """策略2：引号内容结构分析

        分析引号内文本的语言结构特征：
        - 纯名词短语（无动词/无标点）：倾向于非对话
        - 单字+叹号（拟声词/惊呼）：倾向于非对话
        - 单/双字词无标点（物品名/地名）：倾向于非对话
        - 含完整句子结构（有标点/语气词）：倾向于对话

        Returns:
            (score, reasons, suppression_reasons)
        """
        reasons = []
        suppressions = []
        text = quote_info.text.strip()
        score = 0.5  # 默认中性分数

        if not text:
            score = 0.0
            suppressions.append("策略2：引号内容为空")
            return score, reasons, suppressions

        # 检查1：含句子结束标点（是对话的强信号）
        has_sentence_end = bool(re.search(r'[。！？；]', text))
        if has_sentence_end:
            score += 0.3
            reasons.append("策略2：含句子结束标点，倾向于对话")

        # 检查2：含语气词（是对话的信号）
        has_modal_particle = bool(re.search(r'[啊呀呢吧嘛哦呗哇哈嘿哼嗯]$', text))
        if has_modal_particle:
            score += 0.2
            reasons.append("策略2：含语气词结尾，倾向于对话")

        # 检查3：纯名词短语模式
        if _PURE_NOUN_PHRASE_PATTERN.match(text):
            # 进一步检查是否为专有名词（地名/物品名）
            is_proper_noun = any(text.endswith(suffix) for suffix in _PROPER_NOUN_SUFFIXES)
            if is_proper_noun:
                score -= 0.4
                suppressions.append(f"策略2：纯名词短语+专有名词后缀，倾向于非对话（物品/地名）")
            else:
                score -= 0.2
                suppressions.append("策略2：纯名词短语，可能是非对话")

        # 检查4：单字+叹号模式（拟声词/惊呼）
        if _SINGLE_CHAR_EXCLAIM_PATTERN.match(text):
            score -= 0.5
            suppressions.append("策略2：单字+叹号，倾向于拟声词/惊呼")

        # 检查5：无标点的单/双字词——只在高置信度拟声词/地名时才抑制
        if (
            _SINGLE_WORD_PATTERN.match(text)
            and not has_sentence_end
            and not has_modal_particle
        ):
            # 进一步检查：只有当词明确不是对话时才抑制
            # 拟声词特征：重叠字/韵母重复（滋滋、沙沙、哗哗）
            # 地名特征：专有名词后缀
            is_onomatopoeia = len(text) == 2 and text[0] == text[1]
            is_proper_noun = any(text.endswith(suffix) for suffix in _PROPER_NOUN_SUFFIXES)
            if is_onomatopoeia or is_proper_noun:
                score -= 0.3
                suppressions.append("策略2：无标点单/双字词，明确为非对话（拟声/地名）")

        # 检查6（已移除）：省略号不再作为抑制信号
        # 理由：网文对话中大量使用"……"表示停顿/犹豫/语境留白，
        # 不是内心独白的可靠信号。

        # 检查7：含问号（是对话的强信号）
        if '？' in text or '?' in text:
            score += 0.2
            reasons.append("策略2：含问号，倾向于对话")

        # 归一化分数到 [0, 1]
        score = max(0.0, min(1.0, score))

        return score, reasons, suppressions

    def _strategy3_quote_pattern_suppression(
        self,
        quote_info: QuoteInfo,
        full_text: str,
    ) -> Tuple[float, List[str], List[str]]:
        """策略3：引号模式抑制

        检测书本/碑文/书信等引用模式，这些情况下的引号内容
        是引用文字而非角色实时说出的话。

        Returns:
            (score, reasons, suppression_reasons)
        """
        reasons = []
        suppressions = []
        score = 0.5  # 默认中性

        # 合并引号前后的相关上下文（限制为引号直接前后的内容）
        context_range = 15
        before_context = quote_info.context_before[-context_range:]
        after_context = quote_info.context_after[:context_range]
        surrounding = before_context + quote_info.full_text + after_context

        # 检查1：书本引用关键词模式
        for pattern in _BOOK_QUOTE_PATTERNS:
            if pattern.search(surrounding):
                score -= 0.6
                suppressions.append("策略3：书本/碑文引用模式，引号内为引用文字")
                break

        # 检查2：引号前直接包含关键词（必须紧邻引号，10字内）
        for kw in _BOOK_QUOTE_KEYWORDS:
            if kw in before_context:
                kw_pos = before_context.rfind(kw)
                if len(before_context) - kw_pos <= 10:
                    score -= 0.5
                    suppressions.append(f"策略3：引号前含引用关键词'{kw}'")
                    break

        # 检查3：引号内含换行符（可能是诗文/碑文格式）
        if '\n' in quote_info.text or '\r' in quote_info.text:
            score -= 0.3
            suppressions.append("策略3：引号内含换行符，可能是诗文/碑文")

        # 检查4：引号内内容过长且无说话人标记（可能是大段引用）
        # 注意：只有在策略1无说话动词时才检查此项
        if len(quote_info.text) > 100:
            # 检查上下文是否有说话动词
            has_nearby_speech = bool(_SPEECH_VERB_PATTERN.search(
                quote_info.context_before[-20:] + quote_info.context_after[:20]
            ))
            if not has_nearby_speech:
                score -= 0.3
                suppressions.append("策略3：引号内容过长且无说话动词，可能是大段引用")

        # 归一化分数
        score = max(0.0, min(1.0, score))

        return score, reasons, suppressions


# ============================================================
# 单例和便捷函数
# ============================================================

_detector: Optional[DialogueBoundaryDetector] = None


def get_detector() -> DialogueBoundaryDetector:
    """获取对话边界检测器单例

    Returns:
        DialogueBoundaryDetector 实例
    """
    global _detector
    if _detector is None:
        _detector = DialogueBoundaryDetector()
    return _detector


def is_dialogue(text: str, quote_text: str) -> bool:
    """判断引号内容是否为真实对话（便捷函数）

    Args:
        text: 完整文本
        quote_text: 引号内的文本（不含引号）

    Returns:
        是否为真实对话
    """
    return get_detector().is_dialogue(text, quote_text)


def detect_all_quotes(text: str) -> List[DialogueBoundaryResult]:
    """检测文本中所有引号的对话属性（便捷函数）

    Args:
        text: 完整文本

    Returns:
        检测结果列表
    """
    return get_detector().detect_all(text)
