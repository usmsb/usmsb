// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title VIBVesting
 * @notice VIBE 代币多受益人锁仓合约，支持线性释放
 * @dev 支持团队、早期支持者、激励池等多类受益人
 */
contract VIBVesting is Ownable, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度
    uint256 public constant PRECISION = 1e18;

    /// @notice 一年的秒数
    uint256 public constant SECONDS_PER_YEAR = 365 days;

    /// @notice 紧急提取延迟时间 (7天) - 安全增强
    uint256 public constant EMERGENCY_WITHDRAW_DELAY = 7 days;

    /// @notice 移除受益人延迟时间 (7天)
    uint256 public constant REMOVE_BENEFICIARY_DELAY = 7 days;

    /// @notice 最大批量大小限制
    uint256 public constant MAX_BATCH_SIZE = 100;

    /// @notice 待提取地址
    address public pendingWithdrawRecipient;

    /// @notice 提取生效时间
    uint256 public withdrawEffectiveTime;

    /// @notice 待移除受益人
    address public pendingBeneficiaryRemoval;

    /// @notice 移除受益人生效时间
    uint256 public beneficiaryRemovalEffectiveTime;

    // ========== 受益人类型 ==========

    /// @notice 受益人类型
    enum BeneficiaryType {
        TEAM,           // 团队：4 年锁仓
        EARLY_SUPPORTER // 早期支持者：2 年锁仓
    }

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 受益人数量
    uint256 public beneficiaryCount;

    /// @notice 已释放总额
    uint256 public totalReleased;

    /// @notice 受益人信息
    mapping(address => BeneficiaryInfo) public beneficiaries;

    /// @notice 地址是否为受益人
    mapping(address => bool) public isBeneficiary;

    /// @notice 受益人地址列表
    address[] public beneficiaryList;

    // ========== 结构体 ==========

    /**
     * @notice 受益人信息
     */
    struct BeneficiaryInfo {
        uint256 totalAmount;          // 总分配量
        uint256 releasedAmount;       // 已释放量
        uint256 vestingStart;         // 锁仓开始时间
        uint256 vestingDuration;      // 锁仓持续时间（秒）
        uint256 cliffPeriod;          // 悬崖期（秒）
        uint256 vestingType;          // 受益人类型
        bool isActive;                // 是否活跃
    }

    // ========== 事件 ==========

    /// @notice 受益人添加事件
    event BeneficiaryAdded(
        address indexed beneficiary,
        uint256 amount,
        BeneficiaryType beneficiaryType,
        uint256 vestingStart,
        uint256 vestingDuration,
        uint256 cliffPeriod
    );

    /// @notice 代币释放事件
    event TokensReleased(address indexed beneficiary, uint256 amount);

    /// @notice 受益人移除事件
    event BeneficiaryRemoved(address indexed beneficiary, uint256 remainingAmount);
    event BeneficiaryRemovalInitiated(address indexed beneficiary, uint256 effectiveTime);
    event BeneficiaryRemovalCancelled();

    /// @notice 代币地址更新事件
    event TokenUpdated(address indexed oldToken, address indexed newToken);

    /// @notice 紧急提取事件
    event EmergencyWithdraw(address indexed to, uint256 amount);
    event EmergencyWithdrawInitiated(address indexed to, uint256 effectiveTime);
    event EmergencyWithdrawCancelled();

    // ========== 修饰符 ==========

    /// @notice 只允许受益人调用
    modifier onlyBeneficiary() {
        require(isBeneficiary[msg.sender], "VIBVesting: not a beneficiary");
        _;
    }

    /// @notice 检查受益人是否活跃
    modifier isActiveBeneficiary(address beneficiary) {
        require(
            beneficiaries[beneficiary].isActive,
            "VIBVesting: beneficiary not active"
        );
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _vibeToken VIBE 代币地址
     */
    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBVesting: invalid token address");
        vibeToken = IERC20(_vibeToken);
    }

    // ========== 外部函数 ==========

    /**
     * @notice 添加受益人
     * @param beneficiary 受益人地址
     * @param amount 分配数量
     * @param beneficiaryType 受益人类型
     * @param vestingStart 锁仓开始时间
     * @param vestingDuration 锁仓持续时间
     * @param cliffPeriod 悬崖期
     */
    function addBeneficiary(
        address beneficiary,
        uint256 amount,
        BeneficiaryType beneficiaryType,
        uint256 vestingStart,
        uint256 vestingDuration,
        uint256 cliffPeriod
    ) external onlyOwner {
        require(beneficiary != address(0), "VIBVesting: invalid beneficiary");
        require(amount > 0, "VIBVesting: amount must be positive");
        require(!isBeneficiary[beneficiary], "VIBVesting: beneficiary already exists");

        // CEI 模式：先更新状态，再执行外部调用
        // 存储受益人信息
        beneficiaries[beneficiary] = BeneficiaryInfo({
            totalAmount: amount,
            releasedAmount: 0,
            vestingStart: vestingStart,
            vestingDuration: vestingDuration,
            cliffPeriod: cliffPeriod,
            vestingType: uint256(beneficiaryType),
            isActive: true
        });

        isBeneficiary[beneficiary] = true;
        beneficiaryList.push(beneficiary);
        beneficiaryCount++;

        emit BeneficiaryAdded(
            beneficiary,
            amount,
            beneficiaryType,
            vestingStart,
            vestingDuration,
            cliffPeriod
        );

        // 外部调用放在最后
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
    }

    // ========== 注册受益人（不转移代币，用于distributeToPools后） ==========

    /**
     * @notice 注册单个受益人（不转移代币）
     * @dev 用于代币已通过distributeToPools mint到合约后的场景
     * @param beneficiary 受益人地址
     * @param amount 分配数量
     * @param beneficiaryType 受益人类型
     * @param vestingStart 锁仓开始时间
     * @param vestingDuration 锁仓持续时间
     * @param cliffPeriod 悬崖期
     */
    function registerBeneficiary(
        address beneficiary,
        uint256 amount,
        BeneficiaryType beneficiaryType,
        uint256 vestingStart,
        uint256 vestingDuration,
        uint256 cliffPeriod
    ) external onlyOwner {
        require(beneficiary != address(0), "VIBVesting: invalid beneficiary");
        require(amount > 0, "VIBVesting: amount must be positive");
        require(!isBeneficiary[beneficiary], "VIBVesting: beneficiary already exists");

        // 检查合约余额是否足够
        uint256 totalAllocated = _getTotalAllocated();
        require(
            totalAllocated + amount <= vibeToken.balanceOf(address(this)),
            "VIBVesting: insufficient contract balance"
        );

        beneficiaries[beneficiary] = BeneficiaryInfo({
            totalAmount: amount,
            releasedAmount: 0,
            vestingStart: vestingStart,
            vestingDuration: vestingDuration,
            cliffPeriod: cliffPeriod,
            vestingType: uint256(beneficiaryType),
            isActive: true
        });

        isBeneficiary[beneficiary] = true;
        beneficiaryList.push(beneficiary);
        beneficiaryCount++;

        emit BeneficiaryAdded(
            beneficiary,
            amount,
            beneficiaryType,
            vestingStart,
            vestingDuration,
            cliffPeriod
        );
    }

    /**
     * @notice 批量注册团队成员（不转移代币）
     * @dev 用于代币已通过distributeToPools mint到合约后的场景
     * @param teamMembers 团队成员地址数组
     * @param amounts 分配数量数组
     * @param vestingStart 锁仓开始时间
     */
    function registerTeamMembers(
        address[] calldata teamMembers,
        uint256[] calldata amounts,
        uint256 vestingStart
    ) external onlyOwner {
        // 团队成员：4 年锁仓，1 年悬崖期
        _registerBeneficiaries(
            teamMembers,
            amounts,
            vestingStart,
            BeneficiaryType.TEAM,
            4 * SECONDS_PER_YEAR,  // 4年
            365 days               // 1年悬崖期
        );
    }

    /**
     * @notice 批量注册早期支持者（不转移代币）
     * @dev 用于代币已通过distributeToPools mint到合约后的场景
     * @param supporters 支持者地址数组
     * @param amounts 分配数量数组
     * @param vestingStart 锁仓开始时间
     */
    function registerEarlySupporters(
        address[] calldata supporters,
        uint256[] calldata amounts,
        uint256 vestingStart
    ) external onlyOwner {
        // 早期支持者：2 年锁仓，6 个月悬崖期
        _registerBeneficiaries(
            supporters,
            amounts,
            vestingStart,
            BeneficiaryType.EARLY_SUPPORTER,
            2 * SECONDS_PER_YEAR,  // 2年
            182 days               // 6个月悬崖期
        );
    }

    /**
     * @notice 内部函数：获取已分配总额
     */
    function _getTotalAllocated() internal view returns (uint256) {
        uint256 total = 0;
        for (uint256 i = 0; i < beneficiaryList.length; i++) {
            if (beneficiaries[beneficiaryList[i]].isActive) {
                total += beneficiaries[beneficiaryList[i]].totalAmount;
            }
        }
        return total;
    }

    /**
     * @notice 内部函数：批量注册受益人（不转移代币）
     */
    function _registerBeneficiaries(
        address[] calldata beneficiaries_,
        uint256[] calldata amounts,
        uint256 vestingStart,
        BeneficiaryType beneficiaryType,
        uint256 duration,
        uint256 cliff
    ) internal {
        require(
            beneficiaries_.length == amounts.length,
            "VIBVesting: arrays length mismatch"
        );
        require(beneficiaries_.length > 0, "VIBVesting: empty arrays");
        require(beneficiaries_.length <= MAX_BATCH_SIZE, "VIBVesting: exceeds max batch size");

        // 计算总金额
        uint256 totalAmount = 0;
        for (uint256 i = 0; i < amounts.length; i++) {
            totalAmount += amounts[i];
        }

        // 检查合约余额是否足够
        uint256 currentAllocated = _getTotalAllocated();
        require(
            currentAllocated + totalAmount <= vibeToken.balanceOf(address(this)),
            "VIBVesting: insufficient contract balance"
        );

        // 验证并注册所有受益人
        for (uint256 i = 0; i < beneficiaries_.length; i++) {
            require(beneficiaries_[i] != address(0), "VIBVesting: invalid beneficiary");
            require(amounts[i] > 0, "VIBVesting: amount must be positive");
            require(
                !isBeneficiary[beneficiaries_[i]],
                "VIBVesting: beneficiary already exists"
            );

            beneficiaries[beneficiaries_[i]] = BeneficiaryInfo({
                totalAmount: amounts[i],
                releasedAmount: 0,
                vestingStart: vestingStart,
                vestingDuration: duration,
                cliffPeriod: cliff,
                vestingType: uint256(beneficiaryType),
                isActive: true
            });

            isBeneficiary[beneficiaries_[i]] = true;
            beneficiaryList.push(beneficiaries_[i]);
            beneficiaryCount++;

            emit BeneficiaryAdded(
                beneficiaries_[i],
                amounts[i],
                beneficiaryType,
                vestingStart,
                duration,
                cliff
            );
        }
    }

    /**
     * @notice 释放代币
     */
    function release() external nonReentrant onlyBeneficiary {
        BeneficiaryInfo storage info = beneficiaries[msg.sender];

        uint256 releasable = _releasableAmount(msg.sender);
        require(releasable > 0, "VIBVesting: nothing to release");

        info.releasedAmount += releasable;
        totalReleased += releasable;

        vibeToken.safeTransfer(msg.sender, releasable);

        emit TokensReleased(msg.sender, releasable);
    }

    /**
     * @notice 发起移除受益人（需要时间锁）
     * @param beneficiary 受益人地址
     * @dev 安全增强: 移除需要3天时间锁，防止滥用
     */
    function removeBeneficiary(address beneficiary)
        external
        onlyOwner
        isActiveBeneficiary(beneficiary)
    {
        // 如果有待生效的移除，先取消
        if (pendingBeneficiaryRemoval != address(0)) {
            delete pendingBeneficiaryRemoval;
            delete beneficiaryRemovalEffectiveTime;
            emit BeneficiaryRemovalCancelled();
        }

        // 设置待生效的移除
        pendingBeneficiaryRemoval = beneficiary;
        beneficiaryRemovalEffectiveTime = block.timestamp + REMOVE_BENEFICIARY_DELAY;

        emit BeneficiaryRemovalInitiated(beneficiary, beneficiaryRemovalEffectiveTime);
    }

    /**
     * @notice 确认移除受益人（在延迟期过后）
     * @dev 未释放的代币将保留在合约中，用于其他受益人
     */
    function confirmRemoveBeneficiary() external onlyOwner {
        require(pendingBeneficiaryRemoval != address(0), "VIBVesting: no pending removal");
        require(
            block.timestamp >= beneficiaryRemovalEffectiveTime,
            "VIBVesting: removal not yet effective"
        );

        address beneficiary = pendingBeneficiaryRemoval;
        BeneficiaryInfo storage info = beneficiaries[beneficiary];

        // 检查受益人仍然活跃
        require(info.isActive, "VIBVesting: beneficiary not active");

        // 记录未释放的代币数量（保留在合约中）
        uint256 remaining = info.totalAmount - info.releasedAmount;

        // 更新状态
        info.isActive = false;
        isBeneficiary[beneficiary] = false;
        beneficiaryCount--;

        // 清除待生效状态
        delete pendingBeneficiaryRemoval;
        delete beneficiaryRemovalEffectiveTime;

        emit BeneficiaryRemoved(beneficiary, remaining);
    }

    /**
     * @notice 取消待生效的移除
     */
    function cancelBeneficiaryRemoval() external onlyOwner {
        require(pendingBeneficiaryRemoval != address(0), "VIBVesting: no pending removal");

        delete pendingBeneficiaryRemoval;
        delete beneficiaryRemovalEffectiveTime;

        emit BeneficiaryRemovalCancelled();
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 更新 VIBE 代币地址
     * @param _vibeToken 新的代币地址
     */
    function setVibeToken(address _vibeToken) external onlyOwner {
        require(_vibeToken != address(0), "VIBVesting: invalid token address");
        emit TokenUpdated(address(vibeToken), _vibeToken);
        vibeToken = IERC20(_vibeToken);
    }

    /**
     * @notice 紧急提取所有代币（仅限紧急情况）
     * @param to 接收地址
     */
    function emergencyWithdraw(address to) external onlyOwner {
        require(to != address(0), "VIBVesting: invalid recipient");

        // 如果有待生效的提取，先取消
        if (pendingWithdrawRecipient != address(0)) {
            delete pendingWithdrawRecipient;
            delete withdrawEffectiveTime;
            emit EmergencyWithdrawCancelled();
        }

        // 设置待生效的提取
        pendingWithdrawRecipient = to;
        withdrawEffectiveTime = block.timestamp + EMERGENCY_WITHDRAW_DELAY;

        emit EmergencyWithdrawInitiated(to, withdrawEffectiveTime);
    }

    /**
     * @notice 确认紧急提取（在延迟期过后）
     * @dev 只能提取未归属的代币，已归属但未领取的代币受保护
     */
    function confirmEmergencyWithdraw() external onlyOwner {
        require(pendingWithdrawRecipient != address(0), "VIBVesting: no pending withdraw");
        require(
            block.timestamp >= withdrawEffectiveTime,
            "VIBVesting: withdraw not yet effective"
        );

        address recipient = pendingWithdrawRecipient;
        uint256 balance = vibeToken.balanceOf(address(this));

        // 计算已归属但未领取的代币总额（这些代币受保护）
        uint256 totalVestedUnclaimed = 0;
        for (uint256 i = 0; i < beneficiaryList.length; i++) {
            address beneficiary = beneficiaryList[i];
            if (beneficiaries[beneficiary].isActive) {
                totalVestedUnclaimed += _releasableAmount(beneficiary);
            }
        }

        // 只能提取未归属的代币
        uint256 withdrawable = balance > totalVestedUnclaimed
            ? balance - totalVestedUnclaimed
            : 0;

        // 清除状态
        delete pendingWithdrawRecipient;
        delete withdrawEffectiveTime;

        if (withdrawable > 0) {
            vibeToken.safeTransfer(recipient, withdrawable);
        }

        emit EmergencyWithdraw(recipient, withdrawable);
    }

    /**
     * @notice 取消待生效的紧急提取
     */
    function cancelEmergencyWithdraw() external onlyOwner {
        require(pendingWithdrawRecipient != address(0), "VIBVesting: no pending withdraw");

        delete pendingWithdrawRecipient;
        delete withdrawEffectiveTime;

        emit EmergencyWithdrawCancelled();
    }

    // ========== 公共视图函数 ==========

    /**
     * @notice 计算可释放金额
     * @param beneficiary 受益人地址
     * @return 可释放金额
     */
    function _releasableAmount(address beneficiary) internal view returns (uint256) {
        BeneficiaryInfo memory info = beneficiaries[beneficiary];

        uint256 currentBalance = vibeToken.balanceOf(address(this));

        uint256 vestedAmount = _vestedAmount(beneficiary);
        uint256 releasable = vestedAmount - info.releasedAmount;

        // 确保不超过合约余额
        if (releasable > currentBalance) {
            releasable = currentBalance;
        }

        return releasable;
    }

    /**
     * @notice 计算已归属金额
     * @param beneficiary 受益人地址
     * @return 已归属金额
     */
    function _vestedAmount(address beneficiary) internal view returns (uint256) {
        BeneficiaryInfo memory info = beneficiaries[beneficiary];

        uint256 totalAllocation = info.totalAmount;

        // 如果未到开始时间，返回 0
        if (block.timestamp < info.vestingStart) {
            return 0;
        }

        uint256 elapsedTime = block.timestamp - info.vestingStart;

        // 如果在悬崖期内，返回 0
        if (elapsedTime < info.cliffPeriod) {
            return 0;
        }

        // 如果超过锁仓期，返回全部
        if (elapsedTime >= info.vestingDuration) {
            return totalAllocation;
        }

        // 线性释放计算
        uint256 vestedTime = elapsedTime - info.cliffPeriod;
        uint256 vestingTime = info.vestingDuration - info.cliffPeriod;

        return (totalAllocation * vestedTime) / vestingTime;
    }

    /**
     * @notice 获取受益人信息
     * @param beneficiary 受益人地址
     * @return 受益人信息
     */
    function getBeneficiaryInfo(address beneficiary)
        external
        view
        returns (BeneficiaryInfo memory)
    {
        return beneficiaries[beneficiary];
    }

    /**
     * @notice 获取可释放金额
     * @param beneficiary 受益人地址
     * @return 可释放金额
     */
    function getReleasableAmount(address beneficiary) external view returns (uint256) {
        return _releasableAmount(beneficiary);
    }

    /**
     * @notice 获取已归属金额
     * @param beneficiary 受益人地址
     * @return 已归属金额
     */
    function getVestedAmount(address beneficiary) external view returns (uint256) {
        return _vestedAmount(beneficiary);
    }

    /**
     * @notice 获取受益人列表
     * @param offset 偏移量
     * @param limit 数量限制
     * @return 受益人地址列表
     */
    function getBeneficiaries(uint256 offset, uint256 limit)
        external
        view
        returns (address[] memory)
    {
        require(offset < beneficiaryList.length, "VIBVesting: offset out of bounds");
        uint256 end = offset + limit;
        if (end > beneficiaryList.length) {
            end = beneficiaryList.length;
        }

        address[] memory result = new address[](end - offset);
        for (uint256 i = offset; i < end; i++) {
            result[i - offset] = beneficiaryList[i];
        }
        return result;
    }

    /**
     * @notice 获取合约代币余额
     * @return 合约持有的代币数量
     */
    function contractBalance() external view returns (uint256) {
        return vibeToken.balanceOf(address(this));
    }
}
