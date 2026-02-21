#!/bin/bash
#
# Supply Chain Demo - Start Script
# 启动供应链报价 Demo
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
echo -e "${GREEN}  Supply Chain Demo - Starting${NC}"
echo -e "${GREEN}========================================${NC}"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Error: docker-compose is not installed${NC}"
    exit 1
fi

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}Warning: .env file not found, creating from .env.example${NC}"
    if [ -f ".env.example" ]; then
        cp .env.example .env
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi

# 解析命令行参数
MODE="${1:-docker}"

case "$MODE" in
    docker)
        echo -e "${GREEN}Starting with Docker Compose...${NC}"

        # 构建镜像
        echo -e "${YELLOW}Building Docker images...${NC}"
        docker-compose build

        # 启动服务
        echo -e "${YELLOW}Starting services...${NC}"
        docker-compose up -d

        # 等待服务启动
        echo -e "${YELLOW}Waiting for services to start...${NC}"
        sleep 10

        # 检查服务状态
        echo -e "${GREEN}Service Status:${NC}"
        docker-compose ps

        echo -e "${GREEN}========================================${NC}"
        echo -e "${GREEN}  Demo Started Successfully!${NC}"
        echo -e "${GREEN}========================================${NC}"
        echo ""
        echo -e "Services:"
        echo -e "  - Redis: localhost:6379"
        echo -e "  - Supplier Agent: localhost:8001"
        echo -e "  - Buyer Agent: localhost:8002"
        echo -e "  - Predictor Agent: localhost:8003"
        echo -e "  - Match Agent: localhost:8004"
        echo ""
        echo -e "Commands:"
        echo -e "  ./scripts/logs.sh     - View logs"
        echo -e "  ./scripts/stop.sh     - Stop demo"
        echo -e "  ./scripts/test.sh     - Run tests"
        ;;

    local)
        echo -e "${GREEN}Starting in local mode...${NC}"

        # 检查 Python
        if ! command -v python3 &> /dev/null; then
            echo -e "${RED}Error: Python 3 is not installed${NC}"
            exit 1
        fi

        # 安装依赖
        if [ -f "requirements.txt" ]; then
            echo -e "${YELLOW}Installing dependencies...${NC}"
            pip install -r requirements.txt
        fi

        # 启动 Redis (如果可用)
        if command -v redis-server &> /dev/null; then
            echo -e "${YELLOW}Starting Redis...${NC}"
            redis-server --daemonize yes || true
        fi

        # 启动 Demo
        echo -e "${YELLOW}Starting demo...${NC}"
        python3 run_demo.py --mode interactive
        ;;

    *)
        echo -e "${RED}Unknown mode: $MODE${NC}"
        echo "Usage: $0 [docker|local]"
        exit 1
        ;;
esac
