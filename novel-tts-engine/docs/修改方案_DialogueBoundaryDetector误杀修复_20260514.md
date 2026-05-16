# 修改方案：DialogueBoundaryDetector 误杀修复

- **日期**：2026-05-14
- **问题**：`DialogueBoundaryDetector` 在修仙传真实文本上 27 条引号仅放行 1 条，误杀率 96.3%
- **优先级**：P0（阻断全文本分析 pipeline）

---

## 一、问题定位

### 1.1 触发链路

```
analyze_dialogue() 
  → DIALOGUE_PATTERNS 提取 27 条引号
  → DialogueBoundaryDetector.detect_all() 过滤
  → 仅保留 1 条（is_dialogue=True）
  → 其余 26 条被判定为非对话，丢弃
  → speaker_matcher 只收到 1 条对话候选项
```

### 1.2 为何之前未暴露

| 之前的测试 | 测试了什么 | 绕过了什么 |
|-----------|----------|-----------|
| pytest 单元测试 | 函数级别正确性 | 端到端数据流 |
| Phase 1-3 验证 | 类/方法是否存在 | 数据通量 |
| baseline_rules_speaker | 预提取对话片段上的匹配准确率 | **对话检测本身** |
| LLM benchmark | 预提取对话片段上的匹配准确率 | 同上 |

**核心盲区**：所有测试都在"给定对话文本"的前提下运行，从未测试过"从小说原文中提取对话"这一步。

`DialogueBoundaryDetector` 在 benchmark 场景下也从未被触发——因为 `_build_dialogue_cache_from_filtered()` 是本次会话新增的调用路径。

### 1.3 修仙传 27 条引号诊断数据

#### 明确是对话但被过滤的（22 条）

| 引号内容 | 过滤原因 | confidence |
|---------|---------|:----------:|
| "不甘心啊……" | 含省略号→内心独白 | 0.27 |
| "孙项明！" | 15字内无说话动词 | 0.35 |
| "规矩都懂……林家自有灵晶丹药补偿。" | 15字内无说话动词 | 0.35 |
| "明白。" | 15字内无说话动词 | 0.35 |
| "哟，老孙！你也来了啊！" | 15字内无说话动词 | 0.35 |
| "郭道友。" | 15字内无说话动词 | 0.35 |
| "嘿，这次准备往哪边探？" | — | ✅ 唯一通过 |
| "听说东边的'火鸦涧'……油水也足啊。" | 15字内无说话动词 | 0.35 |
| "我自知斤两，还是去老地方'幽石林'碰碰运气。" | 15字内无说话动词 | 0.35 |
| "幽石林好啊，稳妥！" | 15字内无说话动词 | 0.35 |
| "那咱们……各凭机缘？" | 省略号+无说话动词 | 0.35 |
| "自然。" | 15字内无说话动词 | 0.35 |
| "郭垣？！" | 15字内无说话动词 | 0.40 |
| "哼，反应倒快！" | 15字内无说话动词 | 0.35 |
| "可惜，没用！……" | 书本引用模式误判 | 0.28 |
| "想要？自己来拿！" | 书本引用模式误判 | 0.28 |
| "找死！" | 无抑制理由 | 0.43 |
| "哈哈！中了老子的'蛇涎毒'……" | 15字内无说话动词 | 0.35 |
| …以及其余 4 条类似情况 | 同上 | — |

#### 明确是拟声词/地名引用，应被过滤的（4 条）

| 引号内容 | 类型 | 过滤原因 |
|---------|------|---------|
| "嗤！" | 拟声词 | 单字+叹号 |
| "滋滋" | 拟声词 | 无标点双字词 |
| "噗！" | 拟声词 | 单字+叹号 |
| "幽石林"（孤立引用） | 地名 | 纯名词短语 |

#### 争议（1 条）

| 引号内容 | 说明 |
|---------|------|
| "命运" | 修辞强调，不是对话。过滤正确 |

---

## 二、根因分析

### 2.1 策略 1（15 字窗口）是误杀的主因

**技术事实**：策略 1 在窗口内找不到说话动词时，不是"不加分"，而是"加 suppress 标签"。在所有策略中，如果存在 suppression 且无 reasons，最终判定为非对话。

**在修仙传上的表现**：
- 22/27 条引号被策略 1 标记为"15字内无说话动词"
- 修仙文对话经常使用隐含说话方式，动词距离引号远超 15 字
- 例如 "郭垣凑近了些，压低声音，"之后还有 12 字才到引号，加上标点和换行，实际距离可能超过 20 字

**结论**：15 字窗口在 benchmark 数据集上有效（因为对话片段是裁剪过的），但在原始文本中失效。

### 2.2 策略 2（省略号→内心独白）误杀太宽

修仙/玄幻文中大量对话包含"……"（表示停顿或犹豫），不是因为省略号就不是对话：

| 引号内容 | 实际语境 | 判定 |
|---------|---------|------|
| "不甘心啊……" | 角色自言自语 | ❌→内心独白 |
| "那咱们……各凭机缘？" | 两人对话 | ❌→内心独白 |

### 2.3 策略 3（书本引用模式）覆盖面过宽

"写着"、"记载"等关键词的匹配半径为 30 字符，在小说行文中频繁触发，且引号内容过长（>100字）不一定等于引用。

---

## 三、修改方案

### 3.1 核心思路

**将 `DialogueBoundaryDetector` 从"判定对话/非对话"改为"高置信度过滤非对话"。**

当前逻辑：
```
所有引号 → 多策略打分 → is_dialogue=True/False → 丢弃 False 的
```

修改后逻辑：
```
所有引号 → 只过滤高置信度非对话 → 其余全部放行 → 交给 speaker_matcher
```

### 3.2 具体修改项

#### 修改 1：策略 1 不再作为抑制信号

**文件**：`pipeline/dialogue_boundary_detector.py`  
**位置**：`_strategy1_speech_verb_anchor()` 方法，约 L484-487

**现状**：
```python
# 如果窗口内无说话动词，降低分数（但不完全否定）
if not before_verb and not after_verb:
    score += 0.2
    suppressions.append(f"策略1：引号前后{self.anchor_window}字内无说话动词")
```

**修改**：
```python
# 如果窗口内无说话动词，不扣分，不加抑制标签
# 理由：15字窗口在网文语境下过短，说话动词经常距离引号较远。
# 此策略只做加分（有动词=强信号），不做减分（无动词≠非对话）。
if not before_verb and not after_verb:
    score += 0.3  # 中性分数，既不支持也不抑制
```

**影响**：策略 1 从"抑制信号"变为"纯加分信号"。有说话动词加高分，无说话动词不扣分。

#### 修改 2：省略号不再作为抑制信号

**文件**：`pipeline/dialogue_boundary_detector.py`  
**位置**：`_strategy2_content_structure()` 方法，约 L553-556

**现状**：
```python
# 检查6：含省略号（可能是思绪/内心独白）
if re.search(r'[…\.\.\.]{2,}', text):
    score -= 0.2
    suppressions.append("策略2：含省略号，可能是内心独白")
```

**修改**：删除此检查。
```python
# 省略号不再作为抑制信号
# 理由：网文对话中大量使用"……"表示停顿/犹豫/语境留白，
# 不是内心独白的可靠信号。
```

**影响**：`"不甘心啊……"`、`"那咱们……各凭机缘？"` 等正常对话不再被误杀。

#### 修改 3：单/双字词抑制仅对拟声词生效

**文件**：`pipeline/dialogue_boundary_detector.py`  
**位置**：`_strategy2_content_structure()` 方法，约 L545-551

**现状**：
```python
# 检查5：无标点的单/双字词
if (
    _SINGLE_WORD_PATTERN.match(text)
    and not has_sentence_end
    and not has_modal_particle
):
    score -= 0.3
    suppressions.append("策略2：无标点单/双字词，可能是物品名/地名")
```

**修改**：
```python
# 检查5：无标点的单/双字词——只在高置信度拟声词/地名时才抑制
if (
    _SINGLE_WORD_PATTERN.match(text)
    and not has_sentence_end
    and not has_modal_particle
):
    # 进一步检查：只有当词明确不是对话时才抑制
    # 拟声词特征：重叠字/韵母重复（滋滋、沙沙、哗哗）
    # 地名特征：专有名词后缀
    is_onomatopoeia = len(text) == 2 and text[0] == text[1]  # 叠字拟声词
    is_proper_noun = any(text.endswith(suffix) for suffix in _PROPER_NOUN_SUFFIXES)
    if is_onomatopoeia or is_proper_noun:
        score -= 0.3
        suppressions.append("策略2：无标点单/双字词，明确为非对话（拟声/地名）")
    # 否则不抑制——可能是呼唤名/简短回应（如"明白。"、"找死！"这类有标点的不走这个分支）
```

**影响**："滋滋"仍然被过滤，但"明白"这类不会被此分支误杀。

#### 修改 4：策略 3 书本引用——缩小匹配范围

**文件**：`pipeline/dialogue_boundary_detector.py`  
**位置**：`_strategy3_quote_pattern_suppression()` 方法，约 L586

**现状**：
```python
context_range = 30
```

**修改**：
```python
context_range = 15  # 缩小为 15 字符，减少远端误匹配
```

**额外修改**（策略 3 检查 2，约 L598-605）：
```python
# 关键词必须在引号前 10 字内（原为 20 字）
if kw in before_context:
    kw_pos = before_context.rfind(kw)
    if len(before_context) - kw_pos <= 10:  # 从 20 改为 10
```

**影响**：减少策略 3 的误触发范围。

#### 修改 5：关键——`_detect_single` 判定逻辑修改

**文件**：`pipeline/dialogue_boundary_detector.py`  
**位置**：`_detect_single()` 方法，约 L400-411

**现状**：
```python
# 有抑制理由但无支持理由 → 非对话
elif result.suppression_reasons and not result.reasons:
    result.is_dialogue = False
    result.confidence = min(result.confidence, 0.4)
# 既有支持也有抑制 → 降低置信度
elif result.suppression_reasons:
    result.confidence *= 0.7
    result.is_dialogue = result.confidence >= 0.5
# 无抑制理由 → 默认对话
else:
    result.is_dialogue = result.confidence >= 0.5
```

**修改**：
```python
# 修改后的判定逻辑：
# 不轻易判定为非对话。只有以下情况才判非对话：
# 1. 空引号内容（已在前面处理）
# 2. 明确拟声词（策略2-检查4：单字+叹号）且无其他支持信号
# 3. 明确地名引用（策略2-检查3：纯名词+专有后缀）且无标点、无语气词

is_onomatopoeia = any("拟声词" in r for r in result.suppression_reasons)
is_place_name = any("物品/地名" in r for r in result.suppression_reasons)
has_support = len(result.reasons) > 0

if is_onomatopoeia and not has_support:
    result.is_dialogue = False
    result.confidence = 0.2
elif is_place_name and not has_support:
    result.is_dialogue = False
    result.confidence = 0.3
else:
    # 其余情况全部放行，交给 speaker_matcher + LLM 兜底
    result.is_dialogue = True
    result.confidence = max(result.confidence, 0.5)
```

**这是核心改动**：将"不确定时默认否定"改为"不确定时默认放行"。

---

## 四、预期效果

### 4.1 修仙传 27 条引号的预期变化

| 类别 | 当前 | 修改后 |
|------|:----:|:------:|
| 判定为对话 | 1 | 23 |
| 判定为非对话（拟声词） | — | 3（"嗤！"、"滋滋"、"噗！"） |
| 判定为非对话（地名） | — | 1（孤立"幽石林"引用） |
| 正确放行率 | 3.7% | ~85% |

### 4.2 对比 HybridSpeakerMatcher 的接收量

| | 当前 | 修改后 |
|---|:---:|:-----:|
| 第一章对话候选 | 1 条 | ~23 条 |
| speaker_matcher 可匹配 | 1 个对话 | 23 个对话 |
| LLM 可兜底范围 | 无（数据被提前截断） | 全部对话 |

### 4.3 风险的诚实评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|:----:|------|---------|
| 拟声词被误放行 | 低 | "滋滋"进入对话候选 | 叠字检测捕获大部分 |
| 心理独白被放行 | 中 | "不甘心啊……"被当对话 | 即使误放行，speaker_matcher 也无法匹配到说话人（无显式人名），LLM 兜底会判定 unknown |
| 地名引用被放行 | 低 | "幽石林"进入候选 | 孤立引用无法匹配说话人，不会造成污染 |
| 已有的 benchmark 退化 | 低 | 预提取片段不经过此组件 | 不受影响 |

---

## 五、验证方案

### 5.1 必须跑的测试（修改后立即执行）

1. `python tests/baseline_rules_speaker.py` — 规则系统基线不能退化（预期：47.1% 不变）
2. `python tests/test_llm_speaker_benchmark.py` — LLM benchmark 不能退化（预期：100% 不变）
3. 仙修传全文本测试 — 对话识别率应显著提升（预期：第一章从 1→20+ 条对话）

### 5.2 关注指标

| 指标 | 当前基线 | 修改后预期 | 红区 |
|------|:------:|:--------:|:----:|
| 说话人基准 47.1% | 47.1% | 47.1% | <45% |
| LLM benchmark 100% | 100% | 100% | <98% |
| 修仙传对话识别率 | 3.7% | >50% | <30% |
