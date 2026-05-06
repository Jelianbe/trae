# -*- coding: utf-8 -*-
"""
Index-TTS 自动启动脚本
后台静默启动 Index-TTS API 服务，无需打开 WebUI 手动加载模型。
用法：python start_index_tts_api.py [--port 8300]
"""
import os
import sys
import subprocess
import time
import signal
import argparse
from pathlib import Path

# Index-TTS 目录
INDEX_TTS_DIR = Path(__file__).parent / "TTS" / "IndexTTS2-SonicVale"
CONDA_ENV_PY = INDEX_TTS_DIR / "installer_files" / "env" / "python.exe"
MODEL_DIR = INDEX_TTS_DIR / "checkpoints"
DEFAULT_API_PORT = 8300

def check_service_running(port=DEFAULT_API_PORT):
    """检查服务是否已在运行"""
    import requests
    try:
        r = requests.get(f"http://localhost:{port}/", timeout=3)
        return r.status_code == 200
    except:
        return False

def start_api_service(port=DEFAULT_API_PORT):
    """启动 Index-TTS API 服务"""
    if check_service_running(port):
        print(f"Index-TTS API 已在运行 (端口 {port})")
        return True
    
    if not CONDA_ENV_PY.exists():
        print(f"错误: 找不到 Python 解释器: {CONDA_ENV_PY}")
        print("请检查 Index-TTS 整合包是否正确安装")
        return False
    
    if not MODEL_DIR.exists():
        print(f"错误: 找不到模型目录: {MODEL_DIR}")
        return False
    
    print(f"正在启动 Index-TTS API 服务...")
    print(f"模型目录: {MODEL_DIR}")
    print(f"API 端口: {port}")
    print()
    
    # 启动 webui.py 的 API 模式（加载模型并启动 API 线程）
    # 使用 subprocess 在后台启动
    startup_script = INDEX_TTS_DIR / "start_api_headless.py"
    
    if not startup_script.exists():
        print(f"错误: 找不到启动脚本: {startup_script}")
        print("请先运行集成安装")
        return False
    
    # 设置环境变量
    env = os.environ.copy()
    env["PYTHONNOUSERSITE"] = "1"
    env["CUDA_PATH"] = str(INDEX_TTS_DIR / "installer_files" / "env")
    env["CUDA_HOME"] = env["CUDA_PATH"]
    
    process = subprocess.Popen(
        [str(CONDA_ENV_PY), str(startup_script), "--port", str(port)],
        cwd=str(INDEX_TTS_DIR),
        env=env,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    print(f"服务启动中 (PID: {process.pid})...")
    
    # 等待服务就绪
    for i in range(180):  # 最多等待 3 分钟
        time.sleep(1)
        if check_service_running(port):
            print(f"Index-TTS API 启动成功! (端口 {port})")
            return True
        
        # 检查进程是否退出
        if process.poll() is not None:
            stderr = process.stderr.read().decode("utf-8", errors="replace")
            print(f"服务启动失败:")
            print(stderr[-1000:])
            return False
        
        if i % 15 == 0 and i > 0:
            print(f"  等待模型加载... ({i}s)")
    
    print("启动超时，请检查日志")
    return False

def stop_service(port=DEFAULT_API_PORT):
    """停止服务"""
    import requests
    try:
        # 尝试优雅关闭
        r = requests.get(f"http://localhost:{port}/", timeout=3)
        print(f"服务运行中 (端口 {port})，请手动关闭")
    except:
        print(f"服务未运行 (端口 {port})")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Index-TTS API 自动启动")
    parser.add_argument("--port", type=int, default=DEFAULT_API_PORT, help="API 端口")
    parser.add_argument("--stop", action="store_true", help="停止服务")
    args = parser.parse_args()
    
    if args.stop:
        stop_service(args.port)
    else:
        start_api_service(args.port)
