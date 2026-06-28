FROM python:3.11-slim

# FFmpeg + supervisord + 必要なシステムパッケージ
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libpq-dev \
    gcc \
    curl \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存関係を先にコピー（キャッシュ効率化）
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリコードをコピー
COPY . .

# 起動スクリプトに実行権限を付与
RUN chmod +x /app/start.sh

# supervisord 設定ファイルをコピー
COPY supervisord.conf /etc/supervisor/conf.d/vtuber.conf

# Render Disk のマウントパスを作成（disk未使用時の fallback 用）
RUN mkdir -p /opt/render/project/src/uploads

EXPOSE 8000

# supervisord でAPI + Worker + Beat を一括起動
CMD ["/app/start.sh"]
