# Novel-TTS-Engine v7.0 说话人识别改进计划

## Why
当前说话人匹配准确率基线为 72.6%，低于目标 74%。经代码审查发现：说话动词在 8 处独立维护、模块职责越界、上下文窗口割裂、多个算法漏洞。v7.0 改进计划通过 21 项改进（P0/P1/P2 三阶段）系统性修复这些问题，目标将准确率提升至 78%+。

## What Changes
### P0 阶段（原则违反修复 + 代码清理）
- P0-1: 创建 `speech_verb_detector.py` 统一说话动词检测（8处合并为1处）
- P0-2: 将 `nlp_basics._enhance_entities` 迁移到 `entity_cleaner`
- P0-3: 消除 `ROLE_CORE_WORDS` 双重维护
- P0-4: 修复 `MODIFIER_PATTERN` 通配符
- P0-5: 标注所有静态集合的语言学来源和上限约束
- P0-6: 修复 `match_by_title` 的 `in` 子串匹配，改为核心词精确匹配
- P0-7: 移除 `analyze_dialogue` 开头的 `_recent_speakers.clear()`
- P0-8: 修复 `_infer_from_address` 将听话人当说话人的逻辑反转

### P1 阶段（算法缺陷修复 + 准确率提升）
- P1-1: 修复步骤3对 context_after 的跳过逻辑
- P1-2: 扩展 `_is_clean_per_entity` 新增"的"字结构检测
- P1-3: 代词消解失败时传递弱信号
- P1-4: 区分 `is_valid_person_name` / `is_valid_role_descriptor`
- P1-5: 被动过滤逻辑移入 `entity_cleaner`
- P1-6: 评估脚本新增连续模式
- N-1: 引号内称呼语 → 非说话人排除（预计 +4~6%）
- N-2: 动作 → 说话紧邻关联（预计 +2~3%）
- N-4: 对话中"X的"所有格排除（预计 +0.5~1%）

### P2 阶段（架构级重构）
- P2-1: 实现角色频率机制（四层结构 + 晋升）
- P2-2: 引入段落级和章节级上下文
- P2-3: 引入对话轮次模型
- P2-4: 角色消歧机制
- P2-5: 评估脚本支持连续模式
- P2-6: 基准锁定机制

## Impact
- **Affected specs**: 角色库与说话人匹配（AC-005）、进度管理（AC-007）
- **Affected code**: 
  - 新建: `pipeline/speech_verb_detector.py`
  - 重大修改: `pipeline/speaker_matcher.py`、`pipeline/nlp_basics.py`、`pipeline/entity_cleaner.py`
  - 修改: `pipeline/speaker_hint_matcher.py`、`pipeline/descriptive_role_extractor.py`、`pipeline/context_diversity_validator.py`、`pipeline/speaker_role_filter.py`、`pipeline/character_name_validator.py`、`pipeline/character_manager.py`、`pipeline/pronoun_resolver.py`、`pipeline/self_reference_inferrer.py`
  - 修改: `analysis_reports/评估脚本/evaluate_v6_improvements.py`
- **Database changes**: P2-1 需新增 `frequency`、`scope`、`chapter_ids` 字段到 `characters` 表

## ADDED Requirements

### Requirement: 说话动词统一检测
The system SHALL provide a single authoritative source for all speech verb detection through `SpeechVerbDetector` module. All modules requiring speech verb information SHALL obtain it through this module.

### Requirement: 称呼语排除规则
When dialogue content starts with `"X，"` or `"X！"` (where X is 2-4 Chinese characters followed by punctuation), the system SHALL exclude X from being a candidate speaker. X is the addressee, not the speaker.

### Requirement: 角色频率层级
The system SHALL maintain four role levels based on cross-chapter frequency:
- Temporary (freq < 3, in-memory only)
- Chapter (3 ≤ freq < 10, single chapter)
- Project (10 ≤ freq < 30, cross-chapter)
- Main (freq ≥ 30 or user-locked)

## MODIFIED Requirements

### Requirement: 说话人匹配准确率（AC-005）
The system SHALL achieve speaker matching accuracy ≥ 78.0% on the standard 73-sentence test set (current baseline: 72.6%, v7.0 target: 78.0%).

### Requirement: 实体清洗职责（原则5）
`entity_cleaner.py` SHALL handle all entity post-processing (enhancement, trimming, filtering). `nlp_basics.py` SHALL only perform HanLP API calls with zero post-processing.

## REMOVED Requirements
None.
