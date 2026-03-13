// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title AirdropDistributor
 * @notice 空投分发合约
 * @dev 功能：
 *      - Merkle 树验证
 *      - 二阶梯时间机制（前6月100%，7-12月50%）
 *      - 未领取代币自动转入社区稳定基金
 */
contract AirdropDistributor is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 正常期时长 (6个月)
    uint256 public constant NORMAL_PERIOD = 180 days;

    /// @notice 延迟期时长 (6个月)
    uint256 public constant DELAY_PERIOD = 180 days;

    /// @notice 延迟期可领取比例 (50%)
    uint256 public constant DELAY_PERIOD_RATIO = 5000; // 50% = 5000/10000

    /// @notice 精度
    uint256 public constant PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice VIBE 代币
    IERC20 public vibeToken;

    /// @notice 社区稳定基金地址
    address public communityStableFund;

    /// @notice Merkle 根
    bytes32 public merkleRoot;

    /// @notice 开始时间
    uint256 public startTime;

    /// @notice 结束时间
    uint256 public endTime;

    /// @notice 已领取的用户
    mapping(address => bool) public claimed;

    /// @notice 总领取量
    uint256 public totalClaimed;

    /// @notice 领取人数
    uint256 public claimerCount;

    /// @notice 是否已回收未领取
    bool public swept;

    // ========== 事件 ==========

    event Claimed(
        address indexed user,
        uint256 amount,
        uint256 userAmount,
        uint256 fundAmount
    );

    event MerkleRootUpdated(bytes32 newRoot);

    event UnclaimedSwept(uint256 amount, address to);

    // ========== 构造函数 ==========

    constructor(
        address _vibeToken,
        address _communityStableFund,
        bytes32 _merkleRoot
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "Invalid token");
        require(_communityStableFund != address(0), "Invalid fund");

        vibeToken = IERC20(_vibeToken);
        communityStableFund = _communityStableFund;
        merkleRoot = _merkleRoot;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 开始空投
     */
    function startAirdrop() external onlyOwner {
        require(startTime == 0, "Already started");
        startTime = block.timestamp;
        endTime = block.timestamp + NORMAL_PERIOD + DELAY_PERIOD;
    }

    /**
     * @notice 领取空投
     * @param amount 分配数量
     * @param proof Merkle 证明
     */
    function claim(uint256 amount, bytes32[] calldata proof) external nonReentrant whenNotPaused {
        require(startTime > 0, "Airdrop not started");
        require(block.timestamp <= endTime, "Airdrop ended");
        require(!claimed[msg.sender], "Already claimed");

        // 验证 Merkle 证明
        require(_verifyProof(msg.sender, amount, proof), "Invalid proof");

        // 标记已领取
        claimed[msg.sender] = true;

        // 计算可领取数量
        (uint256 userAmount, uint256 fundAmount) = _calculateClaimAmount(amount);

        require(userAmount > 0, "Nothing to claim");

        // 转账给用户
        vibeToken.safeTransfer(msg.sender, userAmount);

        // 延迟期的另一半自动转入稳定基金
        if (fundAmount > 0) {
            vibeToken.safeTransfer(communityStableFund, fundAmount);
        }

        totalClaimed += userAmount;
        claimerCount++;

        emit Claimed(msg.sender, amount, userAmount, fundAmount);
    }

    /**
     * @notice 回收未领取的代币
     * @dev 12个月后任何人都可以触发
     */
    function sweepUnclaimed() external nonReentrant {
        require(startTime > 0, "Airdrop not started");
        require(block.timestamp > endTime, "Airdrop not ended");
        require(!swept, "Already swept");

        swept = true;

        uint256 remaining = vibeToken.balanceOf(address(this));
        if (remaining > 0) {
            vibeToken.safeTransfer(communityStableFund, remaining);
            emit UnclaimedSwept(remaining, communityStableFund);
        }
    }

    /**
     * @notice 查询可领取数量
     */
    function getClaimableAmount(address user, uint256 amount) external view returns (
        uint256 userAmount,
        uint256 fundAmount,
        string memory status
    ) {
        if (claimed[user]) {
            return (0, 0, "Already claimed");
        }

        if (startTime == 0) {
            return (0, 0, "Not started");
        }

        if (block.timestamp > endTime) {
            return (0, 0, "Ended");
        }

        (userAmount, fundAmount) = _calculateClaimAmount(amount);
        return (userAmount, fundAmount, "Claimable");
    }

    /**
     * @notice 获取当前阶段
     */
    function getCurrentPhase() external view returns (
        string memory phase,
        uint256 ratio,
        uint256 timeRemaining
    ) {
        if (startTime == 0) {
            return ("Not started", 0, 0);
        }

        uint256 elapsed = block.timestamp - startTime;

        if (elapsed < NORMAL_PERIOD) {
            return ("Normal (100%)", 10000, NORMAL_PERIOD - elapsed);
        } else if (elapsed < NORMAL_PERIOD + DELAY_PERIOD) {
            return ("Delay (50%)", DELAY_PERIOD_RATIO, NORMAL_PERIOD + DELAY_PERIOD - elapsed);
        } else {
            return ("Ended", 0, 0);
        }
    }

    // ========== 管理员函数 ==========

    function setMerkleRoot(bytes32 _merkleRoot) external onlyOwner {
        require(startTime == 0, "Airdrop already started");
        merkleRoot = _merkleRoot;
        emit MerkleRootUpdated(_merkleRoot);
    }

    function setCommunityStableFund(address _fund) external onlyOwner {
        require(_fund != address(0), "Invalid fund address");
        communityStableFund = _fund;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // ========== 内部函数 ==========

    /**
     * @notice 计算领取数量
     */
    function _calculateClaimAmount(uint256 amount) internal view returns (
        uint256 userAmount,
        uint256 fundAmount
    ) {
        uint256 elapsed = block.timestamp - startTime;

        if (elapsed < NORMAL_PERIOD) {
            // 正常期：100%
            userAmount = amount;
            fundAmount = 0;
        } else if (elapsed < NORMAL_PERIOD + DELAY_PERIOD) {
            // 延迟期：50%
            userAmount = (amount * DELAY_PERIOD_RATIO) / PRECISION;
            fundAmount = amount - userAmount;
        } else {
            // 已结束
            userAmount = 0;
            fundAmount = amount;
        }
    }

    /**
     * @notice 验证 Merkle 证明
     */
    function _verifyProof(
        address user,
        uint256 amount,
        bytes32[] calldata proof
    ) internal view returns (bool) {
        bytes32 leaf = keccak256(abi.encodePacked(user, amount));
        return _verify(leaf, proof);
    }

    /**
     * @notice Merkle 树验证
     */
    function _verify(bytes32 leaf, bytes32[] memory proof) internal view returns (bool) {
        bytes32 computedHash = leaf;

        for (uint256 i = 0; i < proof.length; i++) {
            bytes32 proofElement = proof[i];

            if (computedHash <= proofElement) {
                computedHash = keccak256(abi.encodePacked(computedHash, proofElement));
            } else {
                computedHash = keccak256(abi.encodePacked(proofElement, computedHash));
            }
        }

        return computedHash == merkleRoot;
    }

    // ========== 视图函数 ==========

    function getStats() external view returns (
        uint256 _totalClaimed,
        uint256 _claimerCount,
        uint256 _remaining,
        uint256 _startTime,
        uint256 _endTime,
        bool _swept
    ) {
        _totalClaimed = totalClaimed;
        _claimerCount = claimerCount;
        _remaining = vibeToken.balanceOf(address(this));
        _startTime = startTime;
        _endTime = endTime;
        _swept = swept;
    }
}
