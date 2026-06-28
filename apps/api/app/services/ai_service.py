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

        # ─────────────────────────────────────────────────────────
        # 文字数計算
        # 日本語読み上げ速度: 約6.5字/秒（390字/分）
        # SAFETY_MARGIN: GPTが指示より少なく書く傾向への対抗係数
        # ─────────────────────────────────────────────────────────
        CHARS_PER_SEC = 6.5
        SAFETY_MARGIN = 1.3   # 1.2→1.3に強化（GPTは30%短く書く傾向）

        total_sec = plan.get("total_duration_seconds", 600)
        total_chars_target = int(total_sec * CHARS_PER_SEC * SAFETY_MARGIN)

        # ─────────────────────────────────────────────────────────
        # max_tokens 計算
        # 日本語1文字 ≒ 0.65 tokens（保守的）
        # JSON構造オーバーヘッド: 約1000tokens
        # ─────────────────────────────────────────────────────────
        CHARS_PER_TOKEN_JA = 0.65
        JSON_OVERHEAD_TOKENS = 1200
        max_tokens_needed = int(total_chars_target / CHARS_PER_TOKEN_JA) + JSON_OVERHEAD_TOKENS
        # gpt-4oの上限128,000 / 安全のため16,000でキャップ
        max_tokens = min(max(max_tokens_needed, 4096), 16000)

        structure = plan.get("structure", [])

        # ─────────────────────────────────────────────────────────
        # セクションごとの最低文字数ガイド（具体的な数字で指示）
        # ─────────────────────────────────────────────────────────
        section_lines = []
        for i, s in enumerate(structure, 1):
            sec = s.get("seconds", 60)
            min_chars = int(sec * CHARS_PER_SEC * SAFETY_MARGIN)
            # 具体的な例文量を示す（○行程度と伝える）
            approx_lines = max(3, round(min_chars / 50))
            section_lines.append(
                f"  {i}. 【{s.get('title', '')}】({s.get('section', '')})"
                f" {sec}秒分 → narration を {min_chars}字以上書く"
                f"（約{approx_lines}行〜）"
            )
        section_guide = "\n".join(section_lines)

        # ─────────────────────────────────────────────────────────
        # システムプロンプト: 役割と絶対ルールを最初に宣言
        # ─────────────────────────────────────────────────────────
        system_prompt = (
            f"あなたはプロのVTuber台本ライターです。\n"
            f"今から {total_sec}秒（{total_sec//60}分{total_sec%60:02d}秒）の動画台本をJSON形式で作成します。\n\n"
            f"【絶対ルール】\n"
            f"・narration は「実際に声に出して読む言葉」を一字一句書く。要約・箇条書き・説明文は不合格。\n"
            f"・日本語の読み上げ速度は 6.5字/秒。{total_sec}秒動画には最低 {int(total_sec*CHARS_PER_SEC)}字が必要。\n"
            f"・全 sections の narration 合計が {total_chars_target}字以上でなければ不合格とみなす。\n"
            f"・各セクションの narration は、そのセクションの duration_seconds × 6.5 × 1.3 字以上書くこと。\n"
            f"・full_script は sections の narration を順に連結したもの（省略禁止）。\n"
            f"・出力は必ず正しい JSON オブジェクト1つのみ（コードブロック不要）。"
        )

        # ─────────────────────────────────────────────────────────
        # ユーザープロンプト: 具体的な指示
        # ─────────────────────────────────────────────────────────
        prompt = f"""以下の情報をもとに、{total_sec}秒動画の台本を作成してください。

■ キャラクター
{json.dumps(character, ensure_ascii=False, indent=2)}

■ 動画企画
{json.dumps(plan, ensure_ascii=False, indent=2)}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 各セクションの narration 最低文字数（厳守）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{section_guide}

合計 {total_chars_target}字以上（現在の動画尺 {total_sec}秒 × 6.5字/秒 × 1.3余裕）

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ narration の書き方（重要）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
・「〜について説明します」「〜していきます」などの薄い言葉は禁止
・具体的な数字・固有名詞・ステップ・体験談を盛り込む
・一人称=「{character.get('first_person','私')}」、視聴者の呼び方=「{character.get('viewer_address','みなさん')}」
・文体は話し言葉（「〜だよ！」「〜だよね？」「〜なんだけど」など）
・禁止表現: {json.dumps(character.get('ng_expressions', []), ensure_ascii=False)}
・本編（main）セクションは特に充実させ、1トピックにつき最低200字以上かける
・「〜だよ！」「〜だよね？」などの話し言葉のあと、必ず「具体的には…」「たとえば…」「実際に{character.get('first_person','私')}がやってみたら…」で内容を展開する
・各トピックに「①手順の説明」「②具体例・数字」「③視聴者へのメリット強調」の3要素を入れる

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
■ 出力JSONの構造
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "hook_text": "冒頭フックのnarrationと同一テキスト",
  "full_script": "全narrationを2改行で連結（{total_chars_target}字以上）",
  "subtitle_text": "各セクションのsubtitleを改行で連結",
  "asset_list": [{{"type": "background|insert_image|bgm", "description": "内容"}}],
  "sections": [
    {{
      "section_type": "hook|problem|main|example|summary|cta",
      "title": "セクション名",
      "duration_seconds": 秒数,
      "narration": "読み上げる全文（上記の最低文字数を必ず満たすこと）",
      "subtitle": "字幕テキスト30字以内",
      "direction": "カメラ・演出指示",
      "expression": "normal|smile|surprise|troubled|serious"
    }}
  ]
}}

重要: narration が短いと動画が「無音・間」だらけになります。
必ず各セクションを充実した内容で埋めてください。"""

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            response_format={"type": "json_object"},
            max_tokens=max_tokens,
            temperature=0.85,   # 少し高めにして出力量を増やす
        )

        result = json.loads(response.choices[0].message.content)

        # ─────────────────────────────────────────────────────────
        # 文字数チェック & フォールバック
        # 生成された narration 合計が期待値の60%未満なら再試行
        # ─────────────────────────────────────────────────────────
        sections_out = result.get("sections", [])
        narration_total = sum(len(s.get("narration", "")) for s in sections_out)
        min_acceptable = int(total_sec * CHARS_PER_SEC * 0.8)  # 期待値の80%（81%未満でfallback発動）

        if narration_total < min_acceptable and sections_out:
            # 短すぎるセクションを特定して再生成プロンプトを作る
            short_sections = []
            for s in sections_out:
                dur = s.get("duration_seconds", 60)
                expected = int(dur * CHARS_PER_SEC * SAFETY_MARGIN)
                actual = len(s.get("narration", ""))
                if actual < int(expected * 0.75):  # セクション単位は75%未満で再生成対象
                    short_sections.append({
                        "section_type": s.get("section_type"),
                        "title": s.get("title"),
                        "duration_seconds": dur,
                        "expected_chars": expected,
                        "actual_chars": actual,
                    })

            if short_sections:
                retry_prompt = f"""以下のセクションの narration が短すぎます。書き直してください。

キャラクター一人称: 「{character.get('first_person','私')}」
視聴者の呼び方: 「{character.get('viewer_address','みなさん')}」
動画テーマ: {plan.get('title', '')}

【書き直すセクション】
"""
                for ss in short_sections:
                    retry_prompt += (
                        f"\n■ {ss['title']}（{ss['section_type']}）"
                        f" {ss['duration_seconds']}秒分\n"
                        f"  必要文字数: {ss['expected_chars']}字以上\n"
                        f"  現在の文字数: {ss['actual_chars']}字（不足）\n"
                        f"  → {ss['expected_chars']}字以上の narration を書いてください\n"
                    )
                retry_prompt += f"""
【書き方ルール】
・実際に読み上げる言葉を一字一句書く（「〜について説明します」禁止）
・話し言葉で具体的な数字・事例・ステップを盛り込む
・各セクションを独立した JSON オブジェクトの配列で返す

出力形式（JSONオブジェクト）:
{{
  "sections": [
    {{
      "section_type": "...",
      "title": "...",
      "narration": "（{short_sections[0]['expected_chars']}字以上の完全なテキスト）"
    }}
  ]
}}"""

                retry_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                f"あなたはVTuber台本ライターです。"
                                f"指示した文字数を必ず守って narration を書いてください。"
                            ),
                        },
                        {"role": "user", "content": retry_prompt},
                    ],
                    response_format={"type": "json_object"},
                    max_tokens=max_tokens,
                    temperature=0.9,
                )
                retry_result = json.loads(retry_response.choices[0].message.content)
                retry_sections = retry_result.get("sections", [])

                # 短かったセクションを再生成したものに差し替え
                retry_map = {s.get("section_type"): s for s in retry_sections}
                for i, s in enumerate(sections_out):
                    stype = s.get("section_type")
                    if stype in retry_map and retry_map[stype].get("narration"):
                        sections_out[i]["narration"] = retry_map[stype]["narration"]

                result["sections"] = sections_out

        # full_script を sections から再構築（常に最新のnarrationを反映）
        result["full_script"] = "\n\n".join(
            s.get("narration", "")
            for s in sections_out
            if s.get("narration")
        )

        return result


def get_ai_service() -> BaseAIService:
    """環境設定に基づいてAIサービスを返す
    OPENAI_API_KEY が設定されていれば本番モード（APP_ENV に関係なく）
    """
    if settings.OPENAI_API_KEY:
        return OpenAIService()
    return MockAIService()
