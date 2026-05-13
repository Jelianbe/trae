#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Novel-TTS-Engine FastAPI 后端服务

提供 RESTful API 接口，暴露文本分析、角色识别、情绪标注和 TTS 生成能力。

启动方式：
    cd backend
    uvicorn main:app --reload --host 0.0.0.0 --port 8000

API 文档：
    http://localhost:8000/docs
"""

import sys
import os
import json
import uuid
import tempfile
import time
import logging
import subprocess
import signal
import atexit
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

# 将项目根目录加入 Python 路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Pipeline 模块导入（全局单例，不修改现有代码）
from pipeline.chapter_splitter import ChapterSplitter, NovelStructure, Chapter
from pipeline.pipeline_runner import get_pipeline_runner, PipelineRunner
from pipeline.character_manager import get_character_manager, CharacterManager
from pipeline.tts_generator import get_tts_generator, TTSGenerator

# 配置日志
LOG_DIR = PROJECT_ROOT / "backend" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

file_handler = logging.FileHandler(str(LOG_DIR / "novel-tts.log"), encoding="utf-8", mode="a")
file_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        file_handler,
    ],
)
logger = logging.getLogger("novel-tts-api")

# ============================================================
# Index-TTS 服务管理
# ============================================================

_indextts_process = None
_indextts_port = 8300
_indextts_ready = False

def _start_indextts_service():
    """启动 Index-TTS 服务（后台进程）"""
    global _indextts_process, _indextts_ready
    
    if _indextts_process is not None:
        logger.info("Index-TTS service is already running")
        return
    
    tts_dir = PROJECT_ROOT / "TTS" / "IndexTTS2-SonicVale"
    python_path = tts_dir / "installer_files" / "env" / "python.exe"
    webui_path = tts_dir / "webui.py"
    
    if not python_path.exists():
        logger.warning(f"Index-TTS Python environment not found: {python_path}")
        return
    
    if not webui_path.exists():
        logger.warning(f"Index-TTS webui.py not found: {webui_path}")
        return
    
    try:
        logger.info(f"Starting Index-TTS service on port {_indextts_port}...")
        _indextts_process = subprocess.Popen(
            [
                str(python_path),
                str(webui_path),
                "--port", "7860",
                "--api_port", str(_indextts_port),
                "--host", "127.0.0.1",
                "--model_dir", str(tts_dir / "checkpoints"),
            ],
            cwd=str(tts_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        
        # 等待服务启动并加载模型
        time.sleep(10)
        
        # 检查进程是否还在运行
        if _indextts_process.poll() is not None:
            stdout, stderr = _indextts_process.communicate()
            logger.error(f"Index-TTS service failed to start. stdout: {stdout.decode('utf-8', errors='ignore')}")
            logger.error(f"stderr: {stderr.decode('utf-8', errors='ignore')}")
            _indextts_process = None
            return
        
        # 额外等待模型加载（Index-TTS 模型加载通常需要 10-20 秒）
        logger.info("Waiting for Index-TTS model to load...")
        time.sleep(20)
        
        # 验证模型是否已加载
        import requests
        max_retries = 3
        for i in range(max_retries):
            try:
                resp = requests.get(f"http://127.0.0.1:{_indextts_port}/v2/synthesize", timeout=5)
                # 503 表示模型未加载，200 或其他表示服务就绪
                if resp.status_code != 503:
                    logger.info(f"Index-TTS model loaded and ready")
                    break
                else:
                    logger.info(f"Index-TTS model not loaded yet, retry {i+1}/{max_retries}")
                    time.sleep(5)
            except Exception:
                logger.info(f"Index-TTS not responding, retry {i+1}/{max_retries}")
                time.sleep(5)
        
        logger.info(f"Index-TTS service started successfully (PID: {_indextts_process.pid})")
        _indextts_ready = True
        
    except Exception as e:
        logger.error(f"Failed to start Index-TTS service: {e}")
        _indextts_process = None

def _stop_indextts_service():
    """停止 Index-TTS 服务"""
    global _indextts_process, _indextts_ready
    
    if _indextts_process is None:
        return
    
    try:
        logger.info(f"Stopping Index-TTS service (PID: {_indextts_process.pid})...")
        
        # 优雅停止
        if sys.platform == "win32":
            _indextts_process.terminate()
        else:
            _indextts_process.send_signal(signal.SIGTERM)
        
        # 等待进程结束
        _indextts_process.wait(timeout=5)
        logger.info("Index-TTS service stopped successfully")
        
    except subprocess.TimeoutExpired:
        logger.warning("Index-TTS service did not stop gracefully, killing...")
        _indextts_process.kill()
        
    except Exception as e:
        logger.error(f"Error stopping Index-TTS service: {e}")
        
    finally:
        _indextts_process = None
        _indextts_ready = False

# 注册退出处理
atexit.register(_stop_indextts_service)

# ============================================================
# 应用初始化
# ============================================================

app = FastAPI(
    title="Novel-TTS-Engine API",
    description="网文 TTS 引擎 RESTful API，提供文本分析、角色识别、情绪标注和语音合成能力",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    on_startup=[_start_indextts_service],
    on_shutdown=[_stop_indextts_service],
)

# CORS 配置（开发阶段允许所有来源）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# 内存存储（项目级数据，重启后丢失）
# ============================================================

# 项目存储：{project_id: project_data}
projects_store: Dict[str, Dict[str, Any]] = {}
PROJECTS_DB_PATH = PROJECT_ROOT / "backend" / "projects_db.json"


def _save_projects_db():
    """保存项目数据到 JSON 文件"""
    try:
        data = {}
        for pid, pdata in projects_store.items():
            data[pid] = {
                "project_id": pid,
                "book_title": pdata.get("book_title", ""),
                "content": pdata.get("content", ""),
                "total_chapters": pdata.get("total_chapters", 0),
                "total_volumes": pdata.get("total_volumes", 0),
                "total_words": pdata.get("total_words", 0),
                "created_at": pdata.get("created_at", ""),
            }
        with open(str(PROJECTS_DB_PATH), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _load_projects_db():
    """从 JSON 文件加载项目数据，重新分章"""
    try:
        if PROJECTS_DB_PATH.exists():
            with open(str(PROJECTS_DB_PATH), "r", encoding="utf-8") as f:
                data = json.load(f)
            for pid, pdata in data.items():
                content = pdata.get("content", "")
                if not content:
                    continue
                try:
                    splitter = get_splitter()
                    novel_structure = splitter.split_with_volumes(content)
                    projects_store[pid] = {
                        "project_id": pid,
                        "book_title": pdata.get("book_title", ""),
                        "content": content,
                        "novel_structure": novel_structure,
                        "total_chapters": novel_structure.total_chapters,
                        "total_volumes": novel_structure.total_volumes,
                        "total_words": sum(len(ch.content) for ch in novel_structure.chapters),
                        "created_at": pdata.get("created_at", ""),
                    }
                    analysis_cache[pid] = {}
                except Exception:
                    pass
    except Exception:
        pass


# 章节分析缓存：{project_id: {chapter_index: ChapterResult}}
analysis_cache: Dict[str, Dict[int, Any]] = {}

# TTS 音频文件存储目录
AUDIO_DIR = PROJECT_ROOT / "backend" / "audio_output"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================
# 全局单例懒加载
# ============================================================

_chapter_splitter: Optional[ChapterSplitter] = None
_pipeline_runner: Optional[PipelineRunner] = None
_character_manager: Optional[CharacterManager] = None
_tts_generator: Optional[TTSGenerator] = None


def get_splitter() -> ChapterSplitter:
    global _chapter_splitter
    if _chapter_splitter is None:
        _chapter_splitter = ChapterSplitter()
    return _chapter_splitter


# 启动时加载已有项目（必须在 get_splitter 定义之后）
_load_projects_db()


def get_runner() -> PipelineRunner:
    global _pipeline_runner
    if _pipeline_runner is None:
        _pipeline_runner = get_pipeline_runner()
    return _pipeline_runner


def get_char_manager(db_path: Optional[str] = None) -> CharacterManager:
    global _character_manager
    if _character_manager is None:
        if db_path:
            _character_manager = get_character_manager(db_path)
        else:
            _character_manager = get_character_manager()
    return _character_manager


def get_tts() -> TTSGenerator:
    global _tts_generator
    if _tts_generator is None:
        _tts_generator = get_tts_generator()
    return _tts_generator


# ============================================================
# Pydantic v2 数据模型
# ============================================================

class ChapterInfo(BaseModel):
    """章节基本信息"""
    index: int
    title: str
    word_count: int
    volume_index: int = 0
    volume_title: str = ""
    content: str = ""


class ProjectInfo(BaseModel):
    """项目基本信息"""
    project_id: str
    book_title: str
    total_chapters: int
    total_volumes: int = 0
    total_words: int = 0
    created_at: str


class ProjectUploadResponse(BaseModel):
    """项目上传响应"""
    project_id: str
    book_title: str
    total_chapters: int
    total_volumes: int
    chapters: List[ChapterInfo]


class ProjectSummary(BaseModel):
    """项目概要（列表用）"""
    id: str
    project_id: str
    title: str
    total_chapters: int
    total_volumes: int = 0
    total_words: int = 0
    progress: int = 0
    status: str = "pending"
    lastEdit: str = ""


class VoiceInfo(BaseModel):
    """音色信息"""
    id: int
    name: str
    gender: str
    cat: str
    desc: str = ""
    tags: List[str] = []
    bars: List[int] = []


class SentenceFragment(BaseModel):
    """句子片段数据"""
    text: str
    type: str = "narration"
    speaker: str = ""


class SentenceData(BaseModel):
    """句子级分析数据（MVP 7字段）"""
    text: str
    speaker: str = ""
    emotion: str = "neutral"
    emotion_class: str = "neutral"
    emotion_vector: Optional[List[float]] = None
    sentence_type: str = "narration"
    entities: List[dict] = []
    fragments: List[SentenceFragment] = []


class ChapterAnalysisResponse(BaseModel):
    """章节分析响应"""
    chapter_index: int
    chapter_title: str
    total_sentences: int
    sentences: List[SentenceData]
    statistics: Dict[str, Any] = {}


class CharacterInfo(BaseModel):
    """角色信息"""
    id: Optional[int] = None
    name: str
    gender: str = "unknown"
    aliases: List[str] = []
    first_appearance: Optional[int] = None
    is_locked: bool = False


class CharactersResponse(BaseModel):
    """角色列表响应"""
    total: int
    characters: List[CharacterInfo]


class TTSRequest(BaseModel):
    """TTS 生成请求"""
    text: str = Field(..., min_length=1, max_length=5000, description="要合成的文本")
    speaker: str = Field("default", description="说话人标识")
    emotion: str = Field("neutral", description="情绪标签")
    emotion_vector: Optional[List[float]] = Field(None, description="8维情绪向量（Index-TTS）")
    sentence_type: str = Field("narration", description="句子类型：narration 或 dialogue")
    voice_id: Optional[str] = Field(None, description="指定音色ID（Kokoro引擎）")


class TTSResponse(BaseModel):
    """TTS 生成响应"""
    audio_url: str
    filename: str
    duration_ms: int = 0
    engine: str = "kokoro"


class SynthesizeSegment(BaseModel):
    """章节合成 - 单段文本"""
    text: str
    speaker: str = ""
    emotion: str = "neutral"
    sentence_type: str = "narration"


class ChapterSynthesizeRequest(BaseModel):
    """章节合成请求"""
    segments: List[SynthesizeSegment]


class ChapterSynthesizeResponse(BaseModel):
    """章节合成响应"""
    audio_url: str
    filename: str
    total_duration_ms: int = 0
    segment_count: int = 0
    engine: str = ""
    segment_times: List[dict] = []


class ErrorResponse(BaseModel):
    """错误响应"""
    error: str
    detail: str = ""
    timestamp: str


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    version: str
    pipeline_ready: bool = False
    tts_engine: str = ""
    timestamp: str


# ============================================================
# 错误处理
# ============================================================

@app.exception_handler(ValueError)
async def value_error_handler(request, exc: ValueError):
    return ErrorResponse(
        error="InvalidRequest",
        detail=str(exc),
        timestamp=datetime.now().isoformat(),
    )


@app.exception_handler(Exception)
async def general_error_handler(request, exc: Exception):
    logger.exception(f"未处理的异常: {exc}")
    return ErrorResponse(
        error="InternalError",
        detail="服务器内部错误，请稍后重试",
        timestamp=datetime.now().isoformat(),
    )


# ============================================================
# API 端点
# ============================================================

@app.get("/api/v1/health", response_model=HealthResponse, tags=["系统"])
async def health_check():
    """健康检查"""
    pipeline_ready = False
    tts_engine = ""

    try:
        runner = get_runner()
        pipeline_ready = runner is not None
    except Exception as e:
        logger.warning(f"Pipeline 未就绪: {e}")

    try:
        tts = get_tts()
        tts_engine = tts.engine
    except Exception as e:
        logger.warning(f"TTS 引擎未就绪: {e}")

    return HealthResponse(
        status="ok",
        version="1.0.0",
        pipeline_ready=pipeline_ready,
        tts_engine=tts_engine,
        timestamp=datetime.now().isoformat(),
    )


@app.get("/api/v1/tts/status", tags=["TTS"])
async def tts_status():
    """获取 TTS 服务状态"""
    return {
        "indextts_running": _indextts_process is not None and _indextts_process.poll() is None,
        "indextts_ready": _indextts_ready,
        "indextts_port": _indextts_port,
        "indextts_pid": _indextts_process.pid if _indextts_process else None,
    }


@app.post("/api/v1/tts/restart", tags=["TTS"])
async def restart_tts_service():
    """重启 Index-TTS 服务"""
    global _indextts_ready
    
    _stop_indextts_service()
    _start_indextts_service()
    
    return {
        "status": "ok" if _indextts_ready else "failed",
        "message": "Index-TTS service restarted" if _indextts_ready else "Failed to restart Index-TTS service",
    }


class CreateProjectRequest(BaseModel):
    """创建项目请求（手动输入方式）"""
    title: str = Field(..., description="书名")
    author: str = Field("", description="作者")
    content: str = Field(..., description="小说内容")


@app.post("/api/v1/projects/upload", response_model=ProjectUploadResponse, tags=["项目"])
async def upload_project(file: UploadFile = File(None)):
    """
    上传小说 TXT 文件，自动分章并创建项目。

    - 接收 .txt 文件
    - 调用 ChapterSplitter.split_with_volumes() 分章
    - 返回项目 ID、书名、章节列表
    """
    content = None
    book_title = None

    if file is not None:
        if not file.filename or not file.filename.endswith(".txt"):
            raise HTTPException(status_code=400, detail="请上传 .txt 格式的文本文件")

        try:
            content_bytes = await file.read()
            content = content_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                content = content_bytes.decode("gbk")
            except UnicodeDecodeError:
                raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 或 GBK 编码")
        
        book_title = file.filename.replace(".txt", "").strip()
    else:
        raise HTTPException(status_code=400, detail="请上传文件或使用 /api/v1/projects/create 接口")

    if not content or not content.strip():
        raise HTTPException(status_code=400, detail="文件内容为空")

    project_id = str(uuid.uuid4())[:8]

    try:
        splitter = get_splitter()
        novel_structure = splitter.split_with_volumes(content)
    except Exception as e:
        logger.error(f"分章失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分章处理失败: {str(e)}")

    chapters = [
        ChapterInfo(
            index=ch.index,
            title=ch.title,
            word_count=len(ch.content),
            volume_index=ch.volume_index,
            volume_title=ch.volume_title,
        )
        for ch in novel_structure.chapters
    ]

    total_words = sum(len(ch.content) for ch in novel_structure.chapters)

    projects_store[project_id] = {
        "project_id": project_id,
        "book_title": book_title,
        "content": content,
        "novel_structure": novel_structure,
        "total_chapters": novel_structure.total_chapters,
        "total_volumes": novel_structure.total_volumes,
        "total_words": total_words,
        "created_at": datetime.now().isoformat(),
    }

    analysis_cache[project_id] = {}
    _save_projects_db()

    logger.info(f"项目 {project_id} 创建成功: {book_title}, {novel_structure.total_chapters} 章, {total_words} 字")

    return ProjectUploadResponse(
        project_id=project_id,
        book_title=book_title,
        total_chapters=novel_structure.total_chapters,
        total_volumes=novel_structure.total_volumes,
        chapters=chapters,
    )


@app.post("/api/v1/projects/create", response_model=ProjectUploadResponse, tags=["项目"])
async def create_project(request: CreateProjectRequest):
    """
    手动创建项目（通过输入内容方式）。

    - 接收书名、作者和小说内容
    - 如果内容为空，创建一个空白项目（包含一个默认空章节）
    - 如果有内容，调用 ChapterSplitter.split_with_volumes() 分章
    - 返回项目 ID、书名、章节列表
    """
    if not request.title or not request.title.strip():
        raise HTTPException(status_code=400, detail="书名不能为空")

    project_id = str(uuid.uuid4())[:8]
    book_title = request.title.strip()

    content = request.content or ""
    content = content.strip()

    if not content:
        # 空白项目：创建一个默认章节
        chapters = [
            ChapterInfo(
                index=0,
                title="第1章",
                word_count=0,
                volume_index=0,
                volume_title="",
            )
        ]
        total_words = 0
        novel_structure = NovelStructure(
            total_chapters=1,
            total_volumes=0,
            chapters=[],
        )
    else:
        try:
            splitter = get_splitter()
            novel_structure = splitter.split_with_volumes(request.content)
        except Exception as e:
            logger.error(f"分章失败: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"分章处理失败: {str(e)}")

        chapters = [
            ChapterInfo(
                index=ch.index,
                title=ch.title,
                word_count=len(ch.content),
                volume_index=ch.volume_index,
                volume_title=ch.volume_title,
            )
            for ch in novel_structure.chapters
        ]

        total_words = sum(len(ch.content) for ch in novel_structure.chapters)

    projects_store[project_id] = {
        "project_id": project_id,
        "book_title": book_title,
        "content": request.content,
        "novel_structure": novel_structure,
        "total_chapters": novel_structure.total_chapters,
        "total_volumes": novel_structure.total_volumes,
        "total_words": total_words,
        "created_at": datetime.now().isoformat(),
    }

    analysis_cache[project_id] = {}
    _save_projects_db()

    logger.info(f"项目 {project_id} 创建成功: {book_title}, {novel_structure.total_chapters} 章, {total_words} 字")

    return ProjectUploadResponse(
        project_id=project_id,
        book_title=book_title,
        total_chapters=novel_structure.total_chapters,
        total_volumes=novel_structure.total_volumes,
        chapters=chapters,
    )


@app.get("/api/v1/projects", response_model=List[ProjectSummary], tags=["项目"])
async def list_projects():
    """获取所有项目列表"""
    result = []
    now = datetime.now().isoformat()
    for pid, pdata in projects_store.items():
        p = ProjectSummary(
            id=pid,
            project_id=pid,
            title=pdata.get("book_title", ""),
            total_chapters=pdata.get("total_chapters", 0),
            total_volumes=pdata.get("total_volumes", 0),
            total_words=pdata.get("total_words", 0),
            progress=0,
            status="pending",
            lastEdit=pdata.get("created_at", now),
        )
        result.append(p)
    return result


@app.delete("/api/v1/projects/{project_id}", tags=["项目"])
async def delete_project(project_id: str):
    """删除项目"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")
    del projects_store[project_id]
    analysis_cache.pop(project_id, None)
    _save_projects_db()
    return {"status": "ok", "project_id": project_id}


@app.get("/api/v1/voices", response_model=List[VoiceInfo], tags=["音色"])
async def list_voices():
    """获取音色列表"""
    voices = [
        VoiceInfo(id=1, name="云深", gender="male", cat="male", desc="沉稳磁性，适合旁白和成熟男性角色", tags=["磁性","沉稳","旁白"], bars=[40,65,50,80,55,70,45,60,75,50,65,40,70,55,80,60,45,70,50,65]),
        VoiceInfo(id=2, name="凌风", gender="male", cat="male", desc="清朗少年音，适合年轻男性角色", tags=["少年","清朗","热血"], bars=[60,40,75,50,80,45,70,55,40,65,80,50,60,75,40,55,70,45,80,60]),
        VoiceInfo(id=3, name="若水", gender="female", cat="female", desc="温婉知性，适合女性角色和内心独白", tags=["温婉","知性","柔美"], bars=[30,50,40,60,35,55,45,50,30,60,40,55,35,50,60,45,40,55,30,50]),
        VoiceInfo(id=4, name="铁马", gender="male", cat="male", desc="豪迈刚毅，适合武将和豪爽角色", tags=["豪迈","刚毅","霸气"], bars=[80,60,90,70,85,65,80,75,60,90,70,85,65,80,90,75,60,85,70,80]),
        VoiceInfo(id=5, name="素心", gender="female", cat="female", desc="清冷空灵，适合仙侠女性角色", tags=["清冷","空灵","仙侠"], bars=[25,45,35,55,30,50,40,45,25,55,35,50,30,45,55,40,35,50,25,45]),
        VoiceInfo(id=6, name="墨言", gender="neutral", cat="neutral", desc="中性沉稳，适合旁白和叙述", tags=["中性","沉稳","叙述"], bars=[50,55,45,60,50,55,45,60,50,55,45,60,50,55,45,60,50,55,45,60]),
    ]
    return voices


@app.get("/api/v1/projects/{project_id}", response_model=ProjectInfo, tags=["项目"])
async def get_project(project_id: str):
    """获取项目基本信息"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    project = projects_store[project_id]

    return ProjectInfo(
        project_id=project["project_id"],
        book_title=project["book_title"],
        total_chapters=project["total_chapters"],
        total_volumes=project["total_volumes"],
        total_words=project["total_words"],
        created_at=project["created_at"],
    )


@app.get("/api/v1/projects/{project_id}/chapters", response_model=List[ChapterInfo], tags=["项目"])
async def get_project_chapters(project_id: str):
    """获取项目的章节列表"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    project = projects_store[project_id]
    novel_structure = project["novel_structure"]

    return [
        ChapterInfo(
            index=ch.index,
            title=ch.title,
            word_count=len(ch.content),
            volume_index=ch.volume_index,
            volume_title=ch.volume_title,
            content=ch.content,
        )
        for ch in novel_structure.chapters
    ]


@app.get("/api/v1/projects/{project_id}/chapters/{chapter_index}", response_model=ChapterAnalysisResponse, tags=["分析"])
async def analyze_chapter(project_id: str, chapter_index: int):
    """
    分析指定章节，返回段落/句子级数据。

    - 调用 PipelineRunner.analyze_chapters() 分析
    - 返回包含 speaker、emotion、sfx_words 等字段的结构化数据
    """
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    project = projects_store[project_id]
    novel_structure = project["novel_structure"]

    if chapter_index < 0 or chapter_index >= len(novel_structure.chapters):
        raise HTTPException(
            status_code=400,
            detail=f"章节索引 {chapter_index} 超出范围（0 ~ {len(novel_structure.chapters) - 1}）",
        )

    if chapter_index in analysis_cache.get(project_id, {}):
        cached = analysis_cache[project_id][chapter_index]
        return cached

    chapter = novel_structure.chapters[chapter_index]

    try:
        runner = get_runner()
        # 注入 project_id 到 runner，使角色创建时关联到项目
        runner._current_project_id = project_id

        results = runner.analyze_chapters(
            project["content"],
            start=chapter_index,
            end=chapter_index + 1,
            force=True,  # 强制重新分析，避免章节间缓存冲突
        )

        if not results:
            raise HTTPException(status_code=500, detail="章节分析返回空结果")

        chapter_result = results[0]

        sentences = []
        for sent in chapter_result.sentences:
            fragments = []
            for frag in getattr(sent, "fragments", []):
                fragments.append(SentenceFragment(
                    text=frag.text,
                    type=frag.type,
                    speaker=frag.speaker,
                ))
            sentences.append(SentenceData(
                text=sent.text,
                speaker=sent.speaker,
                emotion=sent.emotion,
                emotion_class=getattr(sent, "emotion_class", "neutral"),
                emotion_vector=getattr(sent, "emotion_vector", None),
                sentence_type=getattr(sent, "type", "narration"),
                entities=getattr(sent, "entities", []),
                fragments=fragments,
            ))

        response = ChapterAnalysisResponse(
            chapter_index=chapter_index,
            chapter_title=chapter.title,
            total_sentences=len(sentences),
            sentences=sentences,
            statistics=chapter_result.statistics,
        )

        if project_id not in analysis_cache:
            analysis_cache[project_id] = {}
        analysis_cache[project_id][chapter_index] = response

        logger.info(f"章节 {chapter_index} 分析完成: {len(sentences)} 个句子")
        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"章节分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"章节分析失败: {str(e)}")


@app.get("/api/v1/projects/{project_id}/characters", response_model=CharactersResponse, tags=["角色"])
async def get_project_characters(project_id: str):
    """获取项目中的所有角色"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    try:
        char_manager = get_char_manager()
        characters = char_manager.get_all_characters(project_id)

        char_list = []
        # 旁白角色始终存在（锁定）
        char_list.append(CharacterInfo(
            id=-1,
            name="旁白",
            gender="neutral",
            aliases=["narrator", "叙述"],
            first_appearance=None,
            is_locked=True,
        ))
        for char in characters:
            char_list.append(CharacterInfo(
                id=getattr(char, "id", None),
                name=char.name,
                gender=getattr(char, "gender", "unknown"),
                aliases=list(getattr(char, "aliases", [])),
                first_appearance=getattr(char, "first_appearance", None),
                is_locked=getattr(char, "is_locked", False),
            ))

        return CharactersResponse(
            total=len(char_list),
            characters=char_list,
        )

    except Exception as e:
        logger.error(f"获取角色列表失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取角色列表失败: {str(e)}")


@app.post("/api/v1/projects/{project_id}/characters/{char_id}/lock", tags=["角色"])
async def lock_character(project_id: str, char_id: int):
    """锁定角色，锁定后在旁白匹配中获得最高优先级"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    try:
        char_manager = get_char_manager()
        success = char_manager.lock_character(char_id, project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"角色 {char_id} 不存在或不属于该项目")
        return {"status": "ok", "message": f"角色 {char_id} 已锁定"}
    except Exception as e:
        logger.error(f"锁定角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"锁定角色失败: {str(e)}")


@app.post("/api/v1/projects/{project_id}/characters/{char_id}/unlock", tags=["角色"])
async def unlock_character(project_id: str, char_id: int):
    """解锁角色，恢复正常匹配"""
    if project_id not in projects_store:
        raise HTTPException(status_code=404, detail=f"项目 {project_id} 不存在")

    try:
        char_manager = get_char_manager()
        success = char_manager.unlock_character(char_id, project_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"角色 {char_id} 不存在或不属于该项目")
        return {"status": "ok", "message": f"角色 {char_id} 已解锁"}
    except Exception as e:
        logger.error(f"解锁角色失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"解锁角色失败: {str(e)}")


@app.post("/api/v1/tts/generate", response_model=TTSResponse, tags=["TTS"])
async def generate_tts(request: TTSRequest):
    """
    生成 TTS 音频。

    - 调用 tts_generator.generate_audio_async() 生成音频
    - 支持 emotion_vector 8维向量（Index-TTS）
    - 返回音频文件下载 URL
    """
    try:
        tts = get_tts()
        logger.info(f"TTS 请求: speaker={request.speaker}, emotion={request.emotion}, type={request.sentence_type}, text_len={len(request.text)}")
        filename = f"tts_{uuid.uuid4().hex[:12]}.wav"
        output_path = AUDIO_DIR / filename

        await tts.generate_audio_async(
            text=request.text,
            speaker=request.speaker,
            emotion=request.emotion,
            output_file=output_path,
            sentence_type=request.sentence_type,
        )

        logger.info(f"TTS 完成: {filename}, size={output_path.stat().st_size if output_path.exists() else 0}")

        if not output_path.exists():
            raise HTTPException(status_code=500, detail="音频文件生成失败")

        file_size = output_path.stat().st_size
        duration_ms = int(file_size / 172) if file_size > 0 else 0

        return TTSResponse(
            audio_url=f"/api/v1/audio/{filename}",
            filename=filename,
            duration_ms=duration_ms,
            engine=tts.engine,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"TTS 生成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"TTS 生成失败: {str(e)}")


@app.post("/api/v1/tts/chapter", response_model=ChapterSynthesizeResponse, tags=["TTS"])
async def synthesize_chapter(request: ChapterSynthesizeRequest):
    """
    合成并合并整章音频。

    - 接受 segments 列表，逐段调用 TTS
    - 使用 pydub 合并为单个音频文件
    - 返回合并后的音频 URL 和每段的时间戳
    """
    import wave
    context = {"segments": []}
    try:
        tts = get_tts()
        audio_segments = []
        segment_times = []
        offset_ms = 0

        for i, seg in enumerate(request.segments):
            if not seg.text or not seg.text.strip():
                segment_times.append({"index": i, "start_ms": offset_ms, "end_ms": offset_ms, "text": seg.text[:40]})
                continue

            tmp_path = AUDIO_DIR / f"tmp_{uuid.uuid4().hex[:8]}_{i}.wav"
            try:
                await tts.generate_audio_async(
                    text=seg.text,
                    speaker=seg.speaker or "default",
                    emotion=seg.emotion or "neutral",
                    output_file=tmp_path,
                    sentence_type=seg.sentence_type or "narration",
                )

                if tmp_path.exists():
                    import wave as wav_lib
                    try:
                        with wav_lib.open(str(tmp_path), 'rb') as wf:
                            frames = wf.getnframes()
                            rate = wf.getframerate()
                            dur_ms = int(frames / rate * 1000) if rate > 0 else 0
                    except Exception:
                        dur_ms = int(tmp_path.stat().st_size / 172)

                    segment_times.append({
                        "index": i,
                        "start_ms": offset_ms,
                        "end_ms": offset_ms + dur_ms,
                        "text": seg.text[:40],
                    })
                    offset_ms += dur_ms

                    from pydub import AudioSegment as PydubSegment
                    try:
                        seg_audio = PydubSegment.from_wav(str(tmp_path))
                        audio_segments.append(seg_audio)
                    except Exception:
                        pass
        
            except Exception as seg_err:
                logger.warning(f"段{i} TTS 失败: {seg_err}")
                segment_times.append({"index": i, "start_ms": offset_ms, "end_ms": offset_ms, "text": seg.text[:40], "error": str(seg_err)[:60]})

        if not audio_segments:
            raise HTTPException(status_code=500, detail="所有段落 TTS 生成均失败")

        # 用 pydub 合并（export to WAV 不需要 ffmpeg）
        merged = audio_segments[0]
        for s in audio_segments[1:]:
            merged = merged + s

        filename = f"chapter_{uuid.uuid4().hex[:12]}.wav"
        output_path = AUDIO_DIR / filename

        # 先试 mp3（需要 ffmpeg），不行就 WAV
        try:
            mp3_path = output_path.with_suffix('.mp3')
            merged.export(str(mp3_path), format="mp3")
            filename = mp3_path.name
            output_path = mp3_path
        except Exception:
            merged.export(str(output_path), format="wav")

        # 清理临时文件
        for f in AUDIO_DIR.glob("tmp_*.wav"):
            try: f.unlink()
            except: pass

        total_dur = sum(st["end_ms"] - st["start_ms"] for st in segment_times)

        return ChapterSynthesizeResponse(
            audio_url=f"/api/v1/audio/{filename}",
            filename=filename,
            total_duration_ms=total_dur,
            segment_count=len(request.segments),
            engine=tts.engine,
            segment_times=segment_times,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"章节合成失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"章节合成失败: {str(e)}")


@app.get("/api/v1/audio/{filename}", tags=["音频"])
async def get_audio(filename: str):
    """下载音频文件"""
    audio_path = AUDIO_DIR / filename

    if not audio_path.exists():
        raise HTTPException(status_code=404, detail=f"音频文件 {filename} 不存在")

    return FileResponse(
        path=str(audio_path),
        media_type="audio/wav",
        filename=filename,
    )


# ============================================================
# 前端静态文件服务（同域，无 CORS 问题）
# ============================================================

FRONTEND_DIR = PROJECT_ROOT / "frontend"

# 挂载 JS、CSS 和 Audio 静态目录
app.mount("/js", StaticFiles(directory=str(FRONTEND_DIR / "js")), name="js")
app.mount("/css", StaticFiles(directory=str(FRONTEND_DIR / "css")), name="css")
app.mount("/audio", StaticFiles(directory=str(FRONTEND_DIR / "audio")), name="audio")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(str(FRONTEND_DIR / "index.html"))


# ============================================================
# 启动入口
# ============================================================

if __name__ == "__main__":
    # 启动 Index-TTS 服务
    _start_indextts_service()
    
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )
