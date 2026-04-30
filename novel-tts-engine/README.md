# Novel-TTS-Engine

小说转有声书 - 智能解析引擎

## 项目简介

将原始小说文本自动解析为结构化的分角色剧本，为有声书制作提供一键式预处理。

## 安装

```bash
uv venv .venv --python 3.11
.venv\Scripts\activate
uv pip install -r requirements.txt
```

## 运行

```bash
streamlit run frontend/app.py
```

## 目录结构

```
novel-tts-engine/
├── pipeline/        # 核心解析流水线
├── db/              # 数据库层
├── models/          # 预置离线模型
├── utils/           # 通用工具
├── frontend/        # 前端界面
├── scripts/         # 脚本
├── tests/           # 测试
└── docs/            # 文档
```
