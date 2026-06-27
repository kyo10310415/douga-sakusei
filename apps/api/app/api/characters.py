import os
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.character import CharacterProfile, CharacterImage

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/characters", tags=["Characters"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class CharacterCreate(BaseModel):
    name: str
    age_setting: Optional[str] = None
    personality: Optional[str] = None
    tone: Optional[str] = None
    first_person: Optional[str] = "わたし"
    viewer_address: Optional[str] = "みなさん"
    specialty_genres: Optional[List[str]] = None
    weak_genres: Optional[List[str]] = None
    character_description: Optional[str] = None
    ng_expressions: Optional[str] = None
    speech_samples: Optional[str] = None
    tts_provider: Optional[str] = "mock"
    voice_type: Optional[str] = None
    speech_rate: Optional[float] = 1.0
    pitch: Optional[float] = 0.0
    emotion_strength: Optional[float] = 0.7
    is_default: Optional[bool] = False


class TTSPreviewRequest(BaseModel):
    provider: str                          # mock / openai / elevenlabs / voicevox
    voice_type: Optional[str] = None       # 声のID / 種類
    speech_rate: Optional[float] = 1.0
    pitch: Optional[float] = 0.0
    emotion_strength: Optional[float] = 0.7
    text: Optional[str] = None             # カスタムテキスト（省略時はデフォルト文）


# プロバイダーごとのデフォルトサンプルテキスト
_SAMPLE_TEXT = "こんにちは！わたしはAIキャラクターです。この声でよろしければ保存してください。"


@router.get("")
def list_characters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    characters = db.query(CharacterProfile).filter(
        CharacterProfile.is_active == True
    ).order_by(CharacterProfile.created_at.desc()).all()

    return [_character_to_dict(c) for c in characters]


@router.post("")
def create_character(
    data: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.is_default:
        # 既存のデフォルトを解除
        db.query(CharacterProfile).filter(
            CharacterProfile.user_id == current_user.id,
            CharacterProfile.is_default == True,
        ).update({"is_default": False})

    character = CharacterProfile(
        user_id=current_user.id,
        **data.dict(),
    )
    db.add(character)
    db.commit()
    db.refresh(character)
    return _character_to_dict(character)


@router.get("/{character_id}")
def get_character(
    character_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    character = db.query(CharacterProfile).filter(
        CharacterProfile.id == character_id,
        CharacterProfile.is_active == True,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")
    return _character_to_dict(character)


@router.put("/{character_id}")
def update_character(
    character_id: str,
    data: CharacterCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    character = db.query(CharacterProfile).filter(
        CharacterProfile.id == character_id,
        CharacterProfile.is_active == True,
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")

    if data.is_default:
        db.query(CharacterProfile).filter(
            CharacterProfile.user_id == current_user.id,
            CharacterProfile.is_default == True,
            CharacterProfile.id != character_id,
        ).update({"is_default": False})

    for key, value in data.dict(exclude_unset=True).items():
        setattr(character, key, value)

    db.commit()
    db.refresh(character)
    return _character_to_dict(character)


@router.post("/{character_id}/images")
async def upload_character_image(
    character_id: str,
    image_type: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """キャラクター画像をアップロード"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="対応していない画像形式です")

    character = db.query(CharacterProfile).filter(
        CharacterProfile.id == character_id
    ).first()
    if not character:
        raise HTTPException(status_code=404, detail="キャラクターが見つかりません")

    # 保存ディレクトリ
    upload_dir = os.path.join(settings.UPLOAD_DIR, "characters", character_id)
    os.makedirs(upload_dir, exist_ok=True)

    # ファイル名生成
    ext = os.path.splitext(file.filename)[1] if file.filename else ".png"
    filename = f"{image_type}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(upload_dir, filename)

    # 保存
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    # 同じimage_typeが既にある場合は削除
    existing = db.query(CharacterImage).filter(
        CharacterImage.character_id == character_id,
        CharacterImage.image_type == image_type,
    ).first()
    if existing:
        db.delete(existing)

    char_image = CharacterImage(
        character_id=character_id,
        image_type=image_type,
        file_path=file_path,
        file_url=f"{settings.STORAGE_BASE_URL}/characters/{character_id}/{filename}",
        original_filename=file.filename,
        mime_type=file.content_type,
        file_size=len(content),
    )
    db.add(char_image)
    db.commit()
    db.refresh(char_image)

    return {
        "id": str(char_image.id),
        "image_type": char_image.image_type,
        "file_url": char_image.file_url,
    }


# ─────────────────────────────────────────────────────────
# TTS プレビュー（サンプル音声生成）
# ─────────────────────────────────────────────────────────

@router.post("/tts-preview")
async def tts_preview(
    req: TTSPreviewRequest,
    current_user: User = Depends(get_current_user),
):
    """
    指定プロバイダー・声の種類でサンプル音声を生成し audio/mpeg または audio/wav で返す。
    APIキー未設定 / 外部サービス未接続の場合は success=False の JSON を返す。
    """
    text = (req.text or _SAMPLE_TEXT).strip()[:200]  # 最大200文字に制限
    provider = req.provider.lower()

    # ── mock ──────────────────────────────────────────────
    if provider == "mock":
        audio_bytes = _generate_silent_wav(text, req.speech_rate or 1.0)
        return Response(content=audio_bytes, media_type="audio/wav")

    # ── OpenAI TTS ────────────────────────────────────────
    if provider == "openai":
        api_key = settings.TTS_API_KEY or settings.OPENAI_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=422,
                detail={
                    "provider": "openai",
                    "error": "OPENAI_API_KEY が設定されていません。",
                    "hint": "Render の環境変数に OPENAI_API_KEY または TTS_API_KEY を追加してください。",
                },
            )
        try:
            import openai as _openai
            client = _openai.AsyncOpenAI(api_key=api_key)
            voice = req.voice_type or "nova"
            response = await client.audio.speech.create(
                model="tts-1",
                voice=voice,
                input=text,
                speed=max(0.25, min(4.0, req.speech_rate or 1.0)),
            )
            audio_bytes = response.content
            return Response(content=audio_bytes, media_type="audio/mpeg")
        except Exception as e:
            logger.error("OpenAI TTS preview error: %s", e)
            raise HTTPException(
                status_code=502,
                detail={"provider": "openai", "error": str(e)},
            )

    # ── ElevenLabs ────────────────────────────────────────
    if provider == "elevenlabs":
        api_key = settings.TTS_API_KEY
        if not api_key:
            raise HTTPException(
                status_code=422,
                detail={
                    "provider": "elevenlabs",
                    "error": "TTS_API_KEY（ElevenLabs APIキー）が設定されていません。",
                    "hint": "Render の環境変数に TTS_API_KEY を追加してください。",
                },
            )
        voice_id = req.voice_type or "21m00Tcm4TlvDq8ikWAM"  # Rachel
        try:
            import httpx
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": api_key,
                        "Content-Type": "application/json",
                    },
                    json={
                        "text": text,
                        "model_id": "eleven_multilingual_v2",
                        "voice_settings": {
                            "stability": 0.5,
                            "similarity_boost": req.emotion_strength or 0.7,
                            "speed": req.speech_rate or 1.0,
                        },
                    },
                )
            if resp.status_code == 200:
                return Response(content=resp.content, media_type="audio/mpeg")
            raise HTTPException(
                status_code=502,
                detail={"provider": "elevenlabs", "error": f"HTTP {resp.status_code}: {resp.text[:200]}"},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("ElevenLabs TTS preview error: %s", e)
            raise HTTPException(
                status_code=502,
                detail={"provider": "elevenlabs", "error": str(e)},
            )

    # ── VOICEVOX ──────────────────────────────────────────
    if provider == "voicevox":
        voicevox_url = settings.VOICEVOX_URL
        speaker_id = int(req.voice_type) if req.voice_type and req.voice_type.isdigit() else 1
        try:
            import httpx
            async with httpx.AsyncClient(timeout=15) as client:
                # 音声合成クエリ
                qr = await client.post(
                    f"{voicevox_url}/audio_query",
                    params={"text": text, "speaker": speaker_id},
                )
                if qr.status_code != 200:
                    raise HTTPException(
                        status_code=422,
                        detail={
                            "provider": "voicevox",
                            "error": "VOICEVOX サーバーに接続できません。",
                            "hint": f"VOICEVOX_URL ({voicevox_url}) が起動しているか確認してください。Render 本番環境では VOICEVOX は利用できません。",
                        },
                    )
                query = qr.json()
                query["speedScale"] = req.speech_rate or 1.0
                query["pitchScale"] = req.pitch or 0.0
                query["intonationScale"] = req.emotion_strength or 0.7

                # 音声生成
                sr = await client.post(
                    f"{voicevox_url}/synthesis",
                    params={"speaker": speaker_id},
                    json=query,
                )
            if sr.status_code == 200:
                return Response(content=sr.content, media_type="audio/wav")
            raise HTTPException(
                status_code=502,
                detail={"provider": "voicevox", "error": f"HTTP {sr.status_code}"},
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error("VOICEVOX TTS preview error: %s", e)
            raise HTTPException(
                status_code=422,
                detail={
                    "provider": "voicevox",
                    "error": "VOICEVOX サーバーに接続できません。",
                    "hint": "Render 本番環境では VOICEVOX は動作しません。ローカル環境でご利用ください。",
                },
            )

    raise HTTPException(status_code=400, detail=f"未対応のプロバイダー: {provider}")


def _generate_silent_wav(text: str, speech_rate: float = 1.0) -> bytes:
    """テキスト長に応じた無音WAVバイト列を生成（mock用）"""
    import struct
    import wave
    import io

    duration = max(1.0, len(text) * 0.07 / speech_rate)
    sample_rate = 22050
    num_samples = int(sample_rate * duration)

    buf = io.BytesIO()
    with wave.open(buf, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * num_samples)
    return buf.getvalue()


def _character_to_dict(c: CharacterProfile) -> dict:
    images = {}
    if c.images:
        for img in c.images:
            images[img.image_type] = {
                "id": str(img.id),
                "url": img.file_url,
                "image_type": img.image_type,
            }

    return {
        "id": str(c.id),
        "name": c.name,
        "age_setting": c.age_setting,
        "personality": c.personality,
        "tone": c.tone,
        "first_person": c.first_person,
        "viewer_address": c.viewer_address,
        "specialty_genres": c.specialty_genres,
        "weak_genres": c.weak_genres,
        "character_description": c.character_description,
        "ng_expressions": c.ng_expressions,
        "speech_samples": c.speech_samples,
        "tts_provider": c.tts_provider,
        "voice_type": c.voice_type,
        "speech_rate": c.speech_rate,
        "pitch": c.pitch,
        "emotion_strength": c.emotion_strength,
        "is_default": c.is_default,
        "is_active": c.is_active,
        "images": images,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }
