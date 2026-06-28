"""
AI分析サービス - OpenAI APIまたはモックに差し替え可能な設計
"""
import json
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from app.core.config import settings


class BaseAIService(ABC):
    @abstractmethod
    async def analyze_weekly_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_video_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_script(self, data: Dict[str, Any]) -> Dict[str, Any]:
        pass


class MockAIService(BaseAIService):
    """開発・テスト用モックAIサービス"""

    async def analyze_weekly_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "trending_video_patterns": "サムネイルに数字を入れた動画のCTRが高い傾向。タイトルに「〇〇する方法」という形式が効果的。",
            "declining_video_patterns": "15分以上の動画は視聴維持率が低下。専門用語が多い動画はコメントが少ない。",
            "high_ctr_title_patterns": "「初心者でもわかる」「たった5分で」「最強の〇〇」などのフレーズが高CTR。",
            "high_retention_patterns": "冒頭15秒での問題提起が明確な動画は平均視聴率が高い。具体例を多用すると離脱が減る。",
            "drop_off_factors": "5分付近での情報の重複。BGMが大きすぎる場合に離脱が増加。",
            "improvement_points": "動画を8-10分に絞る。冒頭でベネフィットを明確に伝える。サムネイルに顔写真を入れる。",
            "next_theme_suggestions": [
                {"title": "初心者向けAIツール5選", "reason": "AI関連コンテンツの視聴数が増加中"},
                {"title": "時間節約テクニック集", "reason": "生産性系コンテンツのCTRが高い"},
                {"title": "失敗から学ぶ教訓集", "reason": "体験談系は視聴維持率が高い"},
            ],
            "next_title_suggestions": [
                "【保存版】初心者でもできるAIツール活用法5選",
                "これだけ知れば大丈夫！最新AIツール完全ガイド",
                "AI初心者が最初にやるべき5つのこと",
                "無料で使えるAIツール5選【2024年最新版】",
                "たった10分でわかるAI活用入門",
            ],
            "next_thumbnail_suggestions": [
                "顔アップ + 驚き表情 + 数字「5選」のテロップ",
                "ツールのスクリーンショット + 「無料」の大文字",
            ],
            "next_script_policy": "冒頭15秒で視聴者の悩みを提示し、解決できることを約束する。各ツールは具体例付きで30秒以内に説明。まとめで全体を振り返る。",
            "summary": "今週は全体的な再生数は前週比+12%と好調。特にショート動画のCTRが改善されています。次回は10分前後の動画でAIツール系コンテンツが推奨されます。",
        }

    async def generate_video_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        character = data.get("character", {})
        theme = data.get("theme", {})
        analysis = data.get("analysis", {})

        character_name = character.get("name", "AIちゃん")
        first_person = character.get("first_person", "わたし")

        return {
            "title": "初心者でもできるAIツール活用法5選【2024年最新版】",
            "goal": "AI初心者の視聴者に実用的なツールを紹介し、登録者増加とファン化を目指す",
            "target_audience": "20-35歳、IT初心者〜中級者、AI活用に興味がある会社員",
            "total_duration_seconds": 600,
            "structure": [
                {"section": "hook", "title": "冒頭フック", "seconds": 15,
                 "description": "「AIツール知らないと損！」という強いフックで興味を引く"},
                {"section": "problem", "title": "問題提起", "seconds": 60,
                 "description": "AI活用できていない現状の課題を共感を持って提示"},
                {"section": "main", "title": "本編：5つのAIツール紹介", "seconds": 420,
                 "description": "各ツールを具体例付きで紹介（1ツール約84秒）"},
                {"section": "example", "title": "具体的な活用例", "seconds": 60,
                 "description": "実際の業務での使い方を実演"},
                {"section": "summary", "title": "まとめ", "seconds": 30,
                 "description": "5つのツールを振り返り、使い始めるよう後押し"},
                {"section": "cta", "title": "CTA", "seconds": 15,
                 "description": "チャンネル登録と次の動画への誘導"},
            ],
            "youtube_title_candidates": [
                "【保存版】初心者でもできるAIツール活用法5選",
                "これだけ知れば大丈夫！最新AIツール完全ガイド",
                "AI初心者が最初にやるべき5つのこと",
                "無料で使えるAIツール5選【2024年最新版】",
                "たった10分でわかるAI活用入門",
            ],
            "youtube_description": f"""今回は初心者でも使えるAIツールを5つ紹介します！

📌 今回紹介するツール
1. ChatGPT - 文章作成・アイデア出し
2. Notion AI - メモ・ドキュメント管理
3. Canva AI - デザイン制作
4. Grammarly - 文章校正
5. Otter.ai - 議事録自動作成

✅ チャンネル登録はこちら：https://youtube.com/channel/xxx

#AI #人工知能 #仕事効率化 #初心者 #AIツール
""",
            "youtube_tags": ["AI", "人工知能", "AIツール", "仕事効率化", "初心者", "ChatGPT", "生産性"],
            "cta": f"この動画が参考になったらチャンネル登録お願いします！次回は「AIプロンプト入門」をお届けします！",
        }

    async def generate_script(self, data: Dict[str, Any]) -> Dict[str, Any]:
        character = data.get("character", {})
        plan = data.get("plan", {})

        name = character.get("name", "AIちゃん")
        first_person = character.get("first_person", "わたし")
        viewer_address = character.get("viewer_address", "みなさん")
        tone = character.get("tone", "明るく元気")

        sections = [
            {
                "section_type": "hook",
                "title": "冒頭フック",
                "duration_seconds": 15,
                "narration": f"ねえ{viewer_address}！AIツール、まだ使ってないの？それ、めちゃくちゃ損してるよ！今日は{first_person}が厳選した、初心者でも今日から使えるAIツール5選を紹介するね！最後まで見てくれると、仕事の効率が絶対変わるから！",
                "subtitle": "AIツール使ってないのは損！今日から変わる5選！",
                "direction": "驚き表情でカメラに近づく演出",
                "expression": "surprise",
            },
            {
                "section_type": "problem",
                "title": "問題提起",
                "duration_seconds": 60,
                "narration": f"{viewer_address}、こんな悩みない？「AIって難しそう」「どれ使えばいいかわからない」「使ってみたけど結局使いこなせなかった」…{first_person}も最初はそうだったんだよね。でも今は毎日AIを使って仕事時間を半分以下にできてるの！その秘密を今日は全部教えちゃうね！",
                "subtitle": "AI、難しそう？最初は私もそう思ってた！",
                "direction": "困り顔から笑顔への表情変化",
                "expression": "troubled",
            },
            {
                "section_type": "main",
                "title": "本編：AIツール5選",
                "duration_seconds": 420,
                "narration": f"まず1つ目はChatGPT！これはもう絶対使ってほしい基本ツール。文章作成からアイデア出しまでなんでもできるの。たとえば…（具体例説明）。2つ目はNotion AI！これはメモやドキュメント管理が格段に楽になるよ。（以下略）",
                "subtitle": "1. ChatGPT  2. Notion AI  3. Canva AI  4. Grammarly  5. Otter.ai",
                "direction": "ツールのスクリーンショットを挿入画像として表示",
                "expression": "smile",
            },
            {
                "section_type": "summary",
                "title": "まとめ",
                "duration_seconds": 30,
                "narration": f"今日紹介した5つのAIツール、どれか1つでも使ってみてね！ChatGPT・Notion AI・Canva AI・Grammarly・Otter.ai。{first_person}のおすすめはまずChatGPTから！無料で使えるから今日中に試してみて！",
                "subtitle": "まとめ：今日から試せる5つのAIツール",
                "direction": "画面に5つのツール名を列挙表示",
                "expression": "normal",
            },
            {
                "section_type": "cta",
                "title": "CTA",
                "duration_seconds": 15,
                "narration": f"この動画が役立ったと思ったら、チャンネル登録と高評価お願いします！次回は「AIプロンプト入門」を予定してるから楽しみにしてね！またね！",
                "subtitle": "チャンネル登録・高評価よろしくお願いします！",
                "direction": "終了カードを表示",
                "expression": "smile",
            },
        ]

        full_script = "\n\n".join([
            f"【{s['title']}】\n{s['narration']}"
            for s in sections
        ])

        return {
            "hook_text": sections[0]["narration"],
            "full_script": full_script,
            "sections": sections,
            "subtitle_text": "\n".join([s["subtitle"] for s in sections]),
            "asset_list": [
                {"type": "background", "description": "テック系グラデーション背景"},
                {"type": "insert_image", "description": "ChatGPTのスクリーンショット"},
                {"type": "insert_image", "description": "Notion AIのスクリーンショット"},
                {"type": "bgm", "description": "明るく軽快なBGM"},
            ],
        }


class OpenAIService(BaseAIService):
    """OpenAI API を使った本番AI分析サービス"""

    def __init__(self):
        import openai
        if not settings.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY が設定されていません")
        self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o"

    async def analyze_weekly_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = f"""
あなたはYouTubeチャンネルの分析専門家です。
以下の週次データを分析し、JSON形式で回答してください。

週次データ:
{json.dumps(data, ensure_ascii=False, indent=2)}

以下のキーを含むJSONを返してください:
- trending_video_patterns: 伸びた動画の共通点
- declining_video_patterns: 伸びなかった動画の共通点
- high_ctr_title_patterns: CTRが高いタイトルの傾向
- high_retention_patterns: 視聴維持率が高い構成の特徴
- drop_off_factors: 離脱が起きやすい要素
- improvement_points: 次回動画で改善すべき点
- next_theme_suggestions: 次回動画テーマ案（配列、各要素にtitleとreasonを含む）
- next_title_suggestions: タイトル案5つ（配列）
- next_thumbnail_suggestions: サムネイル案（配列）
- next_script_policy: 台本方針
- summary: 全体サマリー（200字程度）
"""
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def generate_video_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
        character = data.get("character", {})
        theme = data.get("theme", {})
        analysis = data.get("analysis", {})

        duration = theme.get("default_duration_seconds", 600)
        custom_topic = theme.get("custom_topic", "")

        prompt = f"""あなたはYouTubeチャンネルのトッププランナーです。
以下の情報をもとに、視聴維持率・CTRが高い動画の企画をJSON形式で作成してください。

━━━━━━━━━━━━━━━━━━━━━
■ キャラクター情報
━━━━━━━━━━━━━━━━━━━━━
{json.dumps(character, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━
■ チャンネルテーマ設定
━━━━━━━━━━━━━━━━━━━━━
{json.dumps(theme, ensure_ascii=False, indent=2)}
{"■ 今回の指定トピック: " + custom_topic if custom_topic else ""}

━━━━━━━━━━━━━━━━━━━━━
■ 出力するJSONの構造（必須キー）
━━━━━━━━━━━━━━━━━━━━━
{{
  "title": "企画タイトル（視聴者が興味を持つ魅力的なもの）",
  "goal": "動画の目的・達成したいこと",
  "target_audience": "想定視聴者の詳細プロフィール",
  "total_duration_seconds": {duration},
  "structure": [
    {{
      "section": "hook|problem|main|example|summary|cta",
      "title": "セクション名",
      "seconds": 秒数（整数）,
      "description": "このセクションで話す内容の詳細説明（台本ライターへの指示として具体的に書く。100字以上）"
    }}
  ],
  "youtube_title_candidates": ["タイトル案1", "タイトル案2", "タイトル案3", "タイトル案4", "タイトル案5"],
  "youtube_description": "概要欄テキスト（チャプター・リンク・ハッシュタグ含む）",
  "youtube_tags": ["タグ1", "タグ2", ...],
  "cta": "動画末尾のCTAテキスト"
}}

■ structure の合計 seconds は {duration} 秒（{duration//60}分）に合わせること。
■ description は台本ライターへの詳細な指示として書くこと（「〇〇について話す」ではなく「〇〇を△△の観点から説明し、具体例として□□を挙げる」レベルで）。"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)

    async def generate_script(self, data: Dict[str, Any]) -> Dict[str, Any]:
        character = data.get("character", {})
        plan = data.get("plan", {})

        # 動画尺から各セクションの目安文字数を計算（日本語は約300字/分）
        total_sec = plan.get("total_duration_seconds", 600)
        chars_per_sec = 5  # 約300字/分 = 5字/秒

        # structure から各セクションの秒数を取り出す
        structure = plan.get("structure", [])
        section_guide = ""
        for s in structure:
            sec = s.get("seconds", 60)
            approx_chars = sec * chars_per_sec
            section_guide += (
                f"  - {s.get('title', '')}（{s.get('section', '')}）: "
                f"{sec}秒 → narration は約{approx_chars}文字\n"
            )

        prompt = f"""あなたはプロのVTuber台本ライターです。
以下のキャラクター設定・動画企画をもとに、視聴者を引きつける本格的な台本をJSON形式で作成してください。

━━━━━━━━━━━━━━━━━━━━━
■ キャラクター設定
━━━━━━━━━━━━━━━━━━━━━
{json.dumps(character, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━
■ 動画企画
━━━━━━━━━━━━━━━━━━━━━
{json.dumps(plan, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━
■ 絶対に守るルール
━━━━━━━━━━━━━━━━━━━━━
1. 各セクションの narration は「実際に読み上げる台本テキスト」を丸ごと書く。要約・箇条書き・説明文は禁止。
2. 各セクションの文字数は以下の目安を必ず守ること（少なすぎる narration は不合格）:
{section_guide}
3. キャラクターの口調・一人称（{character.get('first_person','私')}）・視聴者の呼び方（{character.get('viewer_address','みなさん')}）を全セクションで統一する。
4. NG表現（{json.dumps(character.get('ng_expressions', []), ensure_ascii=False)}）は絶対に使用しない。
5. 冒頭フック（hook）は視聴者が「続きを見たい！」と思う強いインパクトで始める。
6. 本編セクション（main）は具体的な情報・例・数字を盛り込み、薄い内容にしない。
7. full_script は全セクションの narration を改行でつないだ完全な台本テキストにする。

━━━━━━━━━━━━━━━━━━━━━
■ 出力するJSONの構造
━━━━━━━━━━━━━━━━━━━━━
{{
  "hook_text": "冒頭15秒の強烈なフックテキスト（narration と同じ内容）",
  "full_script": "全セクションの narration を連結した完全台本テキスト",
  "subtitle_text": "全セクションの subtitle を連結したテキスト",
  "asset_list": [{{"type": "background|insert_image|bgm", "description": "説明"}}],
  "sections": [
    {{
      "section_type": "hook|problem|main|example|summary|cta",
      "title": "セクション名",
      "duration_seconds": 秒数（整数）,
      "narration": "このセクションで実際に読み上げる台本テキスト全文（上記文字数目安を守ること）",
      "subtitle": "画面に表示する字幕テキスト（30字以内）",
      "direction": "カメラ・演出・挿入画像などの指示",
      "expression": "normal|smile|surprise|troubled|serious"
    }}
  ]
}}

必ずすべてのセクションを含め、narration は十分な長さで書くこと。"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "あなたはプロのVTuber台本ライターです。"
                        "指定された文字数・キャラクター設定を厳守し、"
                        "視聴者を飽きさせない本格的な台本を書きます。"
                        "narration が短すぎる台本は品質不合格として、必ず十分な長さで書いてください。"
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)


def get_ai_service() -> BaseAIService:
    """環境設定に基づいてAIサービスを返す
    OPENAI_API_KEY が設定されていれば本番モード（APP_ENV に関係なく）
    """
    if settings.OPENAI_API_KEY:
        return OpenAIService()
    return MockAIService()
