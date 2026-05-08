# Index-TTS API 端口冲突修复

> 版本: v1.0  
> 日期: 2026-05-08  
> 入库原因: webui.py 中 API 和 Gradio 使用相同端口导致冲突

## 问题描述
Index-TTS 的 `webui.py` 中：
- Gradio 使用 `cmd_args.port`（默认 7860，我们改为 8300）
- API FastAPI 也尝试绑定同一端口
- 导致 API 服务启动失败，`/v2/synthesize` 端点不可用

## 错误日志
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8300)
```

## 影响
- Index-TTS HTTP API 不可用
- `tts_indextts.py` 调用 `/v2/synthesize` 返回 404
- 自动回退到 Kokoro 引擎

## 修复方案

### 方案1：分离端口（推荐）
```python
# 在 webui.py 中修改
parser.add_argument("--api_port", type=int, default=8300)
parser.add_argument("--port", type=int, default=7860)

# run_api_server 使用独立端口
threading.Thread(target=run_api_server, args=(cmd_args.api_port,), daemon=True).start()
```

### 方案2：挂载 FastAPI 到 Gradio
```python
# 将 api_app 挂载到 Gradio 的 FastAPI 实例上
demo.app.mount("/api", api_app)
```

## 启动条件
- MVP 已验证通过，Kokoro 作为回退可用
- 需要 Index-TTS 音质验证时修复此问题

## 当前状态
- Kokoro 回退正常工作（已生成 4.58s 音频）
- Index-TTS 需要修复后才能使用
