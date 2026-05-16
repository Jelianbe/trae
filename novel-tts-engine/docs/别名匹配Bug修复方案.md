# 别名匹配 Bug 修复方案（统一执行手册）

> **文档类型**: 统一执行手册 · 包含 Bug 修复 + SRL 新信号接入  
> **报告日期**: 2026-05-16 · 最后更新: 2026-05-16  
> **关联设计文档**: [SRL_ARG0提取方案.md](file:///d:/trae/novel-tts-engine/docs/SRL_ARG0提取方案.md)  
> **问题**: 都市职场准确率 67.06% 中 71.4% 的错误（20/28条）的根因修复  
> **预期收益**: 都市 67.06% → **~89.4%（+22pct）**，西幻无直接影响  
> **SRL 额外收益**: 都市 → **~87-90%**（在 Bug 修复的基础上再 +5~8pct）  

---

## 一、问题全景

"总监" 错误的完整链路 —— 6 个环节，任一环节拦截即可阻断：

```
层级          环节                             文件:行号
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
① 模型层       NER 将 "总监" 误标为 PER         HanLP 模型（不可控）
② 防御层       name_validator.is_valid("总监")  speaker_matcher.py:553
                返回 True（无纯职称词拒绝规则）
③ 创建层       _match_candidate_to_character     speaker_matcher.py:564
                找不到匹配 → 注册临时角色 "总监"
④ 匹配层 A     语境优先路径（line 817）            speaker_matcher.py:817
                "总监" in "赵总监皱起眉头" → True（子串匹配）
⑤ 匹配层 B     角色库旁白匹配（line 332）          speaker_matcher.py:332
                "总监" in "赵总监皱起眉头" → True（子串匹配）
⑥ 持久层       临时角色 "总监" 无淘汰机制          speaker_matcher.py:231-254
                当前 chapter 内永久存活
```

---

## 二、Bug 详解与修复方案

### P0-紧急 ###

#### Bug ③ — 临时角色创建不拒纯职称词（核心阻断）

**位置**: `_match_candidate_to_character()` [speaker_matcher.py:738-741](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L738)

```python
def _match_candidate_to_character(self, candidate_name, context, skip_speech_check=False):
    # 步骤1：精确匹配
    char = self.char_manager.get_character_by_name(candidate_name, self._current_project_id)
    if char: return char
    # 步骤2：别名匹配
    char = self.char_manager.get_character_by_alias(candidate_name, self._current_project_id)
    if char: return char
    # ★ 步骤3：没有检查 candidate_name 是否是纯职称词，直接创建临时角色
    temp_char = self._register_temporary_character(candidate_name, context, skip_speech_check)
    return temp_char
```

**问题说明**: `_match_candidate_to_character` 是所有候选路径的汇合点。当 `candidate_name="总监"` 时，步骤1/2都失败（"总监"既不是角色名也不是别名），步骤3直接创建了临时角色"总监"。一旦"总监"成为角色库中的有效角色，后续所有子串匹配路径都会命中它。

**修复方案**: 在步骤3之前加一道纯职称词拦截：

```python
def _match_candidate_to_character(self, candidate_name, context, skip_speech_check=False):
    char = self.char_manager.get_character_by_name(candidate_name, self._current_project_id)
    if char: return char
    char = self.char_manager.get_character_by_alias(candidate_name, self._current_project_id)
    if char: return char
    # ★ 修复：拒绝纯职称词成为临时角色
    from pipeline.nlp_basics import TITLE_WORDS
    if candidate_name in TITLE_WORDS:
        logger.debug(f"拒绝纯职称词临时角色: '{candidate_name}'")
        return None
    # 现有逻辑
    temp_char = self._register_temporary_character(candidate_name, context, skip_speech_check)
    return temp_char
```

**影响**: 阻断整个链路的根源。处理后 NLP 不会再产出 "总监" 这个临时角色，"总监" 也不会出现在后续角色的备选项中。

**依赖**: 需要 `from pipeline.nlp_basics import TITLE_WORDS`。

**风险**: 极低。`TITLE_WORDS` 中的词都是纯职称（总监/经理/秘书/工程师等），正常人名的姓氏+职称组合不会被拦截（"赵总监"长度为3且不在 `TITLE_WORDS` 中）。

---

#### Bug ⑤ — `_match_from_character_library` 子串匹配（防复发）

**位置**: [speaker_matcher.py:331-336](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L331)

```python
def _match_from_character_library(self, narration, locked_only=False):
    for char in characters:
        if char.name in narration:       # ★ 子串匹配
            return char
        for alias in char.aliases:
            if alias in narration:       # ★ 子串匹配
                return char
    return None
```

**问题说明**: `char.name in narration` 使得即使 "总监" 不是独立角色名，只要旁白中出现 "赵总监"，就会被 "总监" 这个临时角色命中。这是字匹配（"总监"是 "赵总监"的子串），而非词边界匹配。

**修复方案**: 改为词边界匹配。中文的词边界可以通过前后字符判断——角色名前后的字符应为非中文字符或标点/空格/开头/结尾：

```python
def _match_from_character_library(self, narration, locked_only=False):
    for char in characters:
        if self._is_word_boundary_match(narration, char.name):
            return char
        for alias in char.aliases:
            if self._is_word_boundary_match(narration, alias):
                return char
    return None

def _is_word_boundary_match(self, text, target):
    """判断 target 是否在 text 中以独立词的形式出现（词边界匹配）。"""
    idx = text.find(target)
    if idx < 0:
        return False
    # 检查前边界：开头或前一个字符非中文
    if idx > 0:
        prev_char = text[idx - 1]
        if '\u4e00' <= prev_char <= '\u9fff':
            return False
    # 检查后边界：结尾或后一个字符非中文
    end = idx + len(target)
    if end < len(text):
        next_char = text[end]
        if '\u4e00' <= next_char <= '\u9fff':
            return False
    return True
```

**影响**: 即使 "总监" 作为临时角色存在，它也不会再匹配 "赵总监皱起眉头" 中的子串 "总监"。**这是 Bug ③ 的防御加固**。

**风险**: 低。对正常角色名无影响（"赵总监"在 "赵总监皱起眉头" 中前后都是非中文或边界）。

---

### P1-高 ###

#### Bug ② — `name_validator` 拒纯职称词（防御层）

**位置**: `CharacterNameValidator.is_valid()` [speaker_matcher.py:1829](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L1829)

```python
def is_valid(self, name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 6:
        return False
    if name in self._blacklist:
        return False
    # ★ 没有纯职称词过滤
    if len(name) >= 2 and name[0] in SINGLE_CHAR_SURNAMES:
        ...
    return True
```

**修复**: 在 `is_valid` 末尾或 `_blacklist` 检查后增加：

```python
def is_valid(self, name: str) -> bool:
    if not name or len(name) < 2 or len(name) > 6:
        return False
    if name in self._blacklist:
        return False
    # ★ 新增：拒纯职称词（总监/经理/秘书等不应独立成为角色名）
    from pipeline.nlp_basics import TITLE_WORDS
    if name in TITLE_WORDS:
        return False
    ...
```

**影响**: 任何路径企图将纯职称词作为角色候选时，`name_validator` 直接拦截。这是 **Bug ③ 的第二层防御**，防止 `_match_candidate_to_character` 修复遗漏的情况。

**风险**: 极低。正常人名的姓氏+职称（赵总监、李经理）长度 >= 3，不在 `TITLE_WORDS` 中。

---

#### Bug ① — NER 路径的纯职称词过滤（源头）

**位置**: `_extract_context_speakers()` 的 NER 路径 [speaker_matcher.py:551-553](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L551)

```python
# line 547-564
for pe_text, pe_type in reversed(before_pers_expanded):
    if not self._is_clean_per_entity(pe_text):
        continue
    if not self.name_validator.is_valid(pe_text) or self.name_validator.is_verb(pe_text):
        continue
    # ★ 缺少：直接过滤纯职称词
    is_substring = False
    for seen in seen_names:
        if pe_text in seen or seen in pe_text:
            is_substring = True
            break
    if is_substring:
        continue
    char = self._match_candidate_to_character(pe_text, context_before)
    # ★ 如果 pe_text="总监"，这里会调用 Bug ③ 的逻辑
```

**修复方案**: 在 `name_validator.is_valid` 检查后（line 553-554）增加：

```python
if not self.name_validator.is_valid(pe_text) or self.name_validator.is_verb(pe_text):
    continue
# ★ 新增：NER 提取的纯职称词直接跳过
from pipeline.nlp_basics import TITLE_WORDS
if pe_text in TITLE_WORDS:
    continue
```

**影响**: 在 NER 提取阶段直接过滤纯职称词，让它根本不会进入 `_match_candidate_to_character` 的逻辑。

**注意**: 如果 Bug ③ 已修复，此修复属于冗余防御。但仍然建议加上，**以减少 NER 路径的无效调用**。

---

#### Bug ④ — 语境优先路径改为词边界匹配

**位置**: [speaker_matcher.py:812-830](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L812)

```python
# 方向1：语境角色优先（H-20260516-10）
if context_before and not candidates:
    nearby_window = context_before[-120:]
    all_chars = self.char_manager.get_eligible_characters(self._current_project_id)
    sorted_chars = sorted(all_chars, key=lambda c: -len(c.name))
    for char in sorted_chars:
        if char.name in nearby_window and char.name not in seen_names:  # ★ 子串匹配
            ...
```

**修复方案**: 改为调用 `_is_word_boundary_match`：

```python
    for char in sorted_chars:
        if char.name in seen_names:
            continue
        if not self._is_word_boundary_match(nearby_window, char.name):
            continue
        pos = nearby_window.index(char.name)
        ...
```

**注意**: 此修复在 Bug ③ 修复后属于防复发加固。但由于语境优先路径使用的 `char.name in nearby_window` 本就是子串匹配，理论上如果角色库里同时存在 "总监" 和 "赵总监"，它也会错误命中。**建议一并修复**。

---

### P2-中 ###

#### Bug ⑥ — 临时角色质量门禁

**位置**: `_register_temporary_character()` [speaker_matcher.py:231-254](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L231)

```python
def _register_temporary_character(self, name, context, skip_speech_check=False):
    if not skip_speech_check and not self._has_speech_context(context):
        return None
    if name in self._temp_char_cache:
        return self._temp_char_cache[name]
    # ★ 没有质量门禁：不检查 name 是否是合理的人名
    try:
        gender = self._infer_gender_from_context(name, context)
        char = self.char_manager.add_character(name=name, ...)
        ...
```

**修复方案**（可选）: 在创建前增加质量检查：

```python
def _register_temporary_character(self, name, context, skip_speech_check=False):
    if not skip_speech_check and not self._has_speech_context(context):
        return None
    if name in self._temp_char_cache:
        return self._temp_char_cache[name]
    # ★ 新增：质量门禁
    # 1. 纯职称词不创建
    from pipeline.nlp_basics import TITLE_WORDS
    if name in TITLE_WORDS:
        return None
    # 2. 创建后标记低分待验证（预留）
    ...
```

**说明**: Bug ③ 的 `_match_candidate_to_character` 修复已经包含了此处的职称词检查。额外在此处再加一道是 "深度防御"。

---

#### Bug ⑦ — 候选排序短名惩罚

**位置**: 候选排序逻辑 [speaker_matcher.py:~904](file:///d:/trae/novel-tts-engine/pipeline/speaker_matcher.py#L904)

候选排序按置信度降序排序，但置信度计算没有对短名/纯职称名做惩罚：

```python
# 近因衰减（反粘着机制）
# line ~904
from utils.config import RECENCY_DECAY_RECENT, RECENCY_DECAY_SECOND, RECENCY_DECAY_OTHER
```

**修复方案**（可选）: 在排序前对候选名进行质量加权：

```python
def _penalize_short_title_names(self, candidates):
    """对短名/纯职称名进行置信度惩罚，避免它们错误压过完整名。"""
    from pipeline.nlp_basics import TITLE_WORDS
    result = []
    for name, reason, confidence in candidates:
        if name in TITLE_WORDS:
            confidence *= 0.5  # 纯职称词置信度减半
        elif len(name) <= 2:
            confidence = min(confidence, 0.60)  # 2字名上限
        result.append((name, reason, confidence))
    return sorted(result, key=lambda x: -x[2])
```

---

## 三、修复优先级与执行顺序

### 总体策略

**Break the chain at the earliest practical point.** Bug ③ 是性价比最高的单一修复点——阻断后所有下游子串匹配问题自然消失。但为避免遗漏，建议同时修复 Bug ⑤（防御加固）。

| 优先级 | Bug | 文件:行号 | 变更行数 | 预期效果 | 风险 |
|:-----:|:----|:---------:|:--------:|:--------|:----:|
| **P0** | ③ `_match_candidate_to_character` 拒纯职称词 | speaker_matcher.py:738 | +5行 | **阻断 80% 错误** | 极低 |
| **P0** | ⑤ `_match_from_character_library` 词边界匹配 | speaker_matcher.py:331 + 新方法 | +25行 | 防复发 | 低 |
| **P1** | ② `name_validator.is_valid` 拒纯职称词 | speaker_matcher.py:1829 | +3行 | 防御层加固 | 极低 |
| **P1** | ① NER 路径过滤纯职称词 | speaker_matcher.py:553 | +3行 | 源头拦截 | 极低 |
| **P1** | ④ 语境优先路径词边界匹配 | speaker_matcher.py:817 | +3行 | 防复发 | 低 |
| **P2** | ⑥ 临时角色质量门禁 | speaker_matcher.py:231 | +5行 | 深度防御 | 低 |
| **P2** | ⑦ 候选排序短名惩罚 | speaker_matcher.py:904 | +10行 | 兜底排序 | 低 |

### 推荐执行顺序

```
第一刀（P0，阻断链路）：
  Bug ③ → 立刻解决 80% 问题
  Bug ⑤ → 防止复发

第二刀（P1，防御加固）：
  Bug ② → 验证层拦截
  Bug ① → NER 源头过滤
  Bug ④ → 另一条子串匹配路径

第三刀（P2，兜底）：
  Bug ⑥ → 质量门禁
  Bug ⑦ → 排序惩罚

验证（每刀后）：
  pytest tests/test_urban_long_text.py tests/test_fantasy_long_text.py -v
  python tests/test_no_registration.py

### 第四刀（P0，新信号接入）：SRL ARG0 候选提取

**目的**：接入 HanLP SRL 的 ARG0 语义角色论元，作为与现有规则提取**并行互补**的独立信号源。

**核心逻辑**：SRL 回答"谁做了动作"（句法级），规则提取回答"文本里提到了谁"（词汇级）。两个信号从不同维度观察同一段文本，在候选池合并时通过置信度加权区分优先级。

**加权方式**：距离衰减（替代第一版方案的固定 0.80）

| 距离 | 置信度 | 含义 |
|:----:|:-----:|:------|
| distance=0（同句） | **0.90** | ARG0 = 对话的说话人或直接参与方 |
| distance=1（邻句） | **0.80** | ARG0 在紧邻上下文中出现 |
| distance>1（远句） | **0.65** | 仅背景环境描写，几乎不参与竞争 |

**为什么不用固定值**：长距离背景主语（如"赵总监看着窗外，雨越下越大。他转过身，对李经理说"）如果给固定 0.80，会以不合理的优先级压过真正在对话中的角色。

**预期收益**：

| 测试 | Bug修复后 | + SRL | 增量 |
|:----|:---------:|:-----:|:----:|
| 有预注册-都市 | ~89.4% | **~87-90%** | +0~5pct（注：纯度职称修复后已达天花板） |
| 无预注册-都市 | ~82%+ | **~82-85%** | +0~8pct |

**设计决策（摘自设计存档文档）**：
- `require_library=True`：SRL 候选必须映射到已注册角色，不创建临时角色
- 仅用 `context_before`：SRL 需要完整谓词结构，context_after 谓词不完整
- 不缓存到 NLPResult：SRL 是临时结果，~30ms/句，随用随算
- SRL 的双重定位：预处理层（角色发现）+ 候选信号层（置信度加权），互不冲突
- 文体自适应接入点（预留）：SRL 衰减速度可作为文体自适应的第一个变量

**详细设计**，详见：[SRL_ARG0提取方案.md](file:///d:/trae/novel-tts-engine/docs/SRL_ARG0提取方案.md)

---

## 四、代码变更清单

### 文件: `pipeline/speaker_matcher.py`

#### 变更1 — 导入 TITLE_WORDS（在文件头部）

```python
# 在现有 import 后添加（约 line 16）
from pipeline.nlp_basics import TITLE_WORDS
```

#### 变更2 — Bug ③ 修复：`_match_candidate_to_character` 拒纯职称词

```python
def _match_candidate_to_character(self, candidate_name, context, skip_speech_check=False):
    # 步骤1：精确匹配角色名
    char = self.char_manager.get_character_by_name(candidate_name, self._current_project_id)
    if char: return char
    # 步骤2：别名匹配
    char = self.char_manager.get_character_by_alias(candidate_name, self._current_project_id)
    if char: return char
    # ★ 修复：拒绝纯职称词成为临时角色
    if candidate_name in TITLE_WORDS:
        logger.debug(f"拒绝纯职称词临时角色: '{candidate_name}'")
        return None
    # 步骤3：创建临时角色
    temp_char = self._register_temporary_character(candidate_name, context, skip_speech_check)
    return temp_char
```

#### 变更3 — Bug ⑤ 修复：新增词边界匹配方法

在 `_match_from_character_library` 方法附近新增（建议在 `extract_mentioned_characters` 之后）：

```python
@staticmethod
def _is_word_boundary_match(text: str, target: str) -> bool:
    """判断 target 是否在 text 中以独立词形式出现（词边界匹配）。

    中文词边界定义：target 前后字符为非中文字符或文本边界。
    """
    idx = text.find(target)
    if idx < 0:
        return False
    # 前边界检查
    if idx > 0:
        prev_char = text[idx - 1]
        if '\u4e00' <= prev_char <= '\u9fff':
            return False
    # 后边界检查
    end = idx + len(target)
    if end < len(text):
        next_char = text[end]
        if '\u4e00' <= next_char <= '\u9fff':
            return False
    return True
```

#### 变更4 — Bug ⑤ 修复：修改 `_match_from_character_library`

```python
def _match_from_character_library(self, narration, locked_only=False):
    if locked_only:
        characters = self.char_manager.get_locked_characters(self._current_project_id)
    else:
        characters = self.char_manager.get_all_characters(self._current_project_id)
    for char in characters:
        if self._is_word_boundary_match(narration, char.name):
            return char
        for alias in char.aliases:
            if self._is_word_boundary_match(narration, alias):
                return char
    return None
```

#### 变更5 — Bug ② 修复：`name_validator` 拒纯职称词

在 `CharacterNameValidator.is_valid()` 中 `PER_BLACKLIST` 检查后增加：

```python
if name in PER_BLACKLIST:
    return False
# ★ 新增：拒纯职称词
if name in TITLE_WORDS:
    return False
```

#### 变更6 — Bug ① 修复：NER 路径跳过纯职称词

在 `_extract_context_speakers` 的 NER 路径（line 553-554）后增加：

```python
if not self.name_validator.is_valid(pe_text) or self.name_validator.is_verb(pe_text):
    continue
# ★ 新增：NER 提取的纯职称词直接跳过
if pe_text in TITLE_WORDS:
    continue
```

#### 变更7 — Bug ④ 修复：语境优先路径改为词边界匹配

```python
for char in sorted_chars:
    if char.name in seen_names:
        continue
    if not self._is_word_boundary_match(nearby_window, char.name):
        continue
    pos = nearby_window.index(char.name)
    ...
```

#### 变更8 — Bug ⑦ 修复：候选排序短名惩罚

在候选排序逻辑（`_extract_context_speakers` 末尾返回前）增加：

```python
# 短名/纯职称词置信度惩罚（防子串匹配复发）
penalized = []
for name, reason, confidence in candidates:
    if name in TITLE_WORDS:
        confidence *= 0.5
    elif len(name) <= 2:
        confidence = min(confidence, 0.60)
    penalized.append((name, reason, confidence))
candidates = sorted(penalized, key=lambda x: -x[2])
```

---

### SRL 第四刀：代码变更

#### 变更9 — `nlp_basics.py` 新增 `extract_srl_arg0s()` 方法

在 `NLPBasics` 类中新增方法：

```python
def extract_srl_arg0s(self, text: str) -> List[str]:
    """
    从文本中提取 SRL ARG0（动作执行者）。

    Args:
        text: 旁白文本

    Returns:
        归一化后的 ARG0 文本列表（按文本中出现的顺序）
        返回空列表 = 无 ARG0 / SRL 不可用
    """
    if not self._initialized or not text or not text.strip():
        return []

    results = []
    try:
        doc = self.pipeline(text)
        srl_data = doc.get('srl', [])
    except Exception:
        return []

    seen = set()
    for pred_group in srl_data:
        for item in pred_group:
            if item[1] == 'ARG0':
                arg0_text = item[0]
                if arg0_text not in seen:
                    seen.add(arg0_text)
                    results.append(arg0_text)

    return results
```

**设计说明**：HanLP SRL 输出结构为 `[[(文本, 论元角色, start, end), ...], ...]`。每个 PRED 组中可能有一个 ARG0，多个谓词可能共享同一个 ARG0，用 `seen` 去重。

#### 变更10 — `speaker_matcher.py` 新增 `_normalize_srl_arg0()` 方法

```python
def _normalize_srl_arg0(self, arg0_text: str) -> Optional[str]:
    """
    对 SRL ARG0 进行归一化，返回纯净的角色候选名。

    步骤A: 去修饰语（"严肃的赵总监" → "赵总监"）
    步骤B: 去头衔后缀（"艾琳法师" → "艾琳"）
    步骤C: CHARACTER_BLACKLIST 非人物过滤
    """
    # 步骤A1: 去除"的"前修饰
    parts = arg0_text.split('的')
    if len(parts) >= 2:
        candidate = parts[-1].strip()
        if len(candidate) >= 2:
            arg0_text = candidate

    if len(arg0_text) < 2:
        return None

    # 步骤A2: 去除方位介词后缀
    for suffix in ['那边', '这边', '上面', '下面', '里面', '外面',
                   '上', '里', '边', '中', '外', '旁边']:
        if arg0_text.endswith(suffix) and len(arg0_text) > len(suffix) + 1:
            arg0_text = arg0_text[:-len(suffix)]

    if len(arg0_text) < 2:
        return None

    # 步骤B: 去头衔后缀
    for title in TITLE_WORDS:
        if arg0_text.endswith(title) and len(arg0_text) > len(title) + 1:
            core = arg0_text[:-len(title)]
            cn_chars = [c for c in core if '\u4e00' <= c <= '\u9fff']
            if 1 <= len(cn_chars) <= 4:
                arg0_text = core
                break

    if len(arg0_text) < 2:
        return None

    # 步骤C: CHARACTER_BLACKLIST 非人物过滤
    if arg0_text in CHARACTER_BLACKLIST:
        return None
    for exclude in CHARACTER_BLACKLIST:
        if exclude in arg0_text:
            return None

    return arg0_text
```

**说明**：需在文件头部新增导入 `from pipeline.pattern_extractor import CHARACTER_BLACKLIST`（如已存在则跳过）。

#### 变更11 — `speaker_matcher.py` 新增 `_extract_srl_arg0_candidates()` 方法

```python
def _extract_srl_arg0_candidates(self, text: str, dialogue_sentence_index: int) -> List[Tuple[str, float]]:
    """
    从文本中提取 SRL ARG0 并计算距离衰减置信度。

    Args:
        text: 旁白文本（context_before 全文）
        dialogue_sentence_index: 对话句在文本中的句索引（用于距离计算）

    Returns:
        [(归一化角色名, 距离衰减置信度), ...]
    """
    if not text or not text.strip():
        return []

    raw_arg0s = self.nlp.extract_srl_arg0s(text)
    if not raw_arg0s:
        return []

    candidates = []
    seen = set()
    for arg0_text in raw_arg0s:
        normalized = self._normalize_srl_arg0(arg0_text)
        if normalized and normalized not in seen:
            seen.add(normalized)
            # 计算距离衰减置信度
            distance = self._calc_srl_distance(text, arg0_text, dialogue_sentence_index)
            if distance == 0:
                confidence = 0.90
            elif distance == 1:
                confidence = 0.80
            else:
                confidence = 0.65
            candidates.append((normalized, confidence))

    return candidates


def _calc_srl_distance(self, text: str, arg0_text: str, dialogue_sentence_index: int) -> int:
    """计算 ARG0 所在句到对话句的距离。

    简化实现：以句号/问号/感叹号/省略号分句，计算 arg0_text 的
    首次出现句索引与 dialogue_sentence_index 的绝对差。
    """
    import re
    sentences = re.split(r'[。！？!?…]+', text)
    arg0_sentence_index = -1
    for i, sent in enumerate(sentences):
        if arg0_text in sent:
            arg0_sentence_index = i
            break
    if arg0_sentence_index < 0:
        return 99
    return abs(arg0_sentence_index - dialogue_sentence_index)
```

#### 变更12 — `speaker_matcher.py` `_extract_context_speakers()` 中插入 SRL 步骤

在步骤2（描述性角色提取 + 过滤）之后、方向1（语境角色优先）之前插入：

```python
# 步骤2.5: SRL ARG0 候选提取（新信号源）
# 使用 HanLP SRL 从 context_before 中提取动作执行者（ARG0），
# 按距离衰减置信度注入候选池。
# 独立于 DescriptiveRoleExtractor 的规则提取路径，互补而非替代。
if context_before and candidates_ready:
    dialogue_sentence_index = len(self._split_sentences(context_before)) - 1
    srl_results = self._extract_srl_arg0_candidates(
        context_before, dialogue_sentence_index
    )
    for role_name, confidence in srl_results:
        if role_name not in seen_names:
            char = self._match_candidate_to_character(
                role_name, context_before,
                skip_speech_check=True, require_library=True
            )
            if char:
                candidates.append((char.name, 'SRL ARG0', confidence))
                seen_names.add(role_name)
```

#### 变更汇总（第四刀）

| 文件 | 变更 | 行数 |
|------|------|:----:|
| `pipeline/nlp_basics.py` | `NLPBasics` 类新增 `extract_srl_arg0s()` | +~20行 |
| `pipeline/speaker_matcher.py` | 新增 `_normalize_srl_arg0()` | +~45行 |
| `pipeline/speaker_matcher.py` | 新增 `_extract_srl_arg0_candidates()` | +~30行 |
| `pipeline/speaker_matcher.py` | 新增 `_calc_srl_distance()` | +~15行 |
| `pipeline/speaker_matcher.py` | `_extract_context_speakers()` 插入步骤2.5 | +~15行 |
| `pipeline/speaker_matcher.py` | 文件头部新增 import | +~2行 |
| **总增** | | **+~127行** |

---

## 五、验证方案

### 5.1 每刀后的回归测试

```bash
# pytest 基线测试（都市 + 西幻）
pytest tests/test_urban_long_text.py tests/test_fantasy_long_text.py -v

# 无预注册测试
python tests/test_no_registration.py

# Pipeline 单元测试
pytest tests/test_pipeline_runner.py -v
```

### 5.2 验收标准

| 标准 | 当前 | Bug修复后 | +SRL后 |
|:----|:---:|:---------:|:------:|
| 都市 pytest | 67.06% | **≥ 85%** | **≥ 87%** |
| 西幻 pytest | 53.8% | **保持不变** | **保持不变** |
| 无预注册-都市 | 70.6% | **≥ 80%** | **≥ 82%** |
| 无预注册-西幻 | 71.9% | **保持不变** | **保持不变** |
| pytest 单元测试 | 20/20 | **全部通过** | **全部通过** |

### 5.3 Bug 修复验证测试点

修复后，以下典型场景应全部正确：

| # | 场景 | 预测 | 说明 |
|:-:|------|:----:|:------|
| 15 | 刘秘书在精致的笔记本上记录着 | 刘秘书 | 不因"笔记本"存"务"子串而误匹配 |
| 21 | 孙工喘着气说 | 孙工 | 不被其他角色干扰 |
| 46 | 张总微笑着说 | 张总 | SRL/描述性角色正确提取 |
| 48 | 张总转身带路 | 张总 | 动作主语正确 |
| 57 | 张总点头 | 张总 | 近因衰减不压过张总 |
| 71 | 刘秘书回答 | 刘秘书 | 动作主语正确 |

### 5.4 SRL 验证测试点（第四刀后）

| # | 场景 | 预测 | SRL 信号 |
|:-:|------|:----:|:---------|
| 同句 | "刘秘书回答" + "[对话]" | 刘秘书 | ARG0=刘秘书, distance=0 → 0.90 |
| 邻句 | "张总倒了两杯茶。然后问道" + "[对话]" | 张总 | ARG0=张总, distance=1 → 0.80 |
| 远句 | "赵总监看着窗外。雨越下越大。他转过身说" + "[对话]" | 赵总监 | ARG0=赵总监, distance>1 → 0.65（不会压过近因候选） |
| 无 ARG0 | "绝对不能放弃阵地" + "[对话]" | 保持现有 | SRL 无输出，不干扰现有逻辑 |

---

## 六、总执行顺序

### 建议批次

```
第一批（四刀全做，一次性验证）：
  第一刀（P0）：Bug ③ + ⑤
  第二刀（P1）：Bug ② + ① + ④
  第三刀（P2）：Bug ⑥ + ⑦
  第四刀（P0）：SRL ARG0 候选提取（变更9-12）
  → 一次性验证

或

分两批（先恢复基线，再加信号）：
  第一批：第一刀 + 第二刀 + 第三刀（Bug 修复）
    → 验证：都市 ≥ 85%
  第二批：第四刀（SRL 接入）
    → 验证：都市 ≥ 87%，西幻不降
```

### 回退方案

```bash
# 回退整个文件（前三刀）
git checkout -- pipeline/speaker_matcher.py

# 回退 SRL 变更（第四刀单独）
git checkout -- pipeline/nlp_basics.py pipeline/speaker_matcher.py
```
