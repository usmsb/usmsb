// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title IVIBDividend
 * @notice VIBDividend 接口 - STK-006修复
 */
interface IVIBDividend {
    function notifyDividendReceived(uint256 amount) external;
}

/**
 * @title VIBEToken
 * @notice VIBE 是 USMSB 生态系统中的核心 ERC-20 代币
 * @dev 继承 ERC20, ERC20Permit (EIP-2612), Ownable, Pausable
 *      固定总供应量，不可增发
 *      支持交易税 (0.8%) 和销毁机制 (50%)
 */
contract VIBEToken is ERC20, ERC20Permit, Ownable, Pausable {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    /// @notice 代币总供应量 (10 亿 * 10^18)
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10**18;



    /// @notice 交易手续费比例 (0.8%)
    uint256 public constant TRANSACTION_TAX_RATE = 80; // 0.8% = 80/10000

    /// @notice 销毁比例 (50% = 手续费中的 50% 销毁)
    uint256 public constant BURN_RATIO = 5000; // 50% = 5000/10000

    /// @notice 分红池比例 (20% = 交易费的 20% 进入分红池)
    uint256 public constant DIVIDEND_RATIO = 2000; // 20% = 2000/10000

    /// @notice 生态基金比例 (15% = 交易费的 15% 进入生态基金)
    uint256 public constant ECOSYSTEM_FUND_RATIO = 1500; // 15% = 1500/10000

    /// @notice 协议运营比例 (15% = 交易费的 15% 用于协议运营)
    uint256 public constant PROTOCOL_FUND_RATIO = 1500; // 15% = 1500/10000

    /// @notice 精度因子 (处理百分比计算)
    uint256 public constant TAX_PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice 质押合约地址，允许铸造奖励
    address public stakingContract;

    /// @notice 锁仓合约地址，允许释放代币
    address public vestingContract;

    /// @notice 身份合约地址，用于铸造费用
    address public identityContract;

    /// @notice 分红合约地址
    address public dividendContract;

    /// @notice 生态基金合约地址
    address public ecosystemFundContract;

    /// @notice 协议运营基金地址
    address public protocolFundContract;

    /// @notice 释放控制器地址
    address public emissionController;

    /// @notice 已销毁代币总量
    uint256 public totalBurned;

    /// @notice 代币是否已分配到各池
    bool public tokensDistributed;

    /// @notice 是否启用交易税
    bool public transactionTaxEnabled = true;

    /// @notice 免税地址映射 (用于合约间转账)
    mapping(address => bool) public taxExemptedAddresses;

    // ========== 修饰符 ==========

    /// @notice 只允许质押合约调用
    modifier onlyStakingContract() {
        require(
            msg.sender == stakingContract,
            "VIBEToken: caller is not the staking contract"
        );
        _;
    }

    /// @notice 只允许锁仓合约调用
    modifier onlyVestingContract() {
        require(
            msg.sender == vestingContract,
            "VIBEToken: caller is not the vesting contract"
        );
        _;
    }

    /// @notice 只允许分红合约调用
    modifier onlyDividendContract() {
        require(
            msg.sender == dividendContract,
            "VIBEToken: caller is not the dividend contract"
        );
        _;
    }

    /// @notice 只允许生态基金合约调用
    modifier onlyEcosystemFundContract() {
        require(
            msg.sender == ecosystemFundContract,
            "VIBEToken: caller is not the ecosystem fund contract"
        );
        _;
    }

    /// @notice 只允许释放控制器调用
    modifier onlyEmissionController() {
        require(
            msg.sender == emissionController,
            "VIBEToken: caller is not the emission controller"
        );
        _;
    }

    // ========== 事件 ==========

    /// @notice 质押合约地址更新
    event StakingContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 锁仓合约地址更新
    event VestingContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 身份合约地址更新
    event IdentityContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 代币销毁事件
    event TokensBurned(address indexed from, uint256 amount);

    /// @notice 交易税收取事件
    event TransactionTaxCollected(
        address indexed from,
        address indexed to,
        uint256 amount,
        uint256 burnAmount,
        uint256 dividendAmount,
        uint256 ecosystemAmount,
        uint256 protocolAmount
    );

    /// @notice 分红合约地址更新
    event DividendContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 生态基金合约地址更新
    event EcosystemFundContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 协议基金地址更新
    event ProtocolFundContractUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 交易税启用/禁用
    event TransactionTaxStatusChanged(bool enabled);

    /// @notice 免税地址更新
    event TaxExemptStatusUpdated(address indexed addr, bool isExempted);

    /// @notice 释放控制器地址更新
    event EmissionControllerUpdated(address indexed oldAddress, address indexed newAddress);

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数，初始化 VIBE 代币
     * @param _name 代币名称
     * @param _symbol 代币符号
     * @dev 注意: 所有代币通过 distributeToPools() 分配，构造函数不再预铸造
     */
    constructor(
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) ERC20Permit(_name) Ownable(msg.sender) {
        // 注意: 不再在构造函数中预铸造代币
        // 所有代币通过 distributeToPools() 分配到各池
        // 这样确保团队8%通过归属合约锁定

        // 默认免税地址：owner 和合约自己
        taxExemptedAddresses[msg.sender] = true;
        taxExemptedAddresses[address(this)] = true;
    }

    // ========== 外部函数 ==========

    // ========== 代币分配（白皮书规范，10000 bps = 100%） ==========
    // 白皮书: staking 45%/ecosystem 30%/governance 15%/reserve 10% (of 63% emission) + direct: team 8%/early 4%/community 6%/liquidity 12%/airdrop 7%
    uint256 public constant PERCENT_STAKING = 2835;      // 28.35%
    uint256 public constant PERCENT_ECOSYSTEM = 1890;     // 18.90%
    uint256 public constant PERCENT_GOVERNANCE = 945;   //  9.45%
    uint256 public constant PERCENT_RESERVE = 630;      //  6.30%
    uint256 public constant PERCENT_TEAM = 800;         //  8.00%
    uint256 public constant PERCENT_EARLY_SUPPORTER = 400; // 4.00%
    uint256 public constant PERCENT_COMMUNITY = 600;   //  6.00%
    uint256 public constant PERCENT_LIQUIDITY = 1200;  // 12.00%
    uint256 public constant PERCENT_AIRDROP = 700;     //  7.00%
    // Total: 2835+1890+945+630+800+400+600+1200+700 = 10000 ✓

    /// @notice 代币分配事件（白皮书 10000 bps 分配）
    event TokensDistributed(
        address stakingPool,
        address ecosystemPool,
        address governancePool,
        address reservePool,
        address teamVesting,
        address earlySupporterVesting,
        address communityFund,
        address liquidityManager,
        address airdropDistributor
    );

    /**
     * @notice 将 100% 代币分配到各池合约（白皮书规范）
     * @dev 只能由 owner 调用一次
     *
     * 分配比例（占总供应量，10000 bps）：
     * - 质押池: 28.35% → stakingPool
     * - 生态池: 18.90% → ecosystemPool
     * - 治理池:  9.45% → governancePool
     * - 储备池:  6.30% → reservePool
     * - 团队锁仓: 8.00% → teamVesting
     * - 早期支持者: 4.00% → earlySupporterVesting
     * - 社区基金: 6.00% → communityFund
     * - 流动性池: 12.00% → liquidityManager
     * - 空投分发:  7.00% → airdropDistributor
     *
     * @param stakingPool 质押池地址
     * @param ecosystemPool 生态池地址
     * @param governancePool 治理池地址
     * @param reservePool 储备池地址
     * @param teamVesting 团队锁仓合约地址
     * @param earlySupporterVesting 早期支持者锁仓合约地址
     * @param communityFund 社区基金地址
     * @param liquidityManager 流动性管理合约地址
     * @param airdropDistributor 空投分发合约地址
     */
    function distributeToPools(
        address stakingPool,
        address ecosystemPool,
        address governancePool,
        address reservePool,
        address teamVesting,
        address earlySupporterVesting,
        address communityFund,
        address liquidityManager,
        address airdropDistributor
    ) external onlyOwner {
        require(!tokensDistributed, "VIBEToken: tokens already distributed");
        require(stakingPool != address(0) && ecosystemPool != address(0) &&
            governancePool != address(0) && reservePool != address(0) &&
            teamVesting != address(0) && earlySupporterVesting != address(0) &&
            communityFund != address(0) && liquidityManager != address(0) &&
            airdropDistributor != address(0), "VIBEToken: invalid pool address");

        _mint(stakingPool, (TOTAL_SUPPLY * PERCENT_STAKING) / 10000);
        _mint(ecosystemPool, (TOTAL_SUPPLY * PERCENT_ECOSYSTEM) / 10000);
        _mint(governancePool, (TOTAL_SUPPLY * PERCENT_GOVERNANCE) / 10000);
        _mint(reservePool, (TOTAL_SUPPLY * PERCENT_RESERVE) / 10000);
        _mint(teamVesting, (TOTAL_SUPPLY * PERCENT_TEAM) / 10000);
        _mint(earlySupporterVesting, (TOTAL_SUPPLY * PERCENT_EARLY_SUPPORTER) / 10000);
        _mint(communityFund, (TOTAL_SUPPLY * PERCENT_COMMUNITY) / 10000);
        _mint(liquidityManager, (TOTAL_SUPPLY * PERCENT_LIQUIDITY) / 10000);
        _mint(airdropDistributor, (TOTAL_SUPPLY * PERCENT_AIRDROP) / 10000);

        // 设置免税地址
        taxExemptedAddresses[stakingPool] = true;
        taxExemptedAddresses[ecosystemPool] = true;
        taxExemptedAddresses[governancePool] = true;
        taxExemptedAddresses[reservePool] = true;
        taxExemptedAddresses[teamVesting] = true;
        taxExemptedAddresses[earlySupporterVesting] = true;
        taxExemptedAddresses[communityFund] = true;
        taxExemptedAddresses[liquidityManager] = true;
        taxExemptedAddresses[airdropDistributor] = true;

        tokensDistributed = true;
        emit TokensDistributed(
            stakingPool, ecosystemPool, governancePool, reservePool,
            teamVesting, earlySupporterVesting, communityFund,
            liquidityManager, airdropDistributor
        );
    }


    /**
     * @notice 设置质押合约地址
     * @param _stakingContract 质押合约地址
     */
    function setStakingContract(address _stakingContract) external onlyOwner {
        require(
            _stakingContract != address(0),
            "VIBEToken: invalid staking contract"
        );
        require(
            _stakingContract == address(this) || _stakingContract.code.length > 0,
            "VIBEToken: must be contract"
        );
        emit StakingContractUpdated(stakingContract, _stakingContract);
        stakingContract = _stakingContract;
        taxExemptedAddresses[_stakingContract] = true;
    }

    /**
     * @notice 设置锁仓合约地址
     * @param _vestingContract 锁仓合约地址
     */
    function setVestingContract(address _vestingContract) external onlyOwner {
        require(
            _vestingContract != address(0),
            "VIBEToken: invalid vesting contract"
        );
        emit VestingContractUpdated(vestingContract, _vestingContract);
        vestingContract = _vestingContract;
        taxExemptedAddresses[_vestingContract] = true;
    }

    /**
     * @notice 设置身份合约地址
     * @param _identityContract 身份合约地址
     */
    function setIdentityContract(address _identityContract) external onlyOwner {
        require(
            _identityContract != address(0),
            "VIBEToken: invalid identity contract"
        );
        emit IdentityContractUpdated(identityContract, _identityContract);
        identityContract = _identityContract;
        taxExemptedAddresses[_identityContract] = true;
    }

    /**
     * @notice 设置分红合约地址
     * @param _dividendContract 分红合约地址
     */
    function setDividendContract(address _dividendContract) external onlyOwner {
        require(
            _dividendContract != address(0),
            "VIBEToken: invalid dividend contract"
        );
        emit DividendContractUpdated(dividendContract, _dividendContract);
        dividendContract = _dividendContract;
        taxExemptedAddresses[_dividendContract] = true;
    }

    /**
     * @notice 设置生态基金合约地址
     * @param _ecosystemFundContract 生态基金合约地址
     */
    function setEcosystemFundContract(address _ecosystemFundContract) external onlyOwner {
        require(
            _ecosystemFundContract != address(0),
            "VIBEToken: invalid ecosystem fund contract"
        );
        emit EcosystemFundContractUpdated(ecosystemFundContract, _ecosystemFundContract);
        ecosystemFundContract = _ecosystemFundContract;
        taxExemptedAddresses[_ecosystemFundContract] = true;
    }

    /**
     * @notice 设置协议基金地址
     * @param _protocolFundContract 协议基金地址
     */
    function setProtocolFundContract(address _protocolFundContract) external onlyOwner {
        require(
            _protocolFundContract != address(0),
            "VIBEToken: invalid protocol fund contract"
        );
        emit ProtocolFundContractUpdated(protocolFundContract, _protocolFundContract);
        protocolFundContract = _protocolFundContract;
        taxExemptedAddresses[_protocolFundContract] = true;
    }

    /**
     * @notice 设置释放控制器地址
     * @param _emissionController 释放控制器地址
     */
    function setEmissionController(address _emissionController) external onlyOwner {
        require(_emissionController != address(0), "VIBEToken: invalid emission controller");
        emit EmissionControllerUpdated(emissionController, _emissionController);
        emissionController = _emissionController;
        taxExemptedAddresses[_emissionController] = true;
    }

    /**
     * @notice 设置免税地址
     * @param addr 地址
     * @param isExempted 是否免税
     */
    function setTaxExempt(address addr, bool isExempted) external onlyOwner {
        require(addr != address(0), "VIBEToken: invalid address");
        taxExemptedAddresses[addr] = isExempted;
        emit TaxExemptStatusUpdated(addr, isExempted);
    }

    /**
     * @notice 启用/禁用交易税
     * @param enabled 是否启用
     */
    function setTransactionTaxEnabled(bool enabled) external onlyOwner {
        transactionTaxEnabled = enabled;
        emit TransactionTaxStatusChanged(enabled);
    }

    /**
     * @notice 暂停所有转账（紧急情况）
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice 恢复所有转账
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    // ========== LQ-02修复: 紧急提取时间锁 ==========

    /// @notice 紧急提取延迟时间 (2天)
    uint256 public constant EMERGENCY_WITHDRAW_DELAY = 2 days;

    /// @notice 待提取的代币
    address public pendingWithdrawToken;

    /// @notice 待提取金额
    uint256 public pendingWithdrawAmount;

    /// @notice 待提取接收者
    address public pendingWithdrawRecipient;

    /// @notice 提取生效时间
    uint256 public withdrawEffectiveTime;

    /// @notice 紧急提取初始化事件
    event EmergencyWithdrawInitiated(
        address indexed token,
        address indexed recipient,
        uint256 amount,
        uint256 effectiveTime
    );

    /// @notice 紧急提取执行事件
    event EmergencyWithdrawExecuted(
        address indexed token,
        address indexed recipient,
        uint256 amount
    );

    /// @notice 紧急提取取消事件
    event EmergencyWithdrawCancelled();

    /**
     * @notice 初始化紧急提取（仅owner）
     * @param token 代币地址 (address(0) 表示 ETH)
     * @param to 接收者地址
     * @param amount 提取金额
     * @dev LQ-02修复: 添加2天时间锁
     */
    function initiateEmergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner {
        require(to != address(0), "VIBEToken: invalid recipient");
        require(amount > 0, "VIBEToken: amount must be greater than 0");

        // 验证余额
        if (token == address(0)) {
            require(address(this).balance >= amount, "VIBEToken: insufficient ETH balance");
        } else {
            require(IERC20(token).balanceOf(address(this)) >= amount, "VIBEToken: insufficient token balance");
        }

        // 如果有待生效的提取，先取消
        if (pendingWithdrawAmount > 0) {
            delete pendingWithdrawToken;
            delete pendingWithdrawAmount;
            delete pendingWithdrawRecipient;
            delete withdrawEffectiveTime;
            emit EmergencyWithdrawCancelled();
        }

        // 设置待生效的提取
        pendingWithdrawToken = token;
        pendingWithdrawAmount = amount;
        pendingWithdrawRecipient = to;
        withdrawEffectiveTime = block.timestamp + EMERGENCY_WITHDRAW_DELAY;

        emit EmergencyWithdrawInitiated(token, to, amount, withdrawEffectiveTime);
    }

    /**
     * @notice 执行紧急提取（仅owner）
     * @dev LQ-02修复: 必须等待时间锁过期
     */
    function executeEmergencyWithdraw() external onlyOwner {
        require(pendingWithdrawAmount > 0, "VIBEToken: no pending withdraw");
        require(block.timestamp >= withdrawEffectiveTime, "VIBEToken: timelock not expired");

        address token = pendingWithdrawToken;
        uint256 amount = pendingWithdrawAmount;
        address to = pendingWithdrawRecipient;

        // 清除状态
        delete pendingWithdrawToken;
        delete pendingWithdrawAmount;
        delete pendingWithdrawRecipient;
        delete withdrawEffectiveTime;

        // 执行提取
        if (token == address(0)) {
            payable(to).transfer(amount);
        } else {
            IERC20(token).safeTransfer(to, amount);
        }

        emit EmergencyWithdrawExecuted(token, to, amount);
    }

    /**
     * @notice 取消紧急提取（仅owner）
     */
    function cancelEmergencyWithdraw() external onlyOwner {
        require(pendingWithdrawAmount > 0, "VIBEToken: no pending withdraw");

        delete pendingWithdrawToken;
        delete pendingWithdrawAmount;
        delete pendingWithdrawRecipient;
        delete withdrawEffectiveTime;

        emit EmergencyWithdrawCancelled();
    }

    /**
     * @notice 质押合约铸造奖励
     * @param to 接收者地址
     * @param amount 奖励数量
     * @dev Medium #1 修复: 使用更严格的溢出检查
     */
    function mintReward(address to, uint256 amount) external onlyStakingContract {
        require(to != address(0), "VIBEToken: invalid recipient");
        require(amount > 0, "VIBEToken: amount must be greater than 0");
        // 使用更严格的检查，防止任何溢出可能
        uint256 newTotalSupply = totalSupply() + amount;
        require(
            newTotalSupply <= TOTAL_SUPPLY && newTotalSupply >= totalSupply(),
            "VIBEToken: minting exceeds total supply cap or would overflow"
        );
        _mint(to, amount);
    }

    // ========== 安全修复 VULN-001/VULN-002 ==========
    // 已删除无效的 releaseVesting 和 dividendDistribution 函数
    // 原因：这两个函数从合约自身转账，但合约从未预留代币
    //
    // 正确的流程：
    // - VIBVesting: 通过 addBeneficiary 时 safeTransferFrom 转入代币，
    //               release 时从合约余额 safeTransfer 转给用户
    // - VIBDividend: 通过交易税直接收到代币，claimReward 时转给用户
    //
    // 这些函数是遗留代码，已删除以避免混淆和潜在错误调用

    /**
     * @notice 生态基金提取代币
     * @param to 接收者地址
     * @param amount 提取数量
     */
    function ecosystemFundWithdraw(address to, uint256 amount) external onlyEcosystemFundContract {
        _transfer(address(this), to, amount);
    }

    /**
     * @notice 协议基金提取代币
     * @param to 接收者地址
     * @param amount 提取数量
     * @dev 协议基金合约需先授权 VIBEToken 提取 (approve)，然后调用此函数
     */
    function protocolFundWithdraw(address to, uint256 amount) external onlyOwner {
        require(to != address(0), "VIBEToken: invalid recipient");
        require(amount > 0, "VIBEToken: amount must be greater than 0");
        require(protocolFundContract != address(0), "VIBEToken: protocol fund not set");
        // 协议基金合约需先调用 approve(VIBEToken, amount) 授权
        IERC20(address(this)).safeTransferFrom(protocolFundContract, to, amount);
    }

    /**
     * @notice 销毁自己的代币
     * @param amount 销毁数量
     */
    function burn(uint256 amount) external {
        require(amount > 0, "VIBEToken: amount must be greater than 0");
        _burn(msg.sender, amount);
        totalBurned += amount;
        emit TokensBurned(msg.sender, amount);
    }

    // ========== 重写函数 ==========

    /**
     * @notice 重写 _update 以实现交易税和暂停功能
     * @param from 发送者地址
     * @param to 接收者地址
     * @param value 转账金额
     */
    function _update(address from, address to, uint256 value) internal override whenNotPaused {
        // Mint/burn bypass tax
        if (from == address(0) || to == address(0)) {
            super._update(from, to, value);
            return;
        }
        // 如果交易税禁用或地址免税，直接转账
        if (!transactionTaxEnabled || taxExemptedAddresses[from] || taxExemptedAddresses[to]) {
            super._update(from, to, value);
            return;
        }

        // 计算交易税
        uint256 taxAmount = (value * TRANSACTION_TAX_RATE) / TAX_PRECISION;

        if (taxAmount > 0) {
            // 计算各部分金额
            uint256 burnAmount = (taxAmount * BURN_RATIO) / TAX_PRECISION;
            uint256 dividendAmount = (taxAmount * DIVIDEND_RATIO) / TAX_PRECISION;
            uint256 ecosystemAmount = (taxAmount * ECOSYSTEM_FUND_RATIO) / TAX_PRECISION;
            uint256 protocolAmount = (taxAmount * PROTOCOL_FUND_RATIO) / TAX_PRECISION;

            // 安全修复: 计算舍入损失，加到销毁金额中
            // 确保所有税费分配完全，不会在发送者账户中残留
            uint256 totalDistributed = burnAmount + dividendAmount + ecosystemAmount + protocolAmount;
            if (totalDistributed < taxAmount) {
                burnAmount += (taxAmount - totalDistributed);
            }

            // 实际到账金额
            uint256 netAmount = value - taxAmount;

            // 转账净额给接收者
            super._update(from, to, netAmount);

            // 从发送者扣除税费（已经扣除了 netAmount，所以只需要转出 taxAmount）
            // 这里我们需要单独处理税费转账

            // 销毁部分
            if (burnAmount > 0) {
                _burn(from, burnAmount);
                totalBurned += burnAmount;
            }

            // 分红池 - STK-006修复: 转账后通知分红合约更新累计
            if (dividendAmount > 0 && dividendContract != address(0)) {
                super._update(from, dividendContract, dividendAmount);
                // 通知分红合约更新分红累计（用try-catch防止外部调用失败）
                try IVIBDividend(dividendContract).notifyDividendReceived(dividendAmount) {
                    // 成功
                } catch {
                    // 分红合约通知失败，不影响主转账
                }
            }

            // 生态基金
            if (ecosystemAmount > 0 && ecosystemFundContract != address(0)) {
                super._update(from, ecosystemFundContract, ecosystemAmount);
            }

            // 协议基金
            if (protocolAmount > 0 && protocolFundContract != address(0)) {
                super._update(from, protocolFundContract, protocolAmount);
            }

            emit TransactionTaxCollected(
                from,
                to,
                value,
                burnAmount,
                dividendAmount,
                ecosystemAmount,
                protocolAmount
            );
        } else {
            super._update(from, to, value);
        }
    }

    // ========== 视图函数 ==========

    /**
     * @notice 获取当前交易税信息
     * @param value 转账金额
     * @return taxAmount 总税费
     * @return burnAmount 销毁数量
     * @return dividendAmount 分红池数量
     * @return ecosystemAmount 生态基金数量
     * @return protocolAmount 协议基金数量
     */
    function getTaxBreakdown(uint256 value) external view returns (
        uint256 taxAmount,
        uint256 burnAmount,
        uint256 dividendAmount,
        uint256 ecosystemAmount,
        uint256 protocolAmount
    ) {
        taxAmount = (value * TRANSACTION_TAX_RATE) / TAX_PRECISION;
        burnAmount = (taxAmount * BURN_RATIO) / TAX_PRECISION;
        dividendAmount = (taxAmount * DIVIDEND_RATIO) / TAX_PRECISION;
        ecosystemAmount = (taxAmount * ECOSYSTEM_FUND_RATIO) / TAX_PRECISION;
        protocolAmount = (taxAmount * PROTOCOL_FUND_RATIO) / TAX_PRECISION;
    }

    /**
     * @notice 获取净转账金额（扣除税后）
     * @param value 转账金额
     * @return 净到账金额
     */
    function getNetTransferAmount(uint256 value) external view returns (uint256) {
        uint256 taxAmount = (value * TRANSACTION_TAX_RATE) / TAX_PRECISION;
        return value - taxAmount;
    }
}
