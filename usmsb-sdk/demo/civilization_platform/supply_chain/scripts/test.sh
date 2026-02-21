#!/bin/bash
#
# Supply Chain Demo - Test Script
# 运行测试
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
echo -e "${GREEN}  Supply Chain Demo - Tests${NC}"
echo -e "${GREEN}========================================${NC}"

# 解析命令行参数
TEST_TYPE="${1:-all}"
VERBOSE="${2:-}"

if [ "$VERBOSE" = "-v" ] || [ "$VERBOSE" = "--verbose" ]; then
    export LOG_LEVEL=DEBUG
fi

# 显示帮助
show_help() {
    echo "Usage: $0 [test_type] [-v|--verbose]"
    echo ""
    echo "Test Types:"
    echo "  all        - Run all tests (default)"
    echo "  scenario   - Run scenario tests"
    echo "  unit       - Run unit tests (if available)"
    echo "  demo       - Run demo with test scenarios"
    echo ""
    echo "Options:"
    echo "  -v, --verbose - Enable verbose output"
}

case "$TEST_TYPE" in
    -h|--help|help)
        show_help
        exit 0
        ;;
    all)
        echo -e "${YELLOW}Running all tests...${NC}"
        python3 test_scenario.py
        ;;

    scenario)
        echo -e "${YELLOW}Running scenario tests...${NC}"
        python3 test_scenario.py
        ;;

    unit)
        echo -e "${YELLOW}Running unit tests...${NC}"
        if command -v pytest &> /dev/null; then
            pytest tests/unit/ -v 2>/dev/null || echo "No unit tests found"
        else
            echo -e "${YELLOW}pytest not installed, skipping unit tests${NC}"
        fi
        ;;

    demo)
        echo -e "${YELLOW}Running demo with test scenarios...${NC}"
        python3 run_demo.py --mode auto --scenario all
        ;;

    docker)
        echo -e "${YELLOW}Running tests in Docker...${NC}"

        # 确保服务正在运行
        if ! docker-compose ps | grep -q "supply_chain"; then
            echo -e "${YELLOW}Starting services first...${NC}"
            docker-compose up -d
            sleep 10
        fi

        # 在容器中运行测试
        docker-compose exec supplier_agent python -c "
import sys
sys.path.insert(0, '/app/shared')
print('Supplier Agent OK')
" || echo -e "${RED}Supplier Agent test failed${NC}"
        ;;

    *)
        echo -e "Unknown test type: $TEST_TYPE"
        show_help
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  Tests Complete${NC}"
echo -e "${GREEN}========================================${NC}"
