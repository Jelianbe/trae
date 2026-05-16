# Novel-TTS-Engine v7.0 改进验证清单

## P0 阶段验证

- [ ] P0-1: `pipeline/speech_verb_detector.py` 存在且编译通过
- [ ] P0-1: 8处说话动词定义全部改为从 `speech_verb_detector.py` 获取
- [ ] P0-1: 所有使用说话动词的模块通过 SpeechVerbDetector 获取
- [ ] P0-2: `nlp_basics.py` 中不存在 `_enhance_entities` 及相关方法
- [ ] P0-2: `entity_cleaner.py` 中存在实体增强逻辑
- [ ] P0-2: NER 输出与迁移前一致
- [ ] P0-3: `ROLE_CORE_WORDS` 仅在 `descriptive_role_extractor.py` 中定义
- [ ] P0-3: `speaker_matcher.py` 从 `descriptive_role_extractor` 引用 ROLE_CORE_WORDS
- [ ] P0-4: `descriptive_role_extractor.py` 中不存在 `[^\s...]{1,6}` 通配分支
- [ ] P0-4: 不提取"推开门骑士"等无效描述
- [ ] P0-5: 所有静态集合有来源注释和集合性质标注
- [ ] P0-5: 所有经验枚举集合有上限约束
- [ ] P0-6: `match_by_title` 使用核心词精确匹配（非 `in` 判断）
- [ ] P0-6: 不误匹配包含关系
- [ ] P0-7: `analyze_dialogue` 不再清空 `_recent_speakers`
- [ ] P0-7: 新增 `reset_activity()` 方法可供外部调用
- [ ] P0-8: `_infer_from_address` 不再将听话人作为说话人返回
- [ ] P0-8: `"林轩，你又在偷懒！"` 中林轩不被匹配为说话人
- [ ] P0: **模式B准确率 ≥ 72.6%**（回归测试通过）

## P1 阶段验证

- [ ] P1-1: 后文 `"...",林轩说道` 模式正确识别
- [ ] P1-2: `_is_clean_per_entity` 新增"的"字结构检测
- [ ] P1-2: `面目慈祥的老者`、`手持长剑的骑士` 被正确过滤
- [ ] P1-3: 代词消解失败时返回未解析信号
- [ ] P1-3: 后续步骤可利用性别等信息
- [ ] P1-4: `is_valid_person_name` 存在且工作正常
- [ ] P1-4: `is_valid_role_descriptor` 存在且工作正常
- [ ] P1-4: 代号式名字（"暗刃"、"血手"）不被误拒
- [ ] P1-5: 被动动作主体过滤在 `entity_cleaner.py` 中
- [ ] P1-5: `speaker_matcher.py` 中无被动过滤代码
- [ ] P1-6: 评估脚本支持逐段模式
- [ ] P1-6: 评估脚本支持连续模式
- [ ] N-1: `"林轩，你又在偷懒！"` 中林轩被正确排除
- [ ] N-1: 测试集 P5/P18/P19/P23/P24/P25/P26/P27/P32/P35 正确识别
- [ ] N-2: P4 `"黑衣人抽出长剑。"` 正确识别说话人
- [ ] N-2: P15、P28 正确识别说话人
- [ ] N-4: `"萧炎的剑法果然厉害"` 中"萧炎"不参与候选
- [ ] N-4: 不误排除其他上下文中的"萧炎"
- [ ] P1: **模式B准确率 ≥ 76.0%**

## P2 阶段验证

- [ ] P2-1: `characters` 表存在 `frequency` 字段
- [ ] P2-1: `characters` 表存在 `scope` 字段
- [ ] P2-1: `characters` 表存在 `chapter_ids` 字段
- [ ] P2-1: 角色晋升测试通过（临时→单章→项目→主要）
- [ ] P2-2: 段落间活跃度保持
- [ ] P2-3: 3轮对话 A→B→A→B 正确预测下一说话人
- [ ] P2-4: 不同章节的同名角色不混淆
- [ ] P2-5: 连续模式评估与逐段模式差距 ≤ 2%
- [ ] P2-6: 基线记录文件存在且格式正确
- [ ] P2-6: 修改前后基线自动记录
- [ ] P2: **模式B准确率 ≥ 78.0%**

## 原则合规性验证

- [ ] 原则1: 所有静态集合有语言学来源标注
- [ ] 原则1: 无多处独立维护同一集合
- [ ] 原则2: 无候选时返回"未知"，不猜测
- [ ] 原则3: 无静态映射表（词→角色）
- [ ] 原则3: `match_by_title` 使用精确匹配
- [ ] 原则4: 修改后跑回归测试
- [ ] 原则4: 基线记录完整
- [ ] 原则5: nlp_basics 只做 HanLP 调用
- [ ] 原则5: entity_cleaner 只做实体清洗
- [ ] 原则5: speaker_matcher 只做角色匹配
- [ ] 原则6: 角色频率机制工作正常
- [ ] 原则7: 修复位置正确
- [ ] 原则8: 上下文范围由任务决定
- [ ] 原则8: 评估脚本支持两种模式

## 回归测试

- [ ] `python analysis_reports/评估脚本/evaluate_v6_improvements.py` 全部通过
- [ ] `python tests/run_novel_test.py` 真实小说测试通过
- [ ] 断网环境下功能完全正常
