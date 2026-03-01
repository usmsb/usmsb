// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title MockPriceOracle
 * @notice 模拟价格预言机，用于测试
 */
contract MockPriceOracle {
    uint256 private price;
    uint256 private avgPrice;

    function setPrice(uint256 _price) external {
        price = _price;
    }

    function set7DayAverage(uint256 _avgPrice) external {
        avgPrice = _avgPrice;
    }

    function getPrice() external view returns (uint256) {
        return price;
    }

    function get7DayAverage() external view returns (uint256) {
        return avgPrice > 0 ? avgPrice : price;
    }

    function lastValidPrice() external view returns (uint256) {
        return price;
    }
}

/**
 * @title MockDEXRouter
 * @notice 模拟 DEX 路由器，用于测试
 */
contract MockDEXRouter {
    address payable public weth;
    address public vibeToken;
    address public factory;
    address public pair;

    constructor(address _vibeToken) {
        vibeToken = _vibeToken;
        weth = payable(address(new MockWETH()));

        // 创建工厂和配对
        MockDEXFactory _factory = new MockDEXFactory();
        factory = address(_factory);

        // 创建 VIBE-WETH 配对
        pair = _factory.createPair(_vibeToken, weth);
    }

    function getWETH() external view returns (address) {
        return weth;
    }

    function swapExactETHForTokens(
        uint256 /* amountOutMin */,
        address[] calldata path,
        address to,
        uint256 /* deadline */
    ) external payable returns (uint256[] memory amounts) {
        // 简化实现：直接铸造代币给接收者
        amounts = new uint256[](2);
        amounts[0] = msg.value;
        amounts[1] = msg.value * 1000; // 假设 1 ETH = 1000 VIBE

        // 模拟买入（从 VIBE token 转账）
        MockWETH(weth).deposit{value: msg.value}();

        return amounts;
    }

    function addLiquidityETH(
        address token,
        uint256 amountTokenDesired,
        uint256 /* amountTokenMin */,
        uint256 /* amountETHMin */,
        address /* to */,
        uint256 /* deadline */
    ) external payable returns (
        uint256 amountToken,
        uint256 amountETH,
        uint256 liquidity
    ) {
        amountToken = amountTokenDesired;
        amountETH = msg.value;
        liquidity = amountTokenDesired + msg.value; // 简化 LP 计算

        return (amountToken, amountETH, liquidity);
    }

    function removeLiquidityETH(
        address /* token */,
        uint256 liquidity,
        uint256 /* amountTokenMin */,
        uint256 /* amountETHMin */,
        address to,
        uint256 /* deadline */
    ) external returns (
        uint256 amountToken,
        uint256 amountETH
    ) {
        // 简化实现
        amountToken = liquidity / 2;
        amountETH = liquidity / 2;

        // 转账
        MockWETH(weth).deposit{value: amountETH}();

        return (amountToken, amountETH);
    }
}

/**
 * @title MockDEXFactory
 * @notice 模拟 DEX 工厂，用于测试
 */
contract MockDEXFactory {
    mapping(address => mapping(address => address)) public getPair;

    function createPair(address tokenA, address tokenB) external returns (address) {
        MockPair pair = new MockPair(tokenA, tokenB);
        getPair[tokenA][tokenB] = address(pair);
        getPair[tokenB][tokenA] = address(pair);
        return address(pair);
    }
}

/**
 * @title MockPair
 * @notice 模拟 LP 代币对
 */
contract MockPair is ERC20 {
    address public token0;
    address public token1;
    uint112 private reserve0;
    uint112 private reserve1;

    constructor(address _token0, address _token1) ERC20("Mock LP", "MLP") {
        token0 = _token0;
        token1 = _token1;
        // 铸造一些初始 LP
        _mint(msg.sender, 1000000 * 10**18);
        reserve0 = 1000000;
        reserve1 = 1000000;
    }

    function getReserves() external view returns (
        uint112 _reserve0,
        uint112 _reserve1,
        uint32 blockTimestampLast
    ) {
        return (reserve0, reserve1, uint32(block.timestamp));
    }
}

/**
 * @title MockWETH
 * @notice 模拟 WETH
 */
contract MockWETH is ERC20 {
    constructor() ERC20("Wrapped Ether", "WETH") {}

    function deposit() external payable {
        _mint(msg.sender, msg.value);
    }

    function withdraw(uint256 amount) external {
        require(balanceOf(msg.sender) >= amount, "Insufficient balance");
        _burn(msg.sender, amount);
        payable(msg.sender).transfer(amount);
    }

    receive() external payable {
        _mint(msg.sender, msg.value);
    }
}
