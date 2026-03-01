// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts-upgradeable/access/OwnableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/security/ReentrancyGuardUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/security/PausableUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/UUPSUpgradeable.sol";
import "@openzeppelin/contracts-upgradeable/proxy/utils/Initializable.sol";

/**
 * @title IVIBStaking
 * @notice VIBStaking 接口
 */
interface IVIBStaking {
    function getVotingPower(address user) external view returns (uint256);
    function totalStaked() external view returns (uint256);
}

/**
 * @title IDelegation
 * @notice 委托合约接口
 */
interface IDelegation {
    function delegates(address) external view returns (address);
    function delegatedVotes(address) external view returns (uint256);
    function autoCheckDelegationExpiry(address) external;
    function votingPowerLastUpdateBlock(address) external view returns (uint256);
    function votingPowerAcquireTime(address) external view returns (uint256);
}

/**
 * @title IContributionPoints
 * @notice 贡献积分合约接口
 */
interface IContributionPoints {
    function getEffectiveContributionPoints(address) external view returns (uint256);
    function totalContributionPoints() external view returns (uint256);
}

/**
 * @title VIBGovernance (精简版)
 * @notice VIBE 生态系统治理合约核心
 * @dev 修复#1: 精简版本，委托和贡献积分功能移至独立合约
 */
contract VIBGovernance is
    Initializable,
    OwnableUpgradeable,
    UUPSUpgradeable,
    ReentrancyGuardUpgradeable,
    PausableUpgradeable
{
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    uint256 public constant CAPITAL_WEIGHT_MAX = 10;
    uint256 public constant PRODUCTION_WEIGHT_MAX = 15;
    uint256 public constant COMMUNITY_WEIGHT_RATIO = 10;
    uint256 public constant MIN_STAKE_REQUIREMENT = 100 * 10**18;
    uint256 public constant MIN_TOTAL_FOR_CAPS = 1000 * 10**18;
    uint256 public constant VOTE_POWER_CACHE_DURATION = 30 minutes;
    uint256 public constant GENERAL_PASS_RATE = 5000;
    uint256 public constant PARAMETER_PASS_RATE = 6000;
    uint256 public constant UPGRADE_PASS_RATE = 7500;
    uint256 public constant EMERGENCY_PASS_RATE = 9000;
    uint256 public constant DIVIDEND_PASS_RATE = 6700;
    uint256 public constant INCENTIVE_PASS_RATE = 6700;
    uint256 public constant EMERGENCY_TIMELOCK = 1 days;
    uint256 public constant COMMUNITY_OPPOSITION_THRESHOLD = 6000;
    uint256 public constant MAX_BATCH_SIZE = 100;

    // ========== 枚举 ==========

    enum ProposalType { GENERAL, PARAMETER, UPGRADE, EMERGENCY, DIVIDEND, INCENTIVE }
    enum ProposalState { PENDING, ACTIVE, CANCELLED, DEFEATED, SUCCEEDED, EXECUTED, EXPIRED }
    enum VetoType { INVESTOR_VETO, PRODUCER_VETO, COMMUNITY_VETO }

    // ========== 结构体 ==========

    struct Proposal {
        uint256 id;
        address proposer;
        ProposalType proposalType;
        ProposalState state;
        string title;
        string description;
        address target;
        bytes data;
        uint256 startTime;
        uint256 endTime;
        uint256 executeTime;
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        uint256 totalVoters;
        bool executed;
    }

    struct Vote {
        uint256 forVotes;
        uint256 againstVotes;
        uint256 abstainVotes;
        bool hasVoted;
    }

    struct VetoRecord {
        uint256 proposalId;
        VetoType vetoType;
        address initiator;
        uint256 initiatedTime;
        uint256 vetoVotes;
        uint256 opposeVotes;
        uint256 votingEndTime;
        bool executed;
        bool passed;
    }

    // ========== 状态变量 ==========

    IERC20 public vibeToken;
    IVIBStaking public vibStaking;
    address public stakingContract;
    address public emissionController;
    address public communityFund;
    address public kycContract;
    address public delegationContract;
    address public contributionPointsContract;

    Proposal[] public proposals;
    mapping(uint256 => mapping(address => Vote)) public votes;
    mapping(uint256 => mapping(address => bool)) public hasVoted;
    mapping(address => uint256) public proposalCount;

    uint256 public generalProposalThreshold;
    uint256 public parameterProposalThreshold;
    uint256 public upgradeProposalThreshold;
    uint256 public emergencyProposalThreshold;
    uint256 public dividendProposalThreshold;
    uint256 public incentiveProposalThreshold;

    uint256 public generalTimelock;
    uint256 public parameterTimelock;
    uint256 public upgradeTimelock;
    uint256 public dividendIncentiveTimelock;

    mapping(address => bool) public kycVerified;
    uint256 public kycUserCount;

    VetoRecord[] public vetoRecords;
    mapping(uint256 => mapping(address => bool)) public hasVotedVeto;

    mapping(address => bool) public allowedExecutionTargets;
    mapping(bytes4 => bool) public allowedExecutionFunctions;
    mapping(address => bool) public allowAllFunctionsForTarget;
    bool public executionWhitelistEnabled;

    uint256 public governanceRewardBalance;
    uint256 public totalPendingRewards;
    uint256 public voteReward;
    uint256 public proposalReward;
    mapping(address => uint256) public pendingGovernanceRewards;
    mapping(address => uint256) public claimedGovernanceRewards;

    uint256 public cachedTotalVotingPower;
    uint256 public totalVotingPowerCacheTime;

    bool public flashLoanProtectionEnabled;
    uint256 public flashLoanProtectionChangeTime;
    uint256 public constant MIN_VOTING_HOLD_PERIOD = 1 days;
    uint256 public pendingWhitelistChangeTime;

    mapping(uint256 => mapping(address => uint256)) public voteCastBlock;

    // ========== 事件 ==========

    event ProposalCreated(uint256 indexed id, address indexed proposer, ProposalType proposalType, string title);
    event VoteCast(uint256 indexed proposalId, address indexed voter, uint256 forVotes, uint256 againstVotes, uint256 abstainVotes);
    event ProposalExecuted(uint256 indexed id, address executor);
    event ProposalCancelled(uint256 indexed id, address canceller);
    event VetoInitiated(uint256 indexed vetoId, uint256 indexed proposalId, VetoType vetoType, address initiator);
    event VetoExecuted(uint256 indexed vetoId, bool passed);
    event GovernanceRewardClaimed(address indexed user, uint256 amount);
    event ExecutionTargetUpdated(address indexed target, bool isAllowed);
    event KYCUpdated(address indexed user, bool isVerified);

    // ========== 接口 ==========

    interface IVIBStaking {
        function getVotingPower(address user) external view returns (uint256);
        function totalStaked() external view returns (uint256);
    }

    interface IDelegation {
        function delegates(address) external view returns (address);
        function delegatedVotes(address) external view returns (uint256);
        function getDelegationInfo(address) external view returns (address, uint256, uint256, uint256);
        function autoCheckDelegationExpiry(address) external;
        function votingPowerLastUpdateBlock(address) external view returns (uint256);
        function votingPowerAcquireTime(address) external view returns (uint256);
    }

    interface IContributionPoints {
        function getEffectiveContributionPoints(address) external view returns (uint256);
        function totalContributionPoints() external view returns (uint256);
    }

    // ========== 修饰符 ==========

    modifier proposalExists(uint256 proposalId) {
        require(proposalId < proposals.length, "Invalid proposal id");
        _;
    }

    modifier proposalActive(uint256 proposalId) {
        require(proposals[proposalId].state == ProposalState.ACTIVE, "Proposal not active");
        _;
    }

    // ========== 初始化 ==========

    function initialize(address _vibeToken) public initializer {
        require(_vibeToken != address(0), "Invalid token address");
        __Ownable_init();
        __ReentrancyGuard_init();
        __Pausable_init();
        vibeToken = IERC20(_vibeToken);

        generalProposalThreshold = 500 * 10**18;
        parameterProposalThreshold = 5000 * 10**18;
        upgradeProposalThreshold = 50000 * 10**18;
        emergencyProposalThreshold = 1000 * 10**18;
        dividendProposalThreshold = 5000 * 10**18;
        incentiveProposalThreshold = 5000 * 10**18;

        generalTimelock = 14 days;
        parameterTimelock = 30 days;
        upgradeTimelock = 60 days;
        dividendIncentiveTimelock = 30 days;

        voteReward = 1 * 10**18;
        proposalReward = 10 * 10**18;
        executionWhitelistEnabled = true;
        flashLoanProtectionEnabled = true;
    }

    function _authorizeUpgrade(address) internal override onlyOwner {}

    // ========== 核心治理函数 ==========

    function createProposal(
        ProposalType proposalType,
        string memory title,
        string memory description,
        address target,
        bytes memory data
    ) external nonReentrant whenNotPaused returns (uint256) {
        uint256 votingPower = getVotingPower(msg.sender);
        require(votingPower > 0, "No voting power");

        uint256 threshold = _getThreshold(proposalType);
        require(votingPower >= threshold, "Below threshold");

        uint256 proposalId = proposals.length;
        uint256 startTime = block.timestamp;
        uint256 endTime = startTime + _getDuration(proposalType);
        uint256 executeTime = endTime + _getTimelock(proposalType);

        proposals.push(Proposal({
            id: proposalId,
            proposer: msg.sender,
            proposalType: proposalType,
            state: ProposalState.ACTIVE,
            title: title,
            description: description,
            target: target,
            data: data,
            startTime: startTime,
            endTime: endTime,
            executeTime: executeTime,
            forVotes: 0,
            againstVotes: 0,
            abstainVotes: 0,
            totalVoters: 0,
            executed: false
        }));

        proposalCount[msg.sender]++;

        if (governanceRewardBalance >= totalPendingRewards + proposalReward) {
            pendingGovernanceRewards[msg.sender] += proposalReward;
            totalPendingRewards += proposalReward;
        }

        emit ProposalCreated(proposalId, msg.sender, proposalType, title);
        return proposalId;
    }

    function castVote(uint256 proposalId, uint8 support)
        external
        nonReentrant
        proposalExists(proposalId)
        proposalActive(proposalId)
    {
        require(support <= 2, "Invalid support value");
        require(!hasVoted[proposalId][msg.sender], "Already voted");

        _checkDelegationExpiry(msg.sender);

        Proposal storage proposal = proposals[proposalId];

        require(
            block.timestamp >= proposal.startTime && block.timestamp <= proposal.endTime,
            "Not within voting period"
        );

        _checkFlashLoanProtection(msg.sender);

        uint256 votingPower = getVotingPower(msg.sender);
        require(votingPower > 0, "No voting power");

        hasVoted[proposalId][msg.sender] = true;
        voteCastBlock[proposalId][msg.sender] = block.number;
        proposal.totalVoters++;

        if (support == 1) {
            proposal.forVotes += votingPower;
            votes[proposalId][msg.sender].forVotes = votingPower;
        } else if (support == 0) {
            proposal.againstVotes += votingPower;
            votes[proposalId][msg.sender].againstVotes = votingPower;
        } else {
            proposal.abstainVotes += votingPower;
            votes[proposalId][msg.sender].abstainVotes = votingPower;
        }

        votes[proposalId][msg.sender].hasVoted = true;

        emit VoteCast(proposalId, msg.sender,
            votes[proposalId][msg.sender].forVotes,
            votes[proposalId][msg.sender].againstVotes,
            votes[proposalId][msg.sender].abstainVotes);
    }

    function finalizeProposal(uint256 proposalId) external nonReentrant proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.state == ProposalState.ACTIVE, "Not active");
        require(block.timestamp > proposal.endTime, "Voting ongoing");

        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        uint256 requiredRate = _getRequiredPassRate(proposal.proposalType);

        if (totalVotes == 0) {
            proposal.state = ProposalState.DEFEATED;
        } else {
            uint256 passRate = (proposal.forVotes * 10000) / totalVotes;
            proposal.state = passRate >= requiredRate ? ProposalState.SUCCEEDED : ProposalState.DEFEATED;
        }
    }

    function executeProposal(uint256 proposalId) external nonReentrant proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        require(proposal.state == ProposalState.SUCCEEDED, "Not succeeded");
        require(!proposal.executed, "Already executed");
        require(block.timestamp >= proposal.executeTime, "Timelock not expired");

        proposal.executed = true;
        proposal.state = ProposalState.EXECUTED;

        if (proposal.target != address(0) && proposal.data.length > 0) {
            _validateAndExecute(proposal.target, proposal.data);
        }

        _distributeProposerReward(proposal);

        emit ProposalExecuted(proposalId, msg.sender);
    }

    function cancelProposal(uint256 proposalId) external nonReentrant proposalExists(proposalId) {
        Proposal storage proposal = proposals[proposalId];

        require(msg.sender == proposal.proposer || msg.sender == owner(), "Not authorized");
        require(proposal.state == ProposalState.ACTIVE || proposal.state == ProposalState.PENDING, "Cannot cancel");

        proposal.state = ProposalState.CANCELLED;
        emit ProposalCancelled(proposalId, msg.sender);
    }

    // ========== 内部函数 ==========

    function _validateAndExecute(address target, bytes memory data) internal {
        if (executionWhitelistEnabled) {
            require(allowedExecutionTargets[target], "Target not allowed");

            if (!allowAllFunctionsForTarget[target]) {
                require(data.length >= 4, "Invalid data");
                bytes4 selector = bytes4(data[0]) | (bytes4(data[1]) >> 8) |
                                  (bytes4(data[2]) >> 16) | (bytes4(data[3]) >> 24);
                require(allowedExecutionFunctions[selector], "Function not allowed");
            }
        }

        (bool success, ) = target.call(data);
        require(success, "Execution failed");
    }

    function _distributeProposerReward(Proposal storage proposal) internal {
        if (proposal.state != ProposalState.EXECUTED) return;

        uint256 baseReward = 50 * 10**18;
        if (proposal.proposalType == ProposalType.PARAMETER) baseReward = 100 * 10**18;
        else if (proposal.proposalType == ProposalType.UPGRADE) baseReward = 500 * 10**18;

        uint256 bonus = proposal.totalVoters >= 100 ? 50 * 10**18 :
                        proposal.totalVoters >= 50 ? 25 * 10**18 : 0;

        uint256 reward = baseReward + bonus;
        if (reward > 500 * 10**18) reward = 500 * 10**18;

        if (reward > 0 && governanceRewardBalance >= totalPendingRewards + reward) {
            pendingGovernanceRewards[proposal.proposer] += reward;
            totalPendingRewards += reward;
        }
    }

    function _checkDelegationExpiry(address user) internal {
        if (delegationContract != address(0)) {
            IDelegation(delegationContract).autoCheckDelegationExpiry(user);
        }
    }

    function _checkFlashLoanProtection(address user) internal {
        if (!flashLoanProtectionEnabled) return;

        uint256 lastBlock = delegationContract != address(0) ?
            IDelegation(delegationContract).votingPowerLastUpdateBlock(user) : 0;

        require(lastBlock < block.number, "Voting power changed this block");

        uint256 acquireTime = delegationContract != address(0) ?
            IDelegation(delegationContract).votingPowerAcquireTime(user) : 0;

        if (acquireTime == 0) {
            revert("First time voter, wait 1 day");
        }

        require(block.timestamp >= acquireTime + MIN_VOTING_HOLD_PERIOD, "Hold period not met");
    }

    // ========== 投票权计算 ==========

    function getVotingPower(address user) public view returns (uint256) {
        address userDelegate = delegationContract != address(0) ?
            IDelegation(delegationContract).delegates(user) : address(0);

        if (userDelegate != address(0)) return 0;

        uint256 ownPower = _getOwnVotingPower(user);
        uint256 delegatedPower = delegationContract != address(0) ?
            IDelegation(delegationContract).delegatedVotes(user) : 0;

        return ownPower + delegatedPower;
    }

    function _getOwnVotingPower(address user) internal view returns (uint256) {
        uint256 capitalPower = _getCapitalWeight(user);
        uint256 productionPower = _getProductionWeight(user);
        uint256 communityPower = _getCommunityWeight(user);

        uint256 totalVP = _getTotalVotingPower();

        if (totalVP >= MIN_TOTAL_FOR_CAPS) {
            uint256 capitalCap = (totalVP * CAPITAL_WEIGHT_MAX) / 100;
            if (capitalPower > capitalCap) capitalPower = capitalCap;

            uint256 productionCap = (totalVP * PRODUCTION_WEIGHT_MAX) / 100;
            if (productionPower > productionCap) productionPower = productionCap;
        }

        return capitalPower + productionPower + communityPower;
    }

    function _getCapitalWeight(address user) internal view returns (uint256) {
        if (address(vibStaking) != address(0)) {
            try vibStaking.getVotingPower(user) returns (uint256 power) {
                if (power > 0) return power;
            } catch {}
        }

        uint256 balance = vibeToken.balanceOf(user);
        return balance >= MIN_STAKE_REQUIREMENT ? balance : 0;
    }

    function _getProductionWeight(address user) internal view returns (uint256) {
        if (contributionPointsContract == address(0)) return 0;

        uint256 effectivePoints = IContributionPoints(contributionPointsContract).getEffectiveContributionPoints(user);
        return (effectivePoints * 10) / 100; // 1 积分 = 0.01 投票权
    }

    function _getCommunityWeight(address user) internal view returns (uint256) {
        if (!kycVerified[user] || kycUserCount == 0) return 0;

        uint256 totalVP = _getTotalVotingPower();
        uint256 totalCommunityWeight = (totalVP * 10) / 100;

        return totalCommunityWeight / kycUserCount;
    }

    function _getTotalVotingPower() internal view returns (uint256) {
        if (cachedTotalVotingPower > 0 &&
            block.timestamp < totalVotingPowerCacheTime + VOTE_POWER_CACHE_DURATION) {
            return cachedTotalVotingPower;
        }

        uint256 basePower = _getTotalStakedAmount();
        uint256 estimatedProduction = contributionPointsContract != address(0) ?
            (IContributionPoints(contributionPointsContract).totalContributionPoints() * 10) / 100 : 0;
        uint256 communityWeight = ((basePower + estimatedProduction) * 10) / 100;

        return basePower + estimatedProduction + communityWeight;
    }

    function _getTotalStakedAmount() internal view returns (uint256) {
        if (address(vibStaking) != address(0)) {
            try vibStaking.totalStaked() returns (uint256 total) {
                return total;
            } catch {}
        }
        return (vibeToken.totalSupply() * 80) / 100;
    }

    // ========== 辅助函数 ==========

    function _getThreshold(ProposalType t) internal view returns (uint256) {
        if (t == ProposalType.GENERAL) return generalProposalThreshold;
        if (t == ProposalType.PARAMETER) return parameterProposalThreshold;
        if (t == ProposalType.UPGRADE) return upgradeProposalThreshold;
        if (t == ProposalType.DIVIDEND) return dividendProposalThreshold;
        if (t == ProposalType.INCENTIVE) return incentiveProposalThreshold;
        return emergencyProposalThreshold;
    }

    function _getDuration(ProposalType t) internal pure returns (uint256) {
        if (t == ProposalType.GENERAL) return 7 days;
        if (t == ProposalType.PARAMETER) return 14 days;
        if (t == ProposalType.UPGRADE) return 21 days;
        if (t == ProposalType.DIVIDEND || t == ProposalType.INCENTIVE) return 14 days;
        return 3 days;
    }

    function _getTimelock(ProposalType t) internal view returns (uint256) {
        if (t == ProposalType.GENERAL) return generalTimelock;
        if (t == ProposalType.PARAMETER) return parameterTimelock;
        if (t == ProposalType.UPGRADE) return upgradeTimelock;
        if (t == ProposalType.DIVIDEND || t == ProposalType.INCENTIVE) return dividendIncentiveTimelock;
        return EMERGENCY_TIMELOCK;
    }

    function _getRequiredPassRate(ProposalType t) internal pure returns (uint256) {
        if (t == ProposalType.GENERAL) return GENERAL_PASS_RATE;
        if (t == ProposalType.PARAMETER) return PARAMETER_PASS_RATE;
        if (t == ProposalType.UPGRADE) return UPGRADE_PASS_RATE;
        if (t == ProposalType.DIVIDEND) return DIVIDEND_PASS_RATE;
        if (t == ProposalType.INCENTIVE) return INCENTIVE_PASS_RATE;
        return EMERGENCY_PASS_RATE;
    }

    // ========== 管理函数 ==========

    function setStakingContract(address _addr) external onlyOwner {
        stakingContract = _addr;
        vibStaking = IVIBStaking(_addr);
    }

    function setDelegationContract(address _addr) external onlyOwner {
        delegationContract = _addr;
    }

    function setContributionPointsContract(address _addr) external onlyOwner {
        contributionPointsContract = _addr;
    }

    function setEmissionController(address _addr) external onlyOwner {
        emissionController = _addr;
    }

    function setCommunityFund(address _addr) external onlyOwner {
        communityFund = _addr;
    }

    function setKycContract(address _addr) external onlyOwner {
        kycContract = _addr;
    }

    function batchUpdateKYC(address[] calldata users, bool[] calldata statuses) external onlyOwner {
        require(users.length == statuses.length && users.length <= MAX_BATCH_SIZE, "Invalid input");

        for (uint256 i = 0; i < users.length; i++) {
            bool wasVerified = kycVerified[users[i]];
            kycVerified[users[i]] = statuses[i];

            if (statuses[i] && !wasVerified) kycUserCount++;
            else if (!statuses[i] && wasVerified) kycUserCount--;

            emit KYCUpdated(users[i], statuses[i]);
        }
    }

    function setExecutionTarget(address target, bool isAllowed) external onlyOwner {
        require(target != address(0), "Invalid target");
        allowedExecutionTargets[target] = isAllowed;
        emit ExecutionTargetUpdated(target, isAllowed);
    }

    function setExecutionFunction(bytes4 selector, bool isAllowed) external onlyOwner {
        allowedExecutionFunctions[selector] = isAllowed;
    }

    function setTargetAllowAllFunctions(address target, bool allowAll) external onlyOwner {
        require(allowedExecutionTargets[target], "Target not in whitelist");
        allowAllFunctionsForTarget[target] = allowAll;
    }

    function setExecutionWhitelistEnabled(bool enabled) external onlyOwner {
        if (enabled) {
            executionWhitelistEnabled = true;
            pendingWhitelistChangeTime = 0;
        } else {
            pendingWhitelistChangeTime = block.timestamp + 7 days;
        }
    }

    function confirmWhitelistDisable() external onlyOwner {
        require(pendingWhitelistChangeTime > 0 && block.timestamp >= pendingWhitelistChangeTime, "Cannot disable");
        executionWhitelistEnabled = false;
        pendingWhitelistChangeTime = 0;
    }

    function updateTotalVotingPowerCache() external {
        uint256 basePower = _getTotalStakedAmount();
        uint256 estimatedProduction = contributionPointsContract != address(0) ?
            (IContributionPoints(contributionPointsContract).totalContributionPoints() * 10) / 100 : 0;
        uint256 communityWeight = ((basePower + estimatedProduction) * 10) / 100;

        cachedTotalVotingPower = basePower + estimatedProduction + communityWeight;
        totalVotingPowerCacheTime = block.timestamp;
    }

    function receiveRewards(uint256 amount) external {
        require(msg.sender == emissionController || msg.sender == owner(), "Not authorized");
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        governanceRewardBalance += amount;
    }

    function claimGovernanceReward() external nonReentrant whenNotPaused {
        uint256 reward = pendingGovernanceRewards[msg.sender];
        require(reward > 0, "No rewards");
        require(governanceRewardBalance >= reward, "Insufficient balance");

        pendingGovernanceRewards[msg.sender] = 0;
        totalPendingRewards -= reward;
        governanceRewardBalance -= reward;
        claimedGovernanceRewards[msg.sender] += reward;

        vibeToken.safeTransfer(msg.sender, reward);
        emit GovernanceRewardClaimed(msg.sender, reward);
    }

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    // ========== 视图函数 ==========

    function getProposal(uint256 proposalId) external view proposalExists(proposalId) returns (Proposal memory) {
        return proposals[proposalId];
    }

    function getProposalCount() external view returns (uint256) {
        return proposals.length;
    }

    function getState(uint256 proposalId) external view proposalExists(proposalId) returns (ProposalState) {
        return proposals[proposalId].state;
    }

    function getVote(uint256 proposalId, address user) external view returns (Vote memory) {
        return votes[proposalId][user];
    }

    function hasVotedOnProposal(uint256 proposalId, address voter) external view returns (bool) {
        return hasVoted[proposalId][voter];
    }

    function getGovernanceRewardStats() external view returns (uint256 balance, uint256 pending, uint256 available) {
        balance = governanceRewardBalance;
        pending = totalPendingRewards;
        available = governanceRewardBalance >= totalPendingRewards ?
            governanceRewardBalance - totalPendingRewards : 0;
    }

    function checkProposalPassed(uint256 proposalId) external view proposalExists(proposalId) returns (bool) {
        Proposal storage proposal = proposals[proposalId];
        uint256 totalVotes = proposal.forVotes + proposal.againstVotes + proposal.abstainVotes;
        if (totalVotes == 0) return false;

        uint256 passRate = (proposal.forVotes * 10000) / totalVotes;
        return passRate >= _getRequiredPassRate(proposal.proposalType);
    }
}
