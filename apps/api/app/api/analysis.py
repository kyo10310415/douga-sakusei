from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.analysis import AIAnalysisReport
from app.models.youtube import WeeklyMetrics

router = APIRouter(prefix="/analysis", tags=["Analysis"])


@router.post("/run")
def run_analysis(
    weekly_metrics_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
):
    """AI分析を手動実行"""
    from app.jobs.ai_jobs import run_ai_analysis
    task = run_ai_analysis.delay(weekly_metrics_id=weekly_metrics_id)
    return {"task_id": task.id, "status": "started"}


@router.get("/reports")
def list_reports(
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析レポート一覧"""
    reports = db.query(AIAnalysisReport).order_by(
        AIAnalysisReport.created_at.desc()
    ).limit(limit).all()
    return [_report_to_dict(r) for r in reports]


@router.get("/reports/{report_id}")
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """分析レポート詳細"""
    report = db.query(AIAnalysisReport).filter(
        AIAnalysisReport.id == report_id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="レポートが見つかりません")
    return _report_to_dict(report)


def _report_to_dict(r: AIAnalysisReport) -> dict:
    return {
        "id": str(r.id),
        "status": r.status,
        "analysis_type": r.analysis_type,
        "summary": r.summary,
        "trending_video_patterns": r.trending_video_patterns,
        "declining_video_patterns": r.declining_video_patterns,
        "high_ctr_title_patterns": r.high_ctr_title_patterns,
        "high_retention_patterns": r.high_retention_patterns,
        "drop_off_factors": r.drop_off_factors,
        "improvement_points": r.improvement_points,
        "next_theme_suggestions": r.next_theme_suggestions,
        "next_title_suggestions": r.next_title_suggestions,
        "next_thumbnail_suggestions": r.next_thumbnail_suggestions,
        "next_script_policy": r.next_script_policy,
        "analyzed_at": r.analyzed_at.isoformat() if r.analyzed_at else None,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }
