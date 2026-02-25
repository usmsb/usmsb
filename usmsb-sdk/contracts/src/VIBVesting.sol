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

    // ========== 受益人类型 ==========

    /// @notice 受益人类型
    enum BeneficiaryType {
        TEAM,           // 团队：4 年锁仓
        EARLY_SUPPORTER,// 早期支持者：2 年锁仓
        INCENTIVE_POOL, // 激励池：5 年线性释放
        ADVISOR,        // 顾问：2 年锁仓
        PARTNER         // 合作伙伴：3 年锁仓
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

    /// @notice 代币地址更新事件
    event TokenUpdated(address indexed oldToken, address indexed newToken);

    /// @notice 紧急提取事件
    event EmergencyWithdraw(address indexed to, uint256 amount);

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

        // 转入代币
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

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
    }

    /**
     * @notice 批量添加受益人（团队）
     * @param teamMembers 团队成员地址数组
     * @param amounts 分配数量数组
     * @param vestingStart 锁仓开始时间
     */
    function addTeamMembers(
        address[] calldata teamMembers,
        uint256[] calldata amounts,
        uint256 vestingStart
    ) external onlyOwner {
        require(
            teamMembers.length == amounts.length,
            "VIBVesting: arrays length mismatch"
        );
        require(teamMembers.length > 0, "VIBVesting: empty arrays");

        for (uint256 i = 0; i < teamMembers.length; i++) {
            require(teamMembers[i] != address(0), "VIBVesting: invalid beneficiary");
            require(amounts[i] > 0, "VIBVesting: amount must be positive");
            require(
                !isBeneficiary[teamMembers[i]],
                "VIBVesting: beneficiary already exists"
            );

            // 转入代币
            vibeToken.safeTransferFrom(msg.sender, address(this), amounts[i]);

            // 团队成员：4 年锁仓，1 年悬崖期
            uint256 cliff = 365 days;
            uint256 duration = 4 * SECONDS_PER_YEAR;

            beneficiaries[teamMembers[i]] = BeneficiaryInfo({
                totalAmount: amounts[i],
                releasedAmount: 0,
                vestingStart: vestingStart,
                vestingDuration: duration,
                cliffPeriod: cliff,
                vestingType: uint256(BeneficiaryType.TEAM),
                isActive: true
            });

            isBeneficiary[teamMembers[i]] = true;
            beneficiaryList.push(teamMembers[i]);
            beneficiaryCount++;

            emit BeneficiaryAdded(
                teamMembers[i],
                amounts[i],
                BeneficiaryType.TEAM,
                vestingStart,
                duration,
                cliff
            );
        }
    }

    /**
     * @notice 添加早期支持者
     * @param supporters 支持者地址数组
     * @param amounts 分配数量数组
     * @param vestingStart 锁仓开始时间
     */
    function addEarlySupporters(
        address[] calldata supporters,
        uint256[] calldata amounts,
        uint256 vestingStart
    ) external onlyOwner {
        require(
            supporters.length == amounts.length,
            "VIBVesting: arrays length mismatch"
        );
        require(supporters.length > 0, "VIBVesting: empty arrays");

        for (uint256 i = 0; i < supporters.length; i++) {
            require(supporters[i] != address(0), "VIBVesting: invalid beneficiary");
            require(amounts[i] > 0, "VIBVesting: amount must be positive");
            require(
                !isBeneficiary[supporters[i]],
                "VIBVesting: beneficiary already exists"
            );

            vibeToken.safeTransferFrom(msg.sender, address(this), amounts[i]);

            // 早期支持者：2 年锁仓，6 个月悬崖期
            uint256 cliff = 180 days;
            uint256 duration = 2 * SECONDS_PER_YEAR;

            beneficiaries[supporters[i]] = BeneficiaryInfo({
                totalAmount: amounts[i],
                releasedAmount: 0,
                vestingStart: vestingStart,
                vestingDuration: duration,
                cliffPeriod: cliff,
                vestingType: uint256(BeneficiaryType.EARLY_SUPPORTER),
                isActive: true
            });

            isBeneficiary[supporters[i]] = true;
            beneficiaryList.push(supporters[i]);
            beneficiaryCount++;

            emit BeneficiaryAdded(
                supporters[i],
                amounts[i],
                BeneficiaryType.EARLY_SUPPORTER,
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
     * @notice 移除受益人（未释放部分返还给发送者）
     * @param beneficiary 受益人地址
     */
    function removeBeneficiary(address beneficiary)
        external
        onlyOwner
        isActiveBeneficiary(beneficiary)
    {
        BeneficiaryInfo storage info = beneficiaries[beneficiary];

        uint256 remaining = info.totalAmount - info.releasedAmount;

        // 如果有未释放代币，返还给发送者
        if (remaining > 0) {
            vibeToken.safeTransfer(msg.sender, remaining);
        }

        // 更新状态
        info.isActive = false;
        isBeneficiary[beneficiary] = false;
        beneficiaryCount--;

        emit BeneficiaryRemoved(beneficiary, remaining);
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

        uint256 balance = vibeToken.balanceOf(address(this));
        vibeToken.safeTransfer(to, balance);

        emit EmergencyWithdraw(to, balance);
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
