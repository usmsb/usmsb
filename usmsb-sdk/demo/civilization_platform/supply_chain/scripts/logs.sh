#!/bin/bash
#
# Supply Chain Demo - Logs Script
# 查看 Demo 日志
#

set -e

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 项目目录
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

# 解析命令行参数
SERVICE="${1:-}"
FOLLOW="${2:--f}"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Supply Chain Demo - Logs${NC}"
echo -e "${GREEN}========================================${NC}"

# 显示帮助
show_help() {
    echo "Usage: $0 [service] [-f|--follow]"
    echo ""
    echo "Services:"
    echo "  all          - All services (default)"
    echo "  redis        - Redis logs"
    echo "  supplier     - Supplier Agent logs"
    echo "  buyer        - Buyer Agent logs"
    echo "  predictor    - Predictor Agent logs"
    echo "  match        - Match Agent logs"
    echo ""
    echo "Options:"
    echo "  -f, --follow - Follow log output (default)"
    echo "  --no-follow  - Don't follow, show current logs"
}

case "$SERVICE" in
    -h|--help|help)
        show_help
        exit 0
        ;;
    all|"")
        echo -e "${YELLOW}Showing all service logs...${NC}"
        docker-compose logs $FOLLOW
        ;;
    redis)
        echo -e "${YELLOW}Showing Redis logs...${NC}"
        docker-compose logs $FOLLOW redis
        ;;
    supplier)
        echo -e "${YELLOW}Showing Supplier Agent logs...${NC}"
        docker-compose logs $FOLLOW supplier_agent
        ;;
    buyer)
        echo -e "${YELLOW}Showing Buyer Agent logs...${NC}"
        docker-compose logs $FOLLOW buyer_agent
        ;;
    predictor)
        echo -e "${YELLOW}Showing Predictor Agent logs...${NC}"
        docker-compose logs $FOLLOW predictor_agent
        ;;
    match)
        echo -e "${YELLOW}Showing Match Agent logs...${NC}"
        docker-compose logs $FOLLOW match_agent
        ;;
    *)
        echo -e "Unknown service: $SERVICE"
        show_help
        exit 1
        ;;
esac
