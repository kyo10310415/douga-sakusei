from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.theme import VideoThemeSetting

router = APIRouter(prefix="/themes", tags=["Themes"])


class ThemeCreate(BaseModel):
    name: str = "デフォルト設定"
    main_channel_theme: Optional[str] = None
    target_genres: Optional[List[str]] = None
    excluded_genres: Optional[List[str]] = None
    target_audience: Optional[str] = None
    purposes: Optional[List[str]] = None
    default_duration_seconds: Optional[int] = 600
    structure_hook_seconds: Optional[int] = 15
    structure_problem_seconds: Optional[int] = 60
    structure_main_seconds: Optional[int] = 420
    structure_example_seconds: Optional[int] = 60
    structure_summary_seconds: Optional[int] = 30
    structure_cta_seconds: Optional[int] = 15
    custom_structure: Optional[list] = None  # ← 追加
    thumbnail_policy: Optional[str] = None
    title_policy: Optional[str] = None
    description_template: Optional[str] = None
    pinned_comment_template: Optional[str] = None
    is_default: Optional[bool] = False


@router.get("")
def list_themes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    themes = db.query(VideoThemeSetting).filter(
        VideoThemeSetting.user_id == current_user.id,  # ← 自分のテーマのみ
        VideoThemeSetting.is_active == True,
    ).order_by(VideoThemeSetting.created_at.desc()).all()
    return [_theme_to_dict(t) for t in themes]


@router.post("")
def create_theme(
    data: ThemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if data.is_default:
        db.query(VideoThemeSetting).filter(
            VideoThemeSetting.user_id == current_user.id,
            VideoThemeSetting.is_default == True,
        ).update({"is_default": False})

    theme = VideoThemeSetting(user_id=current_user.id, **data.dict())
    db.add(theme)
    db.commit()
    db.refresh(theme)
    return _theme_to_dict(theme)


@router.delete("/{theme_id}")
def delete_theme(
    theme_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    theme = db.query(VideoThemeSetting).filter(
        VideoThemeSetting.id == theme_id,
        VideoThemeSetting.user_id == current_user.id,  # 自分のテーマのみ削除可
        VideoThemeSetting.is_active == True,
    ).first()
    if not theme:
        raise HTTPException(status_code=404, detail="テーマが見つかりません")

    theme.is_active = False  # 論理削除
    db.commit()
    return {"message": "削除しました"}


@router.put("/{theme_id}")
def update_theme(
    theme_id: str,
    data: ThemeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    theme = db.query(VideoThemeSetting).filter(
        VideoThemeSetting.id == theme_id,
        VideoThemeSetting.is_active == True,
    ).first()
    if not theme:
        raise HTTPException(status_code=404, detail="テーマが見つかりません")

    if data.is_default:
        db.query(VideoThemeSetting).filter(
            VideoThemeSetting.user_id == current_user.id,
            VideoThemeSetting.is_default == True,
            VideoThemeSetting.id != theme_id,
        ).update({"is_default": False})

    for key, value in data.dict(exclude_unset=True).items():
        setattr(theme, key, value)

    db.commit()
    db.refresh(theme)
    return _theme_to_dict(theme)


def _theme_to_dict(t: VideoThemeSetting) -> dict:
    return {
        "id": str(t.id),
        "name": t.name,
        "main_channel_theme": t.main_channel_theme,
        "target_genres": t.target_genres,
        "excluded_genres": t.excluded_genres,
        "target_audience": t.target_audience,
        "purposes": t.purposes,
        "default_duration_seconds": t.default_duration_seconds,
        "structure_hook_seconds": t.structure_hook_seconds,
        "structure_problem_seconds": t.structure_problem_seconds,
        "structure_main_seconds": t.structure_main_seconds,
        "structure_example_seconds": t.structure_example_seconds,
        "structure_summary_seconds": t.structure_summary_seconds,
        "structure_cta_seconds": t.structure_cta_seconds,
        "custom_structure": getattr(t, "custom_structure", None),  # ← DB未適用でも安全
        "thumbnail_policy": t.thumbnail_policy,
        "title_policy": t.title_policy,
        "description_template": t.description_template,
        "pinned_comment_template": t.pinned_comment_template,
        "is_default": t.is_default,
        "created_at": t.created_at.isoformat() if t.created_at else None,
    }
