import asyncio
from datetime import datetime
from typing import Optional
from app.jobs.celery_app import celery_app
from app.core.database import SessionLocal
from app.models.analysis import AIAnalysisReport
from app.models.youtube import YouTubeAccount, WeeklyMetrics, VideoMetrics
from app.models.character import CharacterProfile
from app.models.theme import VideoThemeSetting
from app.models.video import VideoPlan, Script, ScriptSection
from app.models.log import JobLog
from app.services.ai_service import get_ai_service


@celery_app.task(
    bind=True,
    name="app.jobs.ai_jobs.run_ai_analysis",
    max_retries=3,
    default_retry_delay=120,
)
def run_ai_analysis(self, weekly_metrics_id: Optional[str] = None, youtube_account_id: Optional[str] = None):
    """週次データをAI分析"""
    db = SessionLocal()
    report = None

    try:
        # 最新の週次データを取得
        query = db.query(WeeklyMetrics)
        if weekly_metrics_id:
            query = query.filter(WeeklyMetrics.id == weekly_metrics_id)
        elif youtube_account_id:
            query = query.filter(WeeklyMetrics.youtube_account_id == youtube_account_id)
        weekly = query.order_by(WeeklyMetrics.created_at.desc()).first()

        # 分析レポート作成
        report = AIAnalysisReport(
            youtube_account_id=weekly.youtube_account_id if weekly else None,
            weekly_metrics_id=weekly.id if weekly else None,
            analysis_type="weekly",
            status="running",
        )
        db.add(report)
        db.commit()

        # 分析用データ準備
        video_metrics = []
        if weekly:
            vms = db.query(VideoMetrics).filter(
                VideoMetrics.weekly_metrics_id == weekly.id
            ).all()
            for vm in vms:
                video_metrics.append({
                    "title": vm.title,
                    "views": vm.views,
                    "ctr": vm.ctr,
                    "avg_view_duration": vm.avg_view_duration,
                    "avg_view_percentage": vm.avg_view_percentage,
                    "likes": vm.likes,
                    "comments": vm.comments,
                })

        analysis_data = {
            "weekly_summary": {
                "total_views": weekly.total_views if weekly else 0,
                "total_impressions": weekly.total_impressions if weekly else 0,
                "ctr": weekly.ctr if weekly else 0,
                "views_change_rate": weekly.views_change_rate if weekly else 0,
            } if weekly else {},
            "videos": video_metrics,
        }

        # AI分析実行
        ai_service = get_ai_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(ai_service.analyze_weekly_data(analysis_data))
        finally:
            loop.close()

        # 結果保存
        report.trending_video_patterns = result.get("trending_video_patterns")
        report.declining_video_patterns = result.get("declining_video_patterns")
        report.high_ctr_title_patterns = result.get("high_ctr_title_patterns")
        report.high_retention_patterns = result.get("high_retention_patterns")
        report.drop_off_factors = result.get("drop_off_factors")
        report.improvement_points = result.get("improvement_points")
        report.next_theme_suggestions = result.get("next_theme_suggestions")
        report.next_title_suggestions = result.get("next_title_suggestions")
        report.next_thumbnail_suggestions = result.get("next_thumbnail_suggestions")
        report.next_script_policy = result.get("next_script_policy")
        report.summary = result.get("summary")
        report.status = "completed"
        report.analyzed_at = datetime.utcnow()
        db.commit()

        # 次のジョブをキック
        generate_video_plan.delay(analysis_report_id=str(report.id))

        return {"status": "success", "report_id": str(report.id)}

    except Exception as exc:
        if report:
            report.status = "failed"
            report.error_message = str(exc)
            db.commit()
        raise self.retry(exc=exc)
    finally:
        db.close()


@celery_app.task(
    bind=True,
    name="app.jobs.ai_jobs.generate_video_plan",
    max_retries=3,
    default_retry_delay=120,
)
def generate_video_plan(self, analysis_report_id: Optional[str] = None):
    """AI分析結果から動画企画を生成"""
    db = SessionLocal()

    try:
        # デフォルトキャラクターとテーマを取得
        character = db.query(CharacterProfile).filter(
            CharacterProfile.is_active == True,
            CharacterProfile.is_default == True,
        ).first()
        if not character:
            character = db.query(CharacterProfile).filter(
                CharacterProfile.is_active == True
            ).first()

        theme = db.query(VideoThemeSetting).filter(
            VideoThemeSetting.is_active == True,
            VideoThemeSetting.is_default == True,
        ).first()
        if not theme:
            theme = db.query(VideoThemeSetting).filter(
                VideoThemeSetting.is_active == True
            ).first()

        # 分析レポート取得
        analysis = None
        if analysis_report_id:
            analysis = db.query(AIAnalysisReport).filter(
                AIAnalysisReport.id == analysis_report_id
            ).first()

        character_dict = {}
        if character:
            character_dict = {
                "name": character.name,
                "age_setting": character.age_setting,
                "personality": character.personality,
                "tone": character.tone,
                "first_person": character.first_person,
                "viewer_address": character.viewer_address,
                "speech_samples": character.speech_samples,
                "ng_expressions": character.ng_expressions,
            }

        theme_dict = {}
        if theme:
            theme_dict = {
                "main_channel_theme": theme.main_channel_theme,
                "target_audience": theme.target_audience,
                "purposes": theme.purposes,
                "title_policy": theme.title_policy,
                "thumbnail_policy": theme.thumbnail_policy,
            }

        analysis_dict = {}
        if analysis:
            analysis_dict = {
                "improvement_points": analysis.improvement_points,
                "next_theme_suggestions": analysis.next_theme_suggestions,
                "next_title_suggestions": analysis.next_title_suggestions,
                "next_script_policy": analysis.next_script_policy,
                "summary": analysis.summary,
            }

        plan_data = {
            "character": character_dict,
            "theme": theme_dict,
            "analysis": analysis_dict,
        }

        ai_service = get_ai_service()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(ai_service.generate_video_plan(plan_data))
        finally:
            loop.close()

        # 動画企画を保存
        video_plan = VideoPlan(
            youtube_account_id=analysis.youtube_account_id if analysis else None,
            analysis_report_id=analysis.id if analysis else None,
            character_id=character.id if character else None,
            theme_id=theme.id if theme else None,
            title=result.get("title", "未タイトル"),
            goal=result.get("goal"),
            target_audience=result.get("target_audience"),
            total_duration_seconds=result.get("total_duration_seconds", 600),
            structure=result.get("structure"),
            youtube_title_candidates=result.get("youtube_title_candidates"),
            youtube_description=result.get("youtube_description"),
            youtube_tags=result.get("youtube_tags"),
            cta=result.get("cta"),
            status="draft",
        )
        db.add(video_plan)
        db.commit()

        # 次のジョブをキック
        from app.jobs.video_jobs import generate_script
        generate_script.delay(video_plan_id=str(video_plan.id))

        return {"status": "success", "video_plan_id": str(video_plan.id)}

    except Exception as exc:
        raise self.retry(exc=exc)
    finally:
        db.close()
