# PostgreSQL 16 + pgvector for FinAgent
FROM postgres:16

# 安装 pgvector 扩展
RUN apt-get update && \
    apt-get install -y --no-install-recommends postgresql-16-pgvector && \
    rm -rf /var/lib/apt/lists/*

# 复制初始化脚本
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
COPY schema.sql /docker-entrypoint-initdb.d/02-schema.sql