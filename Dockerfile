# Pythonの軽量イメージを使用
FROM python:3.9-slim

# 作業ディレクトリ設定
WORKDIR /app

# ファイルをコピーしてインストール
COPY . .
RUN pip install --no-cache-dir -r requirements.txt

# 起動コマンド
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
