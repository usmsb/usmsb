#!/bin/bash
#
# Supply Chain Demo - Stop Script
# 停止供应链报价 Demo
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Supply Chain Demo - Stopping${NC}"
echo -e "${GREEN}========================================${NC}"

# 解析命令行参数
MODE="${1:-docker}"

case "$MODE" in
    docker)
        echo -e "${YELLOW}Stopping Docker Compose services...${NC}"

        # 停止服务
        docker-compose down

        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Demo Stopped Successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
        ;;

    all)
        echo -e "${YELLOW}Stopping all services and cleaning up...${NC}"

        # 停止并删除容器、网络、镜像
        docker-compose down --rmi local -v

        echo -e "${GREEN}All services stopped and cleaned up${NC}"
        ;;

    local)
        echo -e "${YELLOW}Stopping local services...${NC}"

        # 停止 Redis
        if command -v redis-cli &> /dev/null; then
            redis-cli shutdown 2>/dev/null || true
        fi

        # 停止 Python 进程
        pkill -f "run_demo.py" 2>/dev/null || true
        pkill -f "supplier_agent" 2>/dev/null || true
        pkill -f "buyer_agent" 2>/dev/null || true
        pkill -f "predictor_agent" 2>/dev/null || true
        pkill -f "match_agent" 2>/dev/null || true

        echo -e "${GREEN}Local services stopped${NC}"
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: $0 [docker|all|local]"
        exit 1
        ;;
esac
