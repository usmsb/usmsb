// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/security/ReentrancyGuardUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/security/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

/**
 * @title VIBGovernanceDelegation
 * @notice 独立的治理委托管理合约
 * @dev 修复#1: 从VIBGovernance提取以减小主合约大小
 */
contract VIBGovernanceDelegation is
    Initializable,
    OwnableUpgradeable,
    UUPSUpgradeable,
    ReentrancyGuardUpgradeable,
    PausableUpgradeable
{
    // ========== 常量 ==========

    uint256 public constant MAX_DELEGATION_DURATION = 90 days;
    uint256 public constant MAX_DELEGATION_ACCEPT_RATIO = 500;
    uint256 public constant LARGE_VOTE_CHANGE_DELAY = 7 days;
    uint256 public constant LARGE_VOTE_CHANGE_THRESHOLD = 100;
    uint256 public constant MIN_TOTAL_FOR_DELEGATION_LIMIT = 1000 * 10**18;
    uint256 public constant MAX_CONSECUTIVE_ABSTENTIONS = 3;
    uint256 public constant DELEGATION_RECOVERY_DELAY = 7 days;

    // ========== 结构体 ==========

    struct PendingDelegation {
        address from;
        address to;
        uint256 amount;
        uint256 effectiveTime;
        bool isActive;
    }

    struct DelegationStats {
        uint256 totalDelegatedVotes;
        uint256 activeDelegateeCount;
        uint256 pendingRecoveryCount;
    }

    // ========== 状态变量 ==========

    mapping(address => address) public delegates;
    mapping(address => uint256) public delegatedVotes;
    mapping(address => uint256) public delegatedOut;
    mapping(address => uint256) public delegationStartTime;
    mapping(address => uint256) public delegationExpiryTime;
    mapping(address => uint256) public receivedDelegationCount;
    mapping(address => address[]) public delegationSources;
    mapping(address => mapping(address => bool)) public isDelegationSource;

    uint256 public totalDelegatedVotes;

    mapping(address => PendingDelegation) public pendingDelegations;

    mapping(address => uint256) public consecutiveAbstentions;
    mapping(address => uint256) public delegationRecoveryRequestTime;
    mapping(address => bool) public pendingRecovery;

    mapping(uint256 => mapping(address => bool)) public delegateeVotedInProposal;

    address[] internal activeDelegatees;
    mapping(address => bool) public isActiveDelegatee;

    mapping(address => uint256) public votingPowerLastUpdateBlock;
    mapping(address => uint256) public votingPowerAcquireTime;

    address public governanceContract;

    // ========== 事件 ==========

    event Delegated(address indexed from, address indexed to, uint256 amount, uint256 expiryTime);
    event Undelegated(address indexed from, address indexed to, uint256 amount);
    event PendingDelegationCreated(address indexed from, address indexed to, uint256 amount, uint256 effectiveTime);
    event DelegationExpired(address indexed from, address indexed to);
    event DelegationRecoveryRequested(address indexed delegator, address indexed delegatee, uint256 requestTime);
    event DelegationRecovered(address indexed delegator, address indexed delegatee, uint256 amount);
    event ConsecutiveAbstentionRecorded(address indexed delegatee, uint256 consecutiveCount);
    event GovernanceContractUpdated(address indexed oldAddress, address indexed newAddress);

    // ========== 修饰符 ==========

    modifier onlyGovernance() {
        require(msg.sender == governanceContract || msg.sender == owner(), "Not authorized");
        _;
    }

    // ========== 初始化 ==========

    function initialize() public initializer {
        __Ownable_init();
        __ReentrancyGuard_init();
        __Pausable_init();
    }

    function _authorizeUpgrade(address) internal override onlyOwner {}

    function setGovernanceContract(address _governanceContract) external onlyOwner {
        emit GovernanceContractUpdated(governanceContract, _governanceContract);
        governanceContract = _governanceContract;
    }

    // ========== 核心委托函数 ==========

    /**
     * @notice 委托投票权
     */
    function delegate(
        address from,
        address to,
        uint256 votingPower,
        uint256 duration,
        uint256 totalVotingPower
    ) external onlyGovernance nonReentrant whenNotPaused {
        require(to != address(0), "Invalid delegate");
        require(to != from, "Cannot delegate to self");
        require(duration > 0 && duration <= MAX_DELEGATION_DURATION, "Invalid duration");
        require(delegates[from] == address(0), "Already delegated");
        require(delegates[to] == address(0), "Target has delegated");

        uint256 newDelegatedVotes = delegatedVotes[to] + votingPower;
        uint256 maxAllowed = (totalVotingPower * MAX_DELEGATION_ACCEPT_RATIO) / 10000;

        if (totalVotingPower == 0 || totalVotingPower < MIN_TOTAL_FOR_DELEGATION_LIMIT) {
            maxAllowed = votingPower;
        }

        require(newDelegatedVotes <= maxAllowed, "Exceeds 5% limit");

        if (votingPower > (totalVotingPower * LARGE_VOTE_CHANGE_THRESHOLD) / 10000 &&
            totalVotingPower > 0 &&
            totalVotingPower >= MIN_TOTAL_FOR_DELEGATION_LIMIT) {
            pendingDelegations[from] = PendingDelegation({
                from: from,
                to: to,
                amount: votingPower,
                effectiveTime: block.timestamp + LARGE_VOTE_CHANGE_DELAY,
                isActive: true
            });
            emit PendingDelegationCreated(from, to, votingPower, block.timestamp + LARGE_VOTE_CHANGE_DELAY);
        } else {
            _executeDelegation(from, to, votingPower, duration);
        }
    }

    /**
     * @notice 执行待生效委托
     */
    function executePendingDelegation(address from) external onlyGovernance nonReentrant whenNotPaused {
        PendingDelegation storage pending = pendingDelegations[from];
        require(pending.isActive, "No pending delegation");
        require(block.timestamp >= pending.effectiveTime, "Not yet effective");

        _executeDelegation(pending.from, pending.to, pending.amount, MAX_DELEGATION_DURATION);
        pending.isActive = false;
    }

    /**
     * @notice 取消委托
     */
    function undelegate(address from) external onlyGovernance nonReentrant whenNotPaused {
        address delegateAddr = delegates[from];
        require(delegateAddr != address(0), "Not delegated");

        if (pendingDelegations[from].isActive) {
            pendingDelegations[from].isActive = false;
            emit Undelegated(from, pendingDelegations[from].to, pendingDelegations[from].amount);
            return;
        }

        _clearDelegationInternal(from);
    }

    /**
     * @notice 受托人取消收到的委托
     */
    function revokeDelegation(address from) external onlyGovernance nonReentrant whenNotPaused {
        address delegateAddr = delegates[from];
        require(delegateAddr != address(0), "Not delegated");
        require(delegatedVotes[delegateAddr] > 0, "No delegation to revoke");

        _clearDelegationInternal(from);
    }

    // ========== 内部函数 ==========

    function _executeDelegation(address from, address to, uint256 amount, uint256 duration) internal {
        delegates[from] = to;
        delegatedVotes[to] += amount;
        delegatedOut[from] = amount;
        delegationStartTime[from] = block.timestamp;
        delegationExpiryTime[from] = block.timestamp + duration;
        totalDelegatedVotes += amount;

        votingPowerLastUpdateBlock[from] = block.number;
        votingPowerLastUpdateBlock[to] = block.number;

        if (votingPowerAcquireTime[from] == 0) {
            votingPowerAcquireTime[from] = block.timestamp;
        }

        if (!isDelegationSource[to][from]) {
            delegationSources[to].push(from);
            isDelegationSource[to][from] = true;
            receivedDelegationCount[to]++;
        }

        if (!isActiveDelegatee[to]) {
            activeDelegatees.push(to);
            isActiveDelegatee[to] = true;
        }

        emit Delegated(from, to, amount, block.timestamp + duration);
    }

    function _clearDelegationInternal(address user) internal {
        address delegateAddr = delegates[user];
        uint256 amount = delegatedOut[user];

        delegates[user] = address(0);
        delegatedVotes[delegateAddr] -= amount;
        delegatedOut[user] = 0;
        delegationStartTime[user] = 0;
        delegationExpiryTime[user] = 0;
        totalDelegatedVotes -= amount;

        isDelegationSource[delegateAddr][user] = false;
        receivedDelegationCount[delegateAddr]--;

        emit Undelegated(user, delegateAddr, amount);
    }

    // ========== 过期检查 ==========

    function checkDelegationExpiry(address user) external onlyGovernance {
        if (delegates[user] != address(0) && block.timestamp >= delegationExpiryTime[user]) {
            address delegateAddr = delegates[user];
            _clearDelegationInternal(user);
            emit DelegationExpired(user, delegateAddr);
        }
    }

    function autoCheckDelegationExpiry(address user) external onlyGovernance {
        if (delegates[user] != address(0) && block.timestamp >= delegationExpiryTime[user]) {
            address delegateAddr = delegates[user];
            _clearDelegationInternal(user);
            emit DelegationExpired(user, delegateAddr);
        }
    }

    // ========== 恢复机制 ==========

    function requestDelegationRecovery(address delegator) external onlyGovernance whenNotPaused {
        address delegateAddr = delegates[delegator];
        require(delegateAddr != address(0), "Not delegated");
        require(!pendingRecovery[delegator], "Recovery already pending");
        require(consecutiveAbstentions[delegateAddr] >= MAX_CONSECUTIVE_ABSTENTIONS, "Not enough abstentions");

        delegationRecoveryRequestTime[delegator] = block.timestamp;
        pendingRecovery[delegator] = true;

        emit DelegationRecoveryRequested(delegator, delegateAddr, block.timestamp);
    }

    function executeDelegationRecovery(address delegator) external onlyGovernance nonReentrant whenNotPaused {
        require(pendingRecovery[delegator], "No pending recovery");
        require(
            block.timestamp >= delegationRecoveryRequestTime[delegator] + DELEGATION_RECOVERY_DELAY,
            "Recovery delay not passed"
        );

        address delegateAddr = delegates[delegator];
        uint256 amount = delegatedOut[delegator];

        _clearDelegationInternal(delegator);
        pendingRecovery[delegator] = false;
        delegationRecoveryRequestTime[delegator] = 0;
        consecutiveAbstentions[delegateAddr] = 0;

        votingPowerLastUpdateBlock[delegator] = block.number;
        votingPowerLastUpdateBlock[delegateAddr] = block.number;

        emit DelegationRecovered(delegator, delegateAddr, amount);
    }

    // ========== 投票记录 ==========

    function recordDelegateeVote(uint256 proposalId, address delegatee) external onlyGovernance {
        delegateeVotedInProposal[proposalId][delegatee] = true;
        if (consecutiveAbstentions[delegatee] > 0) {
            consecutiveAbstentions[delegatee] = 0;
        }
    }

    function checkDelegateeAbstention(uint256 proposalId, address delegatee) external onlyGovernance {
        if (!delegateeVotedInProposal[proposalId][delegatee]) {
            consecutiveAbstentions[delegatee]++;
            emit ConsecutiveAbstentionRecorded(delegatee, consecutiveAbstentions[delegatee]);
        }
    }

    // ========== 视图函数 ==========

    function getDelegationInfo(address user) external view returns (
        address delegateAddr,
        uint256 delegatedOutAmount,
        uint256 delegatedInAmount,
        uint256 expiryTime
    ) {
        delegateAddr = delegates[user];
        delegatedOutAmount = delegatedOut[user];
        delegatedInAmount = delegatedVotes[user];
        expiryTime = delegationExpiryTime[user];
    }

    function getDelegationSources(address user) external view returns (address[] memory) {
        return delegationSources[user];
    }

    function getActiveDelegateeCount() external view returns (uint256) {
        return activeDelegatees.length;
    }

    function getActiveDelegatees() external view returns (address[] memory) {
        return activeDelegatees;
    }

    function canDelegate(
        address delegateAddr,
        uint256 amount,
        uint256 totalVotingPower
    ) external view returns (bool) {
        if (delegateAddr == address(0)) return false;
        if (delegates[delegateAddr] != address(0)) return false;

        uint256 newDelegatedVotes = delegatedVotes[delegateAddr] + amount;
        uint256 maxAllowed = (totalVotingPower * MAX_DELEGATION_ACCEPT_RATIO) / 10000;

        if (totalVotingPower == 0 || totalVotingPower < MIN_TOTAL_FOR_DELEGATION_LIMIT) {
            maxAllowed = amount;
        }

        return newDelegatedVotes <= maxAllowed;
    }

    function canRequestRecovery(address delegator) external view returns (bool) {
        address delegateAddr = delegates[delegator];
        if (delegateAddr == address(0)) return false;
        if (pendingRecovery[delegator]) return false;
        return consecutiveAbstentions[delegateAddr] >= MAX_CONSECUTIVE_ABSTENTIONS;
    }

    function canExecuteRecovery(address delegator) external view returns (bool) {
        if (!pendingRecovery[delegator]) return false;
        return block.timestamp >= delegationRecoveryRequestTime[delegator] + DELEGATION_RECOVERY_DELAY;
    }

    function getDelegationRecoveryStatus(address delegator) external view returns (
        bool isPending,
        uint256 requestTime,
        bool canExecute,
        uint256 remainingTime
    ) {
        isPending = pendingRecovery[delegator];
        requestTime = delegationRecoveryRequestTime[delegator];

        if (isPending) {
            uint256 executeTime = requestTime + DELEGATION_RECOVERY_DELAY;
            if (block.timestamp >= executeTime) {
                canExecute = true;
                remainingTime = 0;
            } else {
                canExecute = false;
                remainingTime = executeTime - block.timestamp;
            }
        } else {
            canExecute = false;
            remainingTime = 0;
        }
    }

    function isDelegationValid(address user) external view returns (bool) {
        if (delegates[user] == address(0)) return false;
        return block.timestamp < delegationExpiryTime[user];
    }

    function getRemainingDelegationTime(address user) external view returns (uint256) {
        if (delegates[user] == address(0)) return 0;
        if (block.timestamp >= delegationExpiryTime[user]) return 0;
        return delegationExpiryTime[user] - block.timestamp;
    }

    function getDelegationStats() external view returns (DelegationStats memory) {
        return DelegationStats({
            totalDelegatedVotes: totalDelegatedVotes,
            activeDelegateeCount: activeDelegatees.length,
            pendingRecoveryCount: 0 // 需要遍历计算，这里简化
        });
    }

    // ========== 管理函数 ==========

    function updateVotingPowerBlock(address user) external onlyGovernance {
        votingPowerLastUpdateBlock[user] = block.number;
        if (votingPowerAcquireTime[user] == 0) {
            votingPowerAcquireTime[user] = block.timestamp;
        }
    }

    function cleanupInactiveDelegatees(uint256 limit) external onlyGovernance {
        uint256 cleaned = 0;
        uint256 i = 0;

        while (i < activeDelegatees.length && cleaned < limit) {
            address delegatee = activeDelegatees[i];

            if (delegatedVotes[delegatee] == 0) {
                activeDelegatees[i] = activeDelegatees[activeDelegatees.length - 1];
                activeDelegatees.pop();
                isActiveDelegatee[delegatee] = false;
                cleaned++;
            } else {
                i++;
            }
        }
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }
}
