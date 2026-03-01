// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title GovernanceDelegationLib
 * @notice 治理委托功能库（减少主合约大小）
 * @dev 修复#1: 提取委托逻辑到库合约以减小VIBGovernance大小
 */
library GovernanceDelegationLib {
    // ========== 事件 ==========

    event Delegated(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 expiryTime
    );

    event Undelegated(
        address indexed from,
        address indexed to,
        uint256 amount
    );

    event DelegationExpired(
        address indexed from,
        address indexed to
    );

    // ========== 常量 ==========

    uint256 public constant MAX_DELEGATION_DURATION = 90 days;
    uint256 public constant MAX_DELEGATION_ACCEPT_RATIO = 500; // 5%
    uint256 public constant LARGE_VOTE_CHANGE_DELAY = 7 days;
    uint256 public constant LARGE_VOTE_CHANGE_THRESHOLD = 100; // 1%
    uint256 public constant MAX_CONSECUTIVE_ABSTENTIONS = 3;
    uint256 public constant DELEGATION_RECOVERY_DELAY = 7 days;

    // ========== 结构体 ==========

    struct DelegationStorage {
        mapping(address => address) delegates;
        mapping(address => uint256) delegatedVotes;
        mapping(address => uint256) delegatedOut;
        mapping(address => uint256) delegationStartTime;
        mapping(address => uint256) delegationExpiryTime;
        mapping(address => uint256) receivedDelegationCount;
        mapping(address => address[]) delegationSources;
        mapping(address => mapping(address => bool)) isDelegationSource;
        uint256 totalDelegatedVotes;
        mapping(address => uint256) consecutiveAbstentions;
        mapping(address => uint256) delegationRecoveryRequestTime;
        mapping(address => bool) pendingRecovery;
        address[] activeDelegatees;
        mapping(address => bool) isActiveDelegatee;
    }

    struct PendingDelegation {
        address from;
        address to;
        uint256 amount;
        uint256 effectiveTime;
        bool isActive;
    }

    // ========== 核心函数 ==========

    /**
     * @notice 清除过期委托
     * @param ds 委托存储
     * @param user 用户地址
     */
    function clearDelegation(DelegationStorage storage ds, address user) internal {
        if (ds.delegates[user] != address(0) && block.timestamp >= ds.delegationExpiryTime[user]) {
                address delegateAddr = ds.delegates[user];
                uint256 amount = ds.delegatedOut[user];

                ds.delegates[user] = address(0);
                ds.delegatedVotes[delegateAddr] -= amount;
                ds.delegatedOut[user] = 0;
                ds.delegationStartTime[user] = 0;
                ds.delegationExpiryTime[user] = 0;
                ds.totalDelegatedVotes -= amount;

                ds.isDelegationSource[delegateAddr][user] = false;
                ds.receivedDelegationCount[delegateAddr]--;

                emit DelegationExpired(user, delegateAddr);
            }
    }

    /**
     * @notice 执行委托
     * @param ds 委托存储
     * @param from 委托人
     * @param to 受托人
     * @param amount 委托数量
     * @param duration 委托时长
     */
    function executeDelegation(
        DelegationStorage storage ds,
        address from,
        address to,
        uint256 amount,
        uint256 duration
    ) internal {
        ds.delegates[from] = to;
        ds.delegatedVotes[to] += amount;
        ds.delegatedOut[from] = amount;
        ds.delegationStartTime[from] = block.timestamp;
        ds.delegationExpiryTime[from] = block.timestamp + duration;
        ds.totalDelegatedVotes += amount;

        if (!ds.isDelegationSource[to][from]) {
            ds.delegationSources[to].push(from);
            ds.isDelegationSource[to][from] = true;
            ds.receivedDelegationCount[to]++;
        }

        if (!ds.isActiveDelegatee[to]) {
            ds.activeDelegatees.push(to);
            ds.isActiveDelegatee[to] = true;
        }

        emit Delegated(from, to, amount, block.timestamp + duration);
    }

    /**
     * @notice 取消委托
     * @param ds 委托存储
     * @param from 委托人
     */
    function undelegate(DelegationStorage storage ds, address from) internal {
        address delegateAddr = ds.delegates[from];
        require(delegateAddr != address(0), "VIBGovernance: not delegated");

        uint256 amount = ds.delegatedOut[from];

        ds.delegates[from] = address(0);
        ds.delegatedVotes[delegateAddr] -= amount;
        ds.delegatedOut[from] = 0;
        ds.delegationStartTime[from] = 0;
        ds.delegationExpiryTime[from] = 0;
        ds.totalDelegatedVotes -= amount;

        ds.isDelegationSource[delegateAddr][from] = false;
        ds.receivedDelegationCount[delegateAddr]--;

        emit Undelegated(from, delegateAddr, amount);
    }

    /**
     * @notice 检查委托是否有效
     * @param ds 委托存储
     * @param user 用户地址
     * @return 是否有效
     */
    function isDelegationValid(DelegationStorage storage ds, address user) internal view returns (bool) {
        if (ds.delegates[user] == address(0)) return false;
        return block.timestamp < ds.delegationExpiryTime[user];
    }

    /**
     * @notice 获取委托信息
     * @param ds 委托存储
     * @param user 用户地址
     */
    function getDelegationInfo(DelegationStorage storage ds, address user)
        internal
        view
        returns (
            address delegateAddr,
            uint256 delegatedOutAmount,
            uint256 delegatedInAmount,
            uint256 expiryTime
        )
    {
        delegateAddr = ds.delegates[user];
        delegatedOutAmount = ds.delegatedOut[user];
        delegatedInAmount = ds.delegatedVotes[user];
        expiryTime = ds.delegationExpiryTime[user];
    }

    /**
     * @notice 检查是否可以委托
     * @param ds 委托存储
     * @param to 目标地址
     * @param amount 委托数量
     * @param totalVotingPower 总投票权
     * @param minTotalForLimit 最小限制阈值
     */
    function canDelegate(
        DelegationStorage storage ds,
        address to,
        uint256 amount,
        uint256 totalVotingPower,
        uint256 minTotalForLimit
    ) internal view returns (bool) {
        if (to == address(0)) return false;
        if (ds.delegates[to] != address(0)) return false; // 目标已委托给别人

        uint256 newDelegatedVotes = ds.delegatedVotes[to] + amount;
        uint256 maxAllowed = (totalVotingPower * MAX_DELEGATION_ACCEPT_RATIO) / 10000;

        if (totalVotingPower == 0 || totalVotingPower < minTotalForLimit) {
            maxAllowed = amount;
        }

        return newDelegatedVotes <= maxAllowed;
    }

    /**
     * @notice 记录弃权
     * @param ds 委托存储
     * @param delegatee 受托人
     */
    function recordAbstention(DelegationStorage storage ds, address delegatee) internal {
        ds.consecutiveAbstentions[delegatee]++;
    }

    /**
     * @notice 重置弃权计数
     * @param ds 委托存储
     * @param delegatee 受托人
     */
    function resetAbstention(DelegationStorage storage ds, address delegatee) internal {
        if (ds.consecutiveAbstentions[delegatee] > 0) {
            ds.consecutiveAbstentions[delegatee] = 0;
        }
    }
}
