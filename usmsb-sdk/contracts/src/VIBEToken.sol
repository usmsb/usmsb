// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBEToken
 * @notice VIBE 是 USMSB 生态系统中的核心 ERC-20 代币
 * @dev 继承 ERC20, ERC20Permit (EIP-2612), Ownable, Pausable
 *      固定总供应量，不可增发
 *      支持交易税 (0.8%) 和销毁机制 (50%)
 */
contract VIBEToken is ERC20, ERC20Permit, Ownable, Pausable {
    // ========== 常量 ==========

    /// @notice 代币总供应量 (10 亿 * 10^18)
    uint256 public constant TOTAL_SUPPLY = 1_000_000_000 * 10**18;

    /// @notice 初始铸造比例 (8% = 80,000,000 VIBE)
    uint256 public constant INITIAL_MINT_RATIO = 8; // 8%

    /// @notice 剩余代币保留比例
    uint256 public constant TREASURY_RATIO = 92; // 92%

    /// @notice 交易手续费比例 (0.8%)
    uint256 public constant TRANSACTION_TAX_RATE = 8; // 0.8% = 8/1000

    /// @notice 销毁比例 (50% = 手续费中的 50% 销毁)
    uint256 public constant BURN_RATIO = 5000; // 50% = 5000/10000

    /// @notice 分红池比例 (20% = 交易费的 20% 进入分红池)
    uint256 public constant DIVIDEND_RATIO = 2000; // 20% = 2000/10000

    /// @notice 生态基金比例 (20% = 交易费的 20% 进入生态基金)
    uint256 public constant ECOSYSTEM_FUND_RATIO = 2000; // 20% = 2000/10000

    /// @notice 协议运营比例 (10% = 交易费的 10% 用于协议运营)
    uint256 public constant PROTOCOL_FUND_RATIO = 1000; // 10% = 1000/10000

    /// @notice 精度因子 (处理百分比计算)
    uint256 public constant TAX_PRECISION = 10000;

    // ========== 状态变量 ==========

    /// @notice 国库地址，持有剩余 92% 代币
    address public treasury;

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

    /// @notice 国库是否已铸造
    bool public treasuryMinted;

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

    /// @notice 国库地址更新
    event TreasuryUpdated(address indexed oldAddress, address indexed newAddress);

    /// @notice 向国库铸造剩余代币
    event TreasuryMinted(address indexed treasury, uint256 amount);

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
     * @param _treasury 国库地址
     */
    constructor(
        string memory _name,
        string memory _symbol,
        address _treasury
    ) ERC20(_name, _symbol) ERC20Permit(_name) Ownable(msg.sender) {
        require(_treasury != address(0), "VIBEToken: invalid treasury address");

        treasury = _treasury;

        // 构造函数期间禁用交易税，确保初始铸造成功
        bool originalTaxStatus = transactionTaxEnabled;
        transactionTaxEnabled = false;

        // 初始铸造 8% 到部署者地址
        uint256 initialAmount = (TOTAL_SUPPLY * INITIAL_MINT_RATIO) / 100;
        _mint(msg.sender, initialAmount);

        // 恢复交易税设置
        transactionTaxEnabled = originalTaxStatus;

        // 默认免税地址：owner、treasury、合约自己
        taxExemptedAddresses[msg.sender] = true;
        taxExemptedAddresses[_treasury] = true;
        taxExemptedAddresses[address(this)] = true;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 将剩余代币铸造给国库
     * @dev 只能由 owner 调用一次，调用后国库获得 92% 代币
     * @notice 注意: 推荐使用 distributeToPools() 替代此函数，实现完全去中心化分配
     */
    function mintTreasury() external onlyOwner {
        // 检查是否已经铸造过
        require(!treasuryMinted, "VIBEToken: treasury already minted");
        require(!tokensDistributed, "VIBEToken: tokens already distributed");

        uint256 treasuryAmount = (TOTAL_SUPPLY * TREASURY_RATIO) / 100;

        // 确保总供应量不超过硬顶
        require(
            totalSupply() + treasuryAmount <= TOTAL_SUPPLY,
            "VIBEToken: exceeds total supply cap"
        );

        _mint(treasury, treasuryAmount);
        treasuryMinted = true;
        emit TreasuryMinted(treasury, treasuryAmount);
    }

    // ========== 代币分配（完全去中心化） ==========

    /// @notice 代币分配事件
    event TokensDistributed(
        address indexed teamVesting,      // 早期支持者锁仓合约 (4%)
        address indexed stableFund,       // 社区稳定基金 (6%)
        address indexed liquidityManager, // 流动性池 (12%)
        address airdropDistributor,       // 空投分发 (7%)
        address emissionController       // 激励池 (63%)
    );

    /**
     * @notice 将剩余 92% 代币分配到各池合约（完全去中心化）
     * @dev 只能由 owner 调用一次，部署脚本中自动调用
     *
     * 分配比例（占总供应量）:
     * - 早期支持者: 4% → teamVestingContract
     * - 社区稳定基金: 6% → communityStableFund
     * - 流动性池: 12% → liquidityManager
     * - 社区空投: 7% → airdropDistributor
     * - 激励池: 63% → emissionController
     *
     * 注意: 团队 8% 已在构造函数中铸造给部署者
     *
     * @param teamVestingContract 早期支持者锁仓合约地址（独立于团队锁仓）
     * @param communityStableFund 社区稳定基金合约地址
     * @param liquidityManager 流动性管理合约地址
     * @param airdropDistributor 空投分发合约地址
     * @param _emissionController 释放控制器合约地址
     */
    function distributeToPools(
        address teamVestingContract,
        address communityStableFund,
        address liquidityManager,
        address airdropDistributor,
        address _emissionController
    ) external onlyOwner {
        // 检查是否已分配
        require(!tokensDistributed, "VIBEToken: tokens already distributed");
        require(!treasuryMinted, "VIBEToken: treasury already minted, use distributeFromTreasury instead");

        // 验证地址不为零
        require(teamVestingContract != address(0), "VIBEToken: invalid team vesting");
        require(communityStableFund != address(0), "VIBEToken: invalid stable fund");
        require(liquidityManager != address(0), "VIBEToken: invalid liquidity manager");
        require(airdropDistributor != address(0), "VIBEToken: invalid airdrop distributor");
        require(_emissionController != address(0), "VIBEToken: invalid emission controller");

        // 禁用交易税以便分配
        bool originalTaxStatus = transactionTaxEnabled;
        transactionTaxEnabled = false;

        // 计算各池金额
        uint256 teamVestingAmount = (TOTAL_SUPPLY * 4) / 100;      // 4% = 早期支持者
        uint256 stableFundAmount = (TOTAL_SUPPLY * 6) / 100;       // 6% = 社区稳定基金
        uint256 liquidityAmount = (TOTAL_SUPPLY * 12) / 100;       // 12% = 流动性池
        uint256 airdropAmount = (TOTAL_SUPPLY * 7) / 100;          // 7% = 空投
        uint256 emissionAmount = (TOTAL_SUPPLY * 63) / 100;        // 63% = 激励池

        // 铸造代币到各池
        _mint(teamVestingContract, teamVestingAmount);
        _mint(communityStableFund, stableFundAmount);
        _mint(liquidityManager, liquidityAmount);
        _mint(airdropDistributor, airdropAmount);
        _mint(_emissionController, emissionAmount);

        // 设置免税地址
        taxExemptedAddresses[teamVestingContract] = true;
        taxExemptedAddresses[communityStableFund] = true;
        taxExemptedAddresses[liquidityManager] = true;
        taxExemptedAddresses[airdropDistributor] = true;
        taxExemptedAddresses[_emissionController] = true;

        // 保存释放控制器地址
        emissionController = _emissionController;

        // 恢复交易税设置
        transactionTaxEnabled = originalTaxStatus;

        // 标记已分配
        tokensDistributed = true;

        emit TokensDistributed(
            teamVestingContract,
            communityStableFund,
            liquidityManager,
            airdropDistributor,
            _emissionController
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
     * @notice 更新国库地址
     * @param _treasury 新的国库地址
     */
    function setTreasury(address _treasury) external onlyOwner {
        require(_treasury != address(0), "VIBEToken: invalid treasury address");
        emit TreasuryUpdated(treasury, _treasury);
        treasury = _treasury;
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

    /**
     * @notice 质押合约铸造奖励
     * @param to 接收者地址
     * @param amount 奖励数量
     */
    function mintReward(address to, uint256 amount) external onlyStakingContract {
        require(
            totalSupply() + amount <= TOTAL_SUPPLY,
            "VIBEToken: minting exceeds total supply cap"
        );
        _mint(to, amount);
    }

    /**
     * @notice 锁仓合约释放代币
     * @param to 接收者地址
     * @param amount 释放数量
     */
    function releaseVesting(address to, uint256 amount) external onlyVestingContract {
        _transfer(address(this), to, amount);
    }

    /**
     * @notice 分红合约分配奖励
     * @param to 接收者地址
     * @param amount 奖励数量
     */
    function dividendDistribution(address to, uint256 amount) external onlyDividendContract {
        _transfer(address(this), to, amount);
    }

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
     */
    function protocolFundWithdraw(address to, uint256 amount) external onlyOwner {
        require(protocolFundContract != address(0), "VIBEToken: protocol fund not set");
        _transfer(protocolFundContract, to, amount);
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

            // 分红池
            if (dividendAmount > 0 && dividendContract != address(0)) {
                super._update(from, dividendContract, dividendAmount);
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
