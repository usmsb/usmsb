#!/usr/bin/env python3
"""
测试执行脚本 - 全量测试运行器

用途:
- 本地开发: python run_full_tests.py
- CI/CD: python run_full_tests.py --ci
- 仅快速测试: python run_full_tests.py --fast

每次commit自动运行: 在 .git/hooks/pre-commit 中添加调用
"""

import argparse
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path


def run_command(cmd, description):
    """运行命令并返回结果"""
    print(f"\n{'='*60}")
    print(f"  {description}")
    print(f"{'='*60}")
    result = subprocess.run(
        cmd,
        shell=True,
        capture_output=False,
        text=True
    )
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="全量测试运行器")
    parser.add_argument("--ci", action="store_true", help="CI模式: 仅运行CI标记的测试")
    parser.add_argument("--fast", action="store_true", help="快速模式: 仅单元测试")
    parser.add_argument("--unit", action="store_true", help="仅单元测试")
    parser.add_argument("--integration", action="store_true", help="仅集成测试")
    parser.add_argument("--e2e", action="store_true", help="仅E2E测试")
    parser.add_argument("--coverage", action="store_true", default=True, help="生成覆盖率报告")
    parser.add_argument("--module", type=str, help="仅运行指定模块 (agent/wallet/matching等)")
    parser.add_argument("--verbose", "-v", action="store_true", help="详细输出")
    parser.add_argument("--parallel", action="store_true", help="并行运行测试")

    args = parser.parse_args()

    # 测试路径
    test_paths = ["tests/test_business_api_full_coverage.py"]

    # 构建pytest参数
    pytest_args = ["pytest"]

    # 添加测试文件
    pytest_args.extend(test_paths)

    # 标记过滤
    if args.ci:
        pytest_args.extend(["-m", "ci"])
    elif args.fast:
        pytest_args.extend(["-m", "unit"])
    elif args.unit:
        pytest_args.extend(["-m", "unit"])
    elif args.integration:
        pytest_args.extend(["-m", "integration"])
    elif args.e2e:
        pytest_args.extend(["-m", "e2e"])

    # 模块过滤
    if args.module:
        pytest_args.extend(["-m", args.module])

    # 输出选项
    if args.verbose:
        pytest_args.append("-vv")
    else:
        pytest_args.append("-v")

    pytest_args.append("--tb=short")

    # 并行运行
    if args.parallel:
        pytest_args.extend(["-n", "auto"])

    # 覆盖率
    if args.coverage:
        pytest_args.extend([
            "--cov=usmsb_sdk",
            "--cov-report=term-missing",
            "--cov-report=html",
            "--cov-fail-under=70"
        ])

    # 添加额外参数
    pytest_args.extend([
        "-ra",                      # 显示所有非通过测试的摘要
        "--color=yes",
    ])

    print(f"\n{'#'*60}")
    print(f"#  USMSB SDK - 全量测试执行")
    print(f"#  时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"#  命令: {' '.join(pytest_args)}")
    print(f"{'#'*60}\n")

    # 设置环境变量
    os.environ.setdefault("TESTING", "true")
    os.environ.setdefault("PYTHONPATH", str(Path(__file__).parent.parent / "src"))

    # 执行测试
    start_time = time.time()
    success = run_command(" ".join(pytest_args), "测试执行")
    elapsed = time.time() - start_time

    # 输出总结
    print(f"\n{'='*60}")
    print(f"  测试完成")
    print(f"  耗时: {elapsed:.2f}秒")
    print(f"  结果: {'✓ 成功' if success else '✗ 失败'}")
    print(f"{'='*60}")

    # 生成HTML覆盖率报告提示
    if args.coverage and os.path.exists("htmlcov/index.html"):
        print(f"\n覆盖率报告: htmlcov/index.html")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
