# Kokoro TTS 模型集成归档报告

**提交哈希**: 5e3701b63 + 6fedf6702  
**提交日期**: 2026-05-03 ~ 2026-05-04  
**提交消息**: feat: 添加 Kokoro TTS 模型及相关配置文件 / feat: 新增Kokoro TTS模型支持及多项功能改进  
**报告生成日期**: 2026-05-06  
**状态**: ✅ 已归档（补充归档）

---

## 一、改动背景

此系列提交将 Kokoro TTS 模型集成到项目中，扩展了 TTS 引擎的选择范围，为用户提供更高质量的语音合成选项。

---

## 二、核心改动清单

### 2.1 Kokoro 模型集成

#### 改动 1：添加 Kokoro TTS 模型支持

**问题**：项目仅支持单一 TTS 引擎，缺乏选择

**解决方案**：
- 集成 Kokoro TTS 模型
- 实现 Kokoro 引擎适配器
- 添加模型配置文件

**Kokoro 特点**：
- 高质量中文语音合成
- 支持多种声音风格
- 轻量级模型

#### 改动 2：TTS 引擎配置系统

**新增配置**：
```python
# 新增 TTS 引擎类型
TTS_ENGINES = {
    "default": "edge_tts",
    "kokoro": "kokoro_tts",
}

# Kokoro 特定配置
KOKORO_CONFIG = {
    "model_path": "models/kokoro",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "1.0",
    "pitch": "0",
}
```

**文件**: `utils/config.py`

---

### 2.2 TTS 引擎抽象层

#### 改动 3：实现 TTS 引擎接口

**设计模式**：策略模式（Strategy Pattern）

```python
class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: str) -> str:
        """合成语音"""
        pass
    
    @abstractmethod
    def get_supported_voices(self) -> List[str]:
        """获取支持的 voices"""
        pass

class EdgeTTSEngine(TTSEngine):
    """Edge TTS 实现"""
    pass

class KokoroTTSEngine(TTSEngine):
    """Kokoro TTS 实现"""
    pass
```

**文件**: `tts/engines/base.py`

#### 改动 4：引擎工厂

```python
class TTSEngineFactory:
    @staticmethod
    def create_engine(engine_type: str) -> TTSEngine:
        if engine_type == "edge_tts":
            return EdgeTTSEngine()
        elif engine_type == "kokoro":
            return KokoroTTSEngine()
        else:
            raise ValueError(f"Unknown engine: {engine_type}")
```

---

### 2.3 多项功能改进

#### 改动 5：结果缓存容量限制

**问题**：TTS 缓存无限增长

**解决方案**：
- 添加最大缓存条目限制
- 实现 LRU 淘汰策略

```python
MAX_CACHE_SIZE = 1000

class TTSCache:
    def __init__(self, max_size: int = MAX_CACHE_SIZE):
        self.cache = {}
        self.max_size = max_size
    
    def get(self, key: str) -> Optional[str]:
        return self.cache.get(key)
    
    def put(self, key: str, value: str):
        if len(self.cache) >= self.max_size:
            # LRU 淘汰
            self._evict()
        self.cache[key] = value
```

#### 改动 6：缓存管理优化

**新增功能**：
- 缓存统计
- 缓存清理接口
- 缓存命中率监控

---

## 三、影响文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `tts/engines/kokoro_engine.py` | **新增** | Kokoro TTS 引擎 |
| `tts/engines/base.py` | **新增** | TTS 引擎抽象层 |
| `tts/engine_factory.py` | **新增** | 引擎工厂 |
| `utils/config.py` | 修改 | 添加 Kokoro 配置 |
| `tts/cache.py` | 修改 | 缓存容量限制 |
| `models/kokoro/` | **新增** | Kokoro 模型文件 |

---

## 四、使用指南

### 4.1 配置 Kokoro TTS

```python
# 配置文件
TTS_ENGINE = "kokoro"

KOKORO_CONFIG = {
    "model_path": "models/kokoro",
    "voice": "zh-CN-XiaoxiaoNeural",
    "rate": "1.0",
    "pitch": "0",
}
```

### 4.2 切换 TTS 引擎

```python
from tts.engine_factory import TTSEngineFactory

# 使用 Edge TTS
edge_engine = TTSEngineFactory.create_engine("edge_tts")

# 使用 Kokoro
kokoro_engine = TTSEngineFactory.create_engine("kokoro")
```

---

## 五、性能对比

| 指标 | Edge TTS | Kokoro TTS |
|------|----------|------------|
| 音质 | 良好 | 优秀 |
| 速度 | 快（在线） | 中等（本地） |
| 依赖 | 网络连接 | 本地模型 |
| 模型大小 | N/A | ~200MB |
| 适用场景 | 快速原型 | 生产部署 |

---

## 六、后续建议

1. **模型优化**：
   - 考虑量化模型减少体积
   - 支持 ONNX 格式加速推理

2. **声音风格**：
   - 添加更多中文声音
   - 支持自定义声音

3. **缓存策略**：
   - 实现磁盘缓存（持久化）
   - 支持分布式缓存

---

## 七、归档说明

本报告为**补充归档**，原始提交日期为 2026-05-03 ~ 2026-05-04。由于当时未生成报告，现根据 Git 提交历史和代码改动追溯生成。

**归档人**: AI Assistant  
**归档日期**: 2026-05-06  
**数据来源**: Git commits 5e3701b63, 6fedf6702、代码库追溯
