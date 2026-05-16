# Novel-TTS-Engine v7.0 改进任务清单

## 任务清单

### P0 阶段：原则违反修复 + 代码清理

- [ ] P0-1: 创建 `speech_verb_detector.py` 统一说话动词检测
  - [ ] 创建 `pipeline/speech_verb_detector.py` 模块
  - [ ] 定义 SIMPLE_SPEECH_VERBS、EMOTION_MODIFIED_SPEECH、COMPOUND_ACTION_SPEECH 集合
  - [ ] 实现 `SpeechVerbDetector` 类（is_speech_verb、is_speech_related、get_pattern 方法）
  - [ ] 改造 `speaker_hint_matcher.py` 引用 SpeechVerbDetector
  - [ ] 改造 `speaker_matcher.py` 引用 SpeechVerbDetector
  - [ ] 改造 `context_diversity_validator.py` 引用 SpeechVerbDetector
  - [ ] 改造 `speaker_role_filter.py` 引用 SpeechVerbDetector
  - [ ] 改造 `character_name_validator.py` 引用 SpeechVerbDetector
  - [ ] 删除所有模块中独立的说话动词定义
  - [ ] 验证：模式B准确率不降（≥ 72.6%）

- [ ] P0-2: 将 `nlp_basics._enhance_entities` 迁移到 `entity_cleaner`
  - [ ] 在 `entity_cleaner.py` 中新增实体增强方法
  - [ ] 从 `nlp_basics.py` 中删除 `_enhance_entities` 及相关方法
  - [ ] 更新 `nlp_basics.extract_ner_entities()` 调用链
  - [ ] 验证：NER 输出与迁移前一致
  - [ ] 验证：模式B准确率不降

- [ ] P0-3: 消除 `ROLE_CORE_WORDS` 双重维护
  - [ ] 在 `descriptive_role_extractor.py` 保留唯一一份 `ROLE_CORE_WORDS`
  - [ ] 修改 `speaker_matcher.py` 从 `descriptive_role_extractor` 引用
  - [ ] 验证：无功能变化

- [ ] P0-4: 修复 `MODIFIER_PATTERN` 通配符
  - [ ] 在 `descriptive_role_extractor.py` 中移除 `[^\s，。！？\n「」『』""]{1,6}` 通配分支
  - [ ] 将 `MODIFIER_PATTERN` 重构为有意义的修饰语类别
  - [ ] 验证：不提取"推开门骑士"等无效描述
  - [ ] 验证：仍正确提取有效的描述性角色

- [ ] P0-5: 标注所有静态集合的语言学来源
  - [ ] `PRONOUNS` 添加来源注释
  - [ ] `SELF_REFERENCE_MAP` 添加来源注释
  - [ ] `TITLE_WORDS` 确认来源注释存在
  - [ ] `SINGLE_CHAR_SURNAMES` 确认来源注释存在
  - [ ] `MULTI_CHAR_SURNAMES` 确认来源注释存在
  - [ ] `GENDER_HINTS` 添加来源注释
  - [ ] 所有静态集合添加集合性质标注（封闭/经验枚举）
  - [ ] 所有经验枚举集合添加上限约束（assert 或文档）

- [ ] P0-6: 修复 `match_by_title` 的 `in` 子串匹配
  - [ ] 在 `descriptive_role_extractor.py` 中修改 `match_by_title` 方法
  - [ ] 改为核心词精确匹配（从 `title in char.name` 改为精确匹配）
  - [ ] 验证：不误匹配包含关系

- [ ] P0-7: 移除 `analyze_dialogue` 开头的 `_recent_speakers.clear()`
  - [ ] 在 `speaker_matcher.py` 中移除 `self._recent_speakers.clear()`
  - [ ] 新增 `reset_activity()` 方法供外部显式调用
  - [ ] 验证：段落间活跃度保持

- [ ] P0-8: 修复 `_infer_from_address` 逻辑反转
  - [ ] 在 `speaker_matcher.py` 中修改 `_infer_from_address` 方法
  - [ ] 改为排除听话人而非将听话人作为说话人返回
  - [ ] 验证：`"林轩，你又在偷懒！"` 中林轩不被匹配为说话人
  - [ ] 验证：模式B准确率提升

### P1 阶段：算法缺陷修复 + 准确率提升

- [ ] P1-1: 修复步骤3对 context_after 的跳过逻辑
  - [ ] 在 `speaker_matcher.py._extract_context_speakers` 中修改 context_after 处理
  - [ ] 仅跳过"冒号主语"规则，保留其他规则（说话动词、声音指示等）
  - [ ] 验证：后文 `"...",林轩说道` 模式正确识别

- [ ] P1-2: 扩展 `_is_clean_per_entity` 新增"的"字结构检测
  - [ ] 在 `entity_cleaner.py._is_clean_per_entity` 中新增"XX的YY"模式检测
  - [ ] 验证：`面目慈祥的老者`、`手持长剑的骑士` 被正确过滤
  - [ ] 验证：不误过滤纯人名

- [ ] P1-3: 代词消解失败时传递弱信号
  - [ ] 修改 `pronoun_resolver.py` 返回未解析信号
  - [ ] 修改 `speaker_matcher.py._extract_context_speakers` 接收并处理弱信号
  - [ ] 验证：后续步骤可利用性别等信息

- [ ] P1-4: 区分 `is_valid_person_name` / `is_valid_role_descriptor`
  - [ ] 在 `character_name_validator.py` 中重命名 `is_valid` 为 `is_valid_person_name`
  - [ ] 新增 `is_valid_role_descriptor` 方法（更宽松）
  - [ ] 更新调用方：NER 结果用 `is_valid_person_name`，描述性角色用 `is_valid_role_descriptor`
  - [ ] 验证：代号式名字（"暗刃"、"血手"）不被误拒

- [ ] P1-5: 被动过滤逻辑移入 `entity_cleaner`
  - [ ] 在 `entity_cleaner.py` 中新增被动动作主体过滤
  - [ ] 从 `speaker_matcher.py._extract_context_speakers` 中删除被动过滤代码
  - [ ] 验证：行为与迁移前一致

- [ ] P1-6: 评估脚本新增连续模式
  - [ ] 在 `evaluate_v6_improvements.py` 中新增连续模式
  - [ ] 连续模式：整章连续处理，段落间不 reset_activity
  - [ ] 验证：逐段模式和连续模式均可运行
  - [ ] 验证：连续模式结果与生产环境行为一致

- [ ] N-1: 引号内称呼语 → 非说话人排除
  - [ ] 在 `speaker_matcher.py._extract_context_speakers` 中新增称呼语排除逻辑
  - [ ] 实现 `_ADDRESSEE_EXCLUSION` 正则匹配 `"X，"` 开头模式
  - [ ] 验证：`"林轩，你又在偷懒！"` 中林轩被正确排除
  - [ ] 验证：测试集 P5/P18/P19/P23/P24/P25/P26/P27/P32/P35 正确识别
  - [ ] 验证：模式B准确率 ≥ 76.0%

- [ ] N-2: 动作 → 说话紧邻关联
  - [ ] 在 `speaker_matcher.py._extract_context_speakers` 中新增动作关联逻辑
  - [ ] 检测 context_before 最后一句的主语+动作模式
  - [ ] 仅在候选池为空时触发，置信度 0.72
  - [ ] 验证：P4 `"黑衣人抽出长剑。\n"把东西交出来。"` 正确识别
  - [ ] 验证：P15、P28 正确识别

- [ ] N-4: 对话中"X的"所有格排除
  - [ ] 在 `speaker_matcher.py.analyze_dialogue` 中新增所有格过滤
  - [ ] 实现 `_POSSESSIVE_PATTERN` 匹配对话中的 `"X的YY"` 结构
  - [ ] 验证：`"萧炎的剑法果然厉害"` 中"萧炎"不参与候选
  - [ ] 验证：不误排除其他上下文中的"萧炎"

### P2 阶段：架构级重构

- [ ] P2-1: 实现角色频率机制
  - [ ] 修改 `characters` 表结构（新增 frequency、scope、chapter_ids 字段）
  - [ ] 在 `character_manager.py` 中实现频率计数器
  - [ ] 实现四层角色结构（临时/单章/项目/主要）
  - [ ] 实现频率阈值晋升逻辑
  - [ ] 匹配优先级按层级递减
  - [ ] 验证：角色晋升测试通过
  - [ ] 验证：模式B准确率 ≥ 78.0%

- [ ] P2-2: 引入段落级和章节级上下文
  - [ ] 修改 `_recent_speakers` 维护逻辑
  - [ ] 实现章节级别的角色活跃度追踪
  - [ ] 验证：跨段落活跃度保持

- [ ] P2-3: 引入对话轮次模型
  - [ ] 创建 `pipeline/dialogue_turn_tracker.py`
  - [ ] 实现 `DialogueTurnTracker` 类
  - [ ] 实现 A→B→A→B 模式推断
  - [ ] 集成到 `speaker_matcher.py`
  - [ ] 验证：3轮对话正确预测下一说话人

- [ ] P2-4: 角色消歧机制
  - [ ] 实现场景隔离（记录角色出现的章节/段落范围）
  - [ ] 实现同名角色区分
  - [ ] 验证：不同章节的"黑衣人"不混淆

- [ ] P2-5: 评估脚本支持连续模式（P1-6 的完整实现）
  - [ ] 完善连续模式评估
  - [ ] 验证：连续模式与逐段模式差距 ≤ 2%

- [ ] P2-6: 基准锁定机制
  - [ ] 创建 `analysis_reports/基线记录.md`
  - [ ] 实现自动记录修改前后基线的逻辑
  - [ ] 验证：每次修改后基线记录更新

## 任务依赖

- P0-1 无依赖，可与其他 P0 任务并行
- P0-2 无依赖，可与其他 P0 任务并行
- P0-3 无依赖
- P0-4 无依赖
- P0-5 无依赖
- P0-6 无依赖
- P0-7 无依赖
- P0-8 无依赖
- P1-1 无依赖
- P1-2 无依赖
- P1-3 无依赖
- P1-4 无依赖
- P1-5 依赖 P0-2（entity_cleaner 需要存在增强逻辑）
- P1-6 无依赖
- N-1 依赖 P0-8（address 修复必须先完成）
- N-2 无依赖
- N-4 无依赖
- P2-1 无依赖
- P2-2 依赖 P0-7（_recent_speakers 不再清空）
- P2-3 依赖 P2-2（需要章节级上下文）
- P2-4 无依赖
- P2-5 依赖 P1-6（评估脚本连续模式基础）
- P2-6 无依赖

## 执行顺序建议

### 第一波（P0 独立任务，可并行）
1. P0-1: speech_verb_detector.py
2. P0-2: 迁移实体增强
3. P0-3, P0-4, P0-5, P0-6, P0-7, P0-8（并行）

### 第二波（P0 完成后回归测试）
- 运行评估脚本，确认准确率 ≥ 72.6%

### 第三波（P1 任务）
1. P1-1, P1-2, P1-3, P1-4, N-2, N-4（并行，无依赖）
2. P1-5（依赖 P0-2）
3. N-1（依赖 P0-8）
4. P1-6（无依赖）

### 第四波（P1 完成后回归测试）
- 运行评估脚本，确认准确率 ≥ 76.0%

### 第五波（P2 任务）
1. P2-1: 角色频率机制
2. P2-2: 段落级上下文
3. P2-3: 对话轮次模型（依赖 P2-2）
4. P2-4: 角色消歧机制
5. P2-5: 评估脚本连续模式
6. P2-6: 基准锁定机制

### 最终验证
- 运行评估脚本，确认准确率 ≥ 78.0%
- 运行 `tests/run_novel_test.py` 真实小说测试
