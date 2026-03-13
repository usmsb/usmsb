// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";

/**
 * @title IVIBStaking - AI-004修复
 * @notice VIBStaking接口，用于获取用户质押等级
 */
interface IVIBStakingForIdentity {
    enum StakeTier { BRONZE, SILVER, GOLD, PLATINUM }
    function getStakingTier(address user) external view returns (StakeTier);
}

/**
 * @title VIBIdentity
 * @notice VIBE 灵魂绑定代币 (SBT)，实现 ERC-5192 标准
 * @dev 代币不可转移，用于身份认证
 */
contract VIBIdentity is ERC721, ERC721URIStorage, Ownable, Pausable, ReentrancyGuard {
    using SafeERC20 for IERC20;
    // ========== 常量 ==========

    /// @notice 注册费用（VIBE 代币）
    uint256 public constant REGISTRATION_FEE = 100 * 10**18; // 100 VIBE

    /// @notice ETH 注册费用
    uint256 public constant ETH_REGISTRATION_FEE = 0.01 ether;

    /// @notice 最大代币 ID
    uint256 public constant MAX_TOKEN_ID = type(uint256).max - 1;

    // ========== 身份类型 ==========

    /// @notice 身份类型
    enum IdentityType {
        AI_AGENT,        // AI Agent 身份
        HUMAN_PROVIDER,  // 人类服务者认证
        NODE_OPERATOR,   // 节点运营商
        GOVERNANCE       // 治理参与者
    }

    // ========== 状态变量 ==========

    /// @notice VIBE 代币地址
    address public vibeToken;

    /// @notice 当前代币 ID
    uint256 private _currentTokenId;

    /// @notice 身份数量
    uint256 public identityCount;

    /// @notice 已验证身份数量（缓存，避免O(n)遍历）
    uint256 public verifiedCount;

    /// @notice 各类型身份数量（缓存）
    mapping(IdentityType => uint256) public identityTypeCount;

    /// @notice 代币信息
    mapping(uint256 => IdentityInfo) public identities;

    /// @notice 地址到代币 ID 映射
    mapping(address => uint256) public addressToTokenId;

    /// @notice 地址是否已注册
    mapping(address => bool) public isRegistered;

    /// @notice 名称是否已被使用
    mapping(string => bool) public nameUsed;

    // ========== AI-004修复: Agent数量限制追踪 ==========

    /// @notice VIBStaking合约地址
    address public stakingContract;

    /// @notice 用户创建的AI Agent数量
    mapping(address => uint256) public userAgentCount;

    /// @notice Agent创建者映射 (agent地址 => 创建者地址)
    mapping(address => address) public agentCreator;

    /// @notice 各等级Agent数量限制
    uint256 public constant BRONZE_AGENT_LIMIT = 1;
    uint256 public constant SILVER_AGENT_LIMIT = 3;
    uint256 public constant GOLD_AGENT_LIMIT = 10;
    uint256 public constant PLATINUM_AGENT_LIMIT = 50;

    // ========== 结构体 ==========

    /**
     * @notice 身份信息
     */
    struct IdentityInfo {
        address owner;              // 拥有者
        IdentityType identityType; // 身份类型
        string name;                // 名称
        uint256 registrationTime;   // 注册时间
        string metadata;            // 元数据（JSON 字符串）
        bool isVerified;            // 是否已验证
    }

    // ========== 事件 ==========

    /// @notice 身份注册事件
    event IdentityRegistered(
        uint256 indexed tokenId,
        address indexed owner,
        IdentityType identityType,
        string name,
        string metadata
    );

    /// @notice ETH 注册事件
    event IdentityRegisteredWithEth(
        address indexed owner,
        uint256 indexed tokenId,
        uint256 ethAmount
    );

    /// @notice VIBE 注册事件
    event IdentityRegisteredWithVibe(
        address indexed owner,
        uint256 indexed tokenId,
        uint256 vibeAmount
    );

    /// @notice 身份更新事件
    event IdentityUpdated(
        uint256 indexed tokenId,
        string metadata
    );

    /// @notice 身份验证事件
    event IdentityVerified(
        uint256 indexed tokenId,
        bool verified
    );

    /// @notice 身份撤销事件
    event IdentityRevoked(
        uint256 indexed tokenId,
        address indexed owner
    );

    /// @notice 代币地址更新事件
    event TokenUpdated(address indexed oldToken, address indexed newToken);

    /// @notice 注册费用更新事件
    event RegistrationFeeUpdated(uint256 oldFee, uint256 newFee);

    // ========== 修饰符 ==========

    /// @notice 检查地址是否已注册
    modifier notRegistered(address owner) {
        require(!isRegistered[owner], "VIBIdentity: already registered");
        _;
    }

    /// @notice 检查名称是否可用
    modifier nameAvailable(string memory name) {
        require(bytes(name).length > 0, "VIBIdentity: name cannot be empty");
        require(bytes(name).length <= 64, "VIBIdentity: name too long"); // L-03修复
        require(!nameUsed[name], "VIBIdentity: name already used");
        _;
    }

    /// @notice 检查代币是否存在
    modifier tokenExists(uint256 tokenId) {
        require(_ownerOf(tokenId) != address(0), "VIBIdentity: token does not exist");
        _;
    }

    // ========== 构造函数 ==========

    /**
     * @notice 构造函数
     * @param _name 代币名称
     * @param _symbol 代币符号
     * @param _vibeToken VIBE 代币地址
     */
    constructor(
        string memory _name,
        string memory _symbol,
        address _vibeToken
    ) ERC721(_name, _symbol) Ownable(msg.sender) {
        require(_vibeToken != address(0), "VIBIdentity: invalid token address");
        vibeToken = _vibeToken;
    }

    // ========== 外部函数 ==========

    /**
     * @notice 注册 AI Agent 身份
     * @param name Agent 名称
     * @param metadata 元数据（JSON 格式的 agent 能力描述）
     * @return tokenId 代币 ID
     * @dev AI-004修复: 检查Agent数量限制
     */
    function registerAIIdentity(string memory name, string memory metadata)
        external
        payable
        notRegistered(msg.sender)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        // AI-004修复: 检查调用者的Agent数量限制
        _checkAgentLimit(msg.sender);

        tokenId = _registerIdentity(msg.sender, name, metadata, IdentityType.AI_AGENT);

        // AI-004修复: 记录Agent创建者（对于自注册，创建者是自己）
        agentCreator[msg.sender] = msg.sender;
        userAgentCount[msg.sender]++;

        return tokenId;
    }

    /**
     * @notice 为指定的Agent地址注册身份（由创建者调用）
     * @param agentAddress Agent地址
     * @param name Agent 名称
     * @param metadata 元数据
     * @return tokenId 代币 ID
     * @dev AI-004修复: 允许创建者为多个Agent注册身份
     */
    function registerAIIdentityFor(
        address agentAddress,
        string memory name,
        string memory metadata
    )
        external
        payable
        notRegistered(agentAddress)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        require(agentAddress != address(0), "VIBIdentity: invalid agent address");

        // AI-004修复: 检查创建者的Agent数量限制
        _checkAgentLimit(msg.sender);

        tokenId = _registerIdentity(agentAddress, name, metadata, IdentityType.AI_AGENT);

        // 记录Agent创建者
        agentCreator[agentAddress] = msg.sender;
        userAgentCount[msg.sender]++;

        return tokenId;
    }

    /**
     * @notice 检查用户是否达到Agent数量上限
     * @param creator 创建者地址
     * @dev AI-004修复
     */
    function _checkAgentLimit(address creator) internal view {
        uint256 currentCount = userAgentCount[creator];
        uint256 limit = _getAgentLimit(creator);
        require(currentCount < limit, "VIBIdentity: agent limit reached");
    }

    /**
     * @notice 获取用户的Agent数量限制
     * @param user 用户地址
     * @return 限制数量
     * @dev AI-004修复: 根据质押等级返回限制
     */
    function _getAgentLimit(address user) internal view returns (uint256) {
        if (stakingContract != address(0)) {
            try IVIBStakingForIdentity(stakingContract).getStakingTier(user) returns (
                IVIBStakingForIdentity.StakeTier tier
            ) {
                if (tier == IVIBStakingForIdentity.StakeTier.PLATINUM) return PLATINUM_AGENT_LIMIT;
                if (tier == IVIBStakingForIdentity.StakeTier.GOLD) return GOLD_AGENT_LIMIT;
                if (tier == IVIBStakingForIdentity.StakeTier.SILVER) return SILVER_AGENT_LIMIT;
            } catch {
                // 如果调用失败，使用默认限制
            }
        }
        // Bronze或未质押: 默认1个
        return BRONZE_AGENT_LIMIT;
    }

    /**
     * @notice 注册人类服务者身份
     * @param name 服务者名称
     * @param metadata 元数据（技能、证书等信息）
     * @return tokenId 代币 ID
     */
    function registerHumanProvider(string memory name, string memory metadata)
        external
        payable
        notRegistered(msg.sender)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        tokenId = _registerIdentity(msg.sender, name, metadata, IdentityType.HUMAN_PROVIDER);
        return tokenId;
    }

    /**
     * @notice 注册节点运营商身份
     * @param name 节点名称
     * @param metadata 元数据（节点规格、位置等信息）
     * @return tokenId 代币 ID
     */
    function registerNodeOperator(string memory name, string memory metadata)
        external
        payable
        notRegistered(msg.sender)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        tokenId = _registerIdentity(msg.sender, name, metadata, IdentityType.NODE_OPERATOR);
        return tokenId;
    }

    /**
     * @notice 注册治理参与者身份
     * @param name 治理者名称
     * @param metadata 元数据（治理历史、提案记录等）
     * @return tokenId 代币 ID
     */
    function registerGovernance(string memory name, string memory metadata)
        external
        payable
        notRegistered(msg.sender)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        tokenId = _registerIdentity(msg.sender, name, metadata, IdentityType.GOVERNANCE);
        return tokenId;
    }

    /**
     * @notice 使用 ETH 注册身份
     * @param name 名称
     * @param metadata 元数据
     * @param identityType 身份类型
     */
    function registerWithEth(
        string memory name,
        string memory metadata,
        IdentityType identityType
    )
        external
        payable
        nonReentrant
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        require(msg.value >= ETH_REGISTRATION_FEE, "VIBIdentity: insufficient ETH");

        tokenId = _registerIdentity(msg.sender, name, metadata, identityType);

        // 退还多余的 ETH
        if (msg.value > ETH_REGISTRATION_FEE) {
            payable(msg.sender).transfer(msg.value - ETH_REGISTRATION_FEE);
        }

        emit IdentityRegisteredWithEth(msg.sender, tokenId, msg.value);

        return tokenId;
    }

    /**
     * @notice 使用 VIBE 代币注册身份
     * @param name 名称
     * @param metadata 元数据
     * @param identityType 身份类型
     */
    function registerWithVibe(
        string memory name,
        string memory metadata,
        IdentityType identityType
    )
        external
        nonReentrant
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        // 收取 VIBE 注册费
        IERC20(vibeToken).safeTransferFrom(msg.sender, address(this), REGISTRATION_FEE);

        tokenId = _registerIdentity(msg.sender, name, metadata, identityType);

        emit IdentityRegisteredWithVibe(msg.sender, tokenId, REGISTRATION_FEE);

        return tokenId;
    }

    /**
     * @notice 更新身份元数据
     * @param tokenId 代币 ID
     * @param metadata 新的元数据
     */
    function updateMetadata(uint256 tokenId, string memory metadata)
        external
        tokenExists(tokenId)
        whenNotPaused
    {
        require(
            msg.sender == identities[tokenId].owner,
            "VIBIdentity: not the owner"
        );

        identities[tokenId].metadata = metadata;
        emit IdentityUpdated(tokenId, metadata);
    }

    /**
     * @notice 验证身份
     * @param tokenId 代币 ID
     * @param verified 是否验证
     */
    function verifyIdentity(uint256 tokenId, bool verified)
        external
        onlyOwner
        tokenExists(tokenId)
    {
        bool wasVerified = identities[tokenId].isVerified;
        identities[tokenId].isVerified = verified;

        // 更新验证计数
        if (verified && !wasVerified) {
            verifiedCount++;
        } else if (!verified && wasVerified) {
            verifiedCount--;
        }

        emit IdentityVerified(tokenId, verified);
    }

    /**
     * @notice 撤销身份（仅管理员可调用）
     * @param tokenId 代币 ID
     */
    function revokeIdentity(uint256 tokenId)
        external
        onlyOwner
        tokenExists(tokenId)
    {
        address owner = identities[tokenId].owner;
        IdentityType identityType = identities[tokenId].identityType;

        // 释放名称
        string memory name = identities[tokenId].name;
        nameUsed[name] = false;
        isRegistered[owner] = false;
        addressToTokenId[owner] = 0;

        // 更新类型计数
        if (identityTypeCount[identityType] > 0) {
            identityTypeCount[identityType]--;
        }

        // 更新验证计数（如果已验证）
        if (identities[tokenId].isVerified && verifiedCount > 0) {
            verifiedCount--;
        }

        // AI-004修复: 如果是AI Agent，更新创建者的Agent计数
        if (identityType == IdentityType.AI_AGENT) {
            address creator = agentCreator[owner];
            if (creator != address(0) && userAgentCount[creator] > 0) {
                userAgentCount[creator]--;
            }
            agentCreator[owner] = address(0);
        }

        // 销毁代币
        _burn(tokenId);

        emit IdentityRevoked(tokenId, owner);
    }

    // ========== 管理员函数 ==========

    /**
     * @notice 设置 VIBE 代币地址
     * @param _vibeToken 新的代币地址
     */
    function setVibeToken(address _vibeToken) external onlyOwner {
        require(_vibeToken != address(0), "VIBIdentity: invalid token address");
        emit TokenUpdated(vibeToken, _vibeToken);
        vibeToken = _vibeToken;
    }

    /**
     * @notice 设置质押合约地址 - AI-004修复
     * @param _stakingContract 质押合约地址
     */
    function setStakingContract(address _stakingContract) external onlyOwner {
        stakingContract = _stakingContract;
        emit StakingContractUpdated(_stakingContract);
    }

    /// @notice 质押合约更新事件 - AI-004修复
    event StakingContractUpdated(address indexed stakingContract);

    /**
     * @notice 暂停注册
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice 恢复注册
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice 提取合约余额
     * @param amount 提取金额 (0 表示全部)
     */
    function withdraw(uint256 amount) external onlyOwner {
        uint256 availableBalance = address(this).balance;
        require(availableBalance > 0, "VIBIdentity: no balance to withdraw");

        uint256 withdrawAmount = amount == 0 ? availableBalance : amount;
        require(withdrawAmount <= availableBalance, "VIBIdentity: insufficient balance");

        payable(owner()).transfer(withdrawAmount);
    }

    /**
     * @notice 提取 VIBE 代币余额
     * @param amount 提取金额 (0 表示全部)
     */
    function withdrawVibe(uint256 amount) external onlyOwner {
        uint256 availableBalance = IERC20(vibeToken).balanceOf(address(this));
        require(availableBalance > 0, "VIBIdentity: no VIBE balance to withdraw");

        uint256 withdrawAmount = amount == 0 ? availableBalance : amount;
        require(withdrawAmount <= availableBalance, "VIBIdentity: insufficient VIBE balance");

        IERC20(vibeToken).safeTransfer(owner(), withdrawAmount);
    }

    // ========== 公共视图函数 ==========

    /**
     * @notice 获取身份信息
     * @param tokenId 代币 ID
     * @return 身份信息
     */
    function getIdentityInfo(uint256 tokenId)
        external
        view
        returns (IdentityInfo memory)
    {
        return identities[tokenId];
    }

    /**
     * @notice 根据地址获取代币 ID
     * @param owner 地址
     * @return 代币 ID
     */
    function getTokenIdByAddress(address owner) external view returns (uint256) {
        return addressToTokenId[owner];
    }

    /**
     * @notice 检查名称是否可用
     * @param name 名称
     * @return 是否可用
     */
    function checkNameAvailable(string memory name) external view returns (bool) {
        return !nameUsed[name];
    }

    /**
     * @notice 获取身份类型
     * @param tokenId 代币 ID
     * @return 身份类型
     */
    function getIdentityType(uint256 tokenId) external view returns (IdentityType) {
        return identities[tokenId].identityType;
    }

    /**
     * @notice 获取已验证身份数量
     * @return 已验证身份数量
     * @dev 使用缓存计数器，O(1)复杂度
     */
    function getVerifiedCount() external view returns (uint256) {
        return verifiedCount;
    }

    /**
     * @notice 获取指定类型的身份数量
     * @param identityType 身份类型
     * @return 该类型的身份数量
     * @dev 使用缓存计数器，O(1)复杂度
     */
    function getCountByType(IdentityType identityType) external view returns (uint256) {
        return identityTypeCount[identityType];
    }

    /**
     * @notice 获取用户的Agent数量限制 - AI-004修复
     * @param user 用户地址
     * @return 限制数量
     */
    function getAgentLimit(address user) external view returns (uint256) {
        return _getAgentLimit(user);
    }

    /**
     * @notice 获取用户当前已创建的Agent数量 - AI-004修复
     * @param user 用户地址
     * @return 已创建数量
     */
    function getUserAgentCount(address user) external view returns (uint256) {
        return userAgentCount[user];
    }

    /**
     * @notice 获取Agent的创建者 - AI-004修复
     * @param agent Agent地址
     * @return 创建者地址
     */
    function getAgentCreator(address agent) external view returns (address) {
        return agentCreator[agent];
    }

    // ========== 内部函数 ==========

    /**
     * @notice 注册身份的内部实现
     * @param owner 拥有者地址
     * @param name 名称
     * @param metadata 元数据
     * @param identityType 身份类型
     * @return tokenId 新代币 ID
     */
    function _registerIdentity(
        address owner,
        string memory name,
        string memory metadata,
        IdentityType identityType
    ) internal returns (uint256 tokenId) {
        tokenId = _currentTokenId + 1;
        require(tokenId <= MAX_TOKEN_ID, "VIBIdentity: max token id reached");

        _currentTokenId = tokenId;
        identityCount++;
        identityTypeCount[identityType]++; // 更新类型计数

        // 铸造 SBT
        _safeMint(owner, tokenId);

        // 存储身份信息
        identities[tokenId] = IdentityInfo({
            owner: owner,
            identityType: identityType,
            name: name,
            registrationTime: block.timestamp,
            metadata: metadata,
            isVerified: false
        });

        // 更新映射
        addressToTokenId[owner] = tokenId;
        nameUsed[name] = true;
        isRegistered[owner] = true;

        emit IdentityRegistered(tokenId, owner, identityType, name, metadata);

        return tokenId;
    }

    // ========== 重写函数 ==========

    /**
     * @notice 重写 tokenURI 以支持动态 URI
     * @param tokenId 代币 ID
     * @return 代币 URI
     */
    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    /**
     * @notice 重写 supportsInterface
     * @param interfaceId 接口 ID
     * @return 是否支持该接口
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    /**
     * @notice 重写 _update 以防止转账（SBT 不可转移）
     * @param to 接收者
     * @param tokenId 代币 ID
     * @param auth 授权
     * @return to 接收者地址
     */
    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        address owner = _ownerOf(tokenId);

        // 防止转账，但允许铸造（to == address(0)）和销毁（to == address(0)）
        // 当 to == address(0) 时是销毁操作，应该被允许
        if (owner != address(0) && to != address(0)) {
            revert("VIBIdentity: soulbound tokens cannot be transferred");
        }

        return super._update(to, tokenId, auth);
    }

    // ========== 接收函数 ==========

    /**
     * @notice 接收以太
     */
    receive() external payable {
        // 接收注册费用
    }
}
