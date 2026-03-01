// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import "@openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";
import "./libraries/BN128Pairing.sol";

/**
 * @title ZKCredential
 * @notice zk-信用通行证合约 - 零知识证明信用凭证
 * @dev 使用zk-SNARK Groth16验证用户属性，同时保护隐私
 *      使用 BN128Pairing 库进行椭圆曲线配对验证
 */
contract ZKCredential is ERC721, ERC721URIStorage, Ownable, ReentrancyGuard, Pausable {

    // ========== 常量 ==========

    uint256 public constant MAX_CREDENTIAL_DURATION = 365 days;
    uint256 public constant MIN_CREDENTIAL_DURATION = 1 days;

    /// @notice Issuer 变更延迟时间 (7天)
    uint256 public constant ISSUER_CHANGE_DELAY = 7 days;

    // ========== 枚举 ==========

    enum CredentialType {
        IDENTITY,          // 身份凭证
        SERVICE_PROVIDER,  // 服务商凭证
        GOVERNANCE,        // 治理凭证
        PREMIUM,           // VIP凭证
        TRUSTED_NODE       // 可信节点凭证
    }

    enum CredentialStatus {
        ACTIVE,            // 活跃
        EXPIRED,           // 已过期
        REVOKED,           // 已撤销
        USED               // 已使用
    }

    // ========== 数据结构 ==========

    struct Credential {
        bytes32 credentialId;          // 凭证ID
        address holder;                // 持有人
        CredentialType credType;       // 凭证类型
        uint256 validFrom;             // 生效时间
        uint256 validUntil;            // 失效时间
        bytes32 commitment;            // 承诺值(隐私保护)
        bytes32 nullifierHash;         // 无效符哈希(防重放)
        CredentialStatus status;       // 状态
        uint256 score;                 // 评分(链下计算)
        bytes metadata;                // 元数据(加密)
        uint256 createdAt;             // 创建时间
    }

    struct VerificationKey {
        uint256[2] alpha;
        uint256[2][2] beta;
        uint256[2] gamma;
        uint256[2] delta;
        uint256[2][] ic;
        bool isSet;
    }

    struct ProofData {
        uint256[2] a;
        uint256[2][2] b;
        uint256[2] c;
        uint256[] publicInputs;
    }

    struct VerificationRecord {
        bytes32 recordId;
        bytes32 credentialId;
        address verifier;
        uint256 timestamp;
        bool isValid;
        string purpose;
    }

    // ========== 状态变量 ==========

    mapping(bytes32 => Credential) public credentials;
    mapping(bytes32 => bool) public nullifierUsed;
    mapping(address => bytes32[]) public holderCredentials;
    mapping(CredentialType => VerificationKey) public verificationKeys;
    mapping(bytes32 => VerificationRecord[]) public verificationRecords;

    uint256 public totalCredentialsIssued;
    uint256 public totalVerifications;

    address public issuer;
    address public verifier;

    /// @notice 待生效的 issuer 地址
    address public pendingIssuer;

    /// @notice issuer 变更生效时间
    uint256 public issuerChangeEffectiveTime;

    // ========== 事件 ==========

    event CredentialIssued(
        bytes32 indexed credentialId,
        address indexed holder,
        CredentialType credType,
        uint256 validUntil,
        uint256 score
    );

    event CredentialVerified(
        bytes32 indexed credentialId,
        address indexed verifier,
        bool isValid,
        string purpose
    );

    event CredentialRevoked(
        bytes32 indexed credentialId,
        address indexed holder,
        string reason
    );

    event CredentialExpired(
        bytes32 indexed credentialId,
        address indexed holder
    );

    event VerificationKeyUpdated(
        CredentialType indexed credType
    );

    event IssuerUpdated(address indexed oldIssuer, address indexed newIssuer);

    /// @notice 待生效 issuer 设置事件
    event IssuerChangeInitiated(address indexed newIssuer, uint256 effectiveTime);

    /// @notice issuer 变更取消事件
    event IssuerChangeCancelled();

    // ========== 修饰符 ==========

    modifier onlyIssuer() {
        require(msg.sender == issuer || msg.sender == owner(), "ZKCredential: not issuer");
        _;
    }

    modifier credentialExists(bytes32 credentialId) {
        require(credentials[credentialId].createdAt > 0, "ZKCredential: not exists");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        string memory _name,
        string memory _symbol,
        address _issuer,
        address _verifier
    ) ERC721(_name, _symbol) Ownable(msg.sender) {
        require(_issuer != address(0), "ZKCredential: invalid issuer");
        require(_verifier != address(0), "ZKCredential: invalid verifier");

        issuer = _issuer;
        verifier = _verifier;
    }

    // ========== 外部函数 - 凭证管理 ==========

    /**
     * @notice 验证证明并签发凭证
     * @param holder 持有人地址
     * @param credType 凭证类型
     * @param validDuration 有效期(秒)
     * @param commitment 承诺值
     * @param nullifierHash 无效符哈希
     * @param score 评分
     * @param proof zk证明数据
     * @param metadata 加密元数据
     * @return credentialId 凭证ID
     */
    function verifyAndIssue(
        address holder,
        CredentialType credType,
        uint256 validDuration,
        bytes32 commitment,
        bytes32 nullifierHash,
        uint256 score,
        ProofData calldata proof,
        bytes calldata metadata
    ) 
        external 
        onlyIssuer 
        nonReentrant 
        whenNotPaused
        returns (bytes32)
    {
        require(holder != address(0), "ZKCredential: invalid holder");
        require(
            validDuration >= MIN_CREDENTIAL_DURATION && 
            validDuration <= MAX_CREDENTIAL_DURATION,
            "ZKCredential: invalid duration"
        );
        require(!nullifierUsed[nullifierHash], "ZKCredential: nullifier used");

        // 验证zk证明
        require(_verifyProof(credType, proof, commitment, nullifierHash, score, holder), "ZKCredential: invalid proof");

        bytes32 credentialId = keccak256(
            abi.encodePacked(
                holder,
                credType,
                block.timestamp,
                totalCredentialsIssued
            )
        );

        uint256 validFrom = block.timestamp;
        uint256 validUntil = block.timestamp + validDuration;

        credentials[credentialId] = Credential({
            credentialId: credentialId,
            holder: holder,
            credType: credType,
            validFrom: validFrom,
            validUntil: validUntil,
            commitment: commitment,
            nullifierHash: nullifierHash,
            status: CredentialStatus.ACTIVE,
            score: score,
            metadata: metadata,
            createdAt: block.timestamp
        });

        nullifierUsed[nullifierHash] = true;
        holderCredentials[holder].push(credentialId);
        totalCredentialsIssued++;

        // 铸造NFT
        uint256 tokenId = uint256(credentialId);
        _safeMint(holder, tokenId);

        emit CredentialIssued(credentialId, holder, credType, validUntil, score);

        return credentialId;
    }

    /**
     * @notice 验证凭证
     * @param credentialId 凭证ID
     * @param nullifierHash 无效符哈希
     * @param proof zk证明数据
     * @param purpose 验证目的
     * @return isValid 是否有效
     */
    function verifyCredential(
        bytes32 credentialId,
        bytes32 nullifierHash,
        ProofData calldata proof,
        string calldata purpose
    ) 
        external 
        nonReentrant
        credentialExists(credentialId)
        returns (bool)
    {
        Credential storage cred = credentials[credentialId];

        bool isValid = _checkCredentialValidity(cred) && 
                      _verifyOwnership(cred, nullifierHash, proof);

        bytes32 recordId = keccak256(
            abi.encodePacked(
                credentialId,
                msg.sender,
                block.timestamp,
                totalVerifications
            )
        );

        verificationRecords[credentialId].push(VerificationRecord({
            recordId: recordId,
            credentialId: credentialId,
            verifier: msg.sender,
            timestamp: block.timestamp,
            isValid: isValid,
            purpose: purpose
        }));

        totalVerifications++;

        emit CredentialVerified(credentialId, msg.sender, isValid, purpose);

        return isValid;
    }

    /**
     * @notice 撤销凭证
     * @param credentialId 凭证ID
     * @param reason 撤销原因
     */
    function revokeCredential(
        bytes32 credentialId,
        string calldata reason
    ) 
        external 
        onlyIssuer
        credentialExists(credentialId)
    {
        Credential storage cred = credentials[credentialId];

        require(cred.status == CredentialStatus.ACTIVE, "ZKCredential: not active");

        cred.status = CredentialStatus.REVOKED;

        emit CredentialRevoked(credentialId, cred.holder, reason);
    }

    /**
     * @notice 检查并更新过期凭证
     * @param credentialId 凭证ID
     */
    function checkExpiry(bytes32 credentialId) 
        external 
        credentialExists(credentialId)
    {
        Credential storage cred = credentials[credentialId];

        if (cred.status == CredentialStatus.ACTIVE && block.timestamp > cred.validUntil) {
            cred.status = CredentialStatus.EXPIRED;
            emit CredentialExpired(credentialId, cred.holder);
        }
    }

    /**
     * @notice 批量检查过期凭证
     * @param credentialIds 凭证ID数组
     */
    function batchCheckExpiry(bytes32[] calldata credentialIds) external {
        for (uint256 i = 0; i < credentialIds.length; i++) {
            if (credentials[credentialIds[i]].createdAt > 0) {
                Credential storage cred = credentials[credentialIds[i]];
                if (cred.status == CredentialStatus.ACTIVE && block.timestamp > cred.validUntil) {
                    cred.status = CredentialStatus.EXPIRED;
                    emit CredentialExpired(credentialIds[i], cred.holder);
                }
            }
        }
    }

    // ========== 公共视图函数 ==========

    function isCredentialValid(bytes32 credentialId) external view returns (bool) {
        Credential storage cred = credentials[credentialId];
        return _checkCredentialValidity(cred);
    }

    function getCredential(bytes32 credentialId) 
        external 
        view 
        returns (Credential memory) 
    {
        return credentials[credentialId];
    }

    function hasCredentialType(
        address holder,
        CredentialType credType
    ) external view returns (bool) {
        bytes32[] storage credIds = holderCredentials[holder];
        for (uint256 i = 0; i < credIds.length; i++) {
            Credential storage cred = credentials[credIds[i]];
            if (cred.credType == credType && _checkCredentialValidity(cred)) {
                return true;
            }
        }
        return false;
    }

    function getActiveCredentials(
        address holder,
        CredentialType credType
    ) external view returns (bytes32[] memory) {
        bytes32[] storage credIds = holderCredentials[holder];
        uint256 count = 0;

        for (uint256 i = 0; i < credIds.length; i++) {
            if (credentials[credIds[i]].credType == credType && 
                _checkCredentialValidity(credentials[credIds[i]])) {
                count++;
            }
        }

        bytes32[] memory result = new bytes32[](count);
        uint256 index = 0;
        for (uint256 i = 0; i < credIds.length; i++) {
            if (credentials[credIds[i]].credType == credType && 
                _checkCredentialValidity(credentials[credIds[i]])) {
                result[index] = credIds[i];
                index++;
            }
        }

        return result;
    }

    function getHolderCredentials(address holder) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return holderCredentials[holder];
    }

    function getVerificationRecords(bytes32 credentialId) 
        external 
        view 
        returns (VerificationRecord[] memory) 
    {
        return verificationRecords[credentialId];
    }

    function getStats() external view returns (
        uint256 _totalCredentialsIssued,
        uint256 _totalVerifications
    ) {
        return (totalCredentialsIssued, totalVerifications);
    }

    // ========== 内部函数 ==========

    function _checkCredentialValidity(Credential storage cred) internal view returns (bool) {
        return cred.status == CredentialStatus.ACTIVE && 
               block.timestamp >= cred.validFrom &&
               block.timestamp <= cred.validUntil;
    }

    function _verifyProof(
        CredentialType credType,
        ProofData calldata proof,
        bytes32 commitment,
        bytes32 nullifierHash,
        uint256 score,
        address holder
    ) internal view returns (bool) {
        VerificationKey storage vk = verificationKeys[credType];

        // 安全修复: 验证密钥必须已设置，禁用占位符实现
        // 生产环境必须配置正确的Groth16验证密钥
        require(vk.isSet, "ZKCredential: verification key not set");

        // 验证 publicInputs 数据一致性
        if (proof.publicInputs.length >= 3) {
            require(
                bytes32(proof.publicInputs[0]) == commitment,
                "ZKCredential: commitment mismatch"
            );
            require(
                bytes32(proof.publicInputs[1]) == nullifierHash,
                "ZKCredential: nullifier mismatch"
            );
            require(
                proof.publicInputs[2] == score,
                "ZKCredential: score mismatch"
            );
        }

        return _verifySnark(vk, proof, commitment, nullifierHash, score, holder);
    }

    function _verifyOwnership(
        Credential storage cred,
        bytes32 nullifierHash,
        ProofData calldata proof
    ) internal view returns (bool) {
        return cred.nullifierHash == nullifierHash ||
               bytes32(proof.publicInputs[1]) == cred.nullifierHash;
    }

    /// @dev 验证zk-SNARK证明 (Groth16)
    /// 使用 BN128Pairing 库进行椭圆曲线配对验证
    ///
    /// Groth16 验证流程:
    /// 1. 验证公共输入与承诺一致
    /// 2. 使用椭圆曲线配对验证证明
    ///
    /// @param vk 验证密钥
    /// @param proof 证明数据 (Groth16 格式: a, b, c)
    /// @param commitment 承诺值
    /// @param nullifierHash 无效符哈希
    /// @param score 评分
    /// @param holder 持有人地址
    function _verifySnark(
        VerificationKey storage vk,
        ProofData calldata proof,
        bytes32 commitment,
        bytes32 nullifierHash,
        uint256 score,
        address holder
    ) internal view returns (bool) {
        // 验证证明数据结构完整性
        require(vk.alpha[0] != 0 && vk.alpha[1] != 0, "ZKCredential: invalid vk alpha");
        require(vk.beta[0][0] != 0 && vk.beta[0][1] != 0, "ZKCredential: invalid vk beta");
        require(vk.gamma[0] != 0 && vk.gamma[1] != 0, "ZKCredential: invalid vk gamma");
        require(vk.delta[0] != 0 && vk.delta[1] != 0, "ZKCredential: invalid vk delta");
        require(vk.ic.length > 0, "ZKCredential: invalid vk ic");

        // 检查证明数据完整性
        require(proof.a[0] != 0 || proof.a[1] != 0, "ZKCredential: invalid proof a");
        require(proof.b[0][0] != 0 || proof.b[0][1] != 0, "ZKCredential: invalid proof b");
        require(proof.c[0] != 0 || proof.c[1] != 0, "ZKCredential: invalid proof c");

        // 验证公共输入数量
        require(proof.publicInputs.length >= 3, "ZKCredential: insufficient public inputs");

        // 使用 BN128Pairing 库进行完整的 Groth16 验证
        bool isValid = BN128Pairing.verifyProof(
            vk.alpha,
            vk.beta,
            vk.gamma,
            vk.delta,
            vk.ic,
            proof.a,
            proof.b,
            proof.c,
            proof.publicInputs
        );

        require(isValid, "ZKCredential: proof verification failed");

        return true;
    }

    // ========== 管理函数 ==========

    function updateVerificationKey(
        CredentialType credType,
        uint256[2] memory alpha,
        uint256[2][2] memory beta,
        uint256[2] memory gamma,
        uint256[2] memory delta,
        uint256[2][] memory ic
    ) external onlyOwner {
        VerificationKey storage vk = verificationKeys[credType];
        vk.alpha = alpha;
        vk.beta = beta;
        vk.gamma = gamma;
        vk.delta = delta;
        vk.ic = ic;
        vk.isSet = true;

        emit VerificationKeyUpdated(credType);
    }

    /**
     * @notice 发起 issuer 变更（需要经过时间锁）
     * @param _issuer 新的 issuer 地址
     */
    function setIssuer(address _issuer) external onlyOwner {
        require(_issuer != address(0), "ZKCredential: invalid issuer");
        require(_issuer != issuer, "ZKCredential: same as current issuer");

        // 如果有待生效的变更，先取消
        if (pendingIssuer != address(0)) {
            delete pendingIssuer;
            delete issuerChangeEffectiveTime;
            emit IssuerChangeCancelled();
        }

        // 设置待生效的 issuer
        pendingIssuer = _issuer;
        issuerChangeEffectiveTime = block.timestamp + ISSUER_CHANGE_DELAY;

        emit IssuerChangeInitiated(_issuer, issuerChangeEffectiveTime);
    }

    /**
     * @notice 确认 issuer 变更（在延迟期过后）
     */
    function confirmIssuerChange() external onlyOwner {
        require(pendingIssuer != address(0), "ZKCredential: no pending issuer change");
        require(
            block.timestamp >= issuerChangeEffectiveTime,
            "ZKCredential: issuer change not yet effective"
        );

        address oldIssuer = issuer;
        issuer = pendingIssuer;

        // 清除待生效状态
        delete pendingIssuer;
        delete issuerChangeEffectiveTime;

        emit IssuerUpdated(oldIssuer, issuer);
    }

    /**
     * @notice 取消待生效的 issuer 变更
     */
    function cancelIssuerChange() external onlyOwner {
        require(pendingIssuer != address(0), "ZKCredential: no pending issuer change");

        delete pendingIssuer;
        delete issuerChangeEffectiveTime;

        emit IssuerChangeCancelled();
    }

    function setVerifier(address _verifier) external onlyOwner {
        require(_verifier != address(0), "ZKCredential: invalid verifier");
        verifier = _verifier;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    // ========== ERC721 重写 ==========

    function tokenURI(uint256 tokenId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (string memory)
    {
        return super.tokenURI(tokenId);
    }

    function supportsInterface(bytes4 interfaceId)
        public
        view
        override(ERC721, ERC721URIStorage)
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }

    function _update(address to, uint256 tokenId, address auth)
        internal
        override
        returns (address)
    {
        address from = _ownerOf(tokenId);

        if (from != address(0)) {
            bytes32 credentialId = bytes32(tokenId);
            require(
                credentials[credentialId].status == CredentialStatus.REVOKED,
                "ZKCredential: non-transferable"
            );
        }

        return super._update(to, tokenId, auth);
    }
}
