# Index-TTS 进程内直接集成

> 版本: v1.0  
> 日期: 2026-05-08  
> 入库原因: 当前使用 HTTP API 方式调用，存在额外部署步骤

## 当前方案
- 通过 HTTP API 调用外部 Index-TTS 服务（`http://localhost:8300`）
- 适配器文件：`pipeline/tts_indextts.py`
- 优点：进程隔离，模型崩溃不影响主进程

## 备选方案
直接 import IndexTTS 类，应用启动时懒加载：

```python
from indextts.infer import IndexTTS

tts = IndexTTS(cfg_path="checkpoints/config.yaml", model_dir="checkpoints")
wav_bytes = tts.infer(audio_prompt="voice_01.wav", text="你好世界")
```

### 优势
- 无需额外启动服务，随应用一起运行
- 更低延迟（无 HTTP 网络开销）
- 部署更简单（一个命令启动全部功能）

### 劣势
- 模型加载占用应用进程 4-8GB 显存
- 模型崩溃会导致主进程退出
- 无法独立重启 TTS 服务

## 启动条件
满足以下任一条件时考虑实施：
1. 用户反馈 HTTP 部署步骤过于繁琐
2. 需要降低 TTS 延迟（当前 HTTP 开销明显）
3. 应用进程有足够的显存余量

## 实施要点
1. 在 `tts_generator.py` 中新增 `IndexTTSInProcess` 适配器
2. 应用启动时预加载模型或首次调用时懒加载
3. 保留 HTTP 适配器作为 fallback
