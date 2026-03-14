"""
区块链事件监听器

监听 USMSB 生态系统中的智能合约事件，包括：
- VIBEToken: Transfer, Approval
- AgentWallet: Deposited, TransferExecuted, TransferRequested, TransferApproved
- AgentRegistry: AgentRegistered, AgentUnregistered
- VIBStaking: Staked, Unstaked, RewardClaimed
- VIBDividend: DividendClaimed
- VIBGovernance: ProposalCreated, VoteCast
"""

import asyncio
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from web3 import Web3
from web3.contract import Contract

from .config import BlockchainConfig

logger = logging.getLogger(__name__)


@dataclass
class EventFilter:
    """事件过滤器配置"""
    contract_name: str
    event_name: str
    from_block: int | None = None
    to_block: str | None = "latest"
    address: str | None = None
    argument_filters: dict[str, Any] | None = None


@dataclass
class ParsedEvent:
    """解析后的事件数据"""
    contract_name: str
    event_name: str
    event: Any
    block_number: int
    transaction_hash: str
    args: dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class BlockchainEventListener:
    """区块链事件监听器

    支持轮询方式和订阅方式监听区块链事件
    自动处理断线重连和错误恢复
    """

    # 事件参数定义 (用于快速解析)
    EVENT_SIGNATURES = {
        "VIBEToken": {
            "Transfer": {"from": "address", "to": "address", "value": "uint256"},
            "Approval": {"owner": "address", "spender": "address", "value": "uint256"},
        },
        "AgentWallet": {
            "Deposited": {"from": "address", "amount": "uint256"},
            "TransferExecuted": {"to": "address", "amount": "uint256", "from": "address"},
            "TransferRequested": {
                "requestId": "bytes32",
                "to": "address",
                "amount": "uint256",
                "requester": "address"
            },
            "TransferApproved": {"requestId": "bytes32", "approver": "address"},
            "TransferRejected": {"requestId": "bytes32", "rejector": "address"},
            "TransferCompleted": {"requestId": "bytes32"},
        },
        "AgentRegistry": {
            "AgentRegistered": {"agentWallet": "address", "owner": "address"},
            "AgentUnregistered": {"agentWallet": "address"},
        },
        "VIBStaking": {
            "Staked": {
                "user": "address",
                "amount": "uint256",
                "tier": "uint8",
                "lockPeriod": "uint8",
                "unlockTime": "uint256"
            },
            "Unstaked": {"user": "address", "amount": "uint256"},
            "RewardClaimed": {"user": "address", "amount": "uint256"},
            "EmergencyWithdraw": {"user": "address", "amount": "uint256"},
        },
        "VIBDividend": {
            "DividendClaimed": {"user": "address", "amount": "uint256"},
            "DividendDeposited": {
                "from": "address",
                "amount": "uint256",
                "dividendPerToken": "uint256",
            },
        },
        "VIBGovernance": {
            "ProposalCreated": {
                "id": "uint256",
                "proposer": "address",
                "proposalType": "uint8",
                "title": "string"
            },
            "VoteCast": {
                "proposalId": "uint256",
                "voter": "address",
                "forVotes": "uint256",
                "againstVotes": "uint256",
                "abstainVotes": "uint256"
            },
            "ProposalExecuted": {"id": "uint256", "executor": "address"},
            "ProposalCancelled": {"id": "uint256", "canceller": "address"},
        },
    }

    def __init__(self, config: BlockchainConfig, contracts: dict[str, Contract]):
        """
        初始化事件监听器

        Args:
            config: BlockchainConfig 实例
            contracts: 合约名称到合约实例的映射
        """
        self.config = config
        self.contracts = contracts
        self.web3 = Web3(Web3.HTTPProvider(config.rpc_url))

        # 事件处理器注册表 {contract.event: [handlers]}
        self.handlers: dict[str, list[Callable]] = {}

        # 运行状态
        self.running = False
        self.listen_task: asyncio.Task | None = None

        # 同步状态
        self.last_block = self.web3.eth.block_number
        self.start_block = self.last_block

        # 配置
        self.poll_interval: int = 5
        self.batch_size: int = 1000  # 每次查询的最大区块数
        self.max_retries: int = 3
        self.retry_delay: int = 5

        # 事件缓存
        self.event_cache: list[ParsedEvent] = []
        self.cache_max_size: int = 10000

        # 统计
        self.stats = {
            "total_events": 0,
            "processed_events": 0,
            "errors": 0,
            "last_block_processed": self.last_block,
        }

        logger.info(f"EventListener initialized, current block: {self.last_block}")

    def register_handler(
        self,
        contract_name: str,
        event_name: str,
        handler: Callable[[ParsedEvent], Any]
    ):
        """
        注册事件处理器

        Args:
            contract_name: 合约名称 (如 "VIBEToken")
            event_name: 事件名称 (如 "Transfer")
            handler: 事件处理函数，接收 ParsedEvent 对象
        """
        key = f"{contract_name}.{event_name}"
        if key not in self.handlers:
            self.handlers[key] = []
        self.handlers[key].append(handler)
        logger.debug(f"Registered handler for {key}")

    def unregister_handler(
        self,
        contract_name: str,
        event_name: str,
        handler: Callable[[ParsedEvent], Any]
    ):
        """
        取消注册事件处理器

        Args:
            contract_name: 合约名称
            event_name: 事件名称
            handler: 事件处理函数
        """
        key = f"{contract_name}.{event_name}"
        if key in self.handlers:
            try:
                self.handlers[key].remove(handler)
                if not self.handlers[key]:
                    del self.handlers[key]
                logger.debug(f"Unregistered handler for {key}")
            except ValueError:
                logger.warning(f"Handler not found for {key}")

    async def start(self, poll_interval: int | None = None):
        """
        启动事件监听

        Args:
            poll_interval: 轮询间隔（秒），默认使用配置值
        """
        if self.running:
            logger.warning("EventListener is already running")
            return

        if poll_interval is not None:
            self.poll_interval = poll_interval

        self.running = True
        self.listen_task = asyncio.create_task(self._listen_loop())
        logger.info(f"EventListener started, polling every {self.poll_interval}s")

    async def stop(self):
        """停止事件监听"""
        if not self.running:
            return

        self.running = False
        if self.listen_task:
            self.listen_task.cancel()
            try:
                await self.listen_task
            except asyncio.CancelledError:
                pass

        logger.info("EventListener stopped")
        logger.info(f"Stats: {self.stats}")

    async def _listen_loop(self):
        """监听主循环"""
        consecutive_errors = 0

        while self.running:
            try:
                current_block = self.web3.eth.block_number

                if current_block > self.last_block:
                    # 处理新区块
                    await self._process_blocks(self.last_block + 1, current_block)
                    self.last_block = current_block
                    consecutive_errors = 0

                await asyncio.sleep(self.poll_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                consecutive_errors += 1
                self.stats["errors"] += 1
                logger.error(f"Event listener error: {e}")

                if consecutive_errors >= self.max_retries:
                    logger.error("Max retries reached, waiting longer before retry")
                    await asyncio.sleep(self.retry_delay * 2)
                else:
                    await asyncio.sleep(self.retry_delay * consecutive_errors)

    async def _process_blocks(self, from_block: int, to_block: int):
        """
        处理区块范围内的所有事件

        Args:
            from_block: 起始区块号
            to_block: 结束区块号
        """
        logger.debug(f"Processing blocks {from_block} to {to_block}")

        # 分批处理
        batch_from = from_block
        while batch_from <= to_block and self.running:
            batch_to = min(batch_from + self.batch_size - 1, to_block)

            try:
                # 并行处理各类合约事件
                await asyncio.gather(
                    self._process_token_events(batch_from, batch_to),
                    self._process_wallet_events(batch_from, batch_to),
                    self._process_registry_events(batch_from, batch_to),
                    self._process_staking_events(batch_from, batch_to),
                    self._process_dividend_events(batch_from, batch_to),
                    self._process_governance_events(batch_from, batch_to),
                )

                batch_from = batch_to + 1
                self.stats["last_block_processed"] = batch_to

            except Exception as e:
                logger.error(f"Error processing blocks {batch_from}-{batch_to}: {e}")
                break

        logger.debug(
            f"Finished processing blocks {from_block}-{to_block}, "
            f"{self.stats['processed_events'] - self.stats['total_events']} new events"
        )
        self.stats["total_events"] = self.stats["processed_events"]

    async def _process_token_events(self, from_block: int, to_block: int):
        """处理 VIBEToken 事件"""
        if "VIBEToken" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "VIBEToken",
            ["Transfer", "Approval"],
            from_block,
            to_block
        )

    async def _process_wallet_events(self, from_block: int, to_block: int):
        """处理 AgentWallet 事件"""
        if "AgentWallet" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "AgentWallet",
            [
                "Deposited",
                "TransferExecuted",
                "TransferRequested",
                "TransferApproved",
                "TransferRejected",
                "TransferCompleted",
            ],
            from_block,
            to_block
        )

    async def _process_registry_events(self, from_block: int, to_block: int):
        """处理 AgentRegistry 事件"""
        if "AgentRegistry" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "AgentRegistry",
            ["AgentRegistered", "AgentUnregistered"],
            from_block,
            to_block
        )

    async def _process_staking_events(self, from_block: int, to_block: int):
        """处理 VIBStaking 事件"""
        if "VIBStaking" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "VIBStaking",
            ["Staked", "Unstaked", "RewardClaimed", "EmergencyWithdraw"],
            from_block,
            to_block
        )

    async def _process_dividend_events(self, from_block: int, to_block: int):
        """处理 VIBDividend 事件"""
        if "VIBDividend" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "VIBDividend",
            ["DividendClaimed", "DividendDeposited"],
            from_block,
            to_block
        )

    async def _process_governance_events(self, from_block: int, to_block: int):
        """处理 VIBGovernance 事件"""
        if "VIBGovernance" not in self.contracts:
            return

        await self._fetch_and_dispatch(
            "VIBGovernance",
            ["ProposalCreated", "VoteCast", "ProposalExecuted", "ProposalCancelled"],
            from_block,
            to_block
        )

    async def _fetch_and_dispatch(
        self,
        contract_name: str,
        event_names: list[str],
        from_block: int,
        to_block: int
    ):
        """
        获取并分发事件

        Args:
            contract_name: 合约名称
            event_names: 事件名称列表
            from_block: 起始区块
            to_block: 结束区块
        """
        contract = self.contracts.get(contract_name)
        if contract is None:
            return

        for event_name in event_names:
            event_key = f"{contract_name}.{event_name}"
            if event_key not in self.handlers:
                continue

            try:
                # 获取事件日志
                event_filter = getattr(contract.events, event_name)
                logs = event_filter.get_logs(
                    fromBlock=from_block,
                    toBlock=to_block
                )

                # 处理每条日志
                for log in logs:
                    await self._dispatch_event(contract_name, event_name, log)

            except AttributeError:
                logger.warning(f"Event {event_name} not found in {contract_name}")
            except Exception as e:
                logger.error(f"Error fetching {event_key}: {e}")

    async def _dispatch_event(
        self,
        contract_name: str,
        event_name: str,
        event
    ):
        """
        分发事件到处理器

        Args:
            contract_name: 合约名称
            event_name: 事件名称
            event: web3 事件对象
        """
        # 解析事件
        parsed = self._parse_event(contract_name, event_name, event)
        if parsed is None:
            return

        # 添加到缓存
        self.event_cache.append(parsed)
        if len(self.event_cache) > self.cache_max_size:
            self.event_cache = self.event_cache[-self.cache_max_size // 2:]

        # 分发到处理器
        event_key = f"{contract_name}.{event_name}"
        handlers = self.handlers.get(event_key, [])

        for handler in handlers:
            try:
                # 支持同步和异步处理器
                result = handler(parsed)
                if asyncio.iscoroutine(result):
                    await result
                self.stats["processed_events"] += 1
            except Exception as e:
                logger.error(f"Handler error for {event_key}: {e}")

    def _parse_event(
        self,
        contract_name: str,
        event_name: str,
        event
    ) -> ParsedEvent | None:
        """
        解析事件数据

        Args:
            contract_name: 合约名称
            event_name: 事件名称
            event: web3 事件对象

        Returns:
            ParsedEvent 对象，如果解析失败返回 None
        """
        try:
            args = {}
            if hasattr(event, 'args') and event.args:
                # 转换 args 为字典，处理大小写问题
                args = dict(event.args)

                # 转换地址为小写
                for key, value in args.items():
                    if isinstance(value, bytes) and len(value) == 20:
                        args[key] = Web3.to_checksum_address('0x' + value.hex())
                    elif isinstance(value, str) and value.startswith('0x'):
                        try:
                            args[key] = Web3.to_checksum_address(value)
                        except Exception:
                            pass

            return ParsedEvent(
                contract_name=contract_name,
                event_name=event_name,
                event=event,
                block_number=event.get('blockNumber', 0),
                transaction_hash=event.get('transactionHash', b'').hex(),
                args=args,
            )

        except Exception as e:
            logger.error(f"Error parsing event {contract_name}.{event_name}: {e}")
            return None

    async def get_events(
        self,
        contract_name: str,
        event_name: str,
        from_block: int | None = None,
        to_block: str | None = "latest"
    ) -> list[ParsedEvent]:
        """
        获取历史事件

        Args:
            contract_name: 合约名称
            event_name: 事件名称
            from_block: 起始区块
            to_block: 结束区块

        Returns:
            ParsedEvent 列表
        """
        contract = self.contracts.get(contract_name)
        if contract is None:
            raise ValueError(f"Contract {contract_name} not found")

        event_filter = getattr(contract.events, event_name, None)
        if event_filter is None:
            raise ValueError(f"Event {event_name} not found in {contract_name}")

        logs = event_filter.get_logs(fromBlock=from_block, toBlock=to_block)
        return [
            self._parse_event(contract_name, event_name, log)
            for log in logs
            if self._parse_event(contract_name, event_name, log) is not None
        ]

    def get_cached_events(
        self,
        contract_name: str | None = None,
        event_name: str | None = None,
        limit: int | None = None
    ) -> list[ParsedEvent]:
        """
        从缓存获取事件

        Args:
            contract_name: 合约名称过滤
            event_name: 事件名称过滤
            limit: 返回数量限制

        Returns:
            ParsedEvent 列表
        """
        events = self.event_cache

        if contract_name is not None:
            events = [e for e in events if e.contract_name == contract_name]

        if event_name is not None:
            events = [e for e in events if e.event_name == event_name]

        if limit is not None:
            events = events[-limit:]

        return events

    def get_stats(self) -> dict[str, Any]:
        """获取监听器统计信息"""
        return {
            **self.stats,
            "running": self.running,
            "last_block": self.last_block,
            "current_block": self.web3.eth.block_number,
            "handlers_count": sum(len(h) for h in self.handlers.values()),
            "handlers": list(self.handlers.keys()),
        }

    def clear_cache(self):
        """清空事件缓存"""
        self.event_cache.clear()
        logger.info("Event cache cleared")


def create_event_listener(
    config: BlockchainConfig,
    contract_map: dict[str, tuple[str, Any]]
) -> BlockchainEventListener:
    """
    创建事件监听器的便捷函数

    Args:
        config: BlockchainConfig 实例
        contract_map: 合约映射 {name: (address, abi)}

    Returns:
        BlockchainEventListener 实例

    Example:
        listener = create_event_listener(
            config,
            {
                "VIBEToken": (token_address, token_abi),
                "AgentRegistry": (registry_address, registry_abi),
            }
        )
    """
    web3 = Web3(Web3.HTTPProvider(config.rpc_url))
    contracts = {}

    for name, (address, abi) in contract_map.items():
        if address and abi:
            contracts[name] = web3.eth.contract(
                address=Web3.to_checksum_address(address),
                abi=abi
            )
            logger.info(f"Loaded contract {name} at {address}")

    return BlockchainEventListener(config, contracts)


class EventFilterBuilder:
    """事件过滤器构建器"""

    def __init__(self, contract_name: str, event_name: str):
        self.contract_name = contract_name
        self.event_name = event_name
        self._from_block: int | None = None
        self._to_block: str | None = "latest"
        self._address: str | None = None
        self._argument_filters: dict[str, Any] | None = None

    def from_block(self, block: int) -> 'EventFilterBuilder':
        """设置起始区块"""
        self._from_block = block
        return self

    def to_block(self, block: int) -> 'EventFilterBuilder':
        """设置结束区块"""
        self._to_block = block
        return self

    def filter_address(self, addr: str) -> 'EventFilterBuilder':
        """设置地址过滤"""
        self._address = addr
        return self

    def filter_args(self, **kwargs) -> 'EventFilterBuilder':
        """设置参数过滤"""
        if self._argument_filters is None:
            self._argument_filters = {}
        self._argument_filters.update(kwargs)
        return self

    def build(self) -> EventFilter:
        """构建过滤器"""
        return EventFilter(
            contract_name=self.contract_name,
            event_name=self.event_name,
            from_block=self._from_block,
            to_block=self._to_block,
            address=self._address,
            argument_filters=self._argument_filters,
        )


# 便捷函数定义
def filter_events(
    contract_name: str,
    event_name: str
) -> EventFilterBuilder:
    """
    创建事件过滤器

    Args:
        contract_name: 合约名称
        event_name: 事件名称

    Returns:
        EventFilterBuilder 实例

    Example:
        builder = filter_events("VIBEToken", "Transfer")
        builder.filter(from_address="0x...").from_block(1000000)
        event_filter = builder.build()
    """
    return EventFilterBuilder(contract_name, event_name)


# 类型提示辅助
EventCallback = Callable[[ParsedEvent], Any]
AsyncEventCallback = Callable[[ParsedEvent], Any]  # 可以是协程函数


class TypedEventListener(BlockchainEventListener):
    """类型安全的事件监听器"""

    def register(
        self,
        contract_name: str,
        event_name: str,
        handler: EventCallback
    ):
        """类型安全的事件注册"""
        # 验证事件是否存在于签名中
        if contract_name in self.EVENT_SIGNATURES:
            if event_name not in self.EVENT_SIGNATURES[contract_name]:
                logger.warning(f"Event {event_name} not in known signatures for {contract_name}")

        self.register_handler(contract_name, event_name, handler)

    async def subscribe(
        self,
        filters: list[EventFilter],
        handler: EventCallback
    ):
        """
        批量订阅事件

        Args:
            filters: 事件过滤器列表
            handler: 统一处理器
        """
        for event_filter in filters:
            key = f"{event_filter.contract_name}.{event_filter.event_name}"
            self.handlers[key] = [handler]
