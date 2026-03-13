#!/usr/bin/env python3
"""
测试运行器 - 快速运行各类测试

使用方法:
    python run_tests.py              # 运行所有测试
    python run_tests.py --unit       # 仅单元测试
    python run_tests.py --logic      # 仅业务逻辑测试
    python run_tests.py --coverage   # 运行并生成覆盖率报告
    python run_tests.py --security   # 仅安全测试
    python run_tests.py --watch      # 监视模式 (文件变化自动运行)
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path


def get_pytest_args(args):
    """构建pytest参数"""
    pytest_args = ["pytest"]

    # 测试文件 - 全部测试
    test_files = [
        "tests/test_business_api_full_coverage.py",
        "tests/test_business_logic_coverage.py",
        "tests/test_comprehensive_coverage.py",
    ]

    # 安全测试单独标记
    if args.security:
        pytest_args.append("tests/test_security_vulnerability.py")
    elif args.logic:
        pytest_args.append("tests/test_business_logic_coverage.py")
    else:
        # 默认运行所有测试文件
        pytest_args.extend(test_files)
        if not args.security_only:
            pytest_args.append("tests/test_security_vulnerability.py")

    # 标记过滤
    if args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.e2e:
        pytest_args.extend(["-m", "e2e"])
    elif args.ci:
        pytest_args.extend(["-m", "ci"])
    elif args.llm:
        pytest_args.extend(["-m", "requires_llm"])
    elif args.blockchain:
        pytest_args.extend(["-m", "requires_blockchain"])

    # 特定模块
    if args.module:
        pytest_args.extend(["-m", args.module])

    # 输出选项
    if args.verbose:
        pytest_args.append("-vv")
    else:
        pytest_args.append("-v")

    pytest_args.extend([
        "--tb=short",
        "-ra",
        "--color=yes",
    ])

    # 覆盖率
    if args.coverage:
        pytest_args.extend([
            "--cov=usmsb_sdk",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=70",
        ])

    # 监视模式
    if args.watch:
        pytest_args = ["pytest-watch", "--"] + pytest_args

    return pytest_args


def main():
    parser = argparse.ArgumentParser(description="USMSB测试运行器")
    parser.add_argument("--unit", action="store_true", help="仅单元测试")
    parser.add_argument("--logic", action="store_true", help="仅业务逻辑测试")
    parser.add_argument("--integration", action="store_true", help="仅集成测试")
    parser.add_argument("--e2e", action="store_true", help="仅E2E测试")
    parser.add_argument("--ci", action="store_true", help="CI测试 (每次commit运行)")
    parser.add_argument("--llm", action="store_true", help="仅LLM相关测试")
    parser.add_argument("--blockchain", action="store_true", help="仅区块链相关测试")
    parser.add_argument("--security", action="store_true", help="仅安全测试")
    parser.add_argument("--security-only", action="store_true", help="仅运行安全测试文件")
    parser.add_argument("--module", type=str, help="指定模块 (agent/wallet/matching等)")
    parser.add_argument("--coverage", "-c", action="store_true", help="生成覆盖率报告")
    parser.add_argument("--watch", "-w", action="store_true", help="监视模式")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--parallel", "-p", action="store_true", help="并行运行")
    parser.add_argument("--failfast", "-x", action="store_true", help="首次失败停止")
    parser.add_argument("--last-failed", action="store_true", help="仅运行上次失败的测试")

    args = parser.parse_args()

    # 设置PYTHONPATH
    project_root = Path(__file__).parent
    os.environ["PYTHONPATH"] = str(project_root / "src")
    os.environ["TESTING"] = "true"

    # 构建参数
    pytest_args = get_pytest_args(args)

    # 添加额外参数
    if args.parallel:
        pytest_args.insert(1, "-n")
        pytest_args.insert(2, "auto")

    if args.failfast:
        pytest_args.append("-x")

    if args.last_failed:
        pytest_args.append("--lf")

    # 显示命令
    print(f"\nRunning: {' '.join(pytest_args)}\n")

    # 执行
    result = subprocess.run(pytest_args)
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
