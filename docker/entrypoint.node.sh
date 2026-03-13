#!/bin/bash
set -e

# USMSB Platform Node Entrypoint Script
# 新文明平台节点启动脚本

echo "Starting USMSB Platform Node..."

# 设置默认配置
: ${NODE_ID:="node-$(hostname)"}
: ${NODE_NAME:="USMSB Node"}
: ${LOG_LEVEL:="INFO"}

# 导出环境变量
export NODE_ID
export NODE_NAME
export LOG_LEVEL

# 创建必要的目录
mkdir -p /app/data /app/logs

# 检查配置文件
if [ ! -f /app/config.yaml ]; then
    echo "No config.yaml found, using environment variables..."
fi

# 启动节点服务
echo "Node ID: ${NODE_ID}"
echo "Node Name: ${NODE_NAME}"
echo "Log Level: ${LOG_LEVEL}"

# 执行传入的命令
exec "$@"
