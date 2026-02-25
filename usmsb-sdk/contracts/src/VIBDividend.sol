// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBDividend
 * @notice VIBE 分红合约
 * @dev 将交易手续费的 20% 分配给质押者
 *      按质押量比例分配
 */
contract VIBDividend is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 精度因子
    uint256 public constant PRECISION = 1e18;

    /// @notice 提取冷却期 (1天)
    uint256 public constant CLAIM_COOLDOWN = 1 days;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 质押合约地址
    address public stakingContract;

    /// @notice 累计分红每质押代币
    uint256 public dividendPerTokenStored;

    /// @notice 上次更新快照时间
    uint256 public lastUpdateTime;

    /// @notice 用户待领取分红
    mapping(address => uint256) public pendingDividends;

    /// @notice 用户上次领取时的分红每代币
    mapping(address => uint256) public dividendPerTokenPaid;

    /// @notice 用户上次领取时间
    mapping(address => uint256) public lastClaimTime;

    /// @notice 累计已分配分红
    uint256 public totalDividendsDistributed;

    /// @notice 合约中可用分红余额
    uint256 public dividendBalance;

    // ========== 事件 ==========

    /// @notice 分红存入事件
    event DividendDeposited(
        address indexed from,
        uint256 amount,
        uint256 dividendPerToken
    );

    /// @notice 分红领取事件
    event DividendClaimed(
        address indexed user,
        uint256 amount
    );

    /// @notice 质押合约地址更新
    event StakingContractUpdated(
        address indexed oldAddress,
        address indexed newAddress
    );

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _vibeToken VIBE 代币地址
     */
    constructor(address _vibeToken) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBDividend: invalid token address");
        vibeToken = IERC20(_vibeToken);
        lastUpdateTime = block.timestamp;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 接收分红（从 VIBEToken 合约自动调用）
     * @param amount 分红金额
     */
    function receiveDividend(uint256 amount) external {
        require(amount > 0, "VIBDividend: amount must be greater than 0");

        // 从调用者转账代币到合约
        vibeToken.safeTransferFrom(msg.sender, address(this), amount);

        // 更新全局分红
        _updateDividend();

        dividendBalance += amount;

        emit DividendDeposited(msg.sender, amount, dividendPerTokenStored);
    }

    /**
     * @notice 领取分红
     */
    function claimDividend() external nonReentrant whenNotPaused {
        require(
            block.timestamp >= lastClaimTime[msg.sender] + CLAIM_COOLDOWN,
            "VIBDividend: claim cooldown not reached"
        );

        _updateDividend();

        uint256 pending = pendingDividends[msg.sender];
        require(pending > 0, "VIBDividend: no pending dividends");

        // 清除待领取
        pendingDividends[msg.sender] = 0;

        // 更新领取快照
        dividendPerTokenPaid[msg.sender] = dividendPerTokenStored;
        lastClaimTime[msg.sender] = block.timestamp;

        // 转账
        vibeToken.safeTransfer(msg.sender, pending);

        emit DividendClaimed(msg.sender, pending);
    }

    /**
     * @notice 批量领取分红（用于合约升级等场景）
     * @param users 用户地址列表
     */
    function batchClaimDividend(address[] calldata users) external nonReentrant whenNotPaused {
        _updateDividend();

        for (uint256 i = 0; i < users.length; i++) {
            address user = users[i];
            uint256 pending = pendingDividends[user];

            if (pending > 0 &&
                block.timestamp >= lastClaimTime[user] + CLAIM_COOLDOWN) {

                pendingDividends[user] = 0;
                dividendPerTokenPaid[user] = dividendPerTokenStored;
                lastClaimTime[user] = block.timestamp;

                vibeToken.safeTransfer(user, pending);

                emit DividendClaimed(user, pending);
            }
        }
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置质押合约地址
     * @param _stakingContract 质押合约地址
     */
    function setStakingContract(address _stakingContract) external onlyOwner {
        require(_stakingContract != address(0), "VIBDividend: invalid address");
        emit StakingContractUpdated(stakingContract, _stakingContract);
        stakingContract = _stakingContract;
    }

    /**
     * @notice 暂停合约
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice 恢复合约
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 紧急提取代币
     * @param token 代币地址
     * @param to 目标地址
     * @param amount 金额
     */
    function emergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner {
        require(to != address(0), "VIBDividend: invalid address");

        if (token == address(0)) {
            payable(to).transfer(amount);
        } else {
            IERC20(token).safeTransfer(to, amount);
        }
    }

    // ========== 内部函数 ==========

    /**
     * @notice 更新全局分红
     */
    function _updateDividend() internal {
        if (address(stakingContract) == address(0)) {
            return;
        }

        // 获取质押总量
        uint256 totalStaked = _getTotalStaked();

        if (totalStaked == 0) {
            lastUpdateTime = block.timestamp;
            return;
        }

        uint256 timeElapsed = block.timestamp - lastUpdateTime;
        if (timeElapsed == 0) {
            return;
        }

        // 计算新增分红（按时间比例）
        // 这里简化处理，实际应该根据实际收到的分红计算
        // dividendPerTokenStored += (新增分红 * PRECISION) / totalStaked
        // 这里暂时不自动更新，由 receiveDividend 触发

        lastUpdateTime = block.timestamp;
    }

    /**
     * @notice 获取质押总量
     * @return 质押总量
     */
    function _getTotalStaked() internal view returns (uint256) {
        // 如果设置了质押合约，从质押合约获取
        // 这里简化处理，返回 0，实际需要调用质押合约
        if (stakingContract != address(0)) {
            // 调用质押合约的 totalStaked
            (bool success, bytes memory data) = stakingContract.staticcall(
                abi.encodeWithSignature("totalStaked()")
            );
            if (success) {
                return abi.decode(data, (uint256));
            }
        }
        return 0;
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取用户可领取分红
     * @param user 用户地址
     * @return 可领取分红金额
     */
    function getPendingDividend(address user) external view returns (uint256) {
        uint256 totalStaked = _getTotalStaked();
        if (totalStaked == 0) {
            return pendingDividends[user];
        }

        uint256 dividendPerToken = dividendPerTokenStored;
        uint256 pending = pendingDividends[user];

        // 计算自上次领取后的新增分红
        uint256 newDividend = ((dividendPerToken - dividendPerTokenPaid[user]) *
            totalStaked) / PRECISION;

        return pending + newDividend;
    }

    /**
     * @notice 获取合约余额
     * @return 合约余额
     */
    function getBalance() external view returns (uint256) {
        return dividendBalance;
    }
}
