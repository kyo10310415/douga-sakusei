"""
宣伝コンテンツ AI 生成サービス
- 媒体別投稿生成（X / Instagram / TikTok / YouTube Shorts）
- YouTube 分析データとの連携
- OpenAI GPT-4o（OPENAI_API_KEY 未設定時はモック応答）
- 禁止表現チェック
"""
import json
import re
from typing import Optional, Dict, Any, List
from app.core.config import settings


# ── 禁止表現 ──────────────────────────────────────────────
NG_EXPRESSIONS = [
    "必ず収益化できます", "絶対に伸びます", "登録者が確実に増えます",
    "誰でも稼げます", "楽して稼げます", "放置で収益化", "成功保証",
]

# 代替表現マッピング
NG_REPLACEMENTS = {
    "必ず収益化できます": "収益化を目指すための活動設計を支援します",
    "絶対に伸びます": "伸びる可能性を高めるための改善を伴走します",
    "誰でも稼げます": "活動の方向性と導線を整理します",
    "楽して稼げます": "AIを活用して作業負担を減らします",
    "放置で収益化": "継続しやすい運用体制を作ります",
}

# ── プラットフォーム表示名 ────────────────────────────────
PLATFORM_LABELS = {
    "x": "X（Twitter）",
    "instagram": "Instagram",
    "tiktok": "TikTok",
    "youtube_shorts": "YouTube Shorts",
}

# ── ターゲット層ラベル ────────────────────────────────────
SEGMENT_LABELS = {
    "beginner": "これからVTuberを始める人",
    "0_1000": "登録者0〜1000人",
    "1000_10000": "登録者1000〜1万人",
}

# ── 投稿目的ラベル ────────────────────────────────────────
GOAL_LABELS = {
    "awareness": "認知拡大",
    "consult": "無料相談誘導",
    "line": "LINE登録誘導",
    "document": "資料請求誘導",
    "achievement": "実績紹介",
    "knowhow": "ノウハウ提供",
}

# ── トーンラベル ──────────────────────────────────────────
TONE_LABELS = {
    "gentle": "優しい・寄り添う",
    "professional": "専門的・信頼感",
    "provocative": "強めの問題提起",
    "beginner": "初心者向け・やさしい解説",
    "business": "経営者目線・ビジネス視点",
}

# ── CTAラベル ─────────────────────────────────────────────
CTA_LABELS = {
    "free_diagnosis": "無料診断",
    "free_consult": "無料相談",
    "line": "公式LINE",
    "document": "資料請求",
    "dm": "DM相談",
}


def check_ng_expressions(text: str) -> Dict[str, Any]:
    """禁止表現チェック"""
    found = []
    for ng in NG_EXPRESSIONS:
        if ng in text:
            found.append({
                "ng": ng,
                "replacement": NG_REPLACEMENTS.get(ng, "別の表現に変えてください"),
            })
    return {
        "passed": len(found) == 0,
        "violations": found,
    }


def _build_system_prompt() -> str:
    return """あなたはVTuberコンサルサービス「VTuber Studio」の宣伝担当ライターです。
VTuberの活動支援・収益化支援コンサルサービスの宣伝投稿を作成します。

重要ルール：
- 「必ず収益化できます」「絶対に伸びます」などの断言・保証表現は絶対に使わない
- 代わりに「収益化を目指すための活動設計を支援します」「伸びる可能性を高める改善を伴走します」を使う
- 誠実で実用的な内容にする
- ターゲット層の悩みや課題に共感する文章にする
- CTAは自然な形で入れる（押しつけがましくしない）
- 出力は必ず指定されたJSON形式で返す
"""


def _build_youtube_context(youtube_data: Optional[Dict]) -> str:
    if not youtube_data:
        return ""
    lines = ["\n【今週のYouTubeチャンネル分析データ（参考にして内容に活かす）】"]
    if youtube_data.get("total_views"):
        lines.append(f"- 総再生数: {youtube_data['total_views']:,}")
    if youtube_data.get("views_change_rate"):
        rate = youtube_data["views_change_rate"]
        lines.append(f"- 前週比: {'+' if rate >= 0 else ''}{rate:.1f}%")
    if youtube_data.get("summary"):
        lines.append(f"- AI分析サマリー: {youtube_data['summary']}")
    if youtube_data.get("trending_topics"):
        lines.append(f"- 伸びたテーマ: {youtube_data['trending_topics']}")
    return "\n".join(lines)


async def generate_posts_for_platforms(
    theme: str,
    platforms: List[str],
    target_segment: str,
    goal: str,
    tone: str,
    cta: str,
    count: int = 1,
    youtube_data: Optional[Dict] = None,
) -> List[Dict[str, Any]]:
    """
    指定プラットフォーム × count 件の投稿を一括生成
    OpenAI未設定時はモック応答を返す
    """
    if not settings.OPENAI_API_KEY:
        return _mock_generate(theme, platforms, target_segment, goal, tone, cta, count)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    results = []
    yt_ctx = _build_youtube_context(youtube_data)

    for platform in platforms:
        for i in range(count):
            prompt = _build_post_prompt(
                theme, platform, target_segment, goal, tone, cta, i + 1, yt_ctx
            )
            try:
                resp = await client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": _build_system_prompt()},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.8,
                    response_format={"type": "json_object"},
                )
                raw = resp.choices[0].message.content
                data = json.loads(raw)
                data["platform"] = platform
                data["target_segment"] = target_segment
                data["goal"] = goal
                data["tone"] = tone
                data["cta"] = cta
                data["prompt_tokens"] = resp.usage.prompt_tokens
                data["completion_tokens"] = resp.usage.completion_tokens
                data["model"] = resp.model
                # NGチェック
                full_text = " ".join([
                    data.get("body", ""), data.get("caption", ""),
                    str(data.get("hashtags", [])),
                ])
                ng = check_ng_expressions(full_text)
                data["ng_check_passed"] = ng["passed"]
                data["ng_check_details"] = ng["violations"]
                results.append(data)
            except Exception as e:
                # 生成失敗時はエラーポストを追加
                results.append({
                    "platform": platform,
                    "title": f"[生成エラー] {theme}",
                    "body": f"生成に失敗しました: {str(e)[:100]}",
                    "error": True,
                })
    return results


def _build_post_prompt(
    theme: str,
    platform: str,
    target_segment: str,
    goal: str,
    tone: str,
    cta: str,
    idx: int,
    yt_ctx: str,
) -> str:
    segment_label = SEGMENT_LABELS.get(target_segment, target_segment)
    goal_label = GOAL_LABELS.get(goal, goal)
    tone_label = TONE_LABELS.get(tone, tone)
    cta_label = CTA_LABELS.get(cta, cta)
    platform_label = PLATFORM_LABELS.get(platform, platform)

    base = f"""
投稿テーマ: {theme}
ターゲット層: {segment_label}
投稿目的: {goal_label}
トーン: {tone_label}
CTA: {cta_label}
媒体: {platform_label}
バリエーション番号: {idx}
{yt_ctx}
"""
    if platform == "x":
        return base + """
X（旧Twitter）向けの投稿を1件作成してください。
JSON形式で以下のキーを返してください：
{
  "title": "投稿のタイトル（管理用・投稿には使わない）",
  "body": "140〜280字の投稿本文（強い冒頭から始める）",
  "hashtags": ["ハッシュタグ1", "ハッシュタグ2", "ハッシュタグ3"],
  "cta_text": "CTAの一言（本文の最後に自然に入れる形で）",
  "hook": "冒頭の強い一文（本文の最初の一文）"
}
"""
    elif platform == "instagram":
        return base + """
Instagram カルーセル投稿向けの構成を作成してください。
JSON形式で以下のキーを返してください：
{
  "title": "投稿タイトル（管理用）",
  "body": "カルーセル全体の構成（各スライドの内容を箇条書きで）",
  "caption": "Instagramキャプション（300〜500字）",
  "hashtags": ["ハッシュタグ1",...（10〜20個）],
  "slides": [
    {"slide": 1, "title": "1枚目タイトル（強いコピー）", "body": ""},
    {"slide": 2, "title": "", "body": "2枚目の内容"},
    ...
  ],
  "cta_text": "最終スライドのCTA文"
}
"""
    elif platform == "tiktok":
        return base + """
TikTok動画台本を作成してください。15〜60秒の縦動画想定。
JSON形式で以下のキーを返してください：
{
  "title": "動画タイトル（管理用）",
  "body": "台本全体（読み上げテキスト形式）",
  "hook": "冒頭1秒のフック（超短く・インパクト重視）",
  "narration": "ナレーション全文（セクション別に改行）",
  "telop": "テロップ文（画面に表示するテキスト）",
  "cover_text": "表紙テキスト案",
  "cta_text": "最後のCTA",
  "duration_estimate": "推定秒数（数値）"
}
"""
    else:  # youtube_shorts
        return base + """
YouTube Shorts台本を作成してください。30〜60秒の教育系ショート動画想定。
JSON形式で以下のキーを返してください：
{
  "title": "動画タイトル案（60字以内）",
  "body": "台本全体",
  "hook": "冒頭フック（最初の5秒）",
  "problem": "問題提起（視聴者の悩み）",
  "solution": "解決策の提示",
  "description": "概要欄テキスト（200字程度）",
  "cta_text": "最後のCTA",
  "hashtags": ["ハッシュタグ1", "ハッシュタグ2", "ハッシュタグ3"],
  "duration_estimate": "推定秒数（数値）"
}
"""


def _mock_generate(
    theme: str,
    platforms: List[str],
    target_segment: str,
    goal: str,
    tone: str,
    cta: str,
    count: int,
) -> List[Dict[str, Any]]:
    """OpenAI未設定時のモック応答"""
    segment_label = SEGMENT_LABELS.get(target_segment, target_segment)
    cta_label = CTA_LABELS.get(cta, cta)
    results = []

    for platform in platforms:
        for i in range(count):
            if platform == "x":
                results.append({
                    "platform": "x",
                    "title": f"【X投稿】{theme}（案{i+1}）",
                    "body": (
                        f"【{target_segment}向け】\n"
                        f"{theme}について、多くのVTuberが見落としているポイントがあります。\n\n"
                        f"活動の方向性と導線を整理するだけで、継続しやすい運用体制が作れます。\n\n"
                        f"✅ {cta_label}はプロフィールのリンクから\n"
                        f"#VTuber #VTuber活動 #VTuber支援"
                    ),
                    "hashtags": ["VTuber", "VTuber活動", "VTuber支援"],
                    "hook": f"{theme}について、多くのVTuberが見落としているポイントがあります。",
                    "cta_text": f"{cta_label}はプロフィールのリンクから",
                    "target_segment": target_segment,
                    "goal": goal,
                    "tone": tone,
                    "cta": cta,
                    "ng_check_passed": True,
                    "ng_check_details": [],
                    "model": "mock",
                })
            elif platform == "instagram":
                results.append({
                    "platform": "instagram",
                    "title": f"【Instagram】{theme}（案{i+1}）",
                    "body": f"カルーセル構成案：{theme}",
                    "caption": (
                        f"{theme}について解説します📱\n\n"
                        f"{segment_label}のVTuberさんに向けた内容です。\n"
                        f"AIを活用して作業負担を減らし、継続しやすい運用体制を一緒に作りましょう。\n\n"
                        f"👇 {cta_label}はプロフィールリンクから"
                    ),
                    "hashtags": ["VTuber", "VTuber活動", "VTuberデビュー",
                                 "VTuber支援", "VTuber収益化", "VTuberコンサル",
                                 "配信者", "YouTuber", "ゲーム実況", "AI活用"],
                    "slides": [
                        {"slide": 1, "title": f"知らないと損！{theme}", "body": ""},
                        {"slide": 2, "title": "よくある失敗パターン", "body": "・方向性が定まっていない\n・導線が整備されていない"},
                        {"slide": 3, "title": "改善のポイント", "body": "・活動設計を見直す\n・AIで作業を効率化"},
                        {"slide": 4, "title": f"まずは{cta_label}から", "body": "無料でご相談できます"},
                    ],
                    "cta_text": f"{cta_label}はプロフィールリンクから",
                    "target_segment": target_segment,
                    "goal": goal,
                    "tone": tone,
                    "cta": cta,
                    "ng_check_passed": True,
                    "ng_check_details": [],
                    "model": "mock",
                })
            elif platform == "tiktok":
                results.append({
                    "platform": "tiktok",
                    "title": f"【TikTok台本】{theme}（案{i+1}）",
                    "body": f"台本：{theme}についての解説動画",
                    "hook": f"{theme}って知ってる？",
                    "narration": (
                        f"【冒頭】{theme}って知ってますか？\n"
                        f"【問題提起】多くのVTuberがここで躓いています。\n"
                        f"【解決策】活動の方向性を整理するだけで変わります。\n"
                        f"【CTA】詳しくは{cta_label}から相談できます！"
                    ),
                    "telop": f"{theme} / 知らないと損！ / {cta_label}はプロフから",
                    "cover_text": f"VTuberの{theme}",
                    "cta_text": f"詳しくは{cta_label}から！",
                    "duration_estimate": 30,
                    "target_segment": target_segment,
                    "goal": goal,
                    "tone": tone,
                    "cta": cta,
                    "ng_check_passed": True,
                    "ng_check_details": [],
                    "model": "mock",
                })
            else:  # youtube_shorts
                results.append({
                    "platform": "youtube_shorts",
                    "title": f"【知らないと損】{theme} #Shorts",
                    "body": f"台本：{theme}についてのYouTube Shorts",
                    "hook": f"VTuberで{theme}について知らないと損します",
                    "problem": f"{segment_label}が直面する{theme}の問題",
                    "solution": "活動の方向性と導線を整理することで改善できます",
                    "description": (
                        f"{theme}について解説しました。\n"
                        f"{segment_label}向けのVTuber活動支援をしています。\n"
                        f"{cta_label}はプロフィールリンクから👇"
                    ),
                    "cta_text": f"{cta_label}はプロフィールリンクから",
                    "hashtags": ["VTuber", "Shorts", "VTuber活動"],
                    "duration_estimate": 45,
                    "target_segment": target_segment,
                    "goal": goal,
                    "tone": tone,
                    "cta": cta,
                    "ng_check_passed": True,
                    "ng_check_details": [],
                    "model": "mock",
                })
    return results


async def generate_image_prompts(post_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """画像プロンプト生成"""
    platform = post_data.get("platform", "x")
    theme = post_data.get("title", "")
    body = post_data.get("body", "")

    if not settings.OPENAI_API_KEY:
        return _mock_image_prompts(platform, theme)

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    prompt_types = {
        "x": ["x_image"],
        "instagram": ["instagram_carousel_cover", "instagram_carousel_body"],
        "tiktok": ["tiktok_cover"],
        "youtube_shorts": ["youtube_shorts_thumbnail"],
    }
    types = prompt_types.get(platform, ["x_image"])

    results = []
    for img_type in types:
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "user",
                    "content": (
                        f"VTuberコンサルサービスの宣伝画像プロンプトを作成してください。\n"
                        f"テーマ: {theme}\n内容: {body[:200]}\n"
                        f"画像タイプ: {img_type}\n"
                        f"Stable Diffusion / DALL-E向けの英語プロンプトをJSON形式で返してください:\n"
                        f"{{\"prompt\": \"英語プロンプト\", \"negative_prompt\": \"ネガティブプロンプト\"}}"
                    )
                }],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            results.append({"type": img_type, **data})
        except Exception:
            results.append(_mock_image_prompts(platform, theme, img_type)[0])
    return results


def _mock_image_prompts(platform: str, theme: str, img_type: str = None) -> List[Dict]:
    base = {
        "prompt": (
            f"professional VTuber consultant advertisement, anime style character, "
            f"topic: {theme}, clean design, modern Japanese UI, pink and purple gradient, "
            f"high quality, 4k"
        ),
        "negative_prompt": "low quality, blurry, text errors, nsfw",
    }
    if img_type:
        return [{"type": img_type, **base}]
    types = {"x": "x_image", "instagram": "instagram_carousel_cover",
             "tiktok": "tiktok_cover", "youtube_shorts": "youtube_shorts_thumbnail"}
    return [{"type": types.get(platform, "x_image"), **base}]


async def generate_video_scripts(
    post_data: Dict[str, Any],
    durations: List[int] = None,
) -> List[Dict[str, Any]]:
    """動画台本生成（15秒/30秒/60秒）"""
    if durations is None:
        durations = [15, 30, 60]

    theme = post_data.get("title", "")
    platform = post_data.get("platform", "tiktok")

    if not settings.OPENAI_API_KEY:
        return [_mock_video_script(theme, d, platform) for d in durations]

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    results = []
    for duration in durations:
        try:
            resp = await client.chat.completions.create(
                model="gpt-4o",
                messages=[{
                    "role": "system",
                    "content": _build_system_prompt(),
                }, {
                    "role": "user",
                    "content": (
                        f"VTuberコンサルの宣伝動画台本（{duration}秒）を作成してください。\n"
                        f"テーマ: {theme}\nプラットフォーム: {platform}\n\n"
                        f"JSON形式で返してください:\n"
                        f"{{\"duration\": {duration}, \"hook\": \"冒頭フック\", "
                        f"\"narration\": \"ナレーション全文\", \"telop\": \"テロップ\", "
                        f"\"cta\": \"CTA\", \"bgm_image\": \"BGMイメージ\"}}"
                    )
                }],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            results.append(data)
        except Exception:
            results.append(_mock_video_script(theme, duration, platform))
    return results


def _mock_video_script(theme: str, duration: int, platform: str) -> Dict:
    return {
        "duration": duration,
        "hook": f"VTuberで{theme}を知らないと損！",
        "narration": (
            f"【{duration}秒台本】\n"
            f"冒頭（{min(5, duration//6)}秒）: {theme}について知っていますか？\n"
            f"本編（{duration - min(10, duration//3)}秒）: "
            f"活動の方向性と導線を整理するだけで、継続しやすい運用体制が作れます。\n"
            f"CTA（5秒）: 詳しくは無料相談から！"
        ),
        "telop": f"{theme} / プロフリンクから無料相談",
        "cta": "無料相談はプロフィールリンクから",
        "bgm_image": "明るくポップ・テンポ良め・ポジティブな雰囲気",
    }


async def analyze_post_performance(posts_data: List[Dict]) -> Dict[str, Any]:
    """投稿パフォーマンス分析（AI改善提案）"""
    if not settings.OPENAI_API_KEY:
        return {
            "good_patterns": "CTRが高かった投稿：強い問題提起 + 具体的な数字を使ったタイトル",
            "bad_patterns": "反応が薄かった投稿：抽象的な表現・CTAが曖昧",
            "improvements": [
                "冒頭に数字を入れる（「3つの理由」「1000人までにやること」）",
                "CTAをより具体的に（「プロフのリンクから今すぐ相談」）",
                "ハッシュタグをニッチなものに絞る",
            ],
            "platform_tips": {
                "x": "朝7時〜9時・夜21時〜23時の投稿が反応が良い",
                "instagram": "カルーセル投稿は保存率が高い",
                "tiktok": "最初の1秒のフックが最重要",
                "youtube_shorts": "タイトルに「知らないと損」系ワードが有効",
            },
            "next_suggestions": [
                "登録者1000人の壁についての投稿",
                "AI活用で時短できる具体的な作業リスト",
                "VTuberの失敗事例から学ぶシリーズ",
            ],
        }

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    posts_summary = json.dumps(posts_data[:20], ensure_ascii=False, indent=2)
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "system",
            "content": "あなたはSNSマーケティングの専門家です。",
        }, {
            "role": "user",
            "content": (
                f"以下の投稿データを分析して改善提案をJSONで返してください：\n{posts_summary}\n\n"
                "JSON形式: {\"good_patterns\": str, \"bad_patterns\": str, "
                "\"improvements\": [str], \"platform_tips\": {platform: str}, "
                "\"next_suggestions\": [str]}"
            )
        }],
        temperature=0.7,
        response_format={"type": "json_object"},
    )
    return json.loads(resp.choices[0].message.content)
