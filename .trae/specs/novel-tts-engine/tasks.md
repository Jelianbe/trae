# Novel-TTS-Engine - 实现计划（分解与优先级任务列表）

## 阶段划分与里程碑

### 阶段一：骨架搭建 + 选型验证（预估2-3天）
**里程碑 M1**: 所有核心任务已审核，进入阶段二

**阶段一 DoD（准出标准）**:
1. pytest tests/ 全部通过
2. sqlite3 novel_tts.db ".schema" 输出与设计文档一致
3. 启动 app.py，前端无报错，显示正确分章数和词性标签
4. 断网环境下功能完全正常

### 阶段二：对话/旁白分离 + 拟声词（预估2-3天）
**里程碑 M2**: 所有核心任务已审核，进入阶段三

**阶段二 DoD**:
1. 对话/旁白分类准确率 ≥ 85%
2. 拟声词识别准确率 ≥ 95%
3. 前端颜色区分清晰

### 阶段三：角色库 + 说话人匹配（预估4-5天）
**里程碑 M3**: 所有核心任务已审核，进入阶段四

**阶段三 DoD**:
1. 明确对话说话人匹配准确率 ≥ 95%
2. "他/她"性别唯一匹配准确率 ≥ 80%
3. 交织对话正确拆分

### 阶段四：进度管理与编辑保护（预估2天）
**里程碑 M4**: 所有核心任务已审核，进入阶段五

**阶段四 DoD**:
1. 范围分析功能正常
2. 中断续接功能正常
3. 用户修改持久化不丢失

### 阶段五：情绪标注 + TTS 导出（预估2-3天）
**里程碑 M5**: 所有核心任务已审核，进入阶段六

**阶段五 DoD**:
1. 情绪标签正确标注
2. 导出 JSON 格式正确
3. 导出 SSML 格式符合规范

---

## 任务清单

### 阶段一：骨架搭建 + 选型验证

## [已完成] T-001: 项目骨架搭建与环境初始化
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 创建项目目录结构
  - 使用uv初始化虚拟环境
  - 安装核心依赖（fastapi, streamlit, hanlp）
  - 配置前端禁用遥测
- **Acceptance Criteria Addressed**: AC-001
- **Test Requirements**:
  - `programmatic` TR-T001-01: 目录结构与设计文档一致（pipeline/, db/, models/, utils/, frontend/）✅ 已完成
  - `programmatic` TR-T001-02: 依赖安装成功，无版本冲突 ✅ 已完成
  - `human-judgement` TR-T001-03: Streamlit启动无报错 ✅ 已完成
- **Notes**: Python 3.11.9已通过winget安装，虚拟环境已创建，所有依赖已安装成功

## [已完成] T-002: 数据库层实现
- **Priority**: P0
- **Depends On**: T-001
- **Description**: 
  - 创建schema.sql建表语句（角色库、章节进度、句子编辑）
  - 实现db_utils.py连接与查询封装
- **Acceptance Criteria Addressed**: AC-001, AC-007
- **Test Requirements**:
  - `programmatic` TR-T002-01: SQLite表结构与设计文档一致 ✅ 已完成
  - `programmatic` TR-T002-02: pytest测试全部通过 ✅ 已完成（21个测试全部通过）
- **Notes**: 确保断网环境下数据库功能正常

## [已完成] T-003: 分章模块实现
- **Priority**: P0
- **Depends On**: T-001
- **Description**: 
  - 实现chapter_splitter.py
  - 正则匹配章节标题
  - 支持多种常见章节格式
  - 新增卷层级支持
- **Acceptance Criteria Addressed**: AC-002
- **Test Requirements**:
  - `programmatic` TR-T003-01: 正确识别常见章节格式（第X章、第一章等）✅ 已完成
  - `programmatic` TR-T003-02: 返回正确的章节数量和内容边界 ✅ 已完成
  - `programmatic` TR-T003-03: 支持卷层级，新卷后章节重新计数 ✅ 已完成
- **Notes**: 需要覆盖多种章节命名模式，支持卷一/卷二等卷层级结构

## [已完成] T-004: 基础NLP模块实现
- **Priority**: P0
- **Depends On**: T-001
- **Description**: 
  - 实现nlp_basics.py封装HanLP
  - 提供分词、词性标注、NER接口
- **Acceptance Criteria Addressed**: AC-002
- **Test Requirements**:
  - `programmatic` TR-T004-01: 正确输出分词结果 ✅ 已完成
  - `programmatic` TR-T004-02: 正确识别命名实体（人物、地点、机构） ✅ 已完成
- **Notes**: 使用HanLP多任务模型CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH

## [已完成] T-014: 模型离线初始化脚本
- **Priority**: P1
- **Depends On**: T-001
- **Description**: 
  - 实现scripts/init_models.py
  - 下载并初始化所有预置模型
- **Acceptance Criteria Addressed**: AC-001
- **Test Requirements**:
  - `programmatic` TR-T014-01: 模型下载完成，目录结构正确 ✅ 已完成
  - `programmatic` TR-T014-02: 总模型体积≤1.4GB ✅ 已完成（935.3MB）
- **Notes**: 需要网络下载模型（仅初始化阶段）

---

### 阶段二：对话/旁白分离 + 拟声词

## [已完成] T-005: 对话/旁白分类器实现
- **Priority**: P0
- **Depends On**: T-004, M1
- **Description**: 
  - 实现dialogue_classifier.py
  - 规则+FastText混合分类策略
- **Acceptance Criteria Addressed**: AC-003
- **Test Requirements**:
  - `programmatic` TR-T005-01: 分类准确率≥85% ✅ 已完成
  - `programmatic` TR-T005-02: 规则覆盖约70%场景 ✅ 已完成
- **Notes**: 规则优先，统计兜底

## [已完成] T-006: 拟声词检测器实现
- **Priority**: P1
- **Depends On**: T-004, M1
- **Description**: 
  - 实现sfx_detector.py
  - 三重判定：词库 + 正则 + 上下文
  - 构建拟声词词典
- **Acceptance Criteria Addressed**: AC-004
- **Test Requirements**:
  - `programmatic` TR-T006-01: 拟声词识别准确率≥95% ✅ 已完成
  - `programmatic` TR-T006-02: 正确标注sfx类型 ✅ 已完成
- **Notes**: 拟声词库包含70+常见中文拟声词

---

### 阶段三：角色库 + 说话人匹配

## [待开始] T-007: 角色库管理实现
- **Priority**: P0
- **Depends On**: T-002, T-004, M2
- **Description**: 
  - 实现character_manager.py
  - SQLite持久化 + 聚类 + 向量
  - 支持角色别名管理
- **Acceptance Criteria Addressed**: AC-005
- **Test Requirements**:
  - `programmatic` TR-T007-01: 角色库CRUD操作正常
  - `programmatic` TR-T007-02: 角色别名正确映射
- **Notes**: 角色向量化使用FastText

## [待开始] T-008: 说话人匹配器实现
- **Priority**: P0
- **Depends On**: T-005, T-007, M2
- **Description**: 
  - 实现speaker_matcher.py
  - 四级匹配：别名/标准名/向量/活跃度
  - 使用BGE-small L2进行语义相似度排序
- **Acceptance Criteria Addressed**: AC-005
- **Test Requirements**:
  - `programmatic` TR-T008-01: 明确对话匹配准确率≥95%
  - `programmatic` TR-T008-02: 交织对话正确拆分
- **Notes**: BGE-small使用ONNX版本

---

### 阶段四：进度管理与编辑保护

## [待开始] T-010: 流水线调度器实现
- **Priority**: P0
- **Depends On**: T-003, T-004, T-005, T-006, T-007, T-008, T-009, M3
- **Description**: 
  - 实现pipeline_runner.py
  - 总调度，暴露analyze_chapters()接口
  - 支持进度追踪
- **Acceptance Criteria Addressed**: AC-001, AC-007
- **Test Requirements**:
  - `programmatic` TR-T010-01: 完整流程正确输出JSON结构
  - `programmatic` TR-T010-02: 进度追踪正常
- **Notes**: JSON输出包含type/speaker/emotion/speed/tone

## [待开始] T-011: RESTful API实现
- **Priority**: P0
- **Depends On**: T-010, M3
- **Description**: 
  - 实现FastAPI后端接口
  - /api/analyze, /api/pause, /api/progress, /api/edit_sentence等
- **Acceptance Criteria Addressed**: AC-007, AC-008
- **Test Requirements**:
  - `programmatic` TR-T011-01: 所有API端点返回正确状态码
  - `programmatic` TR-T011-02: 编辑操作正确持久化
- **Notes**: 参考前端交互接口设计

---

### 阶段五：情绪标注 + TTS 导出

## [待开始] T-009: 情绪标注器实现
- **Priority**: P1
- **Depends On**: T-004, T-005, M2
- **Description**: 
  - 实现emotion_tagger.py
  - 规则标注六种基础情绪（怒/喜/悲/惊/惧/中性）
  - 朴素贝叶斯兜底
- **Acceptance Criteria Addressed**: AC-006
- **Test Requirements**:
  - `human-judgement` TR-T009-01: 情绪标签符合上下文语义
- **Notes**: 规则优先，覆盖常见情绪表达模式

## [待开始] T-012: 前端界面实现
- **Priority**: P1
- **Depends On**: T-011, M4
- **Description**: 
  - 实现Streamlit前端app.py
  - 章节范围选择、进度显示、编辑界面
- **Acceptance Criteria Addressed**: AC-008
- **Test Requirements**:
  - `human-judgement` TR-T012-01: 界面无报错，颜色区分清晰
  - `human-judgement` TR-T012-02: 功能正常，响应及时
- **Notes**: 禁用遥测

## [待开始] T-013: 导出功能实现
- **Priority**: P1
- **Depends On**: T-010, M4
- **Description**: 
  - 实现JSON/SSML格式导出
  - 支持单章节和全部章节导出
- **Acceptance Criteria Addressed**: AC-008
- **Test Requirements**:
  - `programmatic` TR-T013-01: 导出JSON格式正确
  - `human-judgement` TR-T013-02: SSML格式符合规范
- **Notes**: JSON结构包含所有元数据

---

### 阶段六：UI 打磨与发布

## [待开始] T-015: 单元测试编写
- **Priority**: P2
- **Depends On**: M5
- **Description**: 
  - 编写tests/目录下的单元测试
  - 覆盖核心功能
- **Acceptance Criteria Addressed**: AC-001~AC-007
- **Test Requirements**:
  - `programmatic` TR-T015-01: pytest tests/全部通过
- **Notes**: 每个模块对应测试文件

---

## 需求-任务双向绑定表

| 需求编号 | 需求描述 | 关联任务 |
| :--- | :--- | :--- |
| AC-001 | 项目骨架搭建完成 | T-001, T-002, T-010, T-014 |
| AC-002 | 分章与基础NLP功能完成 | T-003, T-004 |
| AC-003 | 对话/旁白分类完成 | T-005 |
| AC-004 | 拟声词识别完成 | T-006 |
| AC-005 | 角色库与说话人匹配完成 | T-007, T-008 |
| AC-006 | 情绪标注完成 | T-009 |
| AC-007 | 进度管理与编辑保护完成 | T-010, T-011 |
| AC-008 | 前端交互功能完成 | T-012, T-013 |