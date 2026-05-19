# 标准化基线测试

本目录包含所有固定的基线测试脚本。

## 使用方式

```bash
# 运行全部4个基线测试
cd d:\trae\novel-tts-engine
python tests\baseline\run_all_baselines.py

# 运行单个测试
python tests\baseline\test_urban_preset.py
python tests\baseline\test_fantasy_preset.py
python tests\baseline\test_urban_no_preset.py
python tests\baseline\test_fantasy_no_preset.py
```

## 文件说明

| 文件 | 用途 | 预期基线 |
|------|------|---------|
| `test_urban_preset.py` | 都市-有预注册 | ≥100.0% |
| `test_fantasy_preset.py` | 西幻-有预注册 | ≥65.6% |
| `test_urban_no_preset.py` | 都市-无预注册 | ≥78.9% |
| `test_fantasy_no_preset.py` | 西幻-无预注册 | ≥71.9% |
| `run_all_baselines.py` | 统一入口，运行全部4个测试并汇总 | - |
| `BASELINE_REPORT.md` | 每次运行后记录结果 | - |

## 测试标准

所有测试必须满足以下条件才能通过：
1. 准确率不低于预期基线
2. 无新增 UNKNOWN（除非预期如此）
3. 无崩溃/异常

## 注意事项

- 每次修改代码后**必须先运行此基线测试**
- 基线下降时**必须先排查原因**，不得直接推进新开发
- 本目录下的文件**不得随意修改**，只能由评审后更新
