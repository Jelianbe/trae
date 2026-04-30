import os
import sys
import shutil
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MODELS_DIR = PROJECT_ROOT / "models"
HANLP_DIR = MODELS_DIR / "hanlp"

def init_models():
    print("=" * 60)
    print("模型离线初始化脚本")
    print("=" * 60)
    
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    HANLP_DIR.mkdir(parents=True, exist_ok=True)
    
    print("\n[1/3] 初始化HanLP模型...")
    init_hanlp()
    
    print("\n[2/3] 初始化jieba词典...")
    init_jieba()
    
    print("\n[3/3] 检查模型体积...")
    check_model_size()
    
    print("\n" + "=" * 60)
    print("模型初始化完成！")
    print("=" * 60)


def init_hanlp():
    try:
        import hanlp
        
        hanlp_home = HANLP_DIR
        os.environ['HANLP_HOME'] = str(hanlp_home)
        
        print("  下载HanLP多任务模型...")
        print("  模型: CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH")
        
        HanLP = hanlp.load(
            hanlp.pretrained.mtl.CLOSE_TOK_POS_NER_SRL_DEP_SDP_CON_ELECTRA_SMALL_ZH
        )
        
        print("  HanLP模型初始化成功！")
        
        test_text = "测试文本"
        result = HanLP(test_text)
        print(f"  测试结果: {result.get('tok/fine', [])}")
        
    except Exception as e:
        print(f"  HanLP初始化失败: {e}")
        print("  将在首次运行时自动下载")


def init_jieba():
    try:
        import jieba
        
        print("  初始化jieba分词器...")
        jieba.initialize()
        
        test_text = "自然语言处理"
        result = list(jieba.cut(test_text))
        print(f"  测试结果: {' / '.join(result)}")
        
        print("  jieba初始化成功！")
        
    except Exception as e:
        print(f"  jieba初始化失败: {e}")


def check_model_size():
    total_size = 0
    
    for root, dirs, files in os.walk(MODELS_DIR):
        for file in files:
            file_path = Path(root) / file
            total_size += file_path.stat().st_size
    
    total_size_mb = total_size / (1024 * 1024)
    
    hanlp_cache = Path.home() / "AppData" / "Roaming" / "hanlp"
    if hanlp_cache.exists():
        for root, dirs, files in os.walk(hanlp_cache):
            for file in files:
                file_path = Path(root) / file
                total_size += file_path.stat().st_size
    
    total_size_mb_with_cache = total_size / (1024 * 1024)
    
    print(f"  models目录大小: {total_size_mb:.1f} MB")
    print(f"  HanLP缓存大小: {total_size_mb_with_cache - total_size_mb:.1f} MB")
    print(f"  总模型大小: {total_size_mb_with_cache:.1f} MB")
    
    if total_size_mb_with_cache <= 1400:
        print("  ✓ 模型体积符合要求 (≤1.4GB)")
    else:
        print("  ⚠ 模型体积超过1.4GB")


def copy_hanlp_cache_to_local():
    hanlp_cache = Path.home() / "AppData" / "Roaming" / "hanlp"
    
    if not hanlp_cache.exists():
        print("  HanLP缓存目录不存在")
        return
    
    print("  复制HanLP缓存到本地models目录...")
    
    mtl_cache = hanlp_cache / "mtl"
    if mtl_cache.exists():
        dest = HANLP_DIR / "mtl"
        if not dest.exists():
            shutil.copytree(mtl_cache, dest)
            print(f"  已复制到: {dest}")


if __name__ == "__main__":
    init_models()
