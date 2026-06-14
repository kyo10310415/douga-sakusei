import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.config import settings
from app.models.user import User
from app.models.character import CharacterProfile, CharacterImage

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
