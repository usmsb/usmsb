"""
Git Command Skill - 执行 Git 命令的技能

功能：
1. 仓库操作 (clone, init, remote)
2. 分支操作 (branch, checkout, switch, merge)
3. 远程操作 (fetch, pull, push)
4. 提交操作 (add, commit, revert, reset)
5. 查看操作 (status, log, diff, show, blame)
6. GitHub 操作 (通过 gh CLI)

权限控制：
- 工作空间路径隔离
- 远程仓库白名单
- 危险操作限制 (force push, hard reset)
"""

import asyncio
import logging
import os
import shutil
from typing import Any

from usmsb_sdk.core.skills.skill_system import (
    Skill,
    SkillCategory,
    SkillMetadata,
    SkillOutput,
    SkillParameter,
)

logger = logging.getLogger(__name__)


# Git 权限配置
GIT_PERMISSION_CONFIG = {
    "require_wallet": True,
    "require_workspace": True,
    "allowed_operations": {
        "workspace": [
            "status",
            "log",
            "diff",
            "show",
            "branch",
            "add",
            "commit",
            "checkout",
            "switch",
            "merge",
            "stash",
            "stash pop",
            "init",
        ],
        "remote": ["clone", "fetch", "pull", "push", "remote"],
        "dangerous": ["reset --hard", "reset --mixed", "push --force", "filter-branch"],
    },
    "remote_whitelist": {
        "enabled": True,
        "allowed_domains": [
            "github.com",
            "gitlab.com",
            "bitbucket.org",
            "gitee.com",
        ],
        "blocked_patterns": [
            "*internal-secret*",
            "*credentials*",
        ],
    },
    "workspace_restriction": {
        "enabled": True,
        "blocked_paths": ["/", "/etc", "/usr", "/var", "/root", "/home"],
    },
}

# 危险操作列表
GIT_DANGEROUS_OPERATIONS = [
    "reset --hard",
    "reset --mixed",
    "push --force",
    "push -f",
    "filter-branch",
    "filter-branch",
]


class GitPermissionChecker:
    """Git 权限检查器"""

    def __init__(self, config: dict[str, Any] = None):
        self.config = config or GIT_PERMISSION_CONFIG

    def check_path(self, path: str, workspace_root: str | None = None) -> tuple:
        """
        检查路径是否在允许范围内

        Returns:
            (allowed: bool, reason: str)
        """
        if not self.config.get("workspace_restriction", {}).get("enabled", True):
            return True, ""

        abs_path = os.path.abspath(os.path.expanduser(path))

        blocked = self.config.get("workspace_restriction", {}).get("blocked_paths", [])
        for blocked_path in blocked:
            if abs_path.startswith(blocked_path):
                return False, f"Path '{path}' is in blocked directory: {blocked_path}"

        if workspace_root:
            workspace_abs = os.path.abspath(os.path.expanduser(workspace_root))
            if not abs_path.startswith(workspace_abs):
                return False, f"Path '{path}' is outside workspace: {workspace_root}"

        return True, ""

    def check_remote(self, repository: str) -> tuple:
        """
        检查远程仓库是否在白名单中

        Returns:
            (allowed: bool, reason: str)
        """
        if not repository:
            return True, ""

        if not self.config.get("remote_whitelist", {}).get("enabled", True):
            return True, ""

        allowed_domains = self.config.get("remote_whitelist", {}).get("allowed_domains", [])

        # 检查域名
        for domain in allowed_domains:
            if domain in repository:
                return True, ""

        return False, f"Repository domain not in whitelist. Allowed: {allowed_domains}"

    def check_operation(self, command: str, flags: list[str], user_role: str = "human") -> tuple:
        """
        检查操作是否允许

        Returns:
            (allowed: bool, reason: str)
        """
        # 危险操作检查
        full_command = command
        if flags:
            full_command = f"{command} {' '.join(flags)}"

        dangerous_ops = self.config.get("allowed_operations", {}).get("dangerous", [])

        for dangerous in dangerous_ops:
            if dangerous in full_command:
                if user_role not in ["superadmin", "developer"]:
                    return (
                        False,
                        f"Dangerous operation '{dangerous}' requires DEVELOPER or higher role",
                    )

        return True, ""


class GitCommandSkill(Skill):
    """
    执行 Git 命令的技能

    支持的子命令：
    - 仓库: clone, init, remote
    - 分支: branch, checkout, switch, merge
    - 远程: fetch, pull, push
    - 提交: add, commit, revert, reset
    - 查看: status, log, diff, show, blame
    - GitHub: 通过 gh CLI
    """

    def __init__(self):
        super().__init__(
            SkillMetadata(
                name="git_executor",
                version="1.0.0",
                description="执行 Git 命令，管理仓库、分支、远程操作、提交，以及 GitHub 操作",
                category=SkillCategory.ACTION,
                tags=["git", "github", "version-control", "clone", "commit", "push", "pull"],
            )
        )

        self.parameters = {
            "command": SkillParameter(
                name="command",
                type="string",
                description=(
                    "Git 子命令: clone(克隆), init(初始化), remote(远程), "
                    "branch(分支), checkout(检出), switch(切换), merge(合并), "
                    "fetch(获取), pull(拉取), push(推送), add(暂存), commit(提交), "
                    "reset(重置), revert(回滚), status(状态), log(日志), "
                    "diff(差异), show(显示), blame(追责)"
                ),
                required=True,
            ),
            "repository": SkillParameter(
                name="repository",
                type="string",
                description="仓库 URL 或名称 (用于 clone, remote add)",
                required=False,
            ),
            "branch": SkillParameter(
                name="branch",
                type="string",
                description="分支名 (用于 branch, checkout, switch, merge, push -u)",
                required=False,
            ),
            "remote": SkillParameter(
                name="remote",
                type="string",
                description="远程名 (用于 fetch, pull, push)，默认 origin",
                required=False,
                default="origin",
            ),
            "message": SkillParameter(
                name="message",
                type="string",
                description="提交信息 (用于 commit)",
                required=False,
            ),
            "path": SkillParameter(
                name="path",
                type="string",
                description="文件路径或目录 (用于 add, checkout)",
                required=False,
            ),
            "working_dir": SkillParameter(
                name="working_dir",
                type="string",
                description="Git 仓库目录，默认当前目录",
                required=False,
                default=".",
            ),
            "timeout": SkillParameter(
                name="timeout",
                type="integer",
                description="执行超时时间(秒)",
                required=False,
                default=120,
                min_value=1,
                max_value=3600,
            ),
            "flags": SkillParameter(
                name="flags",
                type="array",
                description="额外命令标志，如 ['-m', 'feat: new feature']",
                required=False,
                default=[],
            ),
            "env": SkillParameter(
                name="env",
                type="object",
                description="环境变量",
                required=False,
                default={},
            ),
        }

        self.outputs = {
            "result": SkillOutput(
                name="result",
                type="object",
                description="执行结果包含 success, stdout, stderr, returncode",
            ),
            "repository_info": SkillOutput(
                name="repository_info",
                type="object",
                description="仓库信息 (仅 clone/init 有效)",
            ),
        }

    async def execute(
        self, inputs: dict[str, Any], context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """执行 Git 命令"""
        # 获取上下文信息
        wallet_address = context.get("wallet_address") if context else None
        user_role = context.get("role", "human") if context else "human"
        workspace_root = context.get("workspace_root") if context else None

        # 初始化权限检查器
        permission_checker = GitPermissionChecker(GIT_PERMISSION_CONFIG)

        command = inputs.get("command")
        repository = inputs.get("repository")
        branch = inputs.get("branch")
        remote = inputs.get("remote", "origin")
        message = inputs.get("message")
        path = inputs.get("path")
        working_dir = inputs.get("working_dir", ".")
        timeout = inputs.get("timeout", 120)
        flags = inputs.get("flags", [])
        env = inputs.get("env", {})

        # ===== 权限检查 =====

        # 1. 检查是否需要钱包
        if GIT_PERMISSION_CONFIG.get("require_wallet", True):
            if not wallet_address and command not in ["status", "log", "diff"]:
                return {
                    "success": False,
                    "error": "Wallet address required for this operation",
                    "code": "WALLET_REQUIRED",
                }

        # 2. 检查工作空间路径隔离
        if GIT_PERMISSION_CONFIG.get("workspace_restriction", {}).get("enabled", True):
            allowed, reason = permission_checker.check_path(working_dir, workspace_root)
            if not allowed:
                logger.warning(f"Git path check failed: {reason}")
                return {
                    "success": False,
                    "error": reason,
                    "code": "PATH_RESTRICTED",
                }

        # 3. 检查远程仓库白名单 (clone/pull/push)
        if repository and command in ["clone", "pull", "push", "fetch"]:
            allowed, reason = permission_checker.check_remote(repository)
            if not allowed:
                logger.warning(f"Git remote check failed: {reason}")
                return {
                    "success": False,
                    "error": reason,
                    "code": "REMOTE_NOT_ALLOWED",
                }

        # 4. 检查危险操作 (force push, hard reset)
        allowed, reason = permission_checker.check_operation(command, flags, user_role)
        if not allowed:
            logger.warning(f"Git operation check failed: {reason}")
            return {
                "success": False,
                "error": reason,
                "code": "OPERATION_DENIED",
            }

        import time

        start_time = time.time()

        try:
            if command == "clone":
                result = await self._clone(repository, working_dir, timeout, env, flags)
            elif command == "init":
                result = await self._init(working_dir, timeout, env, flags)
            elif command == "remote":
                result = await self._remote(working_dir, repository, timeout, env)
            elif command == "branch":
                result = await self._branch(working_dir, branch, timeout, env, flags)
            elif command == "checkout":
                result = await self._checkout(working_dir, branch, path, timeout, env, flags)
            elif command == "switch":
                result = await self._switch(working_dir, branch, timeout, env, flags)
            elif command == "merge":
                result = await self._merge(working_dir, branch, timeout, env, flags)
            elif command == "fetch":
                result = await self._fetch(working_dir, remote, timeout, env, flags)
            elif command == "pull":
                result = await self._pull(working_dir, remote, branch, timeout, env, flags)
            elif command == "push":
                result = await self._push(working_dir, remote, branch, timeout, env, flags)
            elif command == "add":
                result = await self._add(working_dir, path, timeout, env, flags)
            elif command == "commit":
                result = await self._commit(working_dir, message, timeout, env, flags)
            elif command == "reset":
                result = await self._reset(working_dir, path, timeout, env, flags)
            elif command == "revert":
                result = await self._revert(working_dir, path, timeout, env, flags)
            elif command == "status":
                result = await self._status(working_dir, timeout, env)
            elif command == "log":
                result = await self._log(working_dir, timeout, env, flags)
            elif command == "diff":
                result = await self._diff(working_dir, timeout, env, flags)
            elif command == "show":
                result = await self._show(working_dir, path, timeout, env, flags)
            elif command == "blame":
                result = await self._blame(working_dir, path, timeout, env, flags)
            elif command == "stash":
                result = await self._stash(working_dir, timeout, env, flags)
            elif command == "stash_pop":
                result = await self._stash_pop(working_dir, timeout, env, flags)
            else:
                result = await self._execute_git_command(
                    ["git", command] + flags, working_dir, timeout, env
                )

            execution_time = time.time() - start_time
            if hasattr(result, "execution_time"):
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
                "repository_info": self._parse_repo_info(result, command)
                if repository or command in ["init", "clone"]
                else None,
            }

        except Exception as e:
            logger.error(f"Git skill execution failed: {e}")
            return {
                "result": {
                    "success": False,
                    "stdout": "",
                    "stderr": str(e),
                    "returncode": -1,
                    "command": command,
                    "working_dir": working_dir,
                    "error": str(e),
                },
                "repository_info": None,
            }

    async def _clone(
        self,
        repository: str,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """克隆仓库"""
        if not repository:
            raise ValueError("repository URL is required for clone")

        cmd = ["git", "clone"]
        cmd.extend(flags)
        cmd.append(repository)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _init(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """初始化仓库"""
        cmd = ["git", "init"]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _remote(
        self,
        working_dir: str,
        repository: str | None,
        timeout: int,
        env: dict[str, str],
    ):
        """远程操作"""
        cmd = ["git", "remote"]
        if repository:
            cmd.extend(["add", "origin", repository])
        else:
            cmd.append("-v")

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _branch(
        self,
        working_dir: str,
        branch: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """分支操作"""
        cmd = ["git", "branch"]
        if branch:
            cmd.append(branch)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _checkout(
        self,
        working_dir: str,
        branch: str | None,
        path: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """检出分支或文件"""
        cmd = ["git", "checkout"]
        if branch:
            cmd.append(branch)
        if path:
            cmd.append(path)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _switch(
        self,
        working_dir: str,
        branch: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """切换分支"""
        cmd = ["git", "switch"]
        if branch:
            cmd.append(branch)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _merge(
        self,
        working_dir: str,
        branch: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """合并分支"""
        cmd = ["git", "merge"]
        if branch:
            cmd.append(branch)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _fetch(
        self,
        working_dir: str,
        remote: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """获取"""
        cmd = ["git", "fetch", remote]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _pull(
        self,
        working_dir: str,
        remote: str,
        branch: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """拉取"""
        cmd = ["git", "pull"]
        cmd.append(remote)
        if branch:
            cmd.append(branch)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _push(
        self,
        working_dir: str,
        remote: str,
        branch: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """推送"""
        cmd = ["git", "push"]
        cmd.append(remote)
        if branch:
            cmd.extend(["-u", branch])
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _add(
        self,
        working_dir: str,
        path: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """暂存"""
        cmd = ["git", "add"]
        cmd.append(path or ".")
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _commit(
        self,
        working_dir: str,
        message: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """提交"""
        cmd = ["git", "commit", "-m"]
        cmd.append(message or "Update")
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _reset(
        self,
        working_dir: str,
        path: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """重置"""
        cmd = ["git", "reset"]
        if path:
            cmd.append(path)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _revert(
        self,
        working_dir: str,
        commit: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """回滚"""
        cmd = ["git", "revert"]
        if commit:
            cmd.append(commit)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _status(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ):
        """状态"""
        return await self._execute_git_command(
            ["git", "status", "--short"], working_dir, timeout, env
        )

    async def _log(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """日志"""
        cmd = ["git", "log", "--oneline", "--graph", "-20"]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _diff(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """差异"""
        cmd = ["git", "diff"]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _show(
        self,
        working_dir: str,
        ref: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """显示"""
        cmd = ["git", "show"]
        if ref:
            cmd.append(ref)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _blame(
        self,
        working_dir: str,
        path: str | None,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """追责"""
        cmd = ["git", "blame"]
        if path:
            cmd.append(path)
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _stash(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """储藏"""
        cmd = ["git", "stash"]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _stash_pop(
        self,
        working_dir: str,
        timeout: int,
        env: dict[str, str],
        flags: list[str],
    ):
        """恢复储藏"""
        cmd = ["git", "stash", "pop"]
        cmd.extend(flags)

        return await self._execute_git_command(cmd, working_dir, timeout, env)

    async def _execute_git_command(
        self,
        cmd: list[str],
        working_dir: str,
        timeout: int,
        env: dict[str, str],
    ):
        """执行 Git 命令"""
        git_path = shutil.which("git")
        if not git_path:
            raise RuntimeError("git not found in PATH")

        cwd = os.path.abspath(os.path.expanduser(working_dir))

        full_env = os.environ.copy()
        full_env.update(env)

        logger.info(f"Executing: {' '.join(cmd)} in {cwd}")

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
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

            return GitExecutionResult(
                success=process.returncode == 0,
                stdout=stdout_str,
                stderr=stderr_str,
                returncode=process.returncode or 0,
                command=" ".join(cmd),
                working_dir=cwd,
                execution_time=0,
            )

        except Exception as e:
            logger.error(f"Git command execution failed: {e}")
            return GitExecutionResult(
                success=False,
                stdout="",
                stderr=str(e),
                returncode=-1,
                command=" ".join(cmd),
                working_dir=cwd,
                execution_time=0,
            )

    def _parse_repo_info(self, result, command: str) -> dict[str, Any] | None:
        """解析仓库信息"""
        if command in ["init", "clone"] and result.success:
            return {
                "command": command,
                "path": result.working_dir,
            }
        return None


class GitExecutionResult:
    """Git 命令执行结果"""

    def __init__(
        self,
        success: bool,
        stdout: str,
        stderr: str,
        returncode: int,
        command: str,
        working_dir: str,
        execution_time: float,
    ):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.command = command
        self.working_dir = working_dir
        self.execution_time = execution_time


git_command_skill = GitCommandSkill()
