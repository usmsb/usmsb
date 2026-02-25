"""
测试运行脚本

用于运行所有测试的统一脚本：
- 单元测试
- 集成测试
- E2E 测试
"""

import os
import sys
import argparse
import subprocess
import time
from datetime import datetime


def run_command(cmd, description):
    """运行命令并报告结果"""
    print(f"\n{'=' * 60}")
    print(f"运行: {description}")
    print(f"命令: {' '.join(cmd)}")
    print('=' * 60)

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - start_time

    print(f"\n输出:\n{result.stdout}")
    if result.stderr:
        print(f"错误:\n{result.stderr}")

    print(f"\n耗时: {elapsed:.2f}秒")
    print(f"返回码: {result.returncode}")

    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description='运行精准匹配系统测试')
    parser.add_argument(
        '--type', '-t',
        choices=['unit', 'integration', 'e2e', 'all'],
        default='all',
        help='测试类型: unit, integration, e2e, all'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    parser.add_argument(
        '--coverage', '-c',
        action='store_true',
        help='生成覆盖率报告'
    )
    parser.add_argument(
        '--html',
        action='store_true',
        help='生成HTML覆盖率报告'
    )

    args = parser.parse_args()

    # 测试目录
    test_dir = os.path.dirname(os.path.abspath(__file__))

    # 结果统计
    results = {
        'unit': None,
        'integration': None,
        'e2e': None
    }

    # 额外参数
    extra_args = []
    if args.verbose:
        extra_args.append('-v')
    if args.coverage:
        extra_args.extend(['--cov-report=term-missing'])
    if args.html:
                extra_args.extend(['--cov-report=html', '--cov-report=coverage.html'])

    # 运行测试
    print(f"\n开始运行测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试类型: {args.type}")

    if args.type in ['unit', 'all']:
        print("\n" + "=" * 60)
        print("单元测试 (Unit Tests)")
        print("=" * 60)

        cmd = [
            sys.executable, '-m', 'pytest',
            os.path.join(test_dir, 'unit', 'test_meta_agent_service.py'),
            os.path.join(test_dir, 'unit', 'test_meta_agent_service_extended.py'),
            *extra_args
        ]
        results['unit'] = run_command(cmd, "Meta Agent 单元测试")

    if args.type in ['integration', 'all']:
        print("\n" + "=" * 60)
        print("集成测试 (Integration Tests)")
        print("=" * 60)

        cmd = [
            sys.executable, '-m', 'pytest',
            os.path.join(test_dir, 'integration', 'test_meta_agent_integration.py'),
            *extra_args
        ]
        results['integration'] = run_command(cmd, "Meta Agent 集成测试")

    if args.type in ['e2e', 'all']:
        print("\n" + "=" * 60)
        print("E2E 测试 (End-to-End Tests)")
        print("=" * 60)
        print("\n注意: E2E 测试需要运行中的服务器")
        print("请确保服务器在 http://localhost:8000 运行")
        print("或设置环境变量 E2E_BASE_URL")

        cmd = [
            sys.executable, '-m', 'pytest',
            os.path.join(test_dir, 'e2e', 'test_precise_matching_e2e.py'),
            *extra_args
        ]
        results['e2e'] = run_command(cmd, "Meta Agent E2E 测试")

    # 打印总结
    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)

    total_passed = 0
    total_failed = 0

    for test_type, passed in results.items():
        if passed is None:
            continue
        if passed:
            print(f"✅ {test_type.upper()}: 通过")
            total_passed += 1
        else:
            print(f"❌ {test_type.upper()}: 失败")
            total_failed += 1

    print(f"\n总计: {total_passed} 通过, {total_failed} 失败")

    # 返回码
    if total_failed > 1:
        sys.exit(1)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
