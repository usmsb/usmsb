// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title VIBIdentity
 * @notice VIBE 灵魂绑定代币 (SBT)，实现 ERC-5192 标准
 * @dev 代币不可转移，用于身份认证
 */
contract VIBIdentity is ERC721, ERC721URIStorage, Ownable, Pausable {
    // ========== 常量 ==========

    /// @notice 注册费用（VIBE 代币）
    uint256 public constant REGISTRATION_FEE = 100 * 10**18; // 100 VIBE

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

    /// @notice 代币信息
    mapping(uint256 => IdentityInfo) public identities;

    /// @notice 地址到代币 ID 映射
    mapping(address => uint256) public addressToTokenId;

    /// @notice 地址是否已注册
    mapping(address => bool) public isRegistered;

    /// @notice 名称是否已被使用
    mapping(string => bool) public nameUsed;

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
     */
    function registerAIIdentity(string memory name, string memory metadata)
        external
        payable
        notRegistered(msg.sender)
        nameAvailable(name)
        whenNotPaused
        returns (uint256 tokenId)
    {
        tokenId = _registerIdentity(msg.sender, name, metadata, IdentityType.AI_AGENT);
        return tokenId;
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
        identities[tokenId].isVerified = verified;
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

        // 释放名称
        string memory name = identities[tokenId].name;
        nameUsed[name] = false;
        isRegistered[owner] = false;
        addressToTokenId[owner] = 0;

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
     */
    function withdraw() external onlyOwner {
        uint256 balance = address(this).balance;
        require(balance > 0, "VIBIdentity: no balance to withdraw");

        payable(owner()).transfer(balance);
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
     */
    function getVerifiedCount() external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 1; i < _currentTokenId; i++) {
            if (_ownerOf(i) != address(0) && identities[i].isVerified) {
                count++;
            }
        }
        return count;
    }

    /**
     * @notice 获取指定类型的身份数量
     * @param identityType 身份类型
     * @return 该类型的身份数量
     */
    function getCountByType(IdentityType identityType) external view returns (uint256) {
        uint256 count = 0;
        for (uint256 i = 1; i < _currentTokenId; i++) {
            if (_ownerOf(i) != address(0) && identities[i].identityType == identityType) {
                count++;
            }
        }
        return count;
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

        // 防止转账，但允许铸造（owner == address(0)）和销毁
        if (owner != address(0)) {
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
