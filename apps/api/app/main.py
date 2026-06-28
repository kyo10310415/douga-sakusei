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


@app.get("/db-check", tags=["system"])
def db_check():
    """DB スキーマ診断 - 必要なカラムが存在するか確認"""
    from app.core.database import engine
    from sqlalchemy import text
    results = {}
    checks = [
        ("video_theme_settings", "custom_structure"),
        ("character_profiles", "voice_instructions"),
        ("video_plans", "id"),
        ("scripts", "id"),
    ]
    try:
        with engine.connect() as conn:
            for table, col in checks:
                try:
                    row = conn.execute(
                        text(f"SELECT column_name FROM information_schema.columns "
                             f"WHERE table_name=:t AND column_name=:c"),
                        {"t": table, "c": col}
                    ).fetchone()
                    results[f"{table}.{col}"] = "✅ exists" if row else "❌ MISSING"
                except Exception as e:
                    results[f"{table}.{col}"] = f"ERROR: {e}"
            # alembic version
            try:
                ver = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                results["alembic_version"] = ver[0] if ver else "none"
            except Exception as e:
                results["alembic_version"] = f"ERROR: {e}"
    except Exception as e:
        return {"error": str(e)}
    return results


# ── 500エラー時にもCORSヘッダーを付ける保護ミドルウェア ──
# FastAPIはデフォルトで500エラー時にCORSミドルウェアをバイパスする場合がある
# → ExceptionMiddlewareより先にCORSミドルウェアが動くようstarlette標準に依存
# （CORSMiddlewareは既に追加済みなので追加対応不要だが念のためコメントで明示）

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
    """起動時の初期化処理
    
    Alembic migration が何らかの理由で失敗した場合のフォールバック:
    必須カラムが存在しない場合は直接 ALTER TABLE で追加する。
    冪等なので何度実行しても安全。
    """
    from app.core.database import engine
    from sqlalchemy import text
    import logging
    logger = logging.getLogger("startup")

    # 追加が必要なカラムの定義: (テーブル名, カラム名, DDL型)
    required_columns = [
        ("video_theme_settings", "custom_structure",  "JSONB"),
        ("character_profiles",   "voice_instructions", "TEXT"),
    ]

    try:
        with engine.begin() as conn:
            for table, column, col_type in required_columns:
                row = conn.execute(
                    text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = :t AND column_name = :c"
                    ),
                    {"t": table, "c": column},
                ).fetchone()

                if row:
                    logger.info(f"[startup] {table}.{column} ✅ already exists")
                else:
                    # カラムが存在しない → 直接 ALTER TABLE で追加
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {col_type}")
                    )
                    logger.warning(
                        f"[startup] {table}.{column} ❌ was MISSING → added via ALTER TABLE"
                    )
    except Exception as e:
        # DB接続失敗などの場合もサーバー起動は止めない
        logger.error(f"[startup] column check failed (non-fatal): {e}")
