from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, Any
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_admin_user
from app.models.user import User
from app.models.log import SystemSetting

router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingUpdate(BaseModel):
    value: Optional[str] = None
    value_json: Optional[Any] = None


@router.get("")
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    settings_list = db.query(SystemSetting).all()
    result = {}
    for s in settings_list:
        if not s.is_sensitive:
            result[s.key] = {
                "value": s.value,
                "value_json": s.value_json,
                "description": s.description,
            }
        else:
            result[s.key] = {
                "value": "***",
                "description": s.description,
            }
    return result


@router.put("")
def update_settings(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    for key, value_data in data.items():
        setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
        if setting:
            if isinstance(value_data, dict):
                setting.value = value_data.get("value")
                setting.value_json = value_data.get("value_json")
            else:
                setting.value = str(value_data)
        else:
            setting = SystemSetting(
                key=key,
                value=str(value_data) if not isinstance(value_data, dict) else None,
                value_json=value_data if isinstance(value_data, dict) else None,
            )
            db.add(setting)
    db.commit()
    return {"status": "updated"}


@router.get("/scheduler")
def get_scheduler_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """スケジューラー設定を取得"""
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "weekly_job_schedule"
    ).first()

    default = {
        "day_of_week": 1,  # 月曜日
        "hour": 9,
        "minute": 0,
        "enabled": True,
    }

    if setting and setting.value_json:
        return setting.value_json
    return default


@router.put("/scheduler")
def update_scheduler_settings(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    """スケジューラー設定を更新"""
    setting = db.query(SystemSetting).filter(
        SystemSetting.key == "weekly_job_schedule"
    ).first()

    if not setting:
        setting = SystemSetting(
            key="weekly_job_schedule",
            description="週次ジョブのスケジュール設定",
        )
        db.add(setting)

    setting.value_json = data

    # Celery Beatスケジュールを更新
    from app.jobs.celery_app import celery_app
    from celery.schedules import crontab

    day = data.get("day_of_week", 1)
    hour = data.get("hour", 9)
    minute = data.get("minute", 0)

    if data.get("enabled", True):
        celery_app.conf.beat_schedule["weekly-pipeline"]["schedule"] = crontab(
            hour=hour, minute=minute, day_of_week=day
        )

    db.commit()
    return {"status": "updated", "schedule": data}
