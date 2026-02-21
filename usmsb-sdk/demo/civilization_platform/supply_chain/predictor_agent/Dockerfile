# PredictorAgent Dockerfile
# 价格预测 Agent 容器镜像

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制共享模块
COPY shared/ /app/shared/

# 复制 Agent 代码
COPY predictor_agent/ /app/predictor_agent/

# 创建模型目录
RUN mkdir -p /app/models

# 设置工作目录到 Agent 目录
WORKDIR /app

# 创建非 root 用户
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8003/health')" || exit 1

# 暴露端口
EXPOSE 8003

# 启动命令
CMD ["python", "-m", "predictor_agent.agent"]
