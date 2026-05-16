# 基于全面功能测试的改进方案 Spec

## Why

全面功能测试暴露了 22.6% 的准确率（287条短用例 + 5套长文本），远低于预期。根因分析识别出5类核心问题，其中对话边界检测（58条FP）和短用例缺上下文（184条"未知"）是最大的gap。需要将测试驱动的修复建议整合到现有的 `代码审查与改进方案_v6.1_20260513.md` 文档中，并规划后续执行任务。

## What Changes

- **更新改进方案文档**：将测试发现的5个修复建议作为 P0-NEW ~ P2-NEW 插入到改进方案中
- **新增测试用例上下文修复任务**：评估脚本需使用完整段落而非单句对话进行评测
- **新增对话边界检测任务**：基于说话动词锚定 + 引号内容结构分析，而非whitelist

## Impact

- **Affected specs**: 对话边界检测（新能力）、评估脚本改进（现有P1-6扩展）、entity_cleaner改进（现有P1-2扩展）
- **Affected code**: `pipeline/speaker_matcher.py`、`pipeline/entity_cleaner.py`、`analysis_reports/评估脚本/`、`docs/代码审查与改进方案_v6.1_20260513.md`

## ADDED Requirements

### Requirement: 对话边界检测增强
The system SHALL NOT treat non-dialogue quoted content as dialogue.

#### Scenario: 地名/物品名引用（引号内无说话动词锚点）
- **WHEN** paragraph contains `"断龙崖"` or `"地火苔"` without nearby speech verb
- **THEN** it shall NOT be detected as dialogue (no false positive)

#### Scenario: 古籍/石碑文字引用
- **WHEN** paragraph contains `"入此门者"…刻于石碑` pattern
- **THEN** it shall NOT be detected as dialogue

#### Scenario: 拟声词/感叹词
- **WHEN** quoted content is single character + exclamation mark (e.g., `"轰！"`)
- **THEN** it shall NOT be detected as dialogue

### Requirement: 评估上下文完整性
The evaluation script SHALL use full paragraph/chapter context, not isolated dialogue sentences.

#### Scenario: GT short case evaluation
- **WHEN** evaluating a dialogue from GT JSON
- **THEN** the system receives the full paragraph containing that dialogue as input
- **AND** the dialogue detection result is matched against expected speakers by text

## MODIFIED Requirements

### Requirement: entity_cleaner 候选保留策略 (P1-2 扩展)
The system SHALL NOT aggressively filter out entities when speech context is detected nearby.

### Requirement: 改进方案文档结构
The document `代码审查与改进方案_v6.1_20260513.md` SHALL be updated with:
- Section 5.5: 测试驱动的修复方案（P0-NEW ~ P2-NEW）
- Updated DoD targets reflecting test baselines
- Updated error analysis summary
