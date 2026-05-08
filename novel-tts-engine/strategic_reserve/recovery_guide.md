# 战略储备模块恢复指南

> 版本: v2.0  
> 日期: 2026-05-08  
> 迁移原因: MVP 聚焦，移除非核心功能

---

## 概述

以下模块已从 `pipeline/` 移至 `strategic_reserve/modules/`，从主流水线中移除。本指南提供完整的恢复步骤。

---

## 储备模块清单

| 模块 | 文件 | 功能 | 移除原因 |
|------|------|------|---------|
| 拟声词检测 | `sfx_detector.py` | 检测文本中的拟声词（如"轰隆"、"沙沙"） | MVP 不需要拟声词 TTS |
| 引号分类 | `quotation_classifier.py` | 区分对话/书面/心理描写 | MVP 仅需对话/旁白 |
| 实体聚类 | `entity_clusterer.py` | 将相似实体名称聚类合并 | 角色识别精度够用，暂不需要 |

---

## 恢复步骤

### 步骤1：移动文件回 pipeline/

```bash
cd d:\trae\novel-tts-engine
move strategic_reserve\modules\sfx_detector.py pipeline\
move strategic_reserve\modules\quotation_classifier.py pipeline\
move strategic_reserve\modules\entity_clusterer.py pipeline\
```

### 步骤2：恢复 pipeline_runner.py 的 import

在 `pipeline/pipeline_runner.py` 的 import 部分添加：

```python
from pipeline.sfx_detector import SfxDetector
from pipeline.entity_clusterer import get_entity_clusterer, EntityClusterer
from pipeline.quotation_classifier import QuotationClassifier, QuotationType
```

### 步骤3：恢复 PipelineRunner.__init__

在 `__init__` 方法中添加：

```python
self.sfx_detector = SfxDetector()
self.entity_clusterer = get_entity_clusterer()
self.quotation_classifier = QuotationClassifier()
```

### 步骤4：恢复 _process_chapter 中的调用

在实体链接之后、说话人匹配之前，恢复拟声词检测：

```python
# 第四步：拟声词检测
self._set_progress("拟声词检测", result.chapter_id, result.chapter_id + 1, 4, "正在检测拟声词...")
sfx_words = self.sfx_detector.detect(content)
```

在句子处理循环中，恢复引号分类：

```python
# 引号内容分类
if '"' in sentence or '"' in sentence:
    quotation_results = self.quotation_classifier.classify_all(sentence)
    if quotation_results:
        best_result = max(quotation_results, key=lambda r: r.confidence)
        quotation_type = best_result.type.value
```

### 步骤5：恢复冷启动聚类

在 `_trigger_cold_start` 方法中恢复 entity_clusterer 调用：

```python
if all_entities:
    self.entity_clusterer.cluster(entities=all_entities, text=self._full_text, write_back=True)
```

### 步骤6：恢复 SentenceData 字段

如果恢复了上述模块，需要同步恢复 `SentenceData` 的相关字段：
- `sfx: List[str]`
- `quotation_type: str`
- `sentence_id: int`
- `sentence_start: int`
- `sentence_end: int`
- `speed: float`
- `tone: str`
- `emotion_text: str`
- `emotion_intensity: float`

---

## 注意事项

1. **数据库兼容性**：恢复模块不需要数据库变更，characters 表已移除的 `activity_weight` 和 `is_confirmed` 字段不受影响
2. **依赖检查**：恢复前确认 `spacy` 模型和其他 NLP 依赖已安装
3. **测试验证**：恢复后运行端到端测试确保流水线正常工作

---

## 决策记录

| 日期 | 决策 | 理由 |
|------|------|------|
| 2026-05-08 | 移入战略储备 | MVP 聚焦，简化数据流 |
| TBD | 评估是否恢复 | 根据用户反馈和产品路线图决定 |
