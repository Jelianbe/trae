# Kokoro TTS 储备方案

> 版本: v1.0  
> 日期: 2026-05-08  
> 入库原因: Index-TTS 集成后，Kokoro 将降为备用引擎

## 当前状态
- Kokoro 82M 是主 TTS 引擎
- 103 个中文音色，CPU 可运行，完全离线
- 首句冷启动约 18 秒，后续推理约 1.4 秒/句
- 不支持情感控制（预留 emotion 接口）

## 降级条件
以下任一条件满足时降级为备用引擎：
1. Index-TTS 集成并验证通过
2. Index-TTS 在音质盲测中 ≥ 4/5
3. Index-TTS 支持情感向量参数

## 降级后的角色
- 作为 Index-TTS 不可用时的回退方案
- 保留全部 Kokoro 相关代码：`pipeline/tts_kokoro.py`
- 保留音色映射：`ROLE_VOICE_MAP`
- 降级条件：Index-TTS 连续 3 次调用失败

## 回退实施要点
1. 在 `tts_generator.py` 中实现引擎优先级
2. Index-TTS 失败时自动回退到 Kokoro
3. 日志记录回退事件，便于排查
