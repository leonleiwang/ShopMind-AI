FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（如 build-essential，以便安装 asyncpg 等）
RUN apt-get update && apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令：Railway 会注入 PORT，本地 Docker 默认 8000
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
