// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBTreasury
 * @notice VIBE 生态基金财政库合约
 * @dev 管理生态基金、社区稳定基金、协议运营基金
 *      支持多签决策
 */
contract VIBTreasury is Ownable, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 基金类型
    enum FundType {
        ECOSYSTEM,      // 生态基金
        COMMUNITY_STABLE, // 社区稳定基金
        PROTOCOL        // 协议运营基金
    }

    /// @notice 支出类别
    enum Category {
        DEVELOPMENT_GRANT,  // 开发者激励
        ECOSYSTEM_INVEST,  // 生态项目投资
        MARKETING,         // 市场推广
        COMMUNITY_OPS,     // 社区运营
        LEGAL,             // 法律/合规
        EMERGENCY          // 紧急支出
    }

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    IERC20 public vibeToken;

    /// @notice 多签钱包成员列表
    address[] public signers;

    /// @notice 多签成员映射
    mapping(address => bool) public isSigner;

    /// @notice 签名阈值 (需要 N 个签名才能执行)
    uint256 public requiredSignatures;

    /// @notice 基金余额
    mapping(FundType => uint256) public fundBalances;

    /// @notice 待处理支出提案
    mapping(bytes32 => SpendProposal) public spendProposals;

    /// @notice 提案签名
    mapping(bytes32 => mapping(address => bool)) public hasSigned;

    /// @notice 提案签名计数
    mapping(bytes32 => uint256) public proposalSignatures;

    /// @notice 是否启用时间锁
    bool public timelockEnabled = true;

    /// @notice 时间锁时长 (24小时)
    uint256 public timelockDuration = 24 hours;

    /// @notice 紧急解锁时间锁时长 (6小时)
    uint256 public constant EMERGENCY_TIMELOCK_DURATION = 6 hours;

    /// @notice 待提取结构
    struct PendingWithdraw {
        address token;
        address to;
        uint256 amount;
        uint256 effectiveTime;
    }

    /// @notice 待生效的紧急提取
    PendingWithdraw public pendingEmergencyWithdraw;

    /// @notice 紧急解锁所需签名比例 (66%，即2/3)
    uint256 public constant EMERGENCY_SIGNATURE_THRESHOLD = 66;

    /// @notice 时间锁释放时间
    mapping(bytes32 => uint256) public timelockReleaseTimes;

    /// @notice 紧急解锁提案标记
    mapping(bytes32 => bool) public emergencyExecuted;

    // ========== 结构体 ==========

    /**
     * @notice 支出提案
     */
    struct SpendProposal {
        bytes32 id;              // 提案 ID
        FundType fundType;       // 基金类型
        Category category;       // 支出类别
        address recipient;       // 接收者
        uint256 amount;          // 金额
        string description;      // 描述
        uint256 createdAt;      // 创建时间
        uint256 executeAfter;   // 可执行时间
        uint256 signatureCount; // 签名数量
        bool executed;           // 是否已执行
        bool cancelled;          // 是否已取消
    }

    // ========== 事件 ==========

    /// @notice 存款事件
    event Deposit(
        FundType indexed fundType,
        address indexed from,
        uint256 amount
    );

    /// @notice 支出提案创建事件
    event SpendProposalCreated(
        bytes32 indexed proposalId,
        FundType fundType,
        Category category,
        address recipient,
        uint256 amount
    );

    /// @notice 提案签名事件
    event ProposalSigned(
        bytes32 indexed proposalId,
        address indexed signer
    );

    /// @notice 提案执行事件
    event SpendProposalExecuted(
        bytes32 indexed proposalId,
        address indexed executor
    );

    /// @notice 紧急提案执行事件
    event EmergencyProposalExecuted(
        bytes32 indexed proposalId,
        uint256 signatureCount
    );

    /// @notice 提案取消事件
    event SpendProposalCancelled(
        bytes32 indexed proposalId,
        address indexed canceller
    );

    /// @notice 签名阈值更新
    event ThresholdUpdated(uint256 oldThreshold, uint256 newThreshold);

    /// @notice 签名者更新
    event SignerUpdated(address indexed signer, bool isAdded);

    /// @notice 时间锁设置更新
    event TimelockUpdated(bool enabled, uint256 duration);
    event EmergencyWithdrawInitiated(address indexed token, address indexed to, uint256 amount, uint256 effectiveTime);
    event EmergencyWithdrawConfirmed(address indexed token, address indexed to, uint256 amount);
    event EmergencyWithdrawCancelled();

    // ========== 修饰符 =========-

    /// @notice 只允许签名者调用
    modifier onlySigner() {
        require(isSigner[msg.sender], "VIBTreasury: not a signer");
        _;
    }

    /// @notice 检查提案是否存在
    modifier proposalExists(bytes32 proposalId) {
        require(spendProposals[proposalId].createdAt > 0, "VIBTreasury: proposal not exists");
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _vibeToken VIBE 代币地址
     * @param _signers 签名者地址列表
     * @param _requiredSignatures 需要的签名数量
     */
    constructor(
        address _vibeToken,
        address[] memory _signers,
        uint256 _requiredSignatures
    ) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBTreasury: invalid token address");
        // 安全修复: 要求至少3个签名者和至少2个必需签名
        require(
            _signers.length >= 3,
            "VIBTreasury: need at least 3 signers"
        );
        require(
            _requiredSignatures >= 2,
            "VIBTreasury: need at least 2 required signatures"
        );
        require(
            _requiredSignatures <= _signers.length,
            "VIBTreasury: threshold exceeds signers"
        );

        vibeToken = IERC20(_vibeToken);
        signers = _signers;
        requiredSignatures = _requiredSignatures;

        for (uint256 i = 0; i < _signers.length; i++) {
            require(_signers[i] != address(0), "VIBTreasury: invalid signer address");
            require(!isSigner[_signers[i]], "VIBTreasury: duplicate signer");
            isSigner[_signers[i]] = true;
        }
    }

    // ========== 外部函数 ==========

    /**
     * @notice 存款到指定基金
     * @param fundType 基金类型
     * @param amount 金额
     */
    function deposit(FundType fundType, uint256 amount) external nonReentrant whenNotPaused {
        require(amount > 0, "VIBTreasury: amount must be greater than 0");

        vibeToken.safeTransferFrom(msg.sender, address(this), amount);
        fundBalances[fundType] += amount;

        emit Deposit(fundType, msg.sender, amount);
    }

    /**
     * @notice 创建支出提案
     * @param fundType 基金类型
     * @param category 支出类别
     * @param recipient 接收者
     * @param amount 金额
     * @param description 描述
     * @return 提案 ID
     */
    function createSpendProposal(
        FundType fundType,
        Category category,
        address recipient,
        uint256 amount,
        string memory description
    ) external onlySigner nonReentrant whenNotPaused returns (bytes32) {
        require(recipient != address(0), "VIBTreasury: invalid recipient");
        require(amount > 0, "VIBTreasury: amount must be greater than 0");
        require(
            fundBalances[fundType] >= amount,
            "VIBTreasury: insufficient fund balance"
        );

        bytes32 proposalId = keccak256(
            abi.encode(
                fundType,
                category,
                recipient,
                amount,
                block.timestamp,
                msg.sender
            )
        );

        uint256 executeAfter = timelockEnabled
            ? block.timestamp + timelockDuration
            : block.timestamp;

        spendProposals[proposalId] = SpendProposal({
            id: proposalId,
            fundType: fundType,
            category: category,
            recipient: recipient,
            amount: amount,
            description: description,
            createdAt: block.timestamp,
            executeAfter: executeAfter,
            signatureCount: 1,
            executed: false,
            cancelled: false
        });

        hasSigned[proposalId][msg.sender] = true;

        emit SpendProposalCreated(proposalId, fundType, category, recipient, amount);
        emit ProposalSigned(proposalId, msg.sender);

        return proposalId;
    }

    /**
     * @notice 签名提案
     * @param proposalId 提案 ID
     */
    function signProposal(bytes32 proposalId)
        external
        onlySigner
        nonReentrant
        proposalExists(proposalId)
    {
        SpendProposal storage proposal = spendProposals[proposalId];

        require(!proposal.executed, "VIBTreasury: already executed");
        require(!proposal.cancelled, "VIBTreasury: already cancelled");
        require(!hasSigned[proposalId][msg.sender], "VIBTreasury: already signed");

        hasSigned[proposalId][msg.sender] = true;
        proposal.signatureCount++;

        emit ProposalSigned(proposalId, msg.sender);
    }

    /**
     * @notice 执行提案
     * @param proposalId 提案 ID
     */
    function executeProposal(bytes32 proposalId)
        external
        onlySigner
        nonReentrant
        proposalExists(proposalId)
    {
        SpendProposal storage proposal = spendProposals[proposalId];

        require(!proposal.executed, "VIBTreasury: already executed");
        require(!proposal.cancelled, "VIBTreasury: already cancelled");
        require(
            proposal.signatureCount >= requiredSignatures,
            "VIBTreasury: not enough signatures"
        );
        require(
            block.timestamp >= proposal.executeAfter,
            "VIBTreasury: timelock not expired"
        );
        require(
            fundBalances[proposal.fundType] >= proposal.amount,
            "VIBTreasury: insufficient balance"
        );

        // 标记为已执行
        proposal.executed = true;
        fundBalances[proposal.fundType] -= proposal.amount;

        // 转账
        vibeToken.safeTransfer(proposal.recipient, proposal.amount);

        emit SpendProposalExecuted(proposalId, msg.sender);
    }

    /**
     * @notice 紧急执行提案（需要超过2/3签名者同意，可绕过时间锁）
     * @param proposalId 提案 ID
     */
    function executeEmergencyProposal(bytes32 proposalId)
        external
        onlySigner
        nonReentrant
        proposalExists(proposalId)
    {
        SpendProposal storage proposal = spendProposals[proposalId];

        require(!proposal.executed, "VIBTreasury: already executed");
        require(!proposal.cancelled, "VIBTreasury: already cancelled");
        require(!emergencyExecuted[proposalId], "VIBTreasury: emergency already executed");

        // 计算紧急解锁所需签名数 (超过2/3)
        uint256 emergencyRequired = (signers.length * EMERGENCY_SIGNATURE_THRESHOLD + 99) / 100;
        require(
            proposal.signatureCount >= emergencyRequired,
            "VIBTreasury: not enough emergency signatures"
        );

        // 检查资金是否足够
        require(
            fundBalances[proposal.fundType] >= proposal.amount,
            "VIBTreasury: insufficient balance"
        );

        // 标记为已执行（紧急）
        proposal.executed = true;
        emergencyExecuted[proposalId] = true;
        fundBalances[proposal.fundType] -= proposal.amount;

        // 转账
        vibeToken.safeTransfer(proposal.recipient, proposal.amount);

        emit SpendProposalExecuted(proposalId, msg.sender);
        emit EmergencyProposalExecuted(proposalId, proposal.signatureCount);
    }

    /**
     * @notice 取消提案
     * @param proposalId 提案 ID
     */
    function cancelProposal(bytes32 proposalId)
        external
        onlySigner
        nonReentrant
        proposalExists(proposalId)
    {
        SpendProposal storage proposal = spendProposals[proposalId];

        require(!proposal.executed, "VIBTreasury: already executed");
        require(!proposal.cancelled, "VIBTreasury: already cancelled");

        proposal.cancelled = true;

        emit SpendProposalCancelled(proposalId, msg.sender);
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 添加签名者
     * @param signer 签名者地址
     */
    function addSigner(address signer) external onlyOwner {
        require(signer != address(0), "VIBTreasury: invalid address");
        require(!isSigner[signer], "VIBTreasury: already a signer");

        isSigner[signer] = true;
        signers.push(signer);

        emit SignerUpdated(signer, true);
    }

    /**
     * @notice 移除签名者
     * @param signer 签名者地址
     */
    function removeSigner(address signer) external onlyOwner {
        require(signer != owner(), "VIBTreasury: cannot remove owner");
        require(isSigner[signer], "VIBTreasury: not a signer");
        require(
            signers.length - 1 >= requiredSignatures,
            "VIBTreasury: cannot remove signer"
        );

        isSigner[signer] = false;

        // 从数组中移除
        for (uint256 i = 0; i < signers.length - 1; i++) {
            if (signers[i] == signer) {
                signers[i] = signers[signers.length - 1];
                break;
            }
        }
        signers.pop();

        emit SignerUpdated(signer, false);
    }

    /**
     * @notice 更新签名阈值
     * @param _requiredSignatures 新的签名阈值
     */
    function updateThreshold(uint256 _requiredSignatures) external onlyOwner {
        require(
            _requiredSignatures > 0 && _requiredSignatures <= signers.length,
            "VIBTreasury: invalid threshold"
        );

        emit ThresholdUpdated(requiredSignatures, _requiredSignatures);
        requiredSignatures = _requiredSignatures;
    }

    /**
     * @notice 更新时间锁设置
     * @param _enabled 是否启用时间锁
     * @param _duration 时间锁时长
     */
    function setTimelock(bool _enabled, uint256 _duration) external onlyOwner {
        timelockEnabled = _enabled;
        timelockDuration = _duration;

        emit TimelockUpdated(_enabled, _duration);
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
     * @notice 紧急提取代币 (需要时间锁)
     * @param token 代币地址
     * @param to 目标地址
     * @param amount 金额
     */
    function emergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner {
        require(to != address(0), "VIBTreasury: invalid address");
        require(amount > 0, "VIBTreasury: amount must be greater than 0");

        // 如果有待生效的提取，先取消
        if (pendingEmergencyWithdraw.to != address(0)) {
            delete pendingEmergencyWithdraw;
            emit EmergencyWithdrawCancelled();
        }

        // 设置待生效的提取
        pendingEmergencyWithdraw = PendingWithdraw({
            token: token,
            to: to,
            amount: amount,
            effectiveTime: block.timestamp + EMERGENCY_TIMELOCK_DURATION
        });

        emit EmergencyWithdrawInitiated(token, to, amount, pendingEmergencyWithdraw.effectiveTime);
    }

    /// @notice 确认紧急提取
    function confirmEmergencyWithdraw() external onlyOwner nonReentrant {
        PendingWithdraw memory pw = pendingEmergencyWithdraw;
        require(pw.to != address(0), "VIBTreasury: no pending withdraw");
        require(block.timestamp >= pw.effectiveTime, "VIBTreasury: withdraw not yet effective");

        // 清除状态
        delete pendingEmergencyWithdraw;

        // 执行提取
        if (pw.token == address(0)) {
            require(address(this).balance >= pw.amount, "VIBTreasury: insufficient balance");
            payable(pw.to).transfer(pw.amount);
        } else {
            require(IERC20(pw.token).balanceOf(address(this)) >= pw.amount, "VIBTreasury: insufficient balance");
            IERC20(pw.token).safeTransfer(pw.to, pw.amount);
        }

        emit EmergencyWithdrawConfirmed(pw.token, pw.to, pw.amount);
    }

    /// @notice 取消紧急提取
    function cancelEmergencyWithdraw() external onlyOwner {
        require(pendingEmergencyWithdraw.to != address(0), "VIBTreasury: no pending withdraw");
        delete pendingEmergencyWithdraw;
        emit EmergencyWithdrawCancelled();
    }

    // ========== 视图函数 =========-

    /**
     * @notice 获取签名者数量
     * @return 签名者数量
     */
    function getSignerCount() external view returns (uint256) {
        return signers.length;
    }

    /**
     * @notice 获取所有签名者
     * @return 签名者地址列表
     */
    function getSigners() external view returns (address[] memory) {
        return signers;
    }

    /**
     * @notice 获取基金余额
     * @param fundType 基金类型
     * @return 基金余额
     */
    function getFundBalance(FundType fundType) external view returns (uint256) {
        return fundBalances[fundType];
    }

    /**
     * @notice 获取提案详情
     * @param proposalId 提案 ID
     * @return 提案详情
     */
    function getProposal(bytes32 proposalId)
        external
        view
        returns (SpendProposal memory)
    {
        return spendProposals[proposalId];
    }

    /**
     * @notice 检查用户是否已签名
     * @param proposalId 提案 ID
     * @param signer 签名者地址
     * @return 是否已签名
     */
    function hasSignerSigned(bytes32 proposalId, address signer)
        external
        view
        returns (bool)
    {
        return hasSigned[proposalId][signer];
    }

    // ========== 接收函数 ==========

    /// @notice 接收 ETH
    receive() external payable {}
}
