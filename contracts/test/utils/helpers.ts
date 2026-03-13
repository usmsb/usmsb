import { ethers } from "hardhat";
import { BigNumber, Contract, Signer } from "ethers";
import { expect } from "chai";

/**
 * Time manipulation helpers
 */
export const time = {
  async latest(): Promise<BigNumber> {
    const block = await ethers.provider.getBlock("latest");
    return BigNumber.from(block.timestamp);
  },

  async latestBlock(): Promise<number> {
    const block = await ethers.provider.getBlock("latest");
    return block.number;
  },

  async advance(seconds: number): Promise<void> {
    await ethers.provider.send("evm_increaseTime", [seconds]);
    await ethers.provider.send("evm_mine", []);
  },

  async advanceBlock(): Promise<void> {
    await ethers.provider.send("evm_mine", []);
  },

  async advanceBlockTo(blockNumber: number): Promise<void> {
    for (let i = await this.latestBlock(); i < blockNumber; i++) {
      await this.advanceBlock();
    }
  },

  async advanceBlockToWithTime(targetTimestamp: BigNumber): Promise<void> {
    const currentTimestamp = await this.latest();
    await this.advance(targetTimestamp.sub(currentTimestamp).toNumber());
  },

  async advanceTimeAndBlock(seconds: number): Promise<void> {
    await ethers.provider.send("evm_increaseTime", [seconds]);
    await ethers.provider.send("evm_mine", []);
  },

  async setNextBlockTimestamp(timestamp: number): Promise<void> {
    await ethers.provider.send("evm_setNextBlockTimestamp", [timestamp]);
  }
};

/**
 * Token helpers
 */
export const token = {
  async getBalance(token: Contract, account: string): Promise<BigNumber> {
    return await token.balanceOf(account);
  },

  async getTotalSupply(token: Contract): Promise<BigNumber> {
    return await token.totalSupply();
  }
};

/**
 * Staking helpers
 */
export const staking = {
  async stake(
    stakingContract: Contract,
    user: Signer,
    amount: BigNumber,
    lockDuration: number
  ): Promise<void> {
    await stakingContract.connect(user).stake(amount, lockDuration);
  },

  async unstake(
    stakingContract: Contract,
    user: Signer,
    amount: BigNumber
  ): Promise<void> {
    await stakingContract.connect(user).unstake(amount);
  },

  async claimRewards(stakingContract: Contract, user: Signer): Promise<void> {
    await stakingContract.connect(user).claimRewards();
  },

  async getStakedAmount(
    stakingContract: Contract,
    user: string
  ): Promise<BigNumber> {
    const stakeInfo = await stakingContract.stakes(user);
    return stakeInfo.amount;
  },

  async getRewards(
    stakingContract: Contract,
    user: string
  ): Promise<BigNumber> {
    return await stakingContract.calculateRewards(user);
  }
};

/**
 * Permit helpers (EIP-2612)
 */
export const permit = {
  async signPermit(
    token: Contract,
    owner: Signer,
    spender: string,
    value: BigNumber,
    deadline: BigNumber,
    nonce?: number
  ): Promise<{ v: number; r: string; s: string }> {
    const ownerAddress = await owner.getAddress();
    const chainId = await owner.getChainId();

    const domain = {
      name: await token.name(),
      version: "1",
      chainId: chainId,
      verifyingContract: token.address
    };

    const types = {
      Permit: [
        { name: "owner", type: "address" },
        { name: "spender", type: "address" },
        { name: "value", type: "uint256" },
        { name: "nonce", type: "uint256" },
        { name: "deadline", type: "uint256" }
      ]
    };

    const currentNonce = nonce !== undefined ? nonce : await token.nonces(ownerAddress);

    const values = {
      owner: ownerAddress,
      spender: spender,
      value: value,
      nonce: currentNonce,
      deadline: deadline
    };

    const signature = await owner._signTypedData(domain, types, values);
    const { v, r, s } = ethers.utils.splitSignature(signature);

    return { v, r, s };
  }
};

/**
 * Event helpers
 */
export const events = {
  async expectEvent(
    tx: Promise<any>,
    contract: Contract,
    eventName: string,
    args?: any[]
  ): Promise<any> {
    const receipt = await (await tx).wait();
    const event = receipt.events?.find((e: any) => e.event === eventName);
    expect(event, `Event ${eventName} not found`).to.not.be.undefined;

    if (args) {
      for (let i = 0; i < args.length; i++) {
        expect(event.args[i]).to.equal(args[i]);
      }
    }

    return event;
  },

  async getEventArgs(
    tx: Promise<any>,
    contract: Contract,
    eventName: string
  ): Promise<any> {
    const receipt = await (await tx).wait();
    const event = receipt.events?.find((e: any) => e.event === eventName);
    expect(event, `Event ${eventName} not found`).to.not.be.undefined;
    return event.args;
  }
};

/**
 * Error helpers
 */
export const errors = {
  async expectRevert(
    tx: Promise<any>,
    expectedError: string
  ): Promise<void> {
    await expect(tx).to.be.revertedWith(expectedError);
  },

  async expectCustomError(
    tx: Promise<any>,
    contract: Contract,
    errorName: string
  ): Promise<void> {
    await expect(tx).to.be.revertedWithCustomError(contract, errorName);
  }
};

/**
 * Gas helpers
 */
export const gas = {
  async estimateGas(tx: Promise<any>): Promise<BigNumber> {
    return await (await tx).estimateGas();
  },

  async getGasPrice(): Promise<BigNumber> {
    return await ethers.provider.getGasPrice();
  }
};

/**
 * Account helpers
 */
export const accounts = {
  async getSigners(): Promise<Signer[]> {
    return await ethers.getSigners();
  },

  async getDeployer(): Promise<Signer> {
    const [deployer] = await ethers.getSigners();
    return deployer;
  },

  async getRandomAccount(): Promise<{ signer: Signer; address: string }> {
    const wallet = ethers.Wallet.createRandom();
    return {
      signer: wallet.connect(ethers.provider),
      address: wallet.address
    };
  },

  async fundAccount(
    from: Signer,
    to: string,
    amount: BigNumber
  ): Promise<void> {
    await from.sendTransaction({
      to: to,
      value: amount
    });
  }
};

/**
 * Contract deployment helpers
 */
export const deploy = {
  async deployContract(
    contractName: string,
    args: any[] = [],
    deployer?: Signer
  ): Promise<Contract> {
    const Factory = await ethers.getContractFactory(contractName, deployer);
    const contract = await Factory.deploy(...args);
    await contract.deployed();
    return contract;
  },

  async deployProxy(
    contractName: string,
    args: any[] = [],
    deployer?: Signer
  ): Promise<Contract> {
    const { upgrades } = require("@openzeppelin/hardhat-upgrades");
    const Factory = await ethers.getContractFactory(contractName, deployer);
    const contract = await upgrades.deployProxy(Factory, args, {
      kind: "uups"
    });
    await contract.deployed();
    return contract;
  }
};

/**
 * Math helpers
 */
export const math = {
  parseEther(value: string): BigNumber {
    return ethers.utils.parseEther(value);
  },

  formatEther(value: BigNumber): string {
    return ethers.utils.formatEther(value);
  },

  parseUnits(value: string, decimals: number): BigNumber {
    return ethers.utils.parseUnits(value, decimals);
  },

  formatUnits(value: BigNumber, decimals: number): string {
    return ethers.utils.formatUnits(value, decimals);
  },

  percentage(value: BigNumber, percent: number): BigNumber {
    return value.mul(percent).div(100);
  },

  // Calculate annual yield
  calculateAPY(
    principal: BigNumber,
    rewards: BigNumber,
    daysStaked: number
  ): BigNumber {
    const annualizedRewards = rewards.mul(365).div(daysStaked);
    return annualizedRewards.mul(10000).div(principal);
  }
};

/**
 * Vesting helpers
 */
export const vesting = {
  async calculateVestingAmount(
    totalAmount: BigNumber,
    startTime: BigNumber,
    cliffDuration: BigNumber,
    vestingDuration: BigNumber,
    currentTime: BigNumber
  ): BigNumber {
    if (currentTime <= startTime.add(cliffDuration)) {
      return BigNumber.from(0);
    }

    if (currentTime >= startTime.add(vestingDuration)) {
      return totalAmount;
    }

    const elapsed = currentTime.sub(startTime);
    const vested = elapsed.mul(totalAmount).div(vestingDuration);
    return vested;
  }
};

/**
 * Identity (SBT) helpers
 */
export const identity = {
  async mintSBT(
    contract: Contract,
    to: string,
    identityType: number,
    metadata: string,
    signer: Signer
  ): Promise<void> {
    await contract.connect(signer).mint(to, identityType, metadata);
  },

  async getIdentityType(
    contract: Contract,
    owner: string
  ): Promise<number> {
    const sbtId = await contract.getIdentityTokenId(owner);
    const identity = await contract.getIdentity(sbtId);
    return identity.identityType;
  }
};
