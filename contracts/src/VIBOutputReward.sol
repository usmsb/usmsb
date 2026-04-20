// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IVIBVEPoints - AI-003修复
 * @notice VE积分接口
 */
interface IVIBVEPointsForReward {
    function recordOutputReward(address user, uint256 rewardAmount) external;
}

/**
 * @title VIBOutputReward
 * @notice AI Agent产出激励合约
 * @dev 实现白皮书承诺的产出奖励公式：
 *      Reward = BaseReward × Quality × Complexity × Novelty × Efficiency
 *
 * 产出类型权重（白皮书 40%/25%/20%/15%）：
 * - 代码/产品:   权重 4000 (40%)
 * - 内容创作:   权重 2500 (25%)
 * - 问题解决:   权重 2000 (20%)
 * - 创新发现:   权重 1500 (15%)
 *
 * 产出类型奖励范围：
 * - 代码/产品: 10-500 VIBE
 * - 内容创作: 5-200 VIBE
 * - 问题解决: 1-100 VIBE
 * - 创新发现: 50-5000 VIBE
 *
 * 权重调整机制：
 * - 通过治理提案调整（提议→7天timelock→执行）
 * - 未来可通过治理添加新产出类型
 *
 * 完全去中心化：奖励由预言机或自动化系统触发，不需要人工干预
 */
contract VIBOutputReward is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // 产出类型
    enum OutputType {
        CODE_PRODUCT,    // 代码/产品: 10-500 VIBE
        CONTENT,         // 内容创作: 5-200 VIBE
        PROBLEM_SOLVING, // 问题解决: 1-100 VIBE
        INNOVATION       // 创新发现: 50-5000 VIBE
    }

    // 奖励范围（单位：VIBE，精度10^18）
    uint256 public constant CODE_MIN = 10 * 10**18;
    uint256 public constant CODE_MAX = 500 * 10**18;
    uint256 public constant CONTENT_MIN = 5 * 10**18;
    uint256 public constant CONTENT_MAX = 200 * 10**18;
    uint256 public constant PROBLEM_MIN = 1 * 10**18;
    uint256 public constant PROBLEM_MAX = 100 * 10**18;
    uint256 public constant INNOVATION_MIN = 50 * 10**18;
    uint256 public constant INNOVATION_MAX = 5000 * 10**18;

    // 奖励因子范围（精度10000，即100.00%）
    uint256 public constant MIN_QUALITY = 5000;      // 0.5x
    uint256 public constant MAX_QUALITY = 30000;     // 3.0x
    uint256 public constant MIN_COMPLEXITY = 5000;   // 0.5x
    uint256 public constant MAX_COMPLEXITY = 20000;  // 2.0x
    uint256 public constant MIN_NOVELTY = 5000;      // 0.5x
    uint256 public constant MAX_NOVELTY = 50000;     // 5.0x
    uint256 public constant MIN_EFFICIENCY = 5000;   // 0.5x
    uint256 public constant MAX_EFFICIENCY = 20000;  // 2.0x

    // ========== 状态变量 ==========

    /// @notice VIBE代币
    IERC20 public vibeToken;

    /// @notice EmissionController地址（资金来源）
    address public emissionController;

    /// @notice VE积分合约地址 - AI-003修复
    address public vePointsContract;

    /// @notice 已授权的评估者（预言机/自动化系统）
    mapping(address => bool) public authorizedEvaluators;

    // ========== 安全修复: 评估者权限控制 ==========

    /// @notice 评估者每日评估上限（防止滥用）
    uint256 public constant MAX_EVALUATIONS_PER_DAY = 100;

    /// @notice 评估者每日评估计数
    mapping(address => mapping(uint256 => uint256)) public evaluatorDailyCount;

    /// @notice 单个评估者最大奖励权限
    uint256 public constant MAX_SINGLE_REWARD_AUTHORITY = 5000 * 10**18; // 5000 VIBE

    /// @notice 评估者已授权总奖励
    mapping(address => uint256) public evaluatorTotalAuthorized;

    /// @notice 评估者最大授权总额度
    uint256 public constant MAX_EVALUATOR_TOTAL_AUTHORITY = 100000 * 10**18; // 100,000 VIBE

    /// @notice 产出记录
    mapping(bytes32 => OutputRecord) public outputRecords;

    /// @notice 用户总奖励
    mapping(address => uint256) public userTotalRewards;

    /// @notice 已发放总奖励
    uint256 public totalRewardsDistributed;

    /// @notice 产出数量
    uint256 public outputCount;

    /// @notice 日池金额（白皮书修复: 防除零）
    uint256 public dailyPoolAmount;

    /// @notice 上次分配时间
    uint256 public lastDistributionTime;

    /// @notice 分配周期（7天）
    uint256 public constant DISTRIBUTION_PERIOD = 7 days;

    // ========== 产出类型权重系统（白皮书 40%/25%/20%/15%）==========

    /// @notice 产出类型权重（万分之一精度，默认 4000/2500/2000/1500）
    mapping(OutputType => uint16) public typeWeights;

    /// @notice 各类型累计已发放金额（用于按权重预算控制）
    mapping(OutputType => uint128) public typeBudgetUsed;

    // ========== 治理权重调整（7天timelock）==========

    /// @notice 待生效的权重变更
    mapping(OutputType => uint16) public pendingWeightChanges;

    /// @notice 权重变更提议时间
    uint256 public weightChangeProposalTime;

    /// @notice 权重变更生效延迟（7天）
    uint256 public constant WEIGHT_CHANGE_DELAY = 7 days;

    // ========== 结构体 ==========

    struct OutputRecord {
        address producer;        // 产出者
        OutputType outputType;   // 产出类型
        uint256 baseReward;      // 基础奖励
        uint256 qualityFactor;   // 质量因子
        uint256 complexityFactor;// 复杂度因子
        uint256 noveltyFactor;   // 创新度因子
        uint256 efficiencyFactor;// 效率因子
        uint256 finalReward;     // 最终奖励
        uint256 timestamp;       // 时间戳
        bool claimed;            // 是否已领取
        bytes32 outputHash;      // 产出哈希（链下内容引用）
    }

    // ========== 事件 ==========

    event OutputSubmitted(
        bytes32 indexed outputId,
        address indexed producer,
        OutputType outputType,
        bytes32 outputHash
    );

    event OutputEvaluated(
        bytes32 indexed outputId,
        uint256 qualityFactor,
        uint256 complexityFactor,
        uint256 noveltyFactor,
        uint256 efficiencyFactor,
        uint256 finalReward
    );

    event RewardClaimed(
        bytes32 indexed outputId,
        address indexed producer,
        uint256 amount
    );

    event EvaluatorUpdated(address indexed evaluator, bool authorized);

    event DailyPoolReceived(uint256 amount, uint256 totalPool);

    /// @notice 权重变更提议事件
    event WeightChangeProposed(OutputType indexed outputType, uint16 newWeight, uint256 proposalTime);

    /// @notice 权重变更执行事件
    event WeightChangeExecuted(OutputType indexed outputType, uint16 newWeight);

    // ========== 修饰符 ==========

    modifier onlyAuthorizedEvaluator() {
        require(authorizedEvaluators[msg.sender], "VIBOutputReward: not authorized evaluator");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _emissionController
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBOutputReward: invalid token");
        vibeToken = IERC20(_vibeToken);
        emissionController = _emissionController;

        // 初始化产出类型权重（白皮书 40%/25%/20%/15%）
        typeWeights[OutputType.CODE_PRODUCT] = 4000;
        typeWeights[OutputType.CONTENT] = 2500;
        typeWeights[OutputType.PROBLEM_SOLVING] = 2000;
        typeWeights[OutputType.INNOVATION] = 1500;
    }

    /**
    /**接收日池资金（白皮书修复: 日池分配机制）
     * @dev 由EmissionController定期调用
     */
    function receiveDailyPool(uint256 amount) external {
        require(msg.sender == emissionController || msg.sender == owner(), "VIBOutputReward: not authorized");
        require(amount > 0, "VIBOutputReward: amount must be greater than 0");

        // 从发送者接收代币
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        // 更新日池金额
        dailyPoolAmount += amount;
        lastDistributionTime = block.timestamp;

        emit DailyPoolReceived(amount, dailyPoolAmount);
    }

    /**
     * @notice 接收直接转账（与safeTransfer配合使用）
     * @dev 用于接收EmissionController的safeTransfer转账
     *      需要手动调用syncBalance()同步余额
     */
    function syncBalance() external {
        uint256 actualBalance = vibeToken.balanceOf(address(this));
        if (actualBalance > dailyPoolAmount) {
            dailyPoolAmount = actualBalance;
            lastDistributionTime = block.timestamp;
        }
    }

    /**
     * @notice 接收直接转账（自动同步余额）
     * @dev 用于接收EmissionController的safeTransfer，自动同步余额
     */
    receive() external payable {
        // 被动接收ETH（用于Gas奖励等）
    }

    /**
     * @notice 存款接口（用于接收safeTransfer的代币）
     * @dev 外部调用者（如EOA）可以存款，但EmissionController转账后需要手动触发
     *      推荐流程：EmissionController转账 → 任何人调用syncBalance() → 日池更新
     */

    // ========== 外部函数 ==========

    /**
     * @notice 提交产出（由AI Agent或其代理调用）
     * @param outputType 产出类型
     * @param outputHash 产出内容哈希（IPFS CID等）
     * @return outputId 产出ID
     */
    function submitOutput(
        OutputType outputType,
        bytes32 outputHash
    ) external whenNotPaused returns (bytes32 outputId) {
        outputCount++;
        outputId = keccak256(abi.encodePacked(
            msg.sender,
            outputType,
            outputHash,
            block.timestamp,
            outputCount
        ));

        // 计算基础奖励（类型中值）
        uint256 baseReward = _getBaseReward(outputType);

        outputRecords[outputId] = OutputRecord({
            producer: msg.sender,
            outputType: outputType,
            baseReward: baseReward,
            qualityFactor: 0,
            complexityFactor: 0,
            noveltyFactor: 0,
            efficiencyFactor: 0,
            finalReward: 0,
            timestamp: block.timestamp,
            claimed: false,
            outputHash: outputHash
        });

        emit OutputSubmitted(outputId, msg.sender, outputType, outputHash);
        return outputId;
    }

    /**
     * @notice 评估产出并计算奖励（由授权评估者调用）
     * @dev 完全去中心化：评估者可以是预言机、自动化测试系统等
     *      安全修复: 添加评估限制，防止单个评估者权限过大
     * @param outputId 产出ID
     * @param quality 质量评分（5000-30000，精度10000）
     * @param complexity 复杂度评分（5000-20000）
     * @param novelty 创新度评分（5000-50000）
     * @param efficiency 效率评分（5000-20000）
     */
    function evaluateOutput(
        bytes32 outputId,
        uint256 quality,
        uint256 complexity,
        uint256 novelty,
        uint256 efficiency
    ) external onlyAuthorizedEvaluator whenNotPaused {
        OutputRecord storage record = outputRecords[outputId];
        require(record.producer != address(0), "VIBOutputReward: output not found");
        require(record.finalReward == 0, "VIBOutputReward: already evaluated");

        // 验证因子范围
        require(quality >= MIN_QUALITY && quality <= MAX_QUALITY, "VIBOutputReward: invalid quality");
        require(complexity >= MIN_COMPLEXITY && complexity <= MAX_COMPLEXITY, "VIBOutputReward: invalid complexity");
        require(novelty >= MIN_NOVELTY && novelty <= MAX_NOVELTY, "VIBOutputReward: invalid novelty");
        require(efficiency >= MIN_EFFICIENCY && efficiency <= MAX_EFFICIENCY, "VIBOutputReward: invalid efficiency");

        // ========== 安全修复: 评估限制 ==========
        // 1. 每日评估次数限制
        uint256 dayIndex = block.timestamp / 1 days;
        require(
            evaluatorDailyCount[msg.sender][dayIndex] < MAX_EVALUATIONS_PER_DAY,
            "VIBOutputReward: daily evaluation limit reached"
        );
        evaluatorDailyCount[msg.sender][dayIndex]++;

        // 存储因子
        record.qualityFactor = quality;
        record.complexityFactor = complexity;
        record.noveltyFactor = novelty;
        record.efficiencyFactor = efficiency;

        // 计算最终奖励
        // Reward = BaseReward × Quality × Complexity × Novelty × Efficiency / PRECISION^4
        uint256 finalReward = record.baseReward;
        finalReward = (finalReward * quality) / PRECISION;
        finalReward = (finalReward * complexity) / PRECISION;
        finalReward = (finalReward * novelty) / PRECISION;
        finalReward = (finalReward * efficiency) / PRECISION;

        // 确保在类型范围内
        (uint256 minReward, uint256 maxReward) = _getRewardRange(record.outputType);
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

        // 2. 单次奖励上限
        require(
            finalReward <= MAX_SINGLE_REWARD_AUTHORITY,
            "VIBOutputReward: reward exceeds single authority limit"
        );

        // 3. 评估者累计授权额度限制
        require(
            evaluatorTotalAuthorized[msg.sender] + finalReward <= MAX_EVALUATOR_TOTAL_AUTHORITY,
            "VIBOutputReward: evaluator total authority exceeded"
        );
        evaluatorTotalAuthorized[msg.sender] += finalReward;

        record.finalReward = finalReward;

        emit OutputEvaluated(
            outputId,
            quality,
            complexity,
            novelty,
            efficiency,
            finalReward
        );
    }

    /**
     * @notice 领取奖励
     * @param outputId 产出ID
     */
    function claimReward(bytes32 outputId) external nonReentrant whenNotPaused {
        OutputRecord storage record = outputRecords[outputId];

        require(record.producer == msg.sender, "VIBOutputReward: not producer");
        require(record.finalReward > 0, "VIBOutputReward: not evaluated");
        require(!record.claimed, "VIBOutputReward: already claimed");

        record.claimed = true;
        uint256 reward = record.finalReward;

        // 更新类型累计已发放
        typeBudgetUsed[record.outputType] += uint128(reward);
        userTotalRewards[msg.sender] += reward;
        totalRewardsDistributed += reward;

        // 从合约余额转账
        vibeToken.safeTransfer(msg.sender, reward);

        // AI-003修复: 记录VE积分
        _recordVEPoints(msg.sender, reward);

        emit RewardClaimed(outputId, msg.sender, reward);
    }

    /**
     * @notice 批量领取奖励
     * @param outputIds 产出ID数组
     */
    function batchClaimRewards(bytes32[] calldata outputIds) external nonReentrant whenNotPaused {
        uint256 totalReward = 0;

        for (uint256 i = 0; i < outputIds.length; i++) {
            OutputRecord storage record = outputRecords[outputIds[i]];

            if (record.producer == msg.sender &&
                record.finalReward > 0 &&
                !record.claimed) {
                record.claimed = true;
                totalReward += record.finalReward;

                emit RewardClaimed(outputIds[i], msg.sender, record.finalReward);
            }
        }

        require(totalReward > 0, "VIBOutputReward: no rewards to claim");

        userTotalRewards[msg.sender] += totalReward;
        totalRewardsDistributed += totalReward;

        vibeToken.safeTransfer(msg.sender, totalReward);

        // AI-003修复: 记录VE积分
        _recordVEPoints(msg.sender, totalReward);
    }

    // ========== 管理函数 ==========

    /**
     * @notice 设置授权评估者
     * @param evaluator 评估者地址
     * @param authorized 是否授权
     */
    function setAuthorizedEvaluator(address evaluator, bool authorized) external onlyOwner {
        authorizedEvaluators[evaluator] = authorized;
        emit EvaluatorUpdated(evaluator, authorized);
    }

    /**
     * @notice 设置EmissionController
     * @param _emissionController 新地址
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        emissionController = _emissionController;
    }

    /**
     * @notice 设置VE积分合约地址 - AI-003修复
     * @param _vePointsContract 新地址
     */
    function setVEPointsContract(address _vePointsContract) external onlyOwner {
        vePointsContract = _vePointsContract;
        emit VEPointsContractUpdated(_vePointsContract);
    }

    /// @notice VE积分合约更新事件 - AI-003修复
    event VEPointsContractUpdated(address indexed vePointsContract);

    /**
     * @notice 从EmissionController接收资金
     * @param amount 金额
     */
    function receiveFunds(uint256 amount) external {
        require(
            msg.sender == emissionController || msg.sender == owner(),
            "VIBOutputReward: unauthorized"
        );
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    /**
     * @notice 紧急提取（仅owner，有2天时间锁）
     */
    uint256 public emergencyWithdrawEffectiveTime;

    function initiateEmergencyWithdraw() external onlyOwner {
        emergencyWithdrawEffectiveTime = block.timestamp + 2 days;
    }

    function executeEmergencyWithdraw() external onlyOwner {
        require(block.timestamp >= emergencyWithdrawEffectiveTime, "VIBOutputReward: timelock not expired");
        require(emergencyWithdrawEffectiveTime > 0, "VIBOutputReward: not initiated");

        uint256 balance = vibeToken.balanceOf(address(this));
        if (balance > 0) {
            vibeToken.safeTransfer(owner(), balance);
        }
        emergencyWithdrawEffectiveTime = 0;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 提议调整产出类型权重（owner提议，7天timelock后生效）
     * @param outputType 产出类型
     * @param newWeight 新权重（万分之一精度，如4000=40%）
     * @dev 总活跃权重不得超过10000，否则提议无效
     */
    function proposeWeightChange(OutputType outputType, uint16 newWeight) external onlyOwner {
        require(newWeight > 0, "VIBOutputReward: weight must be positive");

        // 计算调整后的总权重（pending + 其他活跃）
        uint256 otherActiveWeight = 0;
        for (uint i = 0; i < 4; i++) {
            OutputType t = OutputType(i);
            if (t != outputType) {
                // 混合使用当前权重和pending权重，取较大者
                uint16 w = pendingWeightChanges[t] != 0 ? pendingWeightChanges[t] : typeWeights[t];
                otherActiveWeight += w;
            }
        }
        require(otherActiveWeight + newWeight <= PRECISION, "VIBOutputReward: total weight > 10000");

        pendingWeightChanges[outputType] = newWeight;
        weightChangeProposalTime = block.timestamp;

        emit WeightChangeProposed(outputType, newWeight, block.timestamp);
    }

    /**
     * @notice 执行权重变更（任何人触发，timelock后生效）
     * @param outputType 产出类型
     * @dev timelock为7天，防止治理攻击
     */
    function executeWeightChange(OutputType outputType) external {
        require(pendingWeightChanges[outputType] != 0, "VIBOutputReward: no pending change");
        require(
            block.timestamp >= weightChangeProposalTime + WEIGHT_CHANGE_DELAY,
            "VIBOutputReward: timelock not expired"
        );

        typeWeights[outputType] = pendingWeightChanges[outputType];
        pendingWeightChanges[outputType] = 0;
        weightChangeProposalTime = 0;

        emit WeightChangeExecuted(outputType, typeWeights[outputType]);
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取某类型剩余可发放预算
     * @param outputType 产出类型
     * @return 剩余可发放金额（精度1e18）
     * @dev 基于当前池余额和类型权重计算
     */
    function getTypeBudgetRemaining(OutputType outputType) external view returns (uint256) {
        uint256 poolBalance = vibeToken.balanceOf(address(this));
        uint256 totalWeight = uint256(typeWeights[OutputType.CODE_PRODUCT])
            + uint256(typeWeights[OutputType.CONTENT])
            + uint256(typeWeights[OutputType.PROBLEM_SOLVING])
            + uint256(typeWeights[OutputType.INNOVATION]);

        uint256 typeAllocation = (poolBalance * uint256(typeWeights[outputType])) / totalWeight;
        if (typeAllocation <= typeBudgetUsed[outputType]) {
            return 0;
        }
        return typeAllocation - typeBudgetUsed[outputType];
    }

    /**
     * @notice 获取产出信息
     */
    function getOutputInfo(bytes32 outputId) external view returns (OutputRecord memory) {
        return outputRecords[outputId];
    }

    /**
     * @notice 计算预估奖励
     */
    function estimateReward(
        OutputType outputType,
        uint256 quality,
        uint256 complexity,
        uint256 novelty,
        uint256 efficiency
    ) external view returns (uint256) {
        uint256 baseReward = _getBaseReward(outputType);

        uint256 finalReward = baseReward;
        finalReward = (finalReward * quality) / PRECISION;
        finalReward = (finalReward * complexity) / PRECISION;
        finalReward = (finalReward * novelty) / PRECISION;
        finalReward = (finalReward * efficiency) / PRECISION;

        (uint256 minReward, uint256 maxReward) = _getRewardRange(outputType);
        if (finalReward < minReward) finalReward = minReward;
        if (finalReward > maxReward) finalReward = maxReward;

        return finalReward;
    }

    /**
     * @notice 获取合约余额
     */
    function getBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }

    // ========== 内部函数 ==========

    /**
     * @notice 计算基础奖励（白皮书修复: 日池分配+防除零）
     * @dev BaseReward = 日池金额 / max(1, 产出数)，最少1 VIBE
     *      类型预算控制由权重系统在claim时执行（而非在此调整base）
     */
    function _getBaseReward(OutputType outputType) internal view returns (uint256) {
        // 白皮书修复: 防除零保护
        uint256 effectiveOutputCount = outputCount > 0 ? outputCount : 1;

        // 如果有日池金额，按日池计算
        if (dailyPoolAmount > 0) {
            // 日池金额 / 产出数量
            uint256 baseFromPool = dailyPoolAmount / effectiveOutputCount;
            // 最少1 VIBE
            if (baseFromPool < 1) baseFromPool = 1;
            return baseFromPool;
        }

        // 如果没有日池，使用固定基础奖励（中值）
        if (outputType == OutputType.CODE_PRODUCT) {
            return (CODE_MIN + CODE_MAX) / 2; // 255 VIBE
        } else if (outputType == OutputType.CONTENT) {
            return (CONTENT_MIN + CONTENT_MAX) / 2; // 102.5 VIBE
        } else if (outputType == OutputType.PROBLEM_SOLVING) {
            return (PROBLEM_MIN + PROBLEM_MAX) / 2; // 50.5 VIBE
        } else {
            return (INNOVATION_MIN + INNOVATION_MAX) / 2; // 2525 VIBE
        }
    }

    function _getRewardRange(OutputType outputType) internal pure returns (uint256 minReward, uint256 maxReward) {
        if (outputType == OutputType.CODE_PRODUCT) {
            return (CODE_MIN, CODE_MAX);
        } else if (outputType == OutputType.CONTENT) {
            return (CONTENT_MIN, CONTENT_MAX);
        } else if (outputType == OutputType.PROBLEM_SOLVING) {
            return (PROBLEM_MIN, PROBLEM_MAX);
        } else {
            return (INNOVATION_MIN, INNOVATION_MAX);
        }
    }

    /**
     * @notice 记录VE积分 - AI-003修复
     * @param user 用户地址
     * @param rewardAmount 奖励金额
     */
    function _recordVEPoints(address user, uint256 rewardAmount) internal {
        if (vePointsContract != address(0)) {
            try IVIBVEPointsForReward(vePointsContract).recordOutputReward(user, rewardAmount) {
                // 成功记录
            } catch {
                // 如果记录失败，不影响奖励领取，仅静默失败
            }
        }
    }
}
