"""
NPM/NPX Command Skill - 执行 npm/npx 命令的技能

功能：
1. 执行任意 npm/npx 命令
2. 安装/卸载 npm 包
3. 运行 package.json 中的脚本
4. 启动开发服务器
5. 动态注册为新 skill

权限控制：
- 工作空间路径隔离
- 操作权限检查
- 危险操作限制
"""

import asyncio
import json
import logging
import os
import shutil
from dataclasses import dataclass
from typing import Any

from usmsb_sdk.core.skills.skill_system import (
    Skill,
    SkillCategory,
    SkillMetadata,
    SkillOutput,
    SkillParameter,
    SkillStatus,
)

logger = logging.getLogger(__name__)


# NPM 权限配置
NPM_PERMISSION_CONFIG = {
    "require_wallet": True,
    "require_workspace": True,
    "allowed_operations": {
        "public": ["view", "search", "ls", "outdated", "info"],
        "wallet": ["install", "uninstall", "run", "init", "test", "build"],
        "admin": ["install -g", "uninstall -g", "config edit"],
    },
    "workspace_restriction": {
        "enabled": True,
        "allowed_paths": ["$WORKSPACE", "$TEMP"],
        "blocked_paths": ["/", "/etc", "/usr", "/var", "/root", "/home"],
    },
    "resource_limits": {
        "max_install_size_mb": 500,
        "max_total_packages": 1000,
        "max_daily_installs": 50,
        "command_timeout": 300,
    },
}

# 危险 npm 包列表（已知恶意包）
NPM_BLOCKED_PACKAGES = {
        "flatmap-stream",
        "event-stream@3.3.4",
        "left-pad",
    }


class PermissionChecker:
    """权限检查器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or NPM_PERMISSION_CONFIG

    def check_path(self, path: str, workspace_root: str | None = None) -> tuple:
        """
        检查路径是否在允许范围内

        Returns:
            (allowed: bool, reason: str)
        """
        if not self.config.get("workspace_restriction", {}).get("enabled", True):
            return True, ""

        # 解析路径
        abs_path = os.path.abspath(os.path.expanduser(path))

        # 检查是否包含危险路径
        blocked = self.config.get("workspace_restriction", {}).get("blocked_paths", [])
        for blocked_path in blocked:
            if abs_path.startswith(blocked_path):
                return False, f"Path '{path}' is in blocked directory: {blocked_path}"

        # 如果提供了 workspace_root，检查是否在workspace内
        if workspace_root:
            workspace_abs = os.path.abspath(os.path.expanduser(workspace_root))
            if not abs_path.startswith(workspace_abs):
                return False, f"Path '{path}' is outside workspace: {workspace_root}"

        return True, ""

    def check_package(self, package: str) -> tuple:
        """检查包是否被禁止"""
        if not package:
            return True, ""

        # 检查危险包
        for blocked in NPM_BLOCKED_PACKAGES:
            if package == blocked or package.startswith(blocked + "@"):
                return False, f"Package '{package}' is blocked (known malicious)"

        return True, ""

    def check_operation(self, command: str, user_role: str = "human") -> tuple:
        """
        检查操作是否允许

        Returns:
            (allowed: bool, reason: str)
        """
        # 管理员可以执行所有操作
        if user_role in ["superadmin", "developer"]:
            return True, ""

        # 检查是否是全局安装
        if command in ["install", "uninstall"]:
            if "global" in str(os.environ.get("NPM_GLOBAL", "")):
                return False, "Global install requires DEVELOPER or higher role"

        return True, ""


@dataclass
class NpmExecutionResult:
    """npm 命令执行结果"""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    command: str
    working_dir: str
    execution_time: float


class NpxCommandSkill(Skill):
    """
    执行 npm/npx 命令的技能

    可以执行：
    - npm install/uninstall
    - npx 命令
    - npm run scripts
    - 自定义任意命令
    """

    def __init__(self):
        super().__init__(
            SkillMetadata(
                name="npm_executor",
                version="1.0.0",
                description="执行 npm/npx 命令，安装npm包，运行脚本，启动开发服务器",
                category=SkillCategory.ACTION,
                tags=["npm", "npx", "development", "execution", "shell"],
            )
        )

        self.parameters = {
            "command": SkillParameter(
                name="command",
                type="string",
                description=(
                    "要执行的命令类型: execute(执行命令), install(安装包), "
                    "run(运行脚本), dev(启动开发服务器)"
                ),
                required=True,
                enum=["execute", "install", "uninstall", "run", "dev", "init"],
            ),
            "package": SkillParameter(
                name="package",
                type="string",
                description=(
                    "npm 包名 (用于 install/uninstall)，如 'react', "
                    "'typescript@latest', 'create-react-app'"
                ),
                required=False,
            ),
            "args": SkillParameter(
                name="args",
                type="array",
                description="命令参数数组, 如 ['--save', '--prefix', 'src']",
                required=False,
                default=[],
            ),
            "script": SkillParameter(
                name="script",
                type="string",
                description=(
                    "package.json 中的脚本名称(用于 run), "
                    "如 'dev', 'build', 'start'"
                ),
                required=False,
            ),
            "working_dir": SkillParameter(
                name="working_dir",
                type="string",
                description="执行目录，默认为当前工作目录",
                required=False,
                default=".",
            ),
            "timeout": SkillParameter(
                name="timeout",
                type="integer",
                description="执行超时时间(秒)",
                required=False,
                default=300,
                min_value=1,
                max_value=3600,
            ),
            "env": SkillParameter(
                name="env",
                type="object",
                description="额外的环境变量对象",
                required=False,
                default={},
            ),
            "save_dev": SkillParameter(
                name="save_dev",
                type="boolean",
                description="是否安装为 devDependencies (仅 install 有效)",
                required=False,
                default=False,
            ),
            "global": SkillParameter(
                name="global",
                type="boolean",
                description="是否全局安装 (仅 install 有效)",
                required=False,
                default=False,
            ),
        }

        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="object",
                description="执行结果包含 success, stdout, stderr, returncode",
            ),
            "package_info": SkillOutput(
                name="package_info",
                type="object",
                description="已安装包的信息 (仅 install 有效)",
            ),
        }

    async def execute(
        self, inputs: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """
        执行 npm/npx 命令

        Args:
            inputs: 包含 command, package, args, working_dir, timeout 等
            context: 可选的上下文，包含 wallet_address, role, workspace_root 等

        Returns:
            执行结果字典
        """
        # 获取上下文信息
        wallet_address = context.get("wallet_address") if context else None
        user_role = context.get("role", "human") if context else "human"
        workspace_root = context.get("workspace_root") if context else None

        # 初始化权限检查器
        permission_checker = PermissionChecker(NPM_PERMISSION_CONFIG)

        command_type = inputs.get("command", "execute")
        package = inputs.get("package")
        args = inputs.get("args", [])
        script = inputs.get("script")
        working_dir = inputs.get("working_dir", ".")
        timeout = inputs.get("timeout", 300)
        env = inputs.get("env", {})
        save_dev = inputs.get("save_dev", False)
        global_install = inputs.get("global", False)

        # ===== 权限检查 =====

        # 1. 检查是否需要钱包
        if NPM_PERMISSION_CONFIG.get("require_wallet", True):
            if not wallet_address and command_type not in ["execute"]:
                return {
                    "success": False,
                    "error": "Wallet address required for this operation",
                    "code": "WALLET_REQUIRED",
                }

        # 2. 检查全局安装权限
        if global_install and user_role not in ["superadmin", "developer"]:
            return {
                "success": False,
                "error": "Global installation requires DEVELOPER or higher role",
                "code": "PERMISSION_DENIED",
            }

        # 3. 检查工作空间路径隔离
        if NPM_PERMISSION_CONFIG.get("workspace_restriction", {}).get("enabled", True):
            allowed, reason = permission_checker.check_path(working_dir, workspace_root)
            if not allowed:
                logger.warning(f"NPM path check failed: {reason}")
                return {
                    "success": False,
                    "error": reason,
                    "code": "PATH_RESTRICTED",
                }

        # 4. 检查危险包
        if package:
            allowed, reason = permission_checker.check_package(package)
            if not allowed:
                logger.warning(f"NPM package check failed: {reason}")
                return {
                    "success": False,
                    "error": reason,
                    "code": "PACKAGE_BLOCKED",
                }

        import time

        start_time = time.time()

        try:
            if command_type == "install":
                result = await self._install_package(
                    package=package,
                    args=args,
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                    save_dev=save_dev,
                    global_install=global_install,
                )
            elif command_type == "uninstall":
                result = await self._uninstall_package(
                    package=package,
                    args=args,
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                )
            elif command_type == "run":
                result = await self._run_script(
                    script=script,
                    args=args,
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                )
            elif command_type == "dev":
                result = await self._start_dev_server(
                    working_dir=working_dir,
                    args=args,
                    timeout=timeout,
                    env=env,
                )
            elif command_type == "init":
                result = await self._init_project(
                    package=package,
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                )
            else:
                result = await self._execute_command(
                    cmd=args if args else [],
                    working_dir=working_dir,
                    timeout=timeout,
                    env=env,
                )

            execution_time = time.time() - start_time
            result.execution_time = execution_time

            return {
                "result": {
                    "success": result.success,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "returncode": result.returncode,
                    "command": result.command,
                    "working_dir": result.working_dir,
                    "execution_time": f"{execution_time:.2f}s",
                },
                "package_info": self._parse_package_info(result) if package else None,
            }

        except Exception as e:
            logger.error(f"NPM skill execution failed: {e}")
            return {
                "result": {
                    "success": False,
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": -1,
                    "command": command_type,
                    "working_dir": working_dir,
                    "error": str(e),
                },
                "package_info": None,
            }

    async def _install_package(
        self,
        package: str | None,
        args: list[str],
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        save_dev: bool,
        global_install: bool,
    ) -> NpmExecutionResult:
        """安装 npm 包"""
        if not package:
            raise ValueError("package name is required for install")

        cmd_parts = ["npm", "install"]

        if global_install:
            cmd_parts.append("-g")
        elif save_dev:
            cmd_parts.append("--save-dev")
        else:
            cmd_parts.append("--save")

        cmd_parts.extend(args)
        cmd_parts.append(package)

        return await self._execute_command(cmd_parts, working_dir, timeout, env)

    async def _uninstall_package(
        self,
        package: str | None,
        args: list[str],
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ) -> NpmExecutionResult:
        """卸载 npm 包"""
        if not package:
            raise ValueError("package name is required for uninstall")

        cmd_parts = ["npm", "uninstall"]
        cmd_parts.extend(args)
        cmd_parts.append(package)

        return await self._execute_command(cmd_parts, working_dir, timeout, env)

    async def _run_script(
        self,
        script: str | None,
        args: list[str],
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ) -> NpmExecutionResult:
        """运行 package.json 中的脚本"""
        if not script:
            raise ValueError("script name is required for run")

        cmd_parts = ["npm", "run", script]
        cmd_parts.extend(args)

        return await self._execute_command(cmd_parts, working_dir, timeout, env)

    async def _start_dev_server(
        self,
        working_dir: str,
        args: list[str],
        timeout: int,
        env: dict[str, str],
    ) -> NpmExecutionResult:
        """启动开发服务器 (npm run dev)"""
        cmd_parts = ["npm", "run", "dev"]
        cmd_parts.extend(args)

        return await self._execute_command(cmd_parts, working_dir, timeout, env)

    async def _init_project(
        self,
        package: str | None,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ) -> NpmExecutionResult:
        """初始化新项目"""
        cmd_parts = ["npm", "init"]
        if package:
            cmd_parts.append(package)

        cmd_parts.extend(["-y"])  # 自动确认

        return await self._execute_command(cmd_parts, working_dir, timeout, env)

    async def _execute_command(
        self,
        cmd: list[str],
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ) -> NpmExecutionResult:
        """执行 shell 命令"""
        if not cmd:
            raise ValueError("command is required")

        # 检查 npm/npx 是否可用
        npm_path = shutil.which("npm")
        if not npm_path:
            raise RuntimeError("npm not found in PATH")

        # 构建完整命令
        full_cmd = cmd if isinstance(cmd, list) else cmd.split()

        # 解析工作目录
        cwd = os.path.abspath(os.path.expanduser(working_dir))

        # 确保目录存在
        os.makedirs(cwd, exist_ok=True)

        # 合并环境变量
        full_env = os.environ.copy()
        full_env.update(env)

        logger.info(f"Executing: {' '.join(full_cmd)} in {cwd}")

        try:
            process = await asyncio.create_subprocess_exec(
                *full_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=full_env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout,
                )
            except TimeoutError:
                process.kill()
                await process.wait()
                raise TimeoutError(f"Command timed out after {timeout} seconds")

            stdout_str = stdout.decode("utf-8", errors="replace")
            stderr_str = stderr.decode("utf-8", errors="replace")

            return NpmExecutionResult(
                success=process.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                returncode=process.returncode or 0,
                command=" ".join(full_cmd),
                working_dir=cwd,
                execution_time=0,
            )

        except Exception as e:
            logger.error(f"Command execution failed: {e}")
            return NpmExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                command=" ".join(full_cmd) if cmd else "",
                working_dir=cwd,
                execution_time=0,
            )

    def _parse_package_info(self, result: NpmExecutionResult) -> dict[str, Any] | None:
        """解析包信息"""
        if not result.success:
            return None

        try:
            package_json_path = os.path.join(result.working_dir, "package.json")
            if os.path.exists(package_json_path):
                with open(package_json_path) as f:
                    package_data = json.load(f)
                    return {
                        "name": package_data.get("name"),
                        "version": package_data.get("version"),
                        "dependencies": package_data.get("dependencies", {}),
                        "devDependencies": package_data.get("devDependencies", {}),
                    }
        except Exception as e:
            logger.warning(f"Failed to parse package.json: {e}")

        return None

    async def register_as_skill(
        self,
        skill_name: str,
        description: str,
        npm_command: str,
        category: str = "custom",
    ) -> "DynamicNpmSkill":
        """
        将一个 npm 命令封装注册为新的 Skill

        Args:
            skill_name: 新技能名称
            description: 技能描述
            npm_command: npm 命令，如 "npx create-react-app"
            category: 技能分类

        Returns:
            新的 Skill 实例
        """

        dynamic_skill = DynamicNpmSkill(
            skill_name=skill_name,
            description=description,
            npm_command=npm_command,
            category=category,
        )

        logger.info(f"Registered dynamic npm skill: {skill_name} -> {npm_command}")
        return dynamic_skill


class DynamicNpmSkill(Skill):
    """
    动态创建的 npm 技能

    用户可以自定义命令封装为固定 skill
    """

    def __init__(
        self,
        skill_name: str,
        description: str,
        npm_command: str,
        category: str = "custom",
    ):
        metadata = SkillMetadata(
            name=skill_name,
            version="1.0.0",
            description=description,
            category=SkillCategory.ACTION,
            tags=["npm", "dynamic", category],
            status=SkillStatus.EXPERIMENTAL,
        )
        super().__init__(metadata)

        self.npm_command = npm_command
        self.command_parts = npm_command.split()

        self.parameters = {
            "args": SkillParameter(
                name="args",
                type="array",
                description="命令额外参数",
                required=False,
                default=[],
            ),
            "working_dir": SkillParameter(
                name="working_dir",
                type="string",
                description="执行目录",
                required=False,
                default=".",
            ),
            "timeout": SkillParameter(
                name="timeout",
                type="integer",
                description="超时时间(秒)",
                required=False,
                default=300,
            ),
        }

        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="object",
                description="执行结果",
            ),
        }

    async def execute(
        self, inputs: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """执行动态 npm 命令"""
        args = inputs.get("args", [])
        working_dir = inputs.get("working_dir", ".")
        timeout = inputs.get("timeout", 300)

        full_cmd = self.command_parts + args

        # 复用 NpxCommandSkill 的执行逻辑
        parent = NpxCommandSkill()

        result = await parent._execute_command(
            cmd=full_cmd,
            working_dir=working_dir,
            timeout=timeout,
            env={},
        )

        return {
            "result": {
                "success": result.success,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "command": result.command,
            },
        }


# 全局实例
npx_command_skill = NpxCommandSkill()
