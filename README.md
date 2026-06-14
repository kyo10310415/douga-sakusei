# VTuber Studio - YouTube動画自動生成システム

YouTubeチャンネルのデータを週次で取得・分析し、VTuberキャラクターが話す10分動画を自動生成してYouTubeへ限定公開でアップロードするシステムです。

---

## 🏗 アーキテクチャ

```
vtuber-studio/
├── apps/
│   ├── web/          # Next.js フロントエンド (TypeScript + TailwindCSS)
│   └── api/          # FastAPI バックエンド (Python)
│       ├── app/
│       │   ├── api/          # APIルーター
│       │   ├── models/       # SQLAlchemyモデル
│       │   ├── services/     # AIサービス・TTSサービス・FFmpeg
│       │   ├── jobs/         # Celeryジョブ
│       │   └── core/         # 設定・DB・認証
│       ├── migrations/       # Alembicマイグレーション
│       └── tests/            # テスト
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🚀 セットアップ手順

### 1. 前提条件

- Docker & Docker Compose
- Node.js 20+ (ローカル開発時)
- Python 3.11+ (ローカル開発時)
- FFmpeg (ローカル開発時)

### 2. リポジトリ準備

```bash
git clone <your-repo>
cd vtuber-studio
```

### 3. .env ファイルの作成

```bash
cp .env.example .env
# .env を編集して必要な値を設定してください
```

### 4. Docker Compose で起動

```bash
docker-compose up -d
```

起動するサービス:
- **PostgreSQL** (port 5432)
- **Redis** (port 6379)
- **FastAPI** (port 8000)
- **Celery Worker** (バックグラウンドジョブ)
- **Celery Beat** (スケジューラー)
- **Flower** (Celeryモニター, port 5555)
- **Next.js** (port 3000)

### 5. DBマイグレーション

```bash
# コンテナ内でマイグレーション実行
docker-compose exec api alembic upgrade head

# または手動で実行
cd apps/api
alembic upgrade head
```

### 6. 初回ユーザー登録

ブラウザで `http://localhost:3000/register` にアクセスし、管理者アカウントを作成してください（最初のユーザーが自動的に管理者になります）。

---

## 🔑 .env 設定方法

`.env.example` をコピーして `.env` を作成し、以下を設定:

| 変数名 | 説明 | 必須 |
|--------|------|------|
| `DATABASE_URL` | PostgreSQL接続文字列 | ✅ |
| `REDIS_URL` | Redis接続URL | ✅ |
| `SECRET_KEY` | JWT署名キー (openssl rand -hex 32 で生成) | ✅ |
| `YOUTUBE_CLIENT_ID` | Google Cloud Console のクライアントID | YouTube連携時 |
| `YOUTUBE_CLIENT_SECRET` | Google Cloud Console のクライアントシークレット | YouTube連携時 |
| `OPENAI_API_KEY` | OpenAI APIキー | AI分析有効時 |
| `TTS_PROVIDER` | mock / openai / elevenlabs / voicevox | - |
| `TTS_API_KEY` | TTSプロバイダーのAPIキー | TTS使用時 |

```bash
# SECRET_KEY の生成
openssl rand -hex 32
```

---

## 📺 YouTube OAuth設定

### Google Cloud Console での設定

1. [Google Cloud Console](https://console.cloud.google.com/) にアクセス
2. プロジェクトを作成
3. 「APIとサービス」→「認証情報」→「OAuthクライアントIDを作成」
4. アプリケーションの種類: **ウェブアプリケーション**
5. 承認済みのリダイレクトURI: `http://localhost:8000/api/youtube/oauth/callback`
6. 有効にするAPI:
   - YouTube Data API v3
   - YouTube Analytics API
   - YouTube Reporting API
7. クライアントID・シークレットを `.env` に設定

### OAuth認証の実行

1. `http://localhost:3000/dashboard/settings` にアクセス
2. 「YouTube連携を開始」ボタンをクリック
3. Googleアカウントで認証

---

## ⏰ 週次ジョブの動かし方

### 自動実行（スケジューラー）

ダッシュボード → 設定 → スケジューラー設定から曜日・時刻を変更できます。

```
デフォルト: 毎週月曜日 9:00 (JST)
```

### 手動実行

```bash
# APIから手動実行
curl -X POST http://localhost:8000/api/youtube/sync-weekly \
  -H "Authorization: Bearer YOUR_TOKEN"

# または Celery タスクを直接実行
docker-compose exec celery_worker celery -A app.jobs.celery_app call \
  app.jobs.youtube_jobs.fetch_weekly_youtube_metrics
```

### ジョブ実行フロー

```
① fetch_weekly_youtube_metrics  → YouTube APIでデータ取得
② run_ai_analysis               → AI分析（OpenAI or モック）
③ generate_video_plan           → 動画企画生成
④ generate_script               → 台本生成
⑤ generate_voice                → TTSで音声生成
⑥ generate_assets               → 背景・素材生成
⑦ render_video                  → FFmpegで動画合成
⑧ upload_to_youtube_unlisted    → YouTube限定公開アップロード
⑨ → ダッシュボードに通知        → 人間がレビュー・承認・公開
```

---

## 🎬 FFmpegの使い方

### 動画生成の流れ

1. 各セクションの音声ファイル (WAV) を TTS で生成
2. キャラクター立ち絵 + 背景画像 + 音声をFFmpegで合成
3. セクション動画を結合
4. BGMをミックス
5. 最終的に 1920x1080 MP4 出力

### ローカルでFFmpegをテスト

```bash
# FFmpegのインストール確認
ffmpeg -version

# 手動でシーン生成テスト
cd apps/api
python -c "
import asyncio
from app.services.render_service import RenderService
service = RenderService()
result = asyncio.run(service.render_full_video([
    {
        'title': 'テストシーン',
        'subtitle': 'テスト字幕',
        'expression': 'smile',
        'duration_seconds': 5,
        'audio_path': '',
        'character_image_path': '',
        'background_path': '',
    }
], '/tmp/test_output.mp4'))
print(result)
"
```

---

## 🔌 外部AI APIの差し替え方法

### AIサービス（分析・台本生成）

`apps/api/app/services/ai_service.py` の `BaseAIService` を継承して新しいクラスを作成:

```python
class MyCustomAIService(BaseAIService):
    async def analyze_weekly_data(self, data): ...
    async def generate_video_plan(self, data): ...
    async def generate_script(self, data): ...

# get_ai_service() を更新
def get_ai_service():
    if settings.AI_PROVIDER == "custom":
        return MyCustomAIService()
    return MockAIService()
```

### TTSサービス

`apps/api/app/services/tts_service.py` の `BaseTTSService` を継承:

```python
class MyTTSService(BaseTTSService):
    async def generate_voice(self, text, voice_id, ...): ...
```

`.env` の `TTS_PROVIDER` を変更するだけで切り替え可能。

### キャラクターアニメーション（Live2D, SadTalker等）

`apps/api/app/services/render_service.py` の `BaseCharacterAnimationService` を継承:

```python
class SadTalkerService(BaseCharacterAnimationService):
    async def generate_scene_video(self, character_image_path, audio_path, ...): ...

# get_animation_service() を更新
def get_animation_service():
    if settings.VIDEO_GENERATION_PROVIDER == "sadtalker":
        return SadTalkerService()
    return FFmpegCharacterAnimationService()
```

---

## 🔒 セキュリティ仕様

| 項目 | 実装内容 |
|------|----------|
| APIキー管理 | `.env` ファイルで管理、コードに直書き禁止 |
| OAuthトークン | Fernet暗号化してDB保存 |
| YouTube公開制限 | アップロードは必ず `unlisted`、`public`は人間の承認後のみ |
| 認証 | JWT Bearer Token |
| 操作ログ | 承認・公開・再生成操作をJobLogに保存 |
| 無限リトライ禁止 | max_retries=3 で上限設定 |

---

## 🌐 本番デプロイ (Render)

### render.yaml の構成例

```yaml
services:
  - type: web
    name: vtuber-api
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn app.main:app --host 0.0.0.0 --port $PORT
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: vtuber-db
          property: connectionString
      - key: REDIS_URL
        fromService:
          name: vtuber-redis
          property: connectionString

  - type: worker
    name: vtuber-worker
    startCommand: celery -A app.jobs.celery_app worker --loglevel=info

databases:
  - name: vtuber-db
    plan: starter

  - type: redis
    name: vtuber-redis
```

### 本番デプロイ時の注意点

1. **SECRET_KEY** は必ず長いランダム文字列に変更
2. **ALLOWED_ORIGINS** を本番ドメインに変更
3. **DEBUG=false** に設定
4. HTTPS化（Renderは自動対応）
5. YouTube OAuth のリダイレクトURIを本番URLに更新
6. FFmpegはDockerfileで自動インストール済み

---

## 🧪 テストの実行

```bash
cd apps/api

# 依存関係のインストール
pip install -r requirements.txt

# テスト実行
pytest tests/ -v

# 個別テスト
pytest tests/test_api.py -v
pytest tests/test_security.py -v

# カバレッジ付き
pytest tests/ --cov=app --cov-report=html
```

### 主要テスト項目

| テスト | 内容 |
|--------|------|
| `test_health_check` | ヘルスチェック |
| `test_register_and_login` | 認証フロー |
| `test_create_character` | キャラクター作成 |
| `test_youtube_publish_blocked_without_approval` | **承認前の公開が拒否されること** |
| `test_youtube_publish_allowed_after_approval` | 承認後の公開が許可されること |
| `test_failed_job_status` | 失敗ジョブのステータス |
| `test_max_retry_exceeded` | 最大リトライ超過 |
| `test_cancel_published_job_blocked` | 公開済みジョブのキャンセル拒否 |

---

## 📊 Flowerモニター

Celeryジョブの進行状況をブラウザで確認:

```
http://localhost:5555
```

---

## 🛠 ローカル開発（Docker不使用）

```bash
# PostgreSQL と Redis を別途起動しておく

# API起動
cd apps/api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Celery Worker起動
celery -A app.jobs.celery_app worker --loglevel=info

# Celery Beat起動
celery -A app.jobs.celery_app beat --loglevel=info

# フロントエンド起動
cd apps/web
npm install
npm run dev
```

---

## 📋 実装済み機能

### ✅ バックエンド
- [x] FastAPI アプリケーション構造
- [x] SQLAlchemy モデル（全20テーブル）
- [x] Alembic マイグレーション設定
- [x] JWT認証・ユーザー登録・ログイン
- [x] OAuthトークン暗号化保存
- [x] YouTube API（OAuth / データ取得 / アップロード）
- [x] AI分析サービス（モック + OpenAI対応）
- [x] TTS サービス（モック + OpenAI + ElevenLabs + VOICEVOX）
- [x] FFmpegレンダリングサービス（差し替え可能設計）
- [x] Celery ジョブキュー（週次パイプライン全工程）
- [x] Celery Beat スケジューラー
- [x] 公開承認フロー（承認なし公開を強制ブロック）
- [x] 操作ログ（承認・公開・再生成）
- [x] API全エンドポイント実装

### ✅ フロントエンド
- [x] Next.js + TypeScript + TailwindCSS
- [x] ログイン・新規登録画面
- [x] ダッシュボードレイアウト（サイドバーナビ）
- [x] ダッシュボードトップ（週次サマリー + AIサマリー + ジョブ状況）
- [x] 週次データ画面（グラフ + テーブル + 動画ランキング）
- [x] キャラクター設定画面（画像アップロード対応）
- [x] 動画テーマ設定画面
- [x] AI分析レポート画面
- [x] 動画生成ジョブ管理画面（ステータスフィルター付き）
- [x] 生成動画レビュー画面（チェックリスト + 承認 + 公開）
- [x] 設定画面（YouTube連携 + スケジューラー設定）

### ✅ セキュリティ
- [x] YouTube自動公開の禁止（常にunlisted）
- [x] 承認前公開ブロック（APIレベルで強制）
- [x] 公開操作の二重確認ダイアログ
- [x] 最大リトライ回数制限
- [x] 操作ログ保存

---

## ⚠️ 未実装・今後の課題

### 未実装機能
- [ ] Alembicマイグレーションファイル（autogenerateで生成必要）
- [ ] YouTube Analytics APIの実データ取得（要OAuth完了）
- [ ] Live2D / SadTalker / Wav2Lip 連携
- [ ] AI画像生成（DALL-E / Stable Diffusion）連携
- [ ] サムネイル自動生成
- [ ] 改善ログ（公開後パフォーマンスの自動取り込み）
- [ ] メール通知（レビュー待ち時）
- [ ] 複数YouTubeチャンネル対応
- [ ] ユーザー権限管理（複数ユーザー）

### 外部APIを接続する際の追加作業
1. **OpenAI（AI分析）**: `OPENAI_API_KEY` を設定し `APP_ENV=production` にする
2. **ElevenLabs（TTS）**: `TTS_PROVIDER=elevenlabs` + `TTS_API_KEY` を設定
3. **VOICEVOX**: `TTS_PROVIDER=voicevox` + VOICEVOXサーバーを起動
4. **YouTube**: OAuth認証を完了し、Analytics APIを有効化
5. **画像生成**: `IMAGE_GENERATION_PROVIDER` を設定（AssetGenerationServiceを拡張）
