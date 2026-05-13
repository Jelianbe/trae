# NovelTTS Cloud 项目技术报告

> 文档版本: v1.0  
> 生成日期: 2026-05-10  
> 项目状态: 开发中（后端核心功能完成，前端修复中）

---

# 目录

1. [项目背景](#1-项目背景)
2. [技术栈选型](#2-技术栈选型)
3. [系统架构设计](#3-系统架构设计)
4. [核心功能模块](#4-核心功能模块)
5. [源代码实现](#5-源代码实现)
6. [测试集设计与执行结果](#6-测试集设计与执行结果)
7. [问题与解决方案](#7-问题与解决方案)
8. [项目总结与展望](#8-项目总结与展望)

---

# 1. 项目背景

## 1.1 项目目标

NovelTTS Cloud 是一个中文网络小说自动转语音引擎，核心目标是将长篇小说文本自动分析并转换为带情绪控制的多角色语音输出。

**核心需求**：
- 自动识别小说章节结构
- 自动提取对话中的角色名称（说话人识别）
- 自动为每句对话标注情绪类型
- 支持多种 TTS 引擎（Index-TTS、Kokoro）
- 提供前端界面供用户管理项目和编辑

## 1.2 开发环境

| 项目 | 版本/说明 |
|------|-----------|
| 操作系统 | Windows |
| Python | 3.12+ |
| NLP 引擎 | HanLP (hanlp.common) |
| 数据库 | SQLite |
| Web 框架 | FastAPI (后端) |
| 前端 | 原生 JavaScript SPA |
| 测试框架 | pytest + Playwright |

## 1.3 技术栈选择理由

| 技术 | 选择理由 |
|------|----------|
| **HanLP** | 中文 NLP 领域最成熟的工具包，提供分词、词性标注、命名实体识别 |
| **FastAPI** | 异步支持、自动 OpenAPI 文档生成、类型安全 |
| **SQLite** | 轻量级嵌入式数据库，适合单机部署和开发测试 |
| **原生 JS SPA** | 无构建工具依赖，直接运行 |
| **pytest** | Python 生态标准测试框架，支持参数化和 fixture |

---

# 2. 技术栈选型

## 2.1 后端架构

```
novel-tts-engine/
├── backend/                    # FastAPI Web 服务
│   ├── main.py                 # API 路由定义 (~1400行)
│   └── models.py               # Pydantic 数据模型
├── pipeline/                   # 核心处理流水线
│   ├── chapter_splitter.py     # 章节分割器
│   ├── nlp_basics.py           # NLP 基础分析（分词、词性、NER）
│   ├── speaker_matcher.py      # 说话人匹配器（8级优先级）
│   ├── emotion_extractor.py    # 情绪提取器（规则打分）
│   ├── character_manager.py    # 角色管理器（SQLite 持久化）
│   ├── entity_linker.py        # 实体链接器
│   ├── semantic_ranker.py      # 语义排序器
│   ├── context_validator.py    # 上下文验证器
│   ├── speaker_role_filter.py  # 说话角色过滤器
│   ├── tts_generator.py        # TTS 音频生成器（统一接口）
│   ├── tts_indextts.py         # Index-TTS 引擎适配器
│   ├── tts_kokoro.py           # Kokoro 引擎适配器
│   └── pipeline_runner.py      # 流水线调度器
├── frontend/                   # 前端 SPA
│   ├── index.html              # 单页应用入口
│   ├── css/style.css           # 样式表
│   └── js/                     # JavaScript 代码
│       ├── app.js              # 主应用类
│       ├── api.js              # API 客户端
│       ├── store.js            # 状态管理
│       └── views.js            # 视图渲染
├── tests/                      # 测试集
│   ├── test_emotion_extractor.py  # 情绪识别单元测试
│   ├── test_emotion_tagger.py     # 旧情绪标注器测试
│   ├── test_gateway_emotion.py    # 情绪识别测试网关
│   └── emotion_gt_100.json        # 100条情绪标注 GT 数据
├── strategic_reserve/          # 战略储备库
│   └── modules/                # 储备代码模块
│       ├── quotation_classifier.py  # 引号内容分类器
│       ├── sfx_detector.py          # 拟声词检测器
│       ├── entity_clusterer.py      # 实体聚类器
│       └── dialogue_classifier.py   # 对话分类器
└── docs/                       # 文档
    ├── 前端状态分析报告.md
    ├── 情绪识别分析系统综合文档.md
    ├── 战略储备库.md
    └── 前端改进规划.md
```

## 2.2 数据模型

### 2.2.1 情绪标注结果（三层标注体系）

```python
@dataclass
class EmotionResult:
    """情绪标注结果"""
    emotion_class: str           # L1: neutral / excited / subdued
    emotion_label: str           # L2: joy / anger / sadness / surprise / fear / neutral / unknown
    emotion_vector: List[float]  # L3: 8维向量 [happiness, anger, sadness, fear, disgust, melancholy, surprise, calm]
    emotion_text: str            # 情感软指令描述
    confidence: float            # 置信度 0.0~1.0
    intensity: float = 0.5       # 情绪强度 0.0~1.0
```

### 2.2.2 说话人匹配结果

```python
@dataclass
class MatchResult:
    """说话人匹配结果"""
    speaker: Optional[str]       # 匹配到的角色名
    confidence: float            # 匹配置信度
    method: str                  # 匹配方法（称呼模式/NER/身份词等）
    character: Optional[Character]  # 匹配到的角色对象
```

### 2.2.3 句子结果

```python
@dataclass
class SentenceData:
    """句子级结果"""
    text: str                    # 句子文本
    type: str                    # "dialogue" 或 "narration"
    speaker: Optional[str]       # 说话人
    emotion: Optional[str]       # L2 情绪标签
    emotion_class: Optional[str] # L1 情绪类别
    emotion_vector: Optional[List[float]]  # L3 向量
    entities: List[Entity]       # 实体列表
    fragments: List[Fragment]    # 片段拆分
```

---

# 3. 系统架构设计

## 3.1 流水线架构

系统采用 **6 步串行流水线** 架构：

```
输入文本
    │
    ▼
┌────────────────────────────┐
│ 1. 章节分割                 │  chapter_splitter.py
│    文本 → 章节块             │  基于章节标题正则匹配
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 2. NLP 基础分析             │  nlp_basics.py
│    分词 / 词性标注 / NER   │  HanLP 引擎
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 2.1 上下文多样性验证        │  context_diversity_validator.py
│ 2.2 说话角色过滤            │  speaker_role_filter.py
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 3. 实体链接                 │  entity_linker.py
│    实体 → 角色引用          │  NER 实体链接到角色库
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 4. 说话人匹配               │  speaker_matcher.py
│    对话 → 角色名            │  8级优先级匹配
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 5. 情绪标注                 │  emotion_extractor.py
│    句子 → L1/L2/L3 标注    │  规则打分 + 引导词提取
└────────────────────────────┘
    │
    ▼
┌────────────────────────────┐
│ 6. TTS 生成                 │  tts_generator.py
│    emotion → emo_text      │  Index-TTS / Kokoro
│    emotion_vector → Index  │  8维情感向量
└────────────────────────────┘
```

## 3.2 说话人匹配 8 级优先级

```
优先级 | 方法              | 说明
───────┼──────────────────┼────────────────────────
P1     | 称呼模式匹配      | "X说"、"X道"、"X喊道"
P2     | 代词消解          | "他"、"她" → 上下文角色
P3     | NER 提取 PER 实体 | HanLP NER → 角色名匹配
P4     | 描述性角色提取     | "白衣剑客"、"中年男子"
P5     | 身份词提取        | "将军"、"长老"、"公子"
P6     | 自称推断          | "我"、"老夫" → 说话人
P7     | context_after NER | 对话后文 NER 实体
P8     | 说话动作检测      | 说话动作动词 → 说话人
```

## 3.3 情绪识别三层体系

```
L1 粗分类: neutral, excited, subdued  →  规则系统训练目标
    ↑
    │ map_l2_to_l1()
    │
L2 细分类: joy, anger, sadness, surprise, fear, neutral, unknown  →  主情绪标签
    ↑
    │ map_l2_to_vector()
    │
L3 情感向量: [happiness, anger, sadness, fear, disgust, melancholy, surprise, calm]  →  Index-TTS 消费
```

---

# 4. 核心功能模块

## 4.1 说话人匹配器（speaker_matcher.py）

**职责**：从对话文本中识别说话人角色。

**核心算法**：8 级优先级匹配，从高到低依次尝试，一旦匹配成功立即返回。

**关键方法**：
- `analyze_dialogue(text, chapter_id)` — 分析整个文本中的所有对话
- `match_candidate(candidate, context)` — 匹配单个候选说话人
- `_extract_context_candidates(context)` — 从上下文中提取候选角色
- `_extract_descriptive_roles(text)` — 提取描述性角色（如"白衣剑客"）
- `_extract_identity_words(text)` — 提取身份词（如"将军"）
- `_infer_from_address(text, candidates)` — 从称呼推断说话人
- `match_by_semantic(candidates, context)` — 语义排序
- `match_by_trigger_words(candidates, text)` — 触发词匹配

## 4.2 情绪提取器（emotion_extractor.py）

**职责**：为每句文本标注情绪类型。

**核心算法**：规则打分系统，对 5 种情绪分别打分，取最高分作为结果。

**关键方法**：
- `classify(text, context_hint, context_confidence)` — 情绪分类（主入口）
- `extract_features(text)` — 特征提取
- `_apply_guide_phrase_bonus(text, scores)` — 引导词情绪加分
- `_extract_guide_phrase(text)` — 提取紧邻引号的动词短语
- `_check_special_laughter(text)` — 特殊笑类检查（冷笑→anger，苦笑→sadness）

**情绪信号权重**：

| 情绪 | 核心信号 | 权重 |
|------|----------|:---:|
| anger | 脏话/粗口 | 0.5 |
| anger | 威胁/诅咒词 | 0.5 |
| anger | 情绪动词 | 0.2 |
| fear | 求饶词 | 0.5 |
| fear | 颤抖动词 | 0.4 |
| sadness | 失去/离别词 | 0.5 |
| sadness | 哭泣词 | 0.4 |
| surprise | "居然/竟然" | 0.3-0.4 |
| surprise | 反问句 | 0.3 |
| joy | 感叹句模式 | 0.4 |
| joy | 笑声词 | 0.2-0.3 |
| neutral | 句号结尾 + 无情绪词 | 0.25 |

## 4.3 角色管理器（character_manager.py）

**职责**：管理角色库的创建、查询和持久化。

**核心功能**：
- SQLite 持久化存储
- 角色名称精确匹配
- 别名匹配
- 性别推断
- 临时角色创建

## 4.4 TTS 引擎适配器

**支持引擎**：
- **Index-TTS**：支持 emo_text（情感描述）和 emo_vector（8维向量）两种模式
- **Kokoro**：支持 emotion 参数

**情绪映射表**：
```python
EMOTION_TO_TEXT = {
    "joy": "开心地说",
    "anger": "生气地说",
    "sadness": "悲伤地说",
    "surprise": "惊讶地说",
    "fear": "害怕地说",
    "neutral": "平静地说",
    "unknown": "平静地说",  # unknown 等同于 calm
}
```

---

# 5. 源代码实现

## 5.1 情绪提取器（emotion_extractor.py）

```python
"""情绪提取器：基于规则打分的情绪分类系统"""
import re
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ========================================
# 数据模型
# ========================================

@dataclass
class EmotionResult:
    """情绪标注结果 —— 三层标注体系"""
    emotion_class: str           # L1: neutral / excited / subdued
    emotion_label: str           # L2: joy / anger / sadness / surprise / fear / neutral / unknown
    emotion_vector: List[float]  # L3: 8维向量
    emotion_text: str            # 情感软指令描述
    confidence: float            # 置信度 0.0~1.0
    intensity: float = 0.5       # 情绪强度 0.0~1.0


@dataclass
class EmotionFeatures:
    """情绪特征"""
    text: str
    exclamation_count: int = 0
    question_count: int = 0
    ellipsis_count: int = 0
    exclamation_density: float = 0.0
    avg_sentence_len: float = 0.0
    has_dirty_words: bool = False
    has_repetition: bool = False
    has_short_sentences: bool = False
    has_emotion_adverb: bool = False
    has_emotion_verb: bool = False
    is_exclamatory: bool = False
    is_rhetorical: bool = False
    is_imperative: bool = False
    has_mood_particle: bool = False


# ========================================
# 情绪词典
# ========================================

# 来源：通用中文脏话（社会通用，非文体特定）+ 网文高频粗口
DIRTY_WORDS = [
    '滚', '滚蛋', '混蛋', '王八蛋', '废物', '垃圾', '傻逼', '蠢货',
    '该死', '操', '他妈', '妈的', '草', '卧槽', '靠', '日',
    '贱人', '畜生', '狗东西', '杂种', '废物', '蠢材',
    '放肆', '大胆', '岂有此理', '混蛋', '找死', '活腻',
]

# 来源：通用中文程度副词 + 网文高频情绪副词
EMOTION_ADVERBS = [
    '极其', '非常', '特别', '十分', '格外', '分外',
    '狠狠', '猛地', '突然', '猛然', '骤然', '顿时',
    '不禁', '不由', '忍不住', '情不自禁',
    '愤怒地', '激动地', '颤抖地', '嘶吼地', '咆哮地',
    '冷冷', '淡淡', '微微', '轻轻',
    '咬牙切齿', '怒火中烧', '气急败坏',
]

# 来源：通用中文情绪动词 + 网文高频描写词
EMOTION_VERBS = [
    '怒吼', '咆哮', '嘶吼', '怒吼', '怒骂', '怒吼',
    '痛哭', '抽泣', '哽咽', '流泪', '落泪',
    '大笑', '狂笑', '冷笑', '嘲笑', '讥笑',
    '颤抖', '发抖', '哆嗦', '战栗',
    '瞪眼', '怒视', '盯着', '注视',
    '抓紧', '握紧', '捏紧', '拍打',
]


# ========================================
# 情绪词典 + 正则模式
# ========================================

# L1 粗分类
EMOTION_LABEL_L1 = ['neutral', 'excited', 'subdued']

# L2 细分类（7类，含 unknown）
EMOTION_LABEL_L2 = ['joy', 'anger', 'sadness', 'surprise', 'fear', 'neutral', 'unknown']

# unknown 判定阈值
UNKNOWN_SCORE_THRESHOLD = 0.25
UNKNOWN_MIN_TEXT_LENGTH = 5


# ========================================
# 情绪映射函数
# ========================================

def map_l2_to_l1(emotion_label: str, intensity: float) -> str:
    """L2 → L1 映射"""
    if emotion_label == 'neutral':
        return 'neutral'
    
    if emotion_label == 'unknown':
        return 'neutral'
    
    if emotion_label in ('sadness', 'fear'):
        return 'subdued'
    
    if emotion_label == 'anger':
        return 'excited' if intensity >= 0.4 else 'subdued'
    
    if emotion_label in ('joy', 'surprise'):
        return 'excited' if intensity >= 0.4 else 'neutral'
    
    return 'neutral'


def map_l2_to_vector(emotion_label: str, confidence: float, intensity: float) -> List[float]:
    """L2 + confidence → L3 8维向量动态计算
    
    Index-TTS 2 向量顺序: [happiness, anger, sadness, fear, disgust, melancholy, surprise, calm]
    """
    confidence = max(0.0, min(1.0, confidence))  # 值域验证
    intensity = max(0.0, min(1.0, intensity))
    
    vector = [0.0] * 8
    primary_value = min(confidence * intensity, 1.0)
    
    if emotion_label == 'joy':
        vector[0] = primary_value  # happiness
    elif emotion_label == 'anger':
        vector[1] = primary_value  # anger
    elif emotion_label == 'sadness':
        vector[2] = min(primary_value, 1.0)  # sadness
        vector[5] = min(primary_value * 0.3, 1.0)  # melancholy
    elif emotion_label == 'fear':
        vector[3] = min(primary_value, 1.0)  # fear
        vector[2] = min(primary_value * 0.2, 1.0)  # sadness
    elif emotion_label == 'surprise':
        vector[6] = primary_value  # surprise
    elif emotion_label == 'neutral':
        vector[7] = 1.0  # calm
    elif emotion_label == 'unknown':
        vector[7] = 1.0  # calm
    
    vector = [max(0.0, min(v, 1.0)) for v in vector]  # 最终裁剪
    return vector


# ========================================
# 情绪提取器类
# ========================================

class EmotionExtractor:
    """情绪提取器"""
    
    def __init__(self):
        pass
    
    def extract_features(self, text: str) -> EmotionFeatures:
        """特征提取"""
        features = EmotionFeatures(text=text)
        
        # 标点统计
        features.exclamation_count = text.count('！') + text.count('!')
        features.question_count = text.count('？') + text.count('?')
        features.ellipsis_count = len(re.findall(r'[…]{2,}|[.]{3,}', text))
        
        # 词表匹配
        features.has_dirty_words = any(w in text for w in DIRTY_WORDS)
        features.has_emotion_adverb = any(a in text for a in EMOTION_ADVERBS)
        features.has_emotion_verb = any(v in text for v in EMOTION_VERBS)
        
        return features
    
    def classify(self, text: str, context_hint: Optional[str] = None, 
                 context_confidence: float = 0.0) -> EmotionResult:
        """情绪分类（主入口）"""
        features = self.extract_features(text)
        
        scores = {'anger': 0.0, 'fear': 0.0, 'sadness': 0.0, 'surprise': 0.0, 'joy': 0.0}
        
        # ANGER 信号
        if features.has_dirty_words:
            scores['anger'] += 0.5
        
        if features.has_emotion_verb:
            scores['anger'] += 0.2
        
        # FEAR 信号
        if features.ellipsis_count >= 2:
            scores['fear'] += 0.2
        
        if any(w in text for w in ['颤抖', '发抖', '哆嗦', '战栗']):
            scores['fear'] += 0.4
        
        # SADNESS 信号
        if text.startswith(('唉', '呜', '呜呜')):
            scores['sadness'] += 0.3
        
        if features.ellipsis_count >= 1:
            scores['sadness'] += 0.2
        
        # SURPRISE 信号
        if features.is_rhetorical:
            scores['surprise'] += 0.3
        
        if any(w in text for w in ['居然', '竟然']):
            scores['surprise'] += 0.4
        
        # JOY 信号
        if features.is_exclamatory:
            scores['joy'] += 0.4
        
        if any(w in text for w in ['哈哈', '呵呵', '笑']):
            scores['joy'] += 0.3
        
        # NEUTRAL 信号
        neutral_score = 0.0
        if text.endswith('。') and features.exclamation_count == 0 and features.question_count == 0:
            neutral_score += 0.2
        
        has_emotion_signals = (
            features.has_dirty_words or features.has_emotion_verb or 
            features.has_emotion_adverb or features.is_exclamatory or
            features.is_rhetorical or features.is_imperative
        )
        if not has_emotion_signals:
            neutral_score += 0.2
        
        neutral_score = min(neutral_score, 0.25)
        scores['neutral'] = neutral_score
        
        # 引导词情绪加分
        self._apply_guide_phrase_bonus(text, scores)
        
        # 上下文干预
        if context_hint and context_hint in ('sadness', 'fear', 'anger', 'joy', 'surprise'):
            if context_confidence >= 0.3:
                current_max = max(scores.values())
                if current_max <= 0.25:
                    scores[context_hint] += 0.4
        
        # 取最高分
        best_emotion = max(scores, key=scores.get)
        best_score = scores[best_emotion]
        
        # 祈使句误判修复：愤怒 → 恐惧豁免
        if best_emotion == 'anger' and best_score >= 0.4:
            fear_signals = ['快跑', '逃', '别过来', '救命', '危险', '求饶', '饶命', '别杀', '别伤害']
            has_fear_signal = any(signal in text for signal in fear_signals)
            if has_fear_signal and scores.get('fear', 0) > 0.1:
                best_emotion = 'fear'
                best_score = max(best_score * 0.8, scores['fear'])
        
        # unknown 判定
        if len(text) == 0:
            best_emotion = 'neutral'
            best_score = 0.3
        elif best_score <= UNKNOWN_SCORE_THRESHOLD and len(text) >= UNKNOWN_MIN_TEXT_LENGTH:
            if best_emotion != 'neutral':
                best_emotion = 'unknown'
                best_score = 0.3
        
        confidence = min(best_score, 0.95)
        intensity = min(best_score / 0.8, 1.0)
        
        emotion_class = map_l2_to_l1(best_emotion, intensity)
        emotion_vector = map_l2_to_vector(best_emotion, confidence, intensity)
        emotion_text = generate_emotion_text(best_emotion, intensity)
        
        return EmotionResult(
            emotion_class=emotion_class,
            emotion_label=best_emotion,
            emotion_vector=emotion_vector,
            emotion_text=emotion_text,
            confidence=confidence,
            intensity=intensity,
        )
```

## 5.2 流水线调度器（pipeline_runner.py）

```python
"""流水线调度器：协调所有处理模块"""
import threading
from collections import OrderedDict
from pipeline.chapter_splitter import ChapterSplitter
from pipeline.nlp_basics import get_nlp
from pipeline.speaker_matcher import SpeakerMatcher
from pipeline.emotion_extractor import get_emotion_extractor
from pipeline.character_manager import get_character_manager
from pipeline.entity_linker import get_entity_linker


class PipelineRunner:
    """流水线调度器"""
    
    def __init__(self):
        self.chapter_splitter = ChapterSplitter()
        self.nlp = get_nlp()
        self.char_manager = get_character_manager()
        self.speaker_matcher = SpeakerMatcher(self.char_manager)
        self.entity_linker = get_entity_linker(self.char_manager)
        
        self._result_cache: OrderedDict[str, list] = OrderedDict()
    
    def analyze_chapters(self, content: str, start: int = 0, end: int = 1, 
                         force: bool = False) -> list:
        """分析章节内容（主入口）"""
        chapters = self.chapter_splitter.split(content)
        results = []
        
        for chapter_id, chapter in enumerate(chapters[start:end]):
            result = self._process_chapter(chapter, chapter_id)
            results.append(result)
        
        return results
    
    def _process_chapter(self, chapter: str, chapter_id: int) -> "ChapterResult":
        """处理单个章节"""
        # 第2步：NLP 基础分析
        nlp_result = self.nlp.analyze(chapter)
        entities = nlp_result.entities
        
        # 第3步：实体链接
        linked_entities = self.entity_linker.link(entities, chapter)
        
        # 第5步：说话人匹配
        dialogue_results = self.speaker_matcher.analyze_dialogue(chapter, chapter_id=chapter_id)
        
        # 构建对话映射
        dialogue_map = {}
        for dialogue_text, speaker in dialogue_results:
            if speaker:
                self.char_manager.find_or_create(speaker.name, project_id=0)
            dialogue_map[dialogue_text.strip()] = speaker.name if speaker else ""
        
        # 第6步：情绪标注 + 句子级处理
        sentences = []
        emotion_extractor = get_emotion_extractor()
        prev_emotion = None
        prev_confidence = 0.0
        
        for sentence in self._split_sentences(chapter):
            # 情绪窗口
            emotion_context = chapter[
                max(0, chapter.find(sentence) - 50):
                min(len(chapter), chapter.find(sentence) + len(sentence) + 50)
            ]
            
            emotion_result = emotion_extractor.classify(
                emotion_context,
                context_hint=prev_emotion,
                context_confidence=prev_confidence
            )
            
            # 判断是否为对话
            is_dialogue = False
            speaker = ""
            emotion = emotion_result.emotion_label
            
            for d_text, d_speaker in dialogue_map.items():
                if d_text in sentence:
                    is_dialogue = True
                    speaker = d_speaker
                    break
            
            sentences.append(SentenceData(
                text=sentence,
                type="dialogue" if is_dialogue else "narration",
                speaker=speaker,
                emotion=emotion,
                emotion_class=emotion_result.emotion_class,
                emotion_vector=emotion_result.emotion_vector,
            ))
            
            prev_emotion = emotion
            prev_confidence = emotion_result.confidence
        
        return ChapterResult(
            chapter_id=chapter_id,
            title=f"第{chapter_id + 1}章",
            sentences=sentences,
        )


# 全局单例（线程安全）
_pipeline_runner = None
_pipeline_runner_lock = threading.Lock()

def get_pipeline_runner() -> PipelineRunner:
    global _pipeline_runner
    if _pipeline_runner is None:
        with _pipeline_runner_lock:
            if _pipeline_runner is None:
                _pipeline_runner = PipelineRunner()
    return _pipeline_runner

def reset_pipeline_runner() -> None:
    global _pipeline_runner
    with _pipeline_runner_lock:
        _pipeline_runner = None
```

---

# 6. 测试集设计与执行结果

## 6.1 单元测试：情绪提取器

**文件**: `tests/test_emotion_extractor.py`

### 6.1.1 测试用例设计

| 测试类 | 测试方法 | 测试目标 | 预期结果 |
|--------|---------|---------|---------|
| TestEmotionExtractor | test_anger_dirty_words | 脏话触发愤怒 | label=anger, conf≥0.5 |
| TestEmotionExtractor | test_anger_imperative_exclamation | 祈使句+感叹号 | label=anger, conf≥0.4 |
| TestEmotionExtractor | test_fear_trembling | 颤抖动词+省略号 | label=fear, conf≥0.4 |
| TestEmotionExtractor | test_sadness_sigh | 叹词开头+省略号 | label=sadness, conf≥0.4 |
| TestEmotionExtractor | test_surprise_rhetorical | 反问句 | label=surprise, conf≥0.4 |
| TestEmotionExtractor | test_joy_laughter | 笑声+感叹句 | label=joy, conf≥0.5 |
| TestEmotionExtractor | test_neutral_plain_statement | 平淡叙述 | label=neutral |
| TestEmotionExtractor | test_empty_text | 空文本 | label=neutral |
| TestEmotionExtractor | test_emotion_result_fields | 三层标注字段完整性 | 所有字段存在且合法 |
| TestEmotionExtractor | test_emotion_vector_anger | L3 向量 anger 维度 | anger 维度 > 0 |
| TestEmotionExtractor | test_emotion_vector_neutral | L3 向量 calm 维度 | calm = 1.0 |
| TestEmotionExtractor | test_batch_classify | 批量分类 | 返回结果数=输入数 |

### 6.1.2 测试结果

| 指标 | 结果 |
|------|------|
| 通过数 | 28 |
| 失败数 | 0 |
| 通过率 | **100%** |
| 耗时 | 0.07s |

## 6.2 测试网关：emotion_gt_100.json

**文件**: `tests/test_gateway_emotion.py`

### 6.2.1 数据集设计

| 属性 | 说明 |
|------|------|
| 数据量 | 100 条 |
| 情绪类别 | anger(22), joy(10), sadness(12), surprise(7), fear(11), neutral(21) |
| 文体覆盖 | 都市、修仙、西幻、历史 |
| 标注方式 | 人工标注 |

### 6.2.2 测试结果

| 指标 | 旧基线 | 统一管道后 | 精细化调优后 |
|------|:---:|:---:|:---:|
| **L2 准确率** | **26.7%** | **63.0%** | **64.0%** |
| Neutral 预测比例 | - | 41.0% | 41.0% |
| 脏词误报数 | - | 0 | 0 |
| 错误案例数 | 73 | 37 | 36 |

### 6.2.3 按情绪类别准确率

| 情绪 | GT 数量 | 正确 | 准确率 |
|------|:---:|:---:|:---:|
| anger | 22 | 17 | 77.3% |
| joy | 10 | 8 | 80.0% |
| sadness | 12 | 7 | 58.3% |
| surprise | 7 | 5 | 71.4% |
| fear | 11 | 6 | 54.5% |
| neutral | 21 | 12 | 57.1% |

## 6.3 端到端诊断测试

**测试方法**：使用干净数据库重置所有组件后运行完整 pipeline。

### 6.3.1 测试结果

| 指标 | 预期 | 实际 | 状态 |
|------|------|------|------|
| 情绪识别（隔离） | 63.0% | **0%** | ❌ |
| 情绪识别（Pipeline） | 63.0% | **0%** | ❌ |
| 说话人匹配（Pipeline） | ~80% | **40%** | ❌ |

### 6.3.2 错误分析

| 问题 | 根因 |
|------|------|
| 情绪全部为 unknown | unknown 阈值 0.25 过于激进，正常情绪得分（0.2）被截断 |
| 引导词未提取 | GUIDE_PHRASE_PATTERN 未能匹配 `"林轩冷笑道"` 等引导词 |
| 说话人匹配错误 | 角色库污染（82 个历史角色），匹配优先级错乱 |

## 6.4 Playwright E2E 测试

**文件**: `frontend/tests/v2-editor.spec.js`

| 指标 | 结果 |
|------|------|
| 总用例 | 29 |
| 通过 | 17 |
| 失败 | 12 |
| 失败率 | 41% |
| 阻塞原因 | JS 语法错误导致页面初始化失败 |

---

# 7. 问题与解决方案

## 7.1 P0 问题：已解决

### 7.1.1 双系统并行（情绪识别）

**问题描述**：`EmotionExtractor` 和 `EmotionTagger` 同时运行，逻辑冲突。

**解决方案**：
1. 将 `EmotionTagger` 的引导词提取逻辑迁移到 `EmotionExtractor`
2. 从 `pipeline_runner.py` 中移除 `EmotionTagger` 调用
3. 统一为单一情绪管道

**效果**：L2 准确率从 26.7% 提升至 63.0%（+36.3%）

### 7.1.2 单例模式线程安全

**问题描述**：`get_emotion_extractor()` 无锁保护，并发初始化可能创建多个实例。

**解决方案**：
```python
_extractor: Optional[EmotionExtractor] = None
_extractor_lock = threading.Lock()

def get_emotion_extractor() -> EmotionExtractor:
    global _extractor
    if _extractor is None:
        with _extractor_lock:
            if _extractor is None:
                _extractor = EmotionExtractor()
    return _extractor
```

### 7.1.3 情绪向量值域验证

**问题描述**：`map_l2_to_vector` 未验证 confidence 和 intensity 的取值范围。

**解决方案**：在函数入口处添加 clamp 操作，向量元素做 0~1 裁剪。

### 7.1.4 unknown 情绪类别

**问题描述**：缺少 "无法判断" 的情绪类别，导致低置信度时随机归为某情绪。

**解决方案**：
- 新增 L2 类别 `unknown`
- 判定标准：所有情绪得分 ≤ 0.25 且 `best_emotion != 'neutral'`
- 映射：unknown → neutral（L1），向量 → [0,0,0,0,0,0,0,1]（calm）

## 7.2 P1 问题：已部分解决

### 7.2.1 Index-TTS 接口 Bug

**问题描述**：`EMOTION_TO_TEXT` 映射表缺失 `unknown`，导致 fallback 生成 `[UNKNOWN:unknown]`。

**解决方案**：
```python
EMOTION_TO_TEXT = {
    ...
    "unknown": "平静地说",  # unknown 等同于 calm
}
```

### 7.2.2 祈使句误判为愤怒

**问题描述**：`"快跑！"`、`"别过来！"` 被误判为 anger。

**解决方案**：在 anger 分数 ≥ 0.4 时，检查是否包含恐惧信号词，如果是则将情绪改为 fear。

## 7.3 当前存在的问题

### 7.3.1 情绪识别 unknown 阈值过于激进

**问题描述**：正常情绪得分（0.2）低于 unknown 阈值（0.25），导致大部分对话被归为 unknown。

**影响**：隔离测试准确率 0%，Pipeline 中准确率 0%。

**建议修复**：
1. 提高 unknown 阈值至 0.15
2. 增加引导词加分权重（当前仅为 0.2-0.5）
3. 增加更多情绪信号词

### 7.3.2 角色库污染

**问题描述**：角色库中有 82 个历史角色，干扰当前测试的说话人匹配。

**影响**：说话人匹配准确率 40%。

**建议修复**：测试前清空角色库或创建隔离的测试数据库。

### 7.3.3 前端 JS 语法错误

**问题描述**：`frontend/js/app.js` 存在 `Invalid left-hand side in assignment` 语法错误。

**影响**：页面无法加载，41% E2E 测试失败。

**建议修复**：定位错误行号，修复语法。

### 7.3.4 linked_entities 未传递给说话人匹配

**问题描述**：`pipeline_runner.py` 中 `linked_entities` 计算后未传递给 `speaker_matcher.analyze_dialogue()`。

**影响**：实体链接结果被浪费。

**建议修复**：修改 `analyze_dialogue` 方法签名，接受 `linked_entities` 参数。

---

# 8. 项目总结与展望

## 8.1 已完成的工作

| 模块 | 完成度 | 说明 |
|------|:---:|------|
| 章节分割 | ✅ 100% | 基于正则匹配章节标题 |
| NLP 基础分析 | ✅ 100% | HanLP 分词、词性、NER |
| 说话人匹配 | ⚠️ 80% | 8级优先级算法完整，但实际准确率 40% |
| 情绪识别 | ⚠️ 60% | 规则系统完整，但 unknown 阈值问题导致 0% 准确率 |
| TTS 引擎 | ✅ 100% | Index-TTS + Kokoro 双引擎支持 |
| 前端页面 | ⚠️ 60% | 页面结构完整，但 JS 错误阻塞 |

## 8.2 关键指标

| 指标 | 目标 | 当前 | 差距 |
|------|------|------|------|
| 说话人匹配准确率 | 80% | 40% | -40% |
| 情绪识别准确率 | 63% | 0% (测试集) / 64% (GT) | 待修复 |
| TTS 引擎支持 | 2 | 2 | ✅ |
| 前端可用性 | 100% | 0% (JS错误阻塞) | -100% |

## 8.3 储备库功能

| 功能 | 后端代码 | 前端接入 | 状态 |
|------|:---:|:---:|------|
| 引号内容分类 | ✅ 100% | ❌ 0% | 储备代码，待接入 |
| 拟声词检测 | ✅ 100% | ❌ 0% | 储备代码，待接入 |
| 实体聚类 | ✅ 100% | ❌ 0% | 储备代码，待接入 |
| 修正反馈面板 | ❌ 0% | ❌ 0% | 纯概念文档 |

## 8.4 下一步工作

**P0 优先级**：
1. 修复前端 JS 语法错误
2. 修复情绪识别 unknown 阈值问题
3. 清理角色库污染

**P1 优先级**：
4. 实现前端编辑模式核心功能
5. 连接批量操作 UI
6. 完善撤销/重做系统

**P2 优先级**：
7. 接入引号内容分类器（后端已完成）
8. 接入拟声词检测器（后端已完成）
9. 实现修正反馈面板

---

# 附录：Git 基线

| 标签 | 说明 | 日期 |
|------|------|------|
| `baseline/emotion-v1-unified` | 情绪识别统一管道 v1 基线 | 2026-05-10 |
