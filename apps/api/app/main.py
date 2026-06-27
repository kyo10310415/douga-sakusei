from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.core.config import settings

# FastAPIアプリ作成
app = FastAPI(
    title="VTuber Studio API",
    description="週次YouTube分析・動画自動生成システム",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORSミドルウェア
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ======================================================
# 認証不要エンドポイント（ルーター登録より必ず前に定義）
# ======================================================
@app.get("/health", tags=["system"])
def health_check():
    return {"status": "ok", "service": "VTuber Studio API"}


@app.get("/version", tags=["system"])
def version_check():
    """デプロイバージョン診断用エンドポイント"""
    import os, hashlib
    chars_path = os.path.join(os.path.dirname(__file__), "api", "characters.py")
    try:
        with open(chars_path, "rb") as f:
            content = f.read()
        file_hash = hashlib.md5(content).hexdigest()[:8]
        has_tts_preview = b"tts-preview" in content
        tts_line = None
        for i, line in enumerate(content.decode().splitlines(), 1):
            if "@router.post" in line and "tts-preview" in line:
                tts_line = i
                break
    except Exception as e:
        return {"error": str(e)}
    return {
        "characters_py_hash": file_hash,
        "has_tts_preview_route": has_tts_preview,
        "tts_preview_line": tts_line,
        "file_size_bytes": len(content),
    }


# 静的ファイルサービス
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

# APIルーターを登録
from app.api.auth import router as auth_router
from app.api.youtube import router as youtube_router
from app.api.characters import router as characters_router
from app.api.themes import router as themes_router
from app.api.analysis import router as analysis_router
from app.api.video_jobs import router as video_jobs_router
from app.api.reviews import router as reviews_router
from app.api.settings import router as settings_router
from app.api.dashboard import router as dashboard_router
from app.api.promo import router as promo_router

API_PREFIX = "/api"

app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(youtube_router, prefix=API_PREFIX)
app.include_router(characters_router, prefix=API_PREFIX)
app.include_router(themes_router, prefix=API_PREFIX)
app.include_router(analysis_router, prefix=API_PREFIX)
app.include_router(video_jobs_router, prefix=API_PREFIX)
app.include_router(reviews_router, prefix=API_PREFIX)
app.include_router(settings_router, prefix=API_PREFIX)
app.include_router(dashboard_router, prefix=API_PREFIX)
app.include_router(promo_router, prefix=API_PREFIX)


@app.on_event("startup")
async def startup_event():
    """起動時の初期化処理"""
    pass
