"""转换BGE-small PyTorch模型为ONNX格式"""
from transformers import AutoTokenizer
from optimum.onnxruntime import ORTModelForFeatureExtraction
from pathlib import Path

model_name = "BAAI/bge-small-zh-v1.5"
pytorch_path = Path("models/bge-small-zh-v1.5")
onnx_path = Path("models/bge-small-onnx")

onnx_path.mkdir(parents=True, exist_ok=True)

print("正在加载tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(str(pytorch_path))
tokenizer.save_pretrained(str(onnx_path))
print("✅ tokenizer已保存")

print("正在转换模型为ONNX格式...")
model = ORTModelForFeatureExtraction.from_pretrained(
    str(pytorch_path),
    export=True
)
model.save_pretrained(str(onnx_path))
print(f"✅ ONNX模型已保存至 {onnx_path}")

print("\n验证ONNX模型...")
from optimum.onnxruntime import ORTModelForFeatureExtraction
import torch

tokenizer = AutoTokenizer.from_pretrained(str(onnx_path))
onnx_model = ORTModelForFeatureExtraction.from_pretrained(str(onnx_path))

texts = ["你好。", "他说道。"]
inputs = tokenizer(texts, return_tensors="pt", padding=True, truncation=True, max_length=256)
with torch.no_grad():
    outputs = onnx_model(**inputs)
    embeddings = outputs.last_hidden_state.mean(dim=1)

cosine = torch.cosine_similarity(embeddings[0:1], embeddings[1:2])
print(f"✅ 验证成功，余弦相似度: {cosine.item():.4f}")
print(f"✅ 嵌入维度: {embeddings.shape}")
