const { expect } = require('chai');
const { ethers } = require('hardhat');

describe('VIBEcosystemPool', function () {
  let vibeToken, ecosystemPool, nodeReward, devReward, builderReward;
  let owner, assessor, node, developer, builder, emissionController, user;

  beforeEach(async function () {
    [owner, assessor, node, developer, builder, emissionController, user] = await ethers.getSigners();

    // Deploy VIBE token and mint to treasury
    const VIBEToken = await ethers.getContractFactory('VIBEToken');
    vibeToken = await VIBEToken.deploy('VIBE Token', 'VIBE', owner.address);
    await vibeToken.mintTreasury();

    // Deploy VIBEcosystemPool
    const VIBEcosystemPool = await ethers.getContractFactory('VIBEcosystemPool');
    ecosystemPool = await VIBEcosystemPool.deploy(
      await vibeToken.getAddress(),
      emissionController.address
    );

    // Deploy VIBNodeReward (takes 2 args: vibeToken, identityContract)
    const VIBNodeReward = await ethers.getContractFactory('VIBNodeReward');
    nodeReward = await VIBNodeReward.deploy(
      await vibeToken.getAddress(),
      ethers.ZeroAddress
    );

    // Deploy VIBDevReward (takes 1 arg: vibeToken)
    const VIBDevReward = await ethers.getContractFactory('VIBDevReward');
    devReward = await VIBDevReward.deploy(await vibeToken.getAddress());

    // Deploy VIBBuilderReward (takes 1 arg: vibeToken)
    const VIBBuilderReward = await ethers.getContractFactory('VIBBuilderReward');
    builderReward = await VIBBuilderReward.deploy(await vibeToken.getAddress());

    // Set reward contracts in ecosystem pool
    await ecosystemPool.setRewardContracts(
      await nodeReward.getAddress(),
      await devReward.getAddress(),
      await builderReward.getAddress()
    );

    // Set tax exempt for all pool addresses
    await vibeToken.setTaxExempt(await ecosystemPool.getAddress(), true);
    await vibeToken.setTaxExempt(await nodeReward.getAddress(), true);
    await vibeToken.setTaxExempt(await devReward.getAddress(), true);
    await vibeToken.setTaxExempt(await builderReward.getAddress(), true);
    await vibeToken.setTaxExempt(emissionController.address, true);

    // Transfer tokens to emissionController for testing
    await vibeToken.transfer(emissionController.address, ethers.parseEther('1000000'));
  });

  describe('Deployment', function () {
    it('Should set correct token address', async function () {
      expect(await ecosystemPool.vibeToken()).to.equal(await vibeToken.getAddress());
    });

    it('Should set correct emission controller', async function () {
      expect(await ecosystemPool.emissionController()).to.equal(emissionController.address);
    });

    it('Should have correct distribution ratios', async function () {
      expect(await ecosystemPool.NODE_REWARD_RATIO()).to.equal(4000);
      expect(await ecosystemPool.DEV_REWARD_RATIO()).to.equal(3500);
      expect(await ecosystemPool.BUILDER_REWARD_RATIO()).to.equal(2500);
    });
  });

  describe('Receive and Distribute', function () {
    it('Should distribute funds correctly from emission controller', async function () {
      const amount = ethers.parseEther('1000');

      // Approve and call receiveAndDistribute from emissionController
      await vibeToken.connect(emissionController).approve(
        await ecosystemPool.getAddress(),
        amount
      );

      await ecosystemPool.connect(emissionController).receiveAndDistribute(amount);

      // Check balances
      expect(await vibeToken.balanceOf(await nodeReward.getAddress())).to.equal(
        ethers.parseEther('400') // 40%
      );
      expect(await vibeToken.balanceOf(await devReward.getAddress())).to.equal(
        ethers.parseEther('350') // 35%
      );
      expect(await vibeToken.balanceOf(await builderReward.getAddress())).to.equal(
        ethers.parseEther('250') // 25%
      );
    });

    it('Should track distribution statistics', async function () {
      const amount = ethers.parseEther('1000');

      await vibeToken.connect(emissionController).approve(
        await ecosystemPool.getAddress(),
        amount
      );

      await ecosystemPool.connect(emissionController).receiveAndDistribute(amount);

      expect(await ecosystemPool.totalDistributed()).to.equal(amount);
      expect(await ecosystemPool.totalNodeDistributed()).to.equal(ethers.parseEther('400'));
      expect(await ecosystemPool.totalDevDistributed()).to.equal(ethers.parseEther('350'));
      expect(await ecosystemPool.totalBuilderDistributed()).to.equal(ethers.parseEther('250'));
    });

    it('Should fail if not called by emission controller or owner', async function () {
      const amount = ethers.parseEther('1000');

      await vibeToken.connect(user).approve(await ecosystemPool.getAddress(), amount);

      await expect(
        ecosystemPool.connect(user).receiveAndDistribute(amount)
      ).to.be.revertedWith('VIBEcosystemPool: only emission controller');
    });

    it('Should allow owner to call receiveAndDistribute', async function () {
      const amount = ethers.parseEther('1000');

      await vibeToken.approve(await ecosystemPool.getAddress(), amount);

      // This should succeed because owner is allowed
      await ecosystemPool.receiveAndDistribute(amount);

      expect(await ecosystemPool.totalDistributed()).to.equal(amount);
    });
  });

  describe('Estimate Distribution', function () {
    it('Should correctly estimate distribution amounts', async function () {
      const amount = ethers.parseEther('1000');

      const [nodeAmount, devAmount, builderAmount] =
        await ecosystemPool.estimateDistribution(amount);

      expect(nodeAmount).to.equal(ethers.parseEther('400'));
      expect(devAmount).to.equal(ethers.parseEther('350'));
      expect(builderAmount).to.equal(ethers.parseEther('250'));
    });
  });

  describe('Contract Management', function () {
    it('Should allow owner to update reward contracts', async function () {
      await ecosystemPool.setRewardContracts(
        node.address,
        developer.address,
        builder.address
      );

      expect(await ecosystemPool.nodeRewardContract()).to.equal(node.address);
      expect(await ecosystemPool.devRewardContract()).to.equal(developer.address);
      expect(await ecosystemPool.builderRewardContract()).to.equal(builder.address);
    });

    it('Should allow owner to update emission controller', async function () {
      await ecosystemPool.setEmissionController(node.address);
      expect(await ecosystemPool.emissionController()).to.equal(node.address);
    });
  });

  describe('Emergency Withdraw', function () {
    it('Should initiate emergency withdraw with timelock', async function () {
      await ecosystemPool.initiateEmergencyWithdraw();
      expect(await ecosystemPool.emergencyWithdrawEffectiveTime()).to.be.gt(0);
    });

    it('Should fail to execute before timelock expires', async function () {
      await ecosystemPool.initiateEmergencyWithdraw();

      await expect(
        ecosystemPool.executeEmergencyWithdraw()
      ).to.be.revertedWith('VIBEcosystemPool: timelock not expired');
    });
  });
});

describe('VIBNodeReward', function () {
  let vibeToken, nodeReward;
  let owner, assessor, node1, node2;

  beforeEach(async function () {
    [owner, assessor, node1, node2] = await ethers.getSigners();

    const VIBEToken = await ethers.getContractFactory('VIBEToken');
    vibeToken = await VIBEToken.deploy('VIBE Token', 'VIBE', owner.address);
    await vibeToken.mintTreasury();

    const VIBNodeReward = await ethers.getContractFactory('VIBNodeReward');
    nodeReward = await VIBNodeReward.deploy(
      await vibeToken.getAddress(),
      ethers.ZeroAddress
    );

    // Set assessor
    await nodeReward.setAuthorizedAssessor(assessor.address, true);

    // Set tax exempt
    await vibeToken.setTaxExempt(await nodeReward.getAddress(), true);

    // Fund the contract
    await vibeToken.transfer(await nodeReward.getAddress(), ethers.parseEther('10000'));
  });

  describe('Node Registration', function () {
    it('Should register a GPU node', async function () {
      await nodeReward.connect(node1).registerNode(0, 8); // GPU_COMPUTE, 8 GPUs

      const nodeInfo = await nodeReward.getNodeInfo(node1.address);
      expect(nodeInfo.nodeType).to.equal(0); // GPU_COMPUTE
      expect(nodeInfo.capacity).to.equal(8);
      expect(nodeInfo.isActive).to.be.true;
    });

    it('Should register a CPU node', async function () {
      await nodeReward.connect(node1).registerNode(1, 64); // CPU_COMPUTE, 64 cores

      const nodeInfo = await nodeReward.getNodeInfo(node1.address);
      expect(nodeInfo.nodeType).to.equal(1);
      expect(nodeInfo.capacity).to.equal(64);
    });

    it('Should register a Storage node', async function () {
      await nodeReward.connect(node1).registerNode(2, 10000); // STORAGE, 10000 GB

      const nodeInfo = await nodeReward.getNodeInfo(node1.address);
      expect(nodeInfo.nodeType).to.equal(2);
      expect(nodeInfo.capacity).to.equal(10000);
    });

    it('Should fail to register twice', async function () {
      await nodeReward.connect(node1).registerNode(0, 8);
      await expect(
        nodeReward.connect(node1).registerNode(0, 8)
      ).to.be.revertedWith('VIBNodeReward: already registered');
    });
  });

  describe('Service Recording', function () {
    beforeEach(async function () {
      await nodeReward.connect(node1).registerNode(0, 8); // GPU node with 8 GPUs
    });

    it('Should record GPU service and calculate reward', async function () {
      // Use longer duration to get >= 1 VIBE reward for compute credits
      const duration = 36000; // 10 hours
      const capacity = 8; // Using 8 GPUs
      const qualityScore = 15000; // 1.5x
      const productivityFactor = 12000; // 1.2x
      const reliabilityFactor = 11000; // 1.1x

      const tx = await nodeReward.connect(assessor).recordService(
        node1.address,
        0, // GPU_COMPUTE
        duration,
        capacity,
        qualityScore,
        productivityFactor,
        reliabilityFactor,
        ethers.ZeroHash
      );

      const receipt = await tx.wait();
      const event = receipt.logs.find(l => l.fragment && l.fragment.name === 'ServiceRecorded');
      expect(event).to.exist;

      // Verify compute credits were earned (reward should be >= 1 VIBE)
      const credits = await nodeReward.getComputeCredits(node1.address);
      expect(credits).to.be.gt(0);
    });

    it('Should emit ComputeCreditsEarned event', async function () {
      const duration = 36000; // 10 hours
      const capacity = 8;

      const tx = await nodeReward.connect(assessor).recordService(
        node1.address,
        0,
        duration,
        capacity,
        15000,
        12000,
        11000,
        ethers.ZeroHash
      );

      const receipt = await tx.wait();
      const event = receipt.logs.find(l => l.fragment && l.fragment.name === 'ComputeCreditsEarned');
      expect(event).to.exist;
    });

    it('Should fail if not authorized assessor', async function () {
      await expect(
        nodeReward.connect(node1).recordService(
          node1.address, 0, 3600, 4, 10000, 11000, 10500, ethers.ZeroHash
        )
      ).to.be.revertedWith('VIBNodeReward: not authorized assessor');
    });

    it('Should validate quality score range', async function () {
      // Below minimum
      await expect(
        nodeReward.connect(assessor).recordService(
          node1.address, 0, 3600, 4, 4000, 11000, 10500, ethers.ZeroHash
        )
      ).to.be.revertedWith('VIBNodeReward: invalid quality');

      // Above maximum
      await expect(
        nodeReward.connect(assessor).recordService(
          node1.address, 0, 3600, 4, 30000, 11000, 10500, ethers.ZeroHash
        )
      ).to.be.revertedWith('VIBNodeReward: invalid quality');
    });
  });

  describe('Reward Claiming', function () {
    let serviceId;

    beforeEach(async function () {
      await nodeReward.connect(node1).registerNode(0, 8);

      const tx = await nodeReward.connect(assessor).recordService(
        node1.address, 0, 3600, 4, 10000, 11000, 10500, ethers.ZeroHash
      );

      const receipt = await tx.wait();
      const event = receipt.logs.find(l => l.fragment && l.fragment.name === 'ServiceRecorded');
      serviceId = event.args[0];
    });

    it('Should allow node to claim reward', async function () {
      const balanceBefore = await vibeToken.balanceOf(node1.address);

      await nodeReward.connect(node1).claimReward(serviceId);

      const balanceAfter = await vibeToken.balanceOf(node1.address);
      expect(balanceAfter).to.be.gt(balanceBefore);
    });

    it('Should fail to claim twice', async function () {
      await nodeReward.connect(node1).claimReward(serviceId);

      await expect(
        nodeReward.connect(node1).claimReward(serviceId)
      ).to.be.revertedWith('VIBNodeReward: already claimed');
    });

    it('Should fail if not service provider', async function () {
      await expect(
        nodeReward.connect(node2).claimReward(serviceId)
      ).to.be.revertedWith('VIBNodeReward: not service provider');
    });
  });

  describe('Estimate Reward', function () {
    it('Should estimate GPU service reward correctly', async function () {
      // 1 hour, 4 GPUs, quality 1.0x, productivity 1.1x, reliability 1.05x
      const reward = await nodeReward.estimateReward(
        0, // GPU_COMPUTE
        3600, // 1 hour
        4, // 4 GPUs
        10000, // 1.0x quality
        11000, // 1.1x productivity
        10500 // 1.05x reliability
      );

      // Base: 0.1 VIBE * 4 * 1 = 0.4 VIBE
      // With factors: 0.4 * 1.0 * 1.1 * 1.05 = 0.462 VIBE
      expect(reward).to.equal(ethers.parseEther('0.462'));
    });
  });
});

describe('VIBDevReward', function () {
  let vibeToken, devReward;
  let owner, assessor, dev1, dev2;

  beforeEach(async function () {
    [owner, assessor, dev1, dev2] = await ethers.getSigners();

    const VIBEToken = await ethers.getContractFactory('VIBEToken');
    vibeToken = await VIBEToken.deploy('VIBE Token', 'VIBE', owner.address);
    await vibeToken.mintTreasury();

    const VIBDevReward = await ethers.getContractFactory('VIBDevReward');
    devReward = await VIBDevReward.deploy(await vibeToken.getAddress());

    await devReward.setAuthorizedAssessor(assessor.address, true);

    // Set tax exempt
    await vibeToken.setTaxExempt(await devReward.getAddress(), true);

    await vibeToken.transfer(await devReward.getAddress(), ethers.parseEther('10000'));
  });

  describe('Developer Registration', function () {
    it('Should register a developer', async function () {
      await devReward.connect(dev1).registerDeveloper();
      expect(await devReward.isDeveloper(dev1.address)).to.be.true;
      expect(await devReward.developerCount()).to.equal(1);
    });

    it('Should fail to register twice', async function () {
      await devReward.connect(dev1).registerDeveloper();
      await expect(
        devReward.connect(dev1).registerDeveloper()
      ).to.be.revertedWith('VIBDevReward: already registered');
    });
  });

  describe('Contribution Recording', function () {
    beforeEach(async function () {
      await devReward.connect(dev1).registerDeveloper();
    });

    it('Should record code contribution', async function () {
      const tx = await devReward.connect(assessor).recordContribution(
        dev1.address,
        0, // CODE_CONTRIBUTION
        ethers.parseEther('50'), // base reward
        15000, // quality factor 1.5x
        12000, // impact factor 1.2x
        ethers.ZeroHash,
        'PR #123'
      );

      const receipt = await tx.wait();
      const event = receipt.logs.find(l => l.fragment && l.fragment.name === 'ContributionRecorded');
      expect(event).to.exist;

      // Verify developer points increased
      const stats = await devReward.getDeveloperStats(dev1.address);
      expect(stats.points).to.be.gt(0);
    });

    it('Should validate reward range for code contribution', async function () {
      // Below minimum (5 VIBE)
      await expect(
        devReward.connect(assessor).recordContribution(
          dev1.address, 0, ethers.parseEther('1'), 10000, 10000, ethers.ZeroHash, ''
        )
      ).to.be.revertedWith('VIBDevReward: reward out of range');

      // Above maximum (500 VIBE)
      await expect(
        devReward.connect(assessor).recordContribution(
          dev1.address, 0, ethers.parseEther('600'), 10000, 10000, ethers.ZeroHash, ''
        )
      ).to.be.revertedWith('VIBDevReward: reward out of range');
    });
  });

  describe('Estimate Reward', function () {
    it('Should estimate contribution reward correctly', async function () {
      const reward = await devReward.estimateReward(
        0, // CODE_CONTRIBUTION
        ethers.parseEther('50'), // base
        15000, // quality 1.5x
        12000 // impact 1.2x
      );

      // 50 * 1.5 * 1.2 = 90 VIBE
      expect(reward).to.equal(ethers.parseEther('90'));
    });
  });
});

describe('VIBBuilderReward', function () {
  let vibeToken, builderReward;
  let owner, assessor, builder1, builder2;

  beforeEach(async function () {
    [owner, assessor, builder1, builder2] = await ethers.getSigners();

    const VIBEToken = await ethers.getContractFactory('VIBEToken');
    vibeToken = await VIBEToken.deploy('VIBE Token', 'VIBE', owner.address);
    await vibeToken.mintTreasury();

    const VIBBuilderReward = await ethers.getContractFactory('VIBBuilderReward');
    builderReward = await VIBBuilderReward.deploy(await vibeToken.getAddress());

    await builderReward.setAuthorizedAssessor(assessor.address, true);

    // Set tax exempt
    await vibeToken.setTaxExempt(await builderReward.getAddress(), true);

    await vibeToken.transfer(await builderReward.getAddress(), ethers.parseEther('10000'));
  });

  describe('Builder Registration', function () {
    it('Should register a builder', async function () {
      await builderReward.connect(builder1).registerBuilder();
      expect(await builderReward.isBuilder(builder1.address)).to.be.true;
      expect(await builderReward.builderCountUnique()).to.equal(1);
    });
  });

  describe('Activity Recording', function () {
    beforeEach(async function () {
      await builderReward.connect(builder1).registerBuilder();
    });

    it('Should record community contribution', async function () {
      const tx = await builderReward.connect(assessor).recordBuilderActivity(
        builder1.address,
        0, // COMMUNITY_CONTRIBUTION
        ethers.parseEther('10'), // base reward
        15000, // quality factor 1.5x
        ethers.ZeroHash,
        'Documentation update'
      );

      const receipt = await tx.wait();
      const event = receipt.logs.find(l => l.fragment && l.fragment.name === 'BuilderRecorded');
      expect(event).to.exist;

      const stats = await builderReward.getBuilderStats(builder1.address);
      expect(stats.points).to.be.gt(0);
    });

    it('Should record task completion', async function () {
      await builderReward.connect(assessor).recordBuilderActivity(
        builder1.address,
        1, // TASK_COMPLETION
        ethers.parseEther('50'),
        12000,
        ethers.ZeroHash,
        'Bug fix #456'
      );

      const stats = await builderReward.getBuilderStats(builder1.address);
      expect(stats.points).to.be.gt(0);
    });

    it('Should validate reward range for community contribution', async function () {
      // Below minimum (1 VIBE)
      await expect(
        builderReward.connect(assessor).recordBuilderActivity(
          builder1.address, 0, ethers.parseEther('0.5'), 10000, ethers.ZeroHash, ''
        )
      ).to.be.revertedWith('VIBBuilderReward: reward out of range');

      // Above maximum (50 VIBE)
      await expect(
        builderReward.connect(assessor).recordBuilderActivity(
          builder1.address, 0, ethers.parseEther('60'), 10000, ethers.ZeroHash, ''
        )
      ).to.be.revertedWith('VIBBuilderReward: reward out of range');
    });
  });

  describe('Estimate Reward', function () {
    it('Should estimate activity reward correctly', async function () {
      const reward = await builderReward.estimateReward(
        0, // COMMUNITY_CONTRIBUTION
        ethers.parseEther('10'),
        15000 // 1.5x quality
      );

      // 10 * 1.5 = 15 VIBE
      expect(reward).to.equal(ethers.parseEther('15'));
    });

    it('Should cap reward at maximum', async function () {
      const reward = await builderReward.estimateReward(
        0, // COMMUNITY_CONTRIBUTION
        ethers.parseEther('40'),
        20000 // 2.0x quality -> would be 80, capped at 50
      );

      expect(reward).to.equal(ethers.parseEther('50')); // COMMUNITY_MAX
    });
  });
});
