"""
VIBGovernance 治理合约客户端

实现 VIBE 治理合约的 Python 客户端，支持：
- 获取投票权
- 创建提案
- 投票
- 结算提案
- 执行提案
- 获取提案详情
- 检查提案是否通过
"""

from enum import IntEnum
from typing import Optional, Dict, Any, Union, List, Tuple

from .base import BaseContractClient, TransactionError, ContractError
from ..config import BlockchainConfig
from ..web3_client import Web3Client


class ProposalType(IntEnum):
    """提案类型枚举"""
    GENERAL = 0  # 一般提案
    PARAMETER = 1  # 参数提案
    UPGRADE = 2  # 升级提案
    EMERGENCY = 3  # 紧急提案
    DIVIDEND = 4  # 分红提案
    INCENTIVE = 5  # 激励提案


class ProposalState(IntEnum):
    """提案状态枚举"""
    PENDING = 0  # 待处理
    ACTIVE = 1  # 活跃投票中
    CANCELLED = 2  # 已取消
    DEFEATED = 3  # 已失败
    SUCCEEDED = 4  # 已通过
    EXECUTED = 5  # 已执行
    EXPIRED = 6  # 已过期


class VetoType(IntEnum):
    """否决类型枚举"""
    INVESTOR_VETO = 0  # 投资者否决
    PRODUCER_VETO = 1  # 生产者否决
    COMMUNITY_VETO = 2  # 社区否决


class VIBGovernanceClient(BaseContractClient):
    """VIBE 治理合约客户端

    实现白皮书承诺的治理机制：
    - 多维度投票权（资金权重 + 生产权重 + 社区权重）
    - 多类型提案（一般、参数、升级、紧急、分红、激励）
    - 否决机制（投资者、生产者、社区）
    - 时间锁（根据提案类型不同）
    - 信誉签名验证
    """

    # 合约常量
    MIN_STAKE_REQUIREMENT = 100 * 10**18
    MIN_TOTAL_FOR_CAPS = 1000 * 10**18
    CAPITAL_WEIGHT_MAX = 10  # 资金权重上限 10%
    PRODUCTION_WEIGHT_MAX = 15  # 生产权重上限 15%
    COMMUNITY_WEIGHT_RATIO = 10  # 社区权重比例 10%

    # 通过率（基点）
    GENERAL_PASS_RATE = 5000  # 50%
    PARAMETER_PASS_RATE = 6000  # 60%
    UPGRADE_PASS_RATE = 7500  # 75%
    EMERGENCY_PASS_RATE = 9000  # 90%
    DIVIDEND_PASS_RATE = 6700  # 67%
    INCENTIVE_PASS_RATE = 6700  # 67%

    # 时间锁
    GENERAL_TIMELOCK = 14 * 86400  # 14天
    PARAMETER_TIMELOCK = 30 * 86400  # 30天
    UPGRADE_TIMELOCK = 60 * 86400  # 60天
    DIVIDEND_INCENTIVE_TIMELOCK = 30 * 86400  # 30天
    EMERGENCY_TIMELOCK = 1 * 86400  # 1天

    # 提案期限
    GENERAL_DURATION = 7 * 86400  # 7天
    PARAMETER_DURATION = 14 * 86400  # 14天
    UPGRADE_DURATION = 21 * 86400  # 21天
    DIVIDEND_INCENTIVE_DURATION = 14 * 86400  # 14天
    EMERGENCY_DURATION = 3 * 86400  # 3天

    # 提案阈值
    GENERAL_THRESHOLD = 500 * 10**18
    PARAMETER_THRESHOLD = 5000 * 10**18
    UPGRADE_THRESHOLD = 50000 * 10**18
    EMERGENCY_THRESHOLD = 1000 * 10**18
    DIVIDEND_THRESHOLD = 5000 * 10**18
    INCENTIVE_THRESHOLD = 5000 * 10**18

    def __init__(
        self,
        web3_client: Optional[Web3Client] = None,
        config: Optional[BlockchainConfig] = None,
        contract_address: Optional[str] = None,
        abi: Optional[Union[List[Dict], str]] = None,
    ):
        """
        初始化 VIBGovernance 客户端

        Args:
            web3_client: Web3 客户端实例
            config: 区块链配置
            contract_address: 合约地址（如不指定则从配置中获取）
            abi: 合约 ABI（如不指定则使用内置 ABI）
        """
        super().__init__(web3_client, config)

        # 获取合约地址
        if contract_address is None:
            contract_address = self.config.get_contract_address("VIBGovernance")
            if contract_address is None or contract_address == "待部署":
                raise ContractError("VIBGovernance contract not deployed or configured")

        # 使用内置 ABI（简化版本）
        if abi is None:
            abi = self._get_default_abi()

        self.set_contract(contract_address, abi)

    def _get_default_abi(self) -> List[Dict]:
        """获取默认 ABI"""
        return [
            # 只读函数
            {
                "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
                "name": "getVotingPower",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "getProposal",
                "outputs": [
                    {
                        "components": [
                            {"internalType": "uint256", "name": "id", "type": "uint256"},
                            {"internalType": "address", "name": "proposer", "type": "address"},
                            {"internalType": "enum VIBGovernance.ProposalType", "name": "proposalType", "type": "uint8"},
                            {"internalType": "enum VIBGovernance.ProposalState", "name": "state", "type": "uint8"},
                            {"internalType": "string", "name": "title", "type": "string"},
                            {"internalType": "string", "name": "description", "type": "string"},
                            {"internalType": "address", "name": "target", "type": "address"},
                            {"internalType": "bytes", "name": "data", "type": "bytes"},
                            {"internalType": "uint256", "name": "startTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "endTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "executeTime", "type": "uint256"},
                            {"internalType": "uint256", "name": "forVotes", "type": "uint256"},
                            {"internalType": "uint256", "name": "againstVotes", "type": "uint256"},
                            {"internalType": "uint256", "name": "abstainVotes", "type": "uint256"},
                            {"internalType": "uint256", "name": "totalVoters", "type": "uint256"},
                            {"internalType": "bool", "name": "executed", "type": "bool"},
                        ],
                        "internalType": "struct VIBGovernance.Proposal",
                        "name": "",
                        "type": "tuple",
                    }
                ],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "getState",
                "outputs": [{"internalType": "enum VIBGovernance.ProposalState", "name": "", "type": "uint8"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "checkProposalPassed",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "hasVotedOnProposal",
                "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
                "stateMutability": "view",
                "type": "function",
            },
            {
                "inputs": [],
                "name": "getProposalCount",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "view",
                "type": "function",
            },
            # 写入函数
            {
                "inputs": [
                    {"internalType": "enum VIBGovernance.ProposalType", "name": "proposalType", "type": "uint8"},
                    {"internalType": "string", "name": "title", "type": "string"},
                    {"internalType": "string", "name": "description", "type": "string"},
                    {"internalType": "address", "name": "target", "type": "address"},
                    {"internalType": "bytes", "name": "data", "type": "bytes"},
                ],
                "name": "createProposal",
                "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [
                    {"internalType": "uint256", "name": "proposalId", "type": "uint256"},
                    {"internalType": "uint8", "name": "support", "type": "uint8"},
                ],
                "name": "castVote",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "finalizeProposal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "executeProposal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
            {
                "inputs": [{"internalType": "uint256", "name": "proposalId", "type": "uint256"}],
                "name": "cancelProposal",
                "outputs": [],
                "stateMutability": "nonpayable",
                "type": "function",
            },
        ]

    async def get_voting_power(self, user: str) -> int:
        """获取用户投票权

        投票权 = 资金权重 + 生产权重 + 社区权重

        Args:
            user: 用户地址

        Returns:
            投票权数值

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getVotingPower(self.w3.to_checksum_address(user))
            )
            return int(result) if result else 0
        except Exception as e:
            raise ContractError(f"Failed to get voting power: {e}")

    async def create_proposal(
        self,
        proposal_type: ProposalType,
        title: str,
        description: str,
        target: str,
        data: bytes,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> Tuple[int, str]:
        """创建提案

        Args:
            proposal_type: 提案类型
            title: 提案标题
            description: 提案描述
            target: 目标合约地址
            data: 调用数据
            from_address: 提案人地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            (proposal_id, tx_hash) 提案ID和交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 投票权不足
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)
            target = self.w3.to_checksum_address(target)

            # 检查投票权
            voting_power = await self.get_voting_power(from_address)
            threshold = self._get_threshold(proposal_type)
            if voting_power < threshold:
                raise ValueError(
                    f"Insufficient voting power: {voting_power} < {threshold} "
                    f"(required for {proposal_type.name} proposal)"
                )

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.createProposal(
                    int(proposal_type),
                    title,
                    description,
                    target,
                    data,
                ),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)

            # 从交易回执中获取提案ID（如果可能）
            # 对于新提案，ID通常是提案数量 - 1
            receipt = self.wait_for_transaction(tx_hash, timeout=120)

            # 获取当前提案数量
            proposal_count = self.call_contract_function(
                self.contract.functions.getProposalCount()
            )
            proposal_id = int(proposal_count) - 1

            return proposal_id, tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to create proposal: {e}")

    async def cast_vote(
        self,
        proposal_id: int,
        support: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """对提案投票

        Args:
            proposal_id: 提案ID
            support: 投票方向 (0=反对, 1=支持, 2=弃权)
            from_address: 投票人地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
            ValueError: 无效的投票值
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            if support not in [0, 1, 2]:
                raise ValueError("Invalid support value: must be 0 (against), 1 (for), or 2 (abstain)")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查是否已投票
            has_voted = self.call_contract_function(
                self.contract.functions.hasVotedOnProposal(proposal_id)
            )
            if has_voted:
                raise ValueError(f"Address {from_address} has already voted on proposal {proposal_id}")

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.castVote(proposal_id, support),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to cast vote: {e}")

    async def finalize_proposal(
        self,
        proposal_id: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """结算提案

        根据投票结果决定提案是否通过

        Args:
            proposal_id: 提案ID
            from_address: 调用者地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查提案状态
            state = await self.get_state(proposal_id)
            if state != ProposalState.ACTIVE:
                raise ValueError(f"Proposal {proposal_id} is not in ACTIVE state, current state: {state.name}")

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.finalizeProposal(proposal_id),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to finalize proposal: {e}")

    async def execute_proposal(
        self,
        proposal_id: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """执行提案

        执行已通过的提案，调用目标合约

        Args:
            proposal_id: 提案ID
            from_address: 执行者地址
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 检查提案状态
            state = await self.get_state(proposal_id)
            if state != ProposalState.SUCCEEDED:
                raise ValueError(f"Proposal {proposal_id} is not in SUCCEEDED state, current state: {state.name}")

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.executeProposal(proposal_id),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except ValueError:
            raise
        except Exception as e:
            raise TransactionError(f"Failed to execute proposal: {e}")

    async def cancel_proposal(
        self,
        proposal_id: int,
        from_address: str,
        private_key: str,
        gas_limit: Optional[int] = None,
    ) -> str:
        """取消提案

        Args:
            proposal_id: 提案ID
            from_address: 调用者地址（提案人或owner）
            private_key: 私钥
            gas_limit: 可选的 gas 限制

        Returns:
            交易哈希

        Raises:
            TransactionError: 交易失败
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            from_address = self.w3.to_checksum_address(from_address)

            # 构建交易
            tx = self.build_contract_transaction(
                self.contract.functions.cancelProposal(proposal_id),
                from_address=from_address,
                gas=gas_limit,
            )

            # 签名并发送
            tx_hash = self.sign_and_send_transaction(tx, private_key)
            return tx_hash
        except Exception as e:
            raise TransactionError(f"Failed to cancel proposal: {e}")

    async def get_proposal(self, proposal_id: int) -> Dict[str, Any]:
        """获取提案详情

        Args:
            proposal_id: 提案ID

        Returns:
            提案详情字典，包含：
            - id: 提案ID
            - proposer: 提案人地址
            - proposal_type: 提案类型
            - state: 提案状态
            - title: 提案标题
            - description: 提案描述
            - target: 目标合约地址
            - data: 调用数据
            - start_time: 投票开始时间
            - end_time: 投票结束时间
            - execute_time: 可执行时间
            - for_votes: 支持票数
            - against_votes: 反对票数
            - abstain_votes: 弃权票数
            - total_voters: 总投票人数
            - executed: 是否已执行

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getProposal(proposal_id)
            )

            # 解析结构体返回值
            return {
                "id": int(result[0]),
                "proposer": result[1],
                "proposal_type": ProposalType(int(result[2])),
                "state": ProposalState(int(result[3])),
                "title": result[4],
                "description": result[5],
                "target": result[6],
                "data": result[7].hex() if result[7] else "",
                "start_time": int(result[8]),
                "end_time": int(result[9]),
                "execute_time": int(result[10]),
                "for_votes": int(result[11]),
                "against_votes": int(result[12]),
                "abstain_votes": int(result[13]),
                "total_voters": int(result[14]),
                "executed": result[15],
            }
        except Exception as e:
            raise ContractError(f"Failed to get proposal: {e}")

    async def get_state(self, proposal_id: int) -> ProposalState:
        """获取提案状态

        Args:
            proposal_id: 提案ID

        Returns:
            提案状态

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.getState(proposal_id)
            )
            return ProposalState(int(result))
        except Exception as e:
            raise ContractError(f"Failed to get proposal state: {e}")

    async def check_proposal_passed(self, proposal_id: int) -> bool:
        """检查提案是否通过

        Args:
            proposal_id: 提案ID

        Returns:
            是否通过

        Raises:
            ContractError: 合约调用失败
        """
        try:
            if not self.contract:
                raise ContractError("Contract not initialized")

            result = self.call_contract_function(
                self.contract.functions.checkProposalPassed(proposal_id)
            )
            return bool(result)
        except Exception as e:
            raise ContractError(f"Failed to check if proposal passed: {e}")

    def _get_threshold(self, proposal_type: ProposalType) -> int:
        """获取提案阈值

        Args:
            proposal_type: 提案类型

        Returns:
            所需的最小投票权
        """
        thresholds = {
            ProposalType.GENERAL: self.GENERAL_THRESHOLD,
            ProposalType.PARAMETER: self.PARAMETER_THRESHOLD,
            ProposalType.UPGRADE: self.UPGRADE_THRESHOLD,
            ProposalType.EMERGENCY: self.EMERGENCY_THRESHOLD,
            ProposalType.DIVIDEND: self.DIVIDEND_THRESHOLD,
            ProposalType.INCENTIVE: self.INCENTIVE_THRESHOLD,
        }
        return thresholds.get(proposal_type, self.GENERAL_THRESHOLD)

    def get_required_pass_rate(self, proposal_type: ProposalType) -> int:
        """获取提案通过率要求

        Args:
            proposal_type: 提案类型

        Returns:
            通过率（基点）
        """
        rates = {
            ProposalType.GENERAL: self.GENERAL_PASS_RATE,
            ProposalType.PARAMETER: self.PARAMETER_PASS_RATE,
            ProposalType.UPGRADE: self.UPGRADE_PASS_RATE,
            ProposalType.EMERGENCY: self.EMERGENCY_PASS_RATE,
            ProposalType.DIVIDEND: self.DIVIDEND_PASS_RATE,
            ProposalType.INCENTIVE: self.INCENTIVE_PASS_RATE,
        }
        return rates.get(proposal_type, self.GENERAL_PASS_RATE)

    def get_timelock(self, proposal_type: ProposalType) -> int:
        """获取提案时间锁

        Args:
            proposal_type: 提案类型

        Returns:
            时间锁（秒）
        """
        locks = {
            ProposalType.GENERAL: self.GENERAL_TIMELOCK,
            ProposalType.PARAMETER: self.PARAMETER_TIMELOCK,
            ProposalType.UPGRADE: self.UPGRADE_TIMELOCK,
            ProposalType.EMERGENCY: self.EMERGENCY_TIMELOCK,
            ProposalType.DIVIDEND: self.DIVIDEND_INCENTIVE_TIMELOCK,
            ProposalType.INCENTIVE: self.DIVIDEND_INCENTIVE_TIMELOCK,
        }
        return locks.get(proposal_type, self.GENERAL_TIMELOCK)

    def get_duration(self, proposal_type: ProposalType) -> int:
        """获取提案投票期限

        Args:
            proposal_type: 提案类型

        Returns:
            投票期限（秒）
        """
        durations = {
            ProposalType.GENERAL: self.GENERAL_DURATION,
            ProposalType.PARAMETER: self.PARAMETER_DURATION,
            ProposalType.UPGRADE: self.UPGRADE_DURATION,
            ProposalType.EMERGENCY: self.EMERGENCY_DURATION,
            ProposalType.DIVIDEND: self.DIVIDEND_INCENTIVE_DURATION,
            ProposalType.INCENTIVE: self.DIVIDEND_INCENTIVE_DURATION,
        }
        return durations.get(proposal_type, self.GENERAL_DURATION)

    async def get_proposal_summary(self, proposal_id: int) -> Dict[str, Any]:
        """获取提案摘要信息

        Args:
            proposal_id: 提案ID

        Returns:
            提案摘要，包含：
            - proposal: 提案详情
            - state: 提案状态
            - passed: 是否通过
            - can_execute: 是否可以执行
            - voting_power: 当前用户的投票权
            - has_voted: 当前用户是否已投票
        """
        proposal = await self.get_proposal(proposal_id)
        state = await self.get_state(proposal_id)
        passed = await self.check_proposal_passed(proposal_id)

        # 检查是否可以执行
        current_time = int(self.w3.eth.get_block("latest")["timestamp"])
        can_execute = (
            state == ProposalState.SUCCEEDED and
            not proposal["executed"] and
            current_time >= proposal["execute_time"]
        )

        return {
            "proposal": proposal,
            "state": state,
            "passed": passed,
            "can_execute": can_execute,
            "proposal_type_name": ProposalType(proposal["proposal_type"]).name,
            "state_name": state.name,
        }


__all__ = [
    "VIBGovernanceClient",
    "ProposalType",
    "ProposalState",
    "VetoType",
]
