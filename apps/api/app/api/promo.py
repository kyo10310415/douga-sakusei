"""
コンサル宣伝システム FastAPI ルーター
エンドポイント一覧:
  POST   /promo/generate                — AI投稿一括生成
  GET    /promo/posts                   — 投稿一覧（フィルタ付き）
  GET    /promo/posts/{post_id}         — 投稿詳細
  PUT    /promo/posts/{post_id}         — 投稿編集
  DELETE /promo/posts/{post_id}         — 投稿削除
  POST   /promo/posts/{post_id}/approve — 承認
  POST   /promo/posts/{post_id}/reject  — 差し戻し
  POST   /promo/posts/{post_id}/publish — X自動投稿
  POST   /promo/posts/{post_id}/ng-check — NG表現チェック
  GET    /promo/posts/{post_id}/assets  — 素材一覧
  POST   /promo/posts/{post_id}/assets/generate — 素材生成（画像プロンプト/動画台本）
  POST   /promo/analytics/{post_id}     — 分析数値保存 & AI改善提案
  GET    /promo/analytics/{post_id}     — 分析数値取得
  GET    /promo/templates               — プロンプトテンプレート一覧
  GET    /promo/dashboard               — 宣伝ダッシュボードサマリー
"""
import logging
from typing import Optional, List
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.user import User
from app.models.promo import (
    ContentProject, Post, CreativeAsset,
    PostAnalytics, PromoAIGeneration, PromptTemplate,
)
from app.services import promo_service
from app.services.publishers.x_publisher import XPublisher
from app.services.publishers.manual_export import ManualExportPublisher

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/promo", tags=["promo"])


# ──────────────────────────────────────────────
# Pydantic スキーマ
# ──────────────────────────────────────────────

class GenerateRequest(BaseModel):
    theme: str
    platforms: List[str] = ["x"]
    target_segment: str = "beginner"
    goal: str = "awareness"
    tone: str = "gentle"
    cta: str = ""
    count: int = 1
    weekly_metrics_id: Optional[str] = None  # YouTube分析データ連携


class PostUpdateRequest(BaseModel):
    title: Optional[str] = None
    body: Optional[str] = None
    caption: Optional[str] = None
    hashtags: Optional[List[str]] = None
    cta: Optional[str] = None
    memo: Optional[str] = None
    scheduled_at: Optional[datetime] = None


class RejectRequest(BaseModel):
    reason: str = ""


class AnalyticsUpsertRequest(BaseModel):
    impressions: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    shares: Optional[int] = None
    saves: Optional[int] = None
    profile_clicks: Optional[int] = None
    url_clicks: Optional[int] = None
    leads: Optional[int] = None
    conversions: Optional[int] = None
    memo: Optional[str] = None
    run_ai_analysis: bool = True


class AssetGenerateRequest(BaseModel):
    asset_type: str  # image_prompt / video_script
    duration: Optional[str] = "30s"  # video_script のみ


# ──────────────────────────────────────────────
# ヘルパー
# ──────────────────────────────────────────────

def _post_to_dict(post: Post) -> dict:
    return {
        "id": str(post.id),
        "user_id": str(post.user_id),
        "project_id": str(post.project_id) if post.project_id else None,
        "weekly_metrics_id": str(post.weekly_metrics_id) if post.weekly_metrics_id else None,
        "platform": post.platform,
        "title": post.title,
        "body": post.body,
        "caption": post.caption,
        "hashtags": post.hashtags or [],
        "cta": post.cta,
        "target_segment": post.target_segment,
        "goal": post.goal,
        "tone": post.tone,
        "status": post.status,
        "scheduled_at": post.scheduled_at.isoformat() if post.scheduled_at else None,
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "external_post_id": post.external_post_id,
        "external_post_url": post.external_post_url,
        "memo": post.memo,
        "ng_check_passed": post.ng_check_passed,
        "ng_check_details": post.ng_check_details,
        "created_at": post.created_at.isoformat() if post.created_at else None,
        "updated_at": post.updated_at.isoformat() if post.updated_at else None,
    }


def _asset_to_dict(a: CreativeAsset) -> dict:
    return {
        "id": str(a.id),
        "post_id": str(a.post_id),
        "asset_type": a.asset_type,
        "prompt": a.prompt,
        "content": a.content,
        "file_url": a.file_url,
        "metadata": a.metadata,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


def _get_post_or_404(post_id: str, user_id, db: Session) -> Post:
    post = db.query(Post).filter(Post.id == post_id, Post.user_id == user_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="投稿が見つかりません")
    return post


# ──────────────────────────────────────────────
# エンドポイント
# ──────────────────────────────────────────────

@router.post("/generate")
async def generate_posts(
    req: GenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    AI投稿一括生成
    指定テーマ × 媒体リストで投稿を生成しDBに保存する
    """
    # YouTube 分析データ取得（任意連携）
    youtube_data = None
    if req.weekly_metrics_id:
        try:
            from app.models.youtube import WeeklyMetrics
            wm = db.query(WeeklyMetrics).filter(
                WeeklyMetrics.id == req.weekly_metrics_id,
                WeeklyMetrics.user_id == current_user.id,
            ).first()
            if wm:
                youtube_data = {
                    "week_start": str(wm.week_start) if hasattr(wm, "week_start") else None,
                    "total_views": getattr(wm, "total_views", None),
                    "total_likes": getattr(wm, "total_likes", None),
                    "subscriber_gained": getattr(wm, "subscriber_gained", None),
                    "top_video_title": getattr(wm, "top_video_title", None),
                }
        except Exception as e:
            logger.warning("weekly_metrics取得エラー（スキップ）: %s", e)

    # AI生成
    generated = await promo_service.generate_posts_for_platforms(
        theme=req.theme,
        platforms=req.platforms,
        target_segment=req.target_segment,
        goal=req.goal,
        tone=req.tone,
        cta=req.cta,
        count=req.count,
        youtube_data=youtube_data,
    )

    saved_posts = []
    for item in generated:
        # NG チェック
        ng_result = await promo_service.check_ng_expressions(item.get("body", ""))

        post = Post(
            user_id=current_user.id,
            weekly_metrics_id=req.weekly_metrics_id or None,
            platform=item["platform"],
            title=item.get("title"),
            body=item.get("body"),
            caption=item.get("caption"),
            hashtags=item.get("hashtags", []),
            cta=item.get("cta") or req.cta,
            target_segment=req.target_segment,
            goal=req.goal,
            tone=req.tone,
            status="pending_review",
            ng_check_passed=ng_result["passed"],
            ng_check_details=ng_result,
        )
        db.add(post)
        db.flush()  # IDを確定させてから AI生成履歴を保存

        # AI生成履歴保存
        gen_log = PromoAIGeneration(
            post_id=post.id,
            user_id=current_user.id,
            generation_type="post",
            input_prompt=req.theme,
            output_text=item.get("body", ""),
            model=item.get("model", "mock"),
        )
        db.add(gen_log)

        saved_posts.append(post)

    db.commit()
    for p in saved_posts:
        db.refresh(p)

    return {
        "generated": len(saved_posts),
        "posts": [_post_to_dict(p) for p in saved_posts],
    }


@router.get("/posts")
async def list_posts(
    status: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿一覧（ステータス・媒体フィルタ対応）"""
    q = db.query(Post).filter(Post.user_id == current_user.id)
    if status:
        q = q.filter(Post.status == status)
    if platform:
        q = q.filter(Post.platform == platform)
    total = q.count()
    posts = q.order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "posts": [_post_to_dict(p) for p in posts],
    }


@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿詳細"""
    post = _get_post_or_404(post_id, current_user.id, db)
    return _post_to_dict(post)


@router.put("/posts/{post_id}")
async def update_post(
    post_id: str,
    req: PostUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿編集（draft / pending_review のみ編集可）"""
    post = _get_post_or_404(post_id, current_user.id, db)
    if post.status in ("published",):
        raise HTTPException(status_code=400, detail="投稿済みの投稿は編集できません")

    update_data = req.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(post, key, value)

    # 編集後は再度 pending_review に戻す
    if post.status == "approved":
        post.status = "pending_review"

    # NG チェック再実行
    if req.body:
        ng_result = await promo_service.check_ng_expressions(req.body)
        post.ng_check_passed = ng_result["passed"]
        post.ng_check_details = ng_result

    db.commit()
    db.refresh(post)
    return _post_to_dict(post)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿削除"""
    post = _get_post_or_404(post_id, current_user.id, db)
    db.delete(post)
    db.commit()
    return {"message": "削除しました"}


@router.post("/posts/{post_id}/approve")
async def approve_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿承認（pending_review → approved）"""
    post = _get_post_or_404(post_id, current_user.id, db)
    if post.status != "pending_review":
        raise HTTPException(
            status_code=400,
            detail=f"承認できる状態ではありません（現状: {post.status}）",
        )
    if post.ng_check_passed is False:
        raise HTTPException(
            status_code=400,
            detail="NG表現が含まれています。修正してから承認してください。",
        )
    post.status = "approved"
    db.commit()
    db.refresh(post)
    return _post_to_dict(post)


@router.post("/posts/{post_id}/reject")
async def reject_post(
    post_id: str,
    req: RejectRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """投稿差し戻し（any → draft）"""
    post = _get_post_or_404(post_id, current_user.id, db)
    post.status = "draft"
    if req.reason:
        post.memo = (post.memo or "") + f"\n[差し戻し理由] {req.reason}"
    db.commit()
    db.refresh(post)
    return _post_to_dict(post)


@router.post("/posts/{post_id}/publish")
async def publish_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    投稿を媒体に送信
    - X: XPublisher（tweepy）で自動投稿
    - その他: ManualExportPublisher（エクスポートデータを返す）
    """
    post = _get_post_or_404(post_id, current_user.id, db)
    if post.status not in ("approved", "scheduled"):
        raise HTTPException(
            status_code=400,
            detail=f"承認済みの投稿のみ投稿できます（現状: {post.status}）",
        )

    body = post.body or post.caption or ""
    hashtags = post.hashtags if isinstance(post.hashtags, list) else []
    cta = post.cta or ""

    # 媒体に応じた Publisher を選択
    if post.platform == "x":
        publisher = XPublisher()
    else:
        publisher = ManualExportPublisher(post.platform)

    result = await publisher.publish(body, hashtags=hashtags, cta=cta)

    if result.success:
        post.status = "published"
        post.published_at = datetime.now(timezone.utc)
        post.external_post_id = result.external_post_id
        post.external_post_url = result.external_post_url
        db.commit()
        db.refresh(post)

    return {
        "success": result.success,
        "platform": result.platform,
        "external_post_id": result.external_post_id,
        "external_post_url": result.external_post_url,
        "error_message": result.error_message,
        "raw_response": result.raw_response,
        "post": _post_to_dict(post),
    }


@router.post("/posts/{post_id}/ng-check")
async def ng_check(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """NG表現チェック（再実行）"""
    post = _get_post_or_404(post_id, current_user.id, db)
    text = post.body or post.caption or ""
    ng_result = await promo_service.check_ng_expressions(text)
    post.ng_check_passed = ng_result["passed"]
    post.ng_check_details = ng_result
    db.commit()
    db.refresh(post)
    return {
        "post_id": str(post.id),
        "ng_check": ng_result,
        "status": post.status,
    }


# ── 素材 ────────────────────────────────────────

@router.get("/posts/{post_id}/assets")
async def list_assets(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """素材一覧取得"""
    _get_post_or_404(post_id, current_user.id, db)
    assets = db.query(CreativeAsset).filter(CreativeAsset.post_id == post_id).all()
    return {"assets": [_asset_to_dict(a) for a in assets]}


@router.post("/posts/{post_id}/assets/generate")
async def generate_asset(
    post_id: str,
    req: AssetGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    素材生成
    asset_type: image_prompt → 画像生成プロンプトを生成
    asset_type: video_script → 動画台本（duration: 15s/30s/60s）を生成
    """
    post = _get_post_or_404(post_id, current_user.id, db)
    body_text = post.body or post.caption or ""
    context = {
        "platform": post.platform,
        "goal": post.goal,
        "target_segment": post.target_segment,
        "tone": post.tone,
    }

    if req.asset_type == "image_prompt":
        result = await promo_service.generate_image_prompts(body_text, context=context)
        asset = CreativeAsset(
            post_id=post.id,
            asset_type="image_prompt",
            prompt=result.get("prompt"),
            content=result.get("negative_prompt"),
            metadata=result,
        )
    elif req.asset_type == "video_script":
        result = await promo_service.generate_video_scripts(
            body_text, duration=req.duration or "30s", context=context
        )
        asset = CreativeAsset(
            post_id=post.id,
            asset_type="video_script",
            content=result.get("script"),
            metadata=result,
        )
    else:
        raise HTTPException(status_code=400, detail=f"未対応の asset_type: {req.asset_type}")

    db.add(asset)

    # 生成履歴
    gen_log = PromoAIGeneration(
        post_id=post.id,
        user_id=current_user.id,
        generation_type=req.asset_type,
        input_prompt=body_text[:200],
        output_text=str(result),
        model=result.get("model", "mock"),
    )
    db.add(gen_log)
    db.commit()
    db.refresh(asset)
    return _asset_to_dict(asset)


# ── 分析 ────────────────────────────────────────

@router.post("/analytics/{post_id}")
async def upsert_analytics(
    post_id: str,
    req: AnalyticsUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分析数値の登録・更新 + AI改善提案（オプション）"""
    post = _get_post_or_404(post_id, current_user.id, db)

    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        analytics = PostAnalytics(post_id=post.id)
        db.add(analytics)

    for field_name in [
        "impressions", "likes", "comments", "shares", "saves",
        "profile_clicks", "url_clicks", "leads", "conversions", "memo",
    ]:
        val = getattr(req, field_name, None)
        if val is not None:
            setattr(analytics, field_name, val)

    # AI 改善提案
    if req.run_ai_analysis:
        metrics_dict = {
            "impressions": analytics.impressions,
            "likes": analytics.likes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "url_clicks": analytics.url_clicks,
            "leads": analytics.leads,
        }
        post_data = {
            "platform": post.platform,
            "goal": post.goal,
            "target_segment": post.target_segment,
            "body": post.body or "",
        }
        try:
            analysis_result = await promo_service.analyze_post_performance(
                post_data=post_data, metrics=metrics_dict
            )
            analytics.ai_analysis = analysis_result.get("analysis", "")
        except Exception as e:
            logger.warning("AI改善提案生成エラー: %s", e)

    db.commit()
    db.refresh(analytics)

    return {
        "post_id": post_id,
        "analytics": {
            "id": str(analytics.id),
            "impressions": analytics.impressions,
            "likes": analytics.likes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "saves": analytics.saves,
            "profile_clicks": analytics.profile_clicks,
            "url_clicks": analytics.url_clicks,
            "leads": analytics.leads,
            "conversions": analytics.conversions,
            "memo": analytics.memo,
            "ai_analysis": analytics.ai_analysis,
        },
    }


@router.get("/analytics/{post_id}")
async def get_analytics(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """分析数値取得"""
    _get_post_or_404(post_id, current_user.id, db)
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_id).first()
    if not analytics:
        return {"post_id": post_id, "analytics": None}
    return {
        "post_id": post_id,
        "analytics": {
            "id": str(analytics.id),
            "impressions": analytics.impressions,
            "likes": analytics.likes,
            "comments": analytics.comments,
            "shares": analytics.shares,
            "saves": analytics.saves,
            "profile_clicks": analytics.profile_clicks,
            "url_clicks": analytics.url_clicks,
            "leads": analytics.leads,
            "conversions": analytics.conversions,
            "memo": analytics.memo,
            "ai_analysis": analytics.ai_analysis,
        },
    }


# ── テンプレート ────────────────────────────────

@router.get("/templates")
async def list_templates(
    type: Optional[str] = Query(None),
    platform: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """プロンプトテンプレート一覧"""
    q = db.query(PromptTemplate).filter(PromptTemplate.is_active == True)
    if type:
        q = q.filter(PromptTemplate.type == type)
    if platform:
        q = q.filter(
            (PromptTemplate.platform == platform) | (PromptTemplate.platform.is_(None))
        )
    templates = q.order_by(PromptTemplate.sort_order, PromptTemplate.name).all()
    return {
        "templates": [
            {
                "id": str(t.id),
                "type": t.type,
                "name": t.name,
                "template_text": t.template_text,
                "platform": t.platform,
            }
            for t in templates
        ]
    }


# ── ダッシュボードサマリー ──────────────────────

@router.get("/dashboard")
async def promo_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """宣伝ダッシュボードのサマリー情報"""
    user_id = current_user.id

    total_posts = db.query(Post).filter(Post.user_id == user_id).count()
    status_counts: dict = {}
    for status in ["draft", "pending_review", "approved", "scheduled", "published", "rejected"]:
        status_counts[status] = db.query(Post).filter(
            Post.user_id == user_id, Post.status == status
        ).count()

    platform_counts: dict = {}
    for platform in ["x", "instagram", "tiktok", "youtube_shorts"]:
        platform_counts[platform] = db.query(Post).filter(
            Post.user_id == user_id, Post.platform == platform
        ).count()

    # 直近5件の投稿
    recent_posts = (
        db.query(Post)
        .filter(Post.user_id == user_id)
        .order_by(Post.created_at.desc())
        .limit(5)
        .all()
    )

    # 分析集計（投稿済みのみ）
    total_leads = 0
    total_conversions = 0
    published_posts = (
        db.query(Post)
        .filter(Post.user_id == user_id, Post.status == "published")
        .all()
    )
    for pp in published_posts:
        if pp.analytics:
            total_leads += pp.analytics.leads or 0
            total_conversions += pp.analytics.conversions or 0

    return {
        "total_posts": total_posts,
        "status_counts": status_counts,
        "platform_counts": platform_counts,
        "total_leads": total_leads,
        "total_conversions": total_conversions,
        "recent_posts": [_post_to_dict(p) for p in recent_posts],
    }
