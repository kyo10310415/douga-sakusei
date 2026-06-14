FROM python:3.11-slim

# FFmpeg + 必要なシステムパッケージ
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係を先にコピー（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコードをコピー
COPY . .

# 起動スクリプトに実行権限を付与
RUN chmod +x /app/start.sh

# アップロードディレクトリ作成
RUN mkdir -p /tmp/uploads

EXPOSE 8000

# start.sh でマイグレーション→サーバー起動
CMD ["/app/start.sh"]
