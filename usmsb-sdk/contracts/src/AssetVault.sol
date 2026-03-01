// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721.sol";
import "@openzeppelin/contracts/token/ERC721/IERC721Receiver.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/Pausable.sol";

/**
 * @title AssetVault
 * @notice 资产碎片化合约 - 将创意资产(NFT)碎片化为可交易的ERC20代币
 * @dev 实现NFT存入、碎片发行、收益分发、碎片交易、NFT赎回
 */
contract AssetVault is ERC20, Ownable, ReentrancyGuard, Pausable, IERC721Receiver {
    using SafeERC20 for IERC20;

    // ========== 常量 ==========

    uint256 public constant MIN_SHARES = 100;              // 最小碎片数
    uint256 public constant MAX_SHARES = 1000000;          // 最大碎片数
    uint256 public constant PLATFORM_FEE_RATE = 250;       // 平台费率 2.5% (基点)
    uint256 public constant CREATOR_FEE_RATE = 500;        // 创作者费率 5% (基点)

    // ========== 数据结构 ==========

    struct AssetInfo {
        bytes32 assetId;                  // 资产ID
        address nftContract;              // 原NFT合约地址
        uint256 nftTokenId;               // NFT Token ID
        address originalOwner;            // 原所有者
        uint256 totalShares;              // 总碎片数
        uint256 sharePrice;               // 初始碎片价格
        uint256 sharesSold;               // 已售碎片数
        uint256 totalEarnings;            // 累计收益
        uint256 distributedEarnings;      // 已分发收益
        uint256 createdAt;                // 创建时间
        bool isFragmented;                // 是否已碎片化
        bool isTradable;                  // 是否可交易
        bool isRedeemed;                  // 是否已赎回
        string metadata;                  // 元数据URI
    }

    struct Shareholder {
        uint256 shares;                   // 持有碎片数
        uint256 claimedEarnings;          // 已领取收益
        uint256 purchaseTime;             // 首次购买时间
    }

    // ========== 状态变量 ==========

    IERC20 public paymentToken;

    mapping(bytes32 => AssetInfo) public assets;
    mapping(bytes32 => mapping(address => Shareholder)) public shareholders;
    mapping(bytes32 => address[]) public assetShareholders;
    mapping(address => bytes32[]) public userAssets;

    address public feeCollector;
    uint256 public totalAssetsCreated;
    uint256 public totalVolume;

    // ========== 事件 ==========

    event AssetFragmented(
        bytes32 indexed assetId,
        address indexed nftContract,
        uint256 indexed tokenId,
        address originalOwner,
        uint256 totalShares,
        uint256 sharePrice,
        string metadata
    );

    event SharesPurchased(
        bytes32 indexed assetId,
        address indexed buyer,
        uint256 shareAmount,
        uint256 pricePerShare,
        uint256 totalPaid
    );

    event SharesTransferred(
        bytes32 indexed assetId,
        address indexed from,
        address indexed to,
        uint256 amount
    );

    event EarningsDistributed(
        bytes32 indexed assetId,
        uint256 amount,
        uint256 perShare,
        uint256 totalShareholders
    );

    event EarningsClaimed(
        bytes32 indexed assetId,
        address indexed holder,
        uint256 amount
    );

    event NFTRedeemed(
        bytes32 indexed assetId,
        address indexed redeemer,
        uint256 tokenId
    );

    event TradingStateChanged(
        bytes32 indexed assetId,
        bool isTradable
    );

    // ========== 修饰符 ==========

    modifier assetExists(bytes32 assetId) {
        require(assets[assetId].createdAt > 0, "AssetVault: asset not exists");
        _;
    }

    modifier assetNotRedeemed(bytes32 assetId) {
        require(!assets[assetId].isRedeemed, "AssetVault: asset redeemed");
        _;
    }

    // ========== 构造函数 ==========

    constructor(
        address _paymentToken,
        address _feeCollector,
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) Ownable(msg.sender) {
        require(_paymentToken != address(0), "AssetVault: invalid payment token");
        require(_feeCollector != address(0), "AssetVault: invalid fee collector");

        paymentToken = IERC20(_paymentToken);
        feeCollector = _feeCollector;
    }

    // ========== 外部函数 - 资产管理 ==========

    /**
     * @notice 存入NFT并创建碎片
     * @param nftContract NFT合约地址
     * @param tokenId NFT Token ID
     * @param totalShares 总碎片数
     * @param sharePrice 初始碎片价格
     * @param metadata 元数据URI
     * @return assetId 资产ID
     */
    function depositAndFragment(
        address nftContract,
        uint256 tokenId,
        uint256 totalShares,
        uint256 sharePrice,
        string calldata metadata
    ) external nonReentrant whenNotPaused returns (bytes32) {
        require(totalShares >= MIN_SHARES, "AssetVault: shares too low");
        require(totalShares <= MAX_SHARES, "AssetVault: shares too high");
        require(sharePrice > 0, "AssetVault: zero price");

        // 生成资产ID
        bytes32 assetId = keccak256(
            abi.encodePacked(
                nftContract,
                tokenId,
                msg.sender,
                block.timestamp,
                totalAssetsCreated
            )
        );

        // 转入NFT
        IERC721 nft = IERC721(nftContract);
        nft.safeTransferFrom(msg.sender, address(this), tokenId);

        // 创建资产记录
        assets[assetId] = AssetInfo({
            assetId: assetId,
            nftContract: nftContract,
            nftTokenId: tokenId,
            originalOwner: msg.sender,
            totalShares: totalShares,
            sharePrice: sharePrice,
            sharesSold: 0,
            totalEarnings: 0,
            distributedEarnings: 0,
            createdAt: block.timestamp,
            isFragmented: true,
            isTradable: true,
            isRedeemed: false,
            metadata: metadata
        });

        // 铸造碎片代币给原所有者(保留部分作为创作者份额)
        uint256 creatorShares = (totalShares * 10) / 100; // 10%给创作者
        _mint(msg.sender, creatorShares);

        shareholders[assetId][msg.sender] = Shareholder({
            shares: creatorShares,
            claimedEarnings: 0,
            purchaseTime: block.timestamp
        });
        assetShareholders[assetId].push(msg.sender);
        assets[assetId].sharesSold = creatorShares;

        userAssets[msg.sender].push(assetId);
        totalAssetsCreated++;

        emit AssetFragmented(
            assetId,
            nftContract,
            tokenId,
            msg.sender,
            totalShares,
            sharePrice,
            metadata
        );

        return assetId;
    }

    /**
     * @notice 购买碎片
     * @param assetId 资产ID
     * @param shareAmount 购买数量
     */
    function purchaseShares(
        bytes32 assetId,
        uint256 shareAmount
    ) 
        external 
        nonReentrant 
        whenNotPaused
        assetExists(assetId)
        assetNotRedeemed(assetId)
    {
        AssetInfo storage asset = assets[assetId];

        require(asset.isTradable, "AssetVault: not tradable");
        require(shareAmount > 0, "AssetVault: zero amount");

        uint256 availableShares = asset.totalShares - asset.sharesSold;
        require(shareAmount <= availableShares, "AssetVault: insufficient shares");

        uint256 totalCost = shareAmount * asset.sharePrice;

        // 转入支付代币
        paymentToken.safeTransferFrom(msg.sender, address(this), totalCost);

        // 计算费用
        uint256 platformFee = (totalCost * PLATFORM_FEE_RATE) / 10000;
        uint256 creatorFee = (totalCost * CREATOR_FEE_RATE) / 10000;

        // 更新资产状态
        asset.sharesSold += shareAmount;
        asset.totalEarnings += totalCost;

        // 铸造碎片代币
        _mint(msg.sender, shareAmount);

        // 更新持有人信息
        Shareholder storage holder = shareholders[assetId][msg.sender];
        if (holder.shares == 0) {
            assetShareholders[assetId].push(msg.sender);
            userAssets[msg.sender].push(assetId);
            holder.purchaseTime = block.timestamp;
        }
        holder.shares += shareAmount;

        // 转移费用
        paymentToken.safeTransfer(feeCollector, platformFee);
        paymentToken.safeTransfer(asset.originalOwner, creatorFee);

        totalVolume += totalCost;

        emit SharesPurchased(
            assetId,
            msg.sender,
            shareAmount,
            asset.sharePrice,
            totalCost
        );
    }

    /**
     * @notice 分发收益
     * @param assetId 资产ID
     * @param amount 收益金额
     */
    function distributeEarnings(
        bytes32 assetId,
        uint256 amount
    ) 
        external 
        payable 
        nonReentrant
        assetExists(assetId)
        assetNotRedeemed(assetId)
    {
        require(amount > 0, "AssetVault: zero amount");

        AssetInfo storage asset = assets[assetId];

        // 转入收益
        paymentToken.safeTransferFrom(msg.sender, address(this), amount);

        // 计算每股收益
        uint256 perShare = (amount * 1e18) / asset.totalShares;

        asset.totalEarnings += amount;
        asset.distributedEarnings += amount;

        emit EarningsDistributed(
            assetId,
            amount,
            perShare,
            assetShareholders[assetId].length
        );
    }

    /**
     * @notice 领取收益
     * @param assetId 资产ID
     */
    function claimEarnings(bytes32 assetId) 
        external 
        nonReentrant
        assetExists(assetId)
    {
        AssetInfo storage asset = assets[assetId];
        Shareholder storage holder = shareholders[assetId][msg.sender];

        require(holder.shares > 0, "AssetVault: no shares");

        // 计算待领取收益
        uint256 totalEntitled = (holder.shares * asset.distributedEarnings) / asset.totalShares;
        uint256 unclaimed = totalEntitled - holder.claimedEarnings;

        require(unclaimed > 0, "AssetVault: no earnings");

        holder.claimedEarnings = totalEntitled;

        paymentToken.safeTransfer(msg.sender, unclaimed);

        emit EarningsClaimed(assetId, msg.sender, unclaimed);
    }

    /**
     * @notice 赎回NFT(需要持有全部碎片)
     * @param assetId 资产ID
     */
    function redeemNFT(bytes32 assetId)
        external
        nonReentrant
        assetExists(assetId)
        assetNotRedeemed(assetId)
    {
        AssetInfo storage asset = assets[assetId];
        Shareholder storage holder = shareholders[assetId][msg.sender];

        // 检查是否持有全部份额
        require(holder.shares >= asset.totalShares, "AssetVault: insufficient shares");

        // 检查 NFT 是否在合约中
        require(
            IERC721(asset.nftContract).ownerOf(asset.nftTokenId) == address(this),
            "AssetVault: NFT not in vault"
        );

        // 检查合约是否有 NFT 转移权限
        require(
            IERC721(asset.nftContract).getApproved(asset.nftTokenId) == address(this) ||
            IERC721(asset.nftContract).isApprovedForAll(msg.sender, address(this)),
            "AssetVault: NFT transfer not approved"
        );

        asset.isRedeemed = true;

        // 销毁碎片代币
        _burn(msg.sender, asset.totalShares);

        // 转出NFT
        IERC721 nft = IERC721(asset.nftContract);
        nft.safeTransferFrom(address(this), msg.sender, asset.nftTokenId);

        emit NFTRedeemed(assetId, msg.sender, asset.nftTokenId);
    }

    /**
     * @notice 设置交易状态
     * @param assetId 资产ID
     * @param isTradable 是否可交易
     */
    function setTradingState(
        bytes32 assetId,
        bool isTradable
    ) 
        external 
        assetExists(assetId)
    {
        AssetInfo storage asset = assets[assetId];
        require(
            msg.sender == asset.originalOwner || msg.sender == owner(),
            "AssetVault: not authorized"
        );

        asset.isTradable = isTradable;

        emit TradingStateChanged(assetId, isTradable);
    }

    // ========== 公共视图函数 ==========

    function getAssetInfo(bytes32 assetId) 
        external 
        view 
        returns (AssetInfo memory) 
    {
        return assets[assetId];
    }

    function getShareholder(
        bytes32 assetId,
        address holder
    ) external view returns (Shareholder memory) {
        return shareholders[assetId][holder];
    }

    function getUnclaimedEarnings(
        bytes32 assetId,
        address holder
    ) external view returns (uint256) {
        AssetInfo storage asset = assets[assetId];
        Shareholder storage shareholder = shareholders[assetId][holder];

        if (shareholder.shares == 0) return 0;

        uint256 totalEntitled = (shareholder.shares * asset.distributedEarnings) / asset.totalShares;
        return totalEntitled - shareholder.claimedEarnings;
    }

    function getAssetShareholders(bytes32 assetId) 
        external 
        view 
        returns (address[] memory) 
    {
        return assetShareholders[assetId];
    }

    function getUserAssets(address user) 
        external 
        view 
        returns (bytes32[] memory) 
    {
        return userAssets[user];
    }

    function getAvailableShares(bytes32 assetId) 
        external 
        view 
        returns (uint256) 
    {
        AssetInfo storage asset = assets[assetId];
        return asset.totalShares - asset.sharesSold;
    }

    function getStats() external view returns (
        uint256 _totalAssetsCreated,
        uint256 _totalVolume
    ) {
        return (totalAssetsCreated, totalVolume);
    }

    // ========== ERC721Receiver ==========

    function onERC721Received(
        address,
        address,
        uint256,
        bytes calldata
    ) external pure override returns (bytes4) {
        return IERC721Receiver.onERC721Received.selector;
    }

    // ========== 管理函数 ==========

    function setFeeCollector(address _feeCollector) external onlyOwner {
        require(_feeCollector != address(0), "AssetVault: invalid address");
        feeCollector = _feeCollector;
    }

    function pause() external onlyOwner {
        _pause();
    }

    function unpause() external onlyOwner {
        _unpause();
    }

    function emergencyWithdraw(
        address token,
        address to,
        uint256 amount
    ) external onlyOwner nonReentrant {
        require(to != address(0), "AssetVault: invalid recipient");
        require(amount > 0, "AssetVault: amount must be greater than 0");
        IERC20(token).safeTransfer(to, amount);
    }
}
