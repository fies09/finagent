# FinAgent 金融AI量化服务 Dockerfile
# 基于 Python 3.13 + ccxt + backtrader + FastAPI

FROM python:3.13-slim

WORKDIR /app

# 安装系统依赖 (ccxt/backtrader 编译需要)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app.py .
COPY config/ config/
COPY core/ core/
COPY tests/ tests/

# 创建数据目录
RUN mkdir -p data reports

EXPOSE 8000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]