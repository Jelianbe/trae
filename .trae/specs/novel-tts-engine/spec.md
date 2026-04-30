# Novel-TTS-Engine - 产品需求文档

## Overview
- **Summary**: 开发一个纯本地运行、低运行时内存消耗的桌面软件，将原始小说文本自动解析为结构化的分角色剧本，为有声书制作提供一键式预处理。
- **Purpose**: 解决有声书制作中人工标注角色、情绪、对话类型的繁琐工作，提供高质量的自动化解析方案。
- **Target Users**: 有声书制作人员、小说创作者、TTS引擎集成开发者

## Goals
- 开发完整的小说文本智能解析引擎，支持离线运行
- 实现对话/旁白/拟声词分类，准确率≥85%
- 实现角色识别与说话人匹配，准确率≥95%（明确对话）
- 实现情绪标注（怒/喜/悲/惊/惧/中性）
- 输出结构化JSON，可直接对接TTS引擎
- 提供前端界面支持章节范围选择、中断/续接、进度回溯

## Non-Goals (Out of Scope)
- 不提供在线云服务或API
- 不包含TTS语音合成功能
- 不支持非中文文本解析
- 不提供云端模型更新

## Background & Context
- 项目基于HanLP、FastText、BGE-small等轻量级NLP模型构建
- 采用规则优先、统计兜底的混合策略（规则~70%，ML~30%）
- 目标运行时RAM峰值<3GB，安装包<2GB

## Functional Requirements
- **FR-001**: 支持小说文本分章处理，自动识别章节标题
- **FR-002**: 实现对话/旁白/拟声词的自动分类
- **FR-003**: 建立角色库，支持说话人匹配与归属
- **FR-004**: 实现情绪自动标注（六种基础情绪）
- **FR-005**: 输出包含type/speaker/emotion/speed/tone的JSON结构
- **FR-006**: 支持章节范围选择、中断续接、进度回溯
- **FR-007**: 支持用户手动编辑修正，修改永久保存
- **FR-008**: 支持JSON/SSML格式导出

## Non-Functional Requirements
- **NFR-001**: 纯本地运行，零网络依赖
- **NFR-002**: 运行时RAM峰值≤3GB
- **NFR-003**: 安装包体积≤2GB
- **NFR-004**: 对话/旁白分类准确率≥85%
- **NFR-005**: 拟声词识别准确率≥95%
- **NFR-006**: 明确对话说话人匹配准确率≥95%

## Constraints
- **Technical**: Python 3.10+，FastAPI，Streamlit，SQLite
- **Business**: 纯本地部署，无云端依赖
- **Dependencies**: HanLP完整离线版、FastText中文词向量、BGE-small ONNX

## Assumptions
- 用户具备基础的Python环境知识
- 用户拥有≥8GB内存的计算机
- 用户使用UTF-8编码的中文小说文本

## Acceptance Criteria

### AC-001: 项目骨架搭建完成
- **Given**: 空白项目目录
- **When**: 执行环境初始化命令
- **Then**: 项目结构完整，依赖安装成功，前端可正常运行
- **Verification**: `programmatic`

### AC-002: 分章与基础NLP功能完成
- **Given**: 包含章节标题的小说文本
- **When**: 上传文本并执行分析
- **Then**: 正确识别章节边界，输出分词、词性标注、NER结果
- **Verification**: `programmatic`

### AC-003: 对话/旁白分类完成
- **Given**: 包含对话和旁白的小说文本
- **When**: 执行分类分析
- **Then**: 分类准确率≥85%
- **Verification**: `programmatic`

### AC-004: 拟声词识别完成
- **Given**: 包含拟声词的小说文本
- **When**: 执行拟声词检测
- **Then**: 拟声词识别准确率≥95%
- **Verification**: `programmatic`

### AC-005: 角色库与说话人匹配完成
- **Given**: 包含多角色对话的小说文本
- **When**: 执行说话人匹配
- **Then**: 明确对话匹配准确率≥95%，交织对话正确拆分
- **Verification**: `programmatic`

### AC-006: 情绪标注完成
- **Given**: 包含情感表达的小说文本
- **When**: 执行情绪分析
- **Then**: 正确标注六种基础情绪
- **Verification**: `human-judgment`

### AC-007: 进度管理与编辑保护完成
- **Given**: 已分析的小说项目
- **When**: 执行暂停、续接、编辑操作
- **Then**: 进度正确保存，用户修改永不丢失
- **Verification**: `programmatic`

### AC-008: 前端交互功能完成
- **Given**: 启动前端应用
- **When**: 执行章节选择、分析、导出操作
- **Then**: 界面无报错，功能正常
- **Verification**: `human-judgment`

## Open Questions
- [ ] 是否需要支持特定的小说格式（如epub、txt等）？
- [ ] 是否需要提供批量处理功能？
- [ ] 是否需要支持用户自定义情绪标签？