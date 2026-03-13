"""
完整业务API测试套件 - 覆盖所有20个API模块

测试分类:
- unit: 单元测试 (单个API功能)
- integration: 集成测试 (跨模块业务逻辑)
- e2e: 端到端测试 (完整业务流程)

业务闭环覆盖:
1. Agent生命周期闭环
2. 认证授权闭环
3. 钱包管理闭环
4. 质押Staking闭环
5. 需求->匹配->协作闭环
6. 工作流闭环
7. 治理闭环
8. 交易闭环
9. 环境管理闭环
10. 学习洞察闭环
11. 网络探索闭环

运行命令:
    pytest tests/test_business_api_full_coverage.py -v                    # 全部测试
    pytest tests/test_business_api_full_coverage.py -m unit             # 仅单元测试
    pytest tests/test_business_api_full_coverage.py -m integration      # 仅集成测试
    pytest tests/test_business_api_full_coverage.py -m e2e              # 仅E2E测试
    pytest tests/test_business_api_full_coverage.py -m agent            # 仅Agent模块
    pytest tests/test_business_api_full_coverage.py -m "ci and not slow"  # CI/CD测试
"""

import pytest
import time
import uuid
from typing import Any, Dict

# ============================================================================
# 标记定义
# ============================================================================

# 测试类型
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
    pytest.mark.e2e,
    pytest.mark.ci,
]


# ============================================================================
# ============================================================================
# 第一部分: Agent生命周期测试 (agents.py, heartbeat.py)
# ============================================================================
# ============================================================================

class TestAgentLifecycle:
    """Agent生命周期完整测试"""

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_create(self, api_client, sample_agent_data):
        """测试1: 创建Agent"""
        response = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(response, 201)

        data = response.json()
        assert_field_in_response(data, "agent_id", sample_agent_data["agent_id"])
        assert_field_in_response(data, "name", sample_agent_data["name"])

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_get(self, api_client, sample_agent_data):
        """测试2: 获取Agent详情"""
        # 先创建
        create_response = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(create_response, 201)

        # 再获取
        response = await api_client.get(f"/agents/{sample_agent_data['agent_id']}")
        assert_response_success(response)

        data = response.json()
        assert data["agent_id"] == sample_agent_data["agent_id"]

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_list(self, api_client, sample_agent_data):
        """测试3: 列出所有Agent"""
        # 先创建
        await api_client.post("/agents", json=sample_agent_data)

        # 列表查询
        response = await api_client.get("/agents")
        assert_response_success(response)

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_update(self, api_client, sample_agent_data):
        """测试4: 更新Agent"""
        # 先创建
        await api_client.post("/agents", json=sample_agent_data)

        # 更新
        update_data = {"name": "UpdatedAgent", "description": "Updated description"}
        response = await api_client.put(
            f"/agents/{sample_agent_data['agent_id']}",
            json=update_data
        )
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_delete(self, api_client, sample_agent_data):
        """测试5: 删除Agent"""
        # 先创建
        await api_client.post("/agents", json=sample_agent_data)

        # 删除
        response = await api_client.delete(f"/agents/{sample_agent_data['agent_id']}")
        assert_response_success(response, 204)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_heartbeat(self, api_client, sample_agent_data):
        """测试6: Agent心跳"""
        # 先创建
        await api_client.post("/agents", json=sample_agent_data)

        # 发送心跳
        heartbeat_data = {"status": "online"}
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/heartbeat",
            json=heartbeat_data
        )
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_status_filter(self, api_client, sample_agent_data):
        """测试7: 按状态过滤Agent"""
        # 创建在线Agent
        data = sample_agent_data.copy()
        data["status"] = "online"
        await api_client.post("/agents", json=data)

        # 按状态过滤
        response = await api_client.get("/agents?status=online")
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_type_filter(self, api_client, sample_agent_data):
        """测试8: 按类型过滤Agent"""
        response = await api_client.get("/agents?agent_type=ai_agent")
        assert_response_success(response)


@pytest.mark.agent
@pytest.mark.integration
class TestAgentLifecycleIntegration:
    """Agent生命周期集成测试 - 完整闭环"""

    async def test_full_agent_lifecycle(self, api_client, sample_agent_data):
        """测试: 完整Agent生命周期"""
        agent_id = sample_agent_data["agent_id"]

        # 1. 注册
        create_resp = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(create_resp, 201)

        # 2. 查询
        get_resp = await api_client.get(f"/agents/{agent_id}")
        assert_response_success(get_resp)

        # 3. 发送心跳
        heartbeat_resp = await api_client.post(
            f"/agents/{agent_id}/heartbeat",
            json={"status": "online"}
        )
        assert_response_success(heartbeat_resp)

        # 4. 再次查询验证心跳
        get_resp2 = await api_client.get(f"/agents/{agent_id}")
        data = get_resp2.json()
        assert data["status"] == "online"

        # 5. 更新
        update_resp = await api_client.put(
            f"/agents/{agent_id}",
            json={"description": "Updated via lifecycle test"}
        )
        assert_response_success(update_resp)

        # 6. 删除
        delete_resp = await api_client.delete(f"/agents/{agent_id}")
        assert_response_success(delete_resp, 204)


# ============================================================================
# ============================================================================
# 第二部分: 认证授权测试 (auth.py, agent_auth.py, unified_auth.py)
# ============================================================================
# ============================================================================

class TestAuthentication:
    """认证授权测试"""

    @pytest.mark.auth
    @pytest.mark.unit
    async def test_wallet_auth_init(self, api_client, test_wallet):
        """测试9: 钱包认证初始化"""
        response = await api_client.post("/auth/wallet/init", json={
            "wallet_address": test_wallet
        })
        assert_response_success(response)

    @pytest.mark.auth
    @pytest.mark.unit
    async def test_wallet_auth_verify(self, api_client, test_wallet):
        """测试10: 钱包认证验证"""
        # 初始化
        init_resp = await api_client.post("/auth/wallet/init", json={
            "wallet_address": test_wallet
        })
        assert_response_success(init_resp)

        # 验证 (简化版 - 实际需要签名)
        verify_resp = await api_client.post("/auth/wallet/verify", json={
            "wallet_address": test_wallet,
            "signature": "0x" + "00" * 65
        })
        assert_response_success(verify_resp)

    @pytest.mark.auth
    @pytest.mark.unit
    async def test_agent_api_key_create(self, api_client, sample_agent_data):
        """测试11: 创建Agent API密钥"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建API Key
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/api-keys",
            json={"name": "TestKey", "permissions": ["read", "write"]}
        )
        assert_response_success(response, 201)


@pytest.mark.auth
@pytest.mark.integration
class TestAuthenticationIntegration:
    """认证授权集成测试"""

    async def test_full_auth_flow(self, api_client, test_wallet):
        """测试: 完整认证流程"""
        # 1. 初始化
        init_resp = await api_client.post("/auth/wallet/init", json={
            "wallet_address": test_wallet
        })
        assert_response_success(init_resp)

        # 2. 验证
        verify_resp = await api_client.post("/auth/wallet/verify", json={
            "wallet_address": test_wallet,
            "signature": "0x" + "00" * 65
        })
        assert_response_success(verify_resp)


# ============================================================================
# ============================================================================
# 第三部分: 钱包管理测试 (wallet.py)
# ============================================================================
# ============================================================================

class TestWallet:
    """钱包管理测试"""

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_create(self, api_client, sample_agent_data):
        """测试12: 创建钱包"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建钱包
        response = await api_client.post("/wallet", json={
            "agent_id": sample_agent_data["agent_id"]
        })
        assert_response_success(response, 201)

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_get(self, api_client, sample_agent_data):
        """测试13: 获取钱包信息"""
        # 先创建Agent和钱包
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/wallet", json={
            "agent_id": sample_agent_data["agent_id"]
        })

        # 获取钱包
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}")
        assert_response_success(response)

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_balance(self, api_client, sample_agent_data):
        """测试14: 查询余额"""
        # 先创建Agent和钱包
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/wallet", json={
            "agent_id": sample_agent_data["agent_id"]
        })

        # 查询余额
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}/balance")
        assert_response_success(response)


@pytest.mark.wallet
@pytest.mark.integration
class TestWalletIntegration:
    """钱包集成测试"""

    async def test_full_wallet_flow(self, api_client, sample_agent_data):
        """测试: 完整钱包流程"""
        agent_id = sample_agent_data["agent_id"]

        # 1. 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 2. 创建钱包
        wallet_resp = await api_client.post("/wallet", json={"agent_id": agent_id})
        assert_response_success(wallet_resp, 201)

        # 3. 查询钱包
        get_resp = await api_client.get(f"/wallet/{agent_id}")
        assert_response_success(get_resp)


# ============================================================================
# ============================================================================
# 第四部分: 质押Staking测试 (staking.py)
# ============================================================================
# ============================================================================

class TestStaking:
    """质押测试"""

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_create(self, api_client, sample_agent_data):
        """测试15: 创建质押"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建质押
        response = await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 1000.0
        })
        assert_response_success(response, 201)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_get(self, api_client, sample_agent_data):
        """测试16: 获取质押信息"""
        # 先创建Agent和质押
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 1000.0
        })

        # 获取质押
        response = await api_client.get(f"/staking/{sample_agent_data['agent_id']}")
        assert_response_success(response)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_unlock(self, api_client, sample_agent_data):
        """测试17: 解锁质押"""
        # 先创建质押
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 1000.0
        })

        # 解锁
        response = await api_client.post(
            f"/staking/{sample_agent_data['agent_id']}/unlock",
            json={"amount": 500.0}
        )
        assert_response_success(response)


@pytest.mark.staking
@pytest.mark.integration
class TestStakingIntegration:
    """质押集成测试"""

    async def test_full_staking_flow(self, api_client, sample_agent_data):
        """测试: 完整质押流程"""
        agent_id = sample_agent_data["agent_id"]

        # 1. 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 2. 质押
        stake_resp = await api_client.post("/staking/stake", json={
            "agent_id": agent_id,
            "amount": 1000.0
        })
        assert_response_success(stake_resp, 201)

        # 3. 查询质押状态
        get_resp = await api_client.get(f"/staking/{agent_id}")
        assert_response_success(get_resp)


# ============================================================================
# ============================================================================
# 第五部分: 需求-匹配-协作闭环 (demands.py, matching.py, collaborations.py)
# ============================================================================
# ============================================================================

class TestDemandMatchingCollaboration:
    """需求-匹配-协作完整测试"""

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_demand_create(self, api_client, sample_demand_data):
        """测试18: 创建需求"""
        response = await api_client.post("/demands", json=sample_demand_data)
        assert_response_success(response, 201)

        data = response.json()
        assert_field_in_response(data, "title", sample_demand_data["title"])

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_demand_list(self, api_client, sample_demand_data):
        """测试19: 列出需求"""
        await api_client.post("/demands", json=sample_demand_data)

        response = await api_client.get("/demands")
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_demand_get(self, api_client, sample_demand_data):
        """测试20: 获取需求详情"""
        create_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = create_resp.json()

        response = await api_client.get(f"/demands/{demand['id']}")
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_matching_execute(self, api_client, sample_demand_data, sample_service_data):
        """测试21: 执行匹配"""
        # 创建需求和服务
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        service_resp = await api_client.post("/services", json=sample_service_data)
        service = service_resp.json()

        # 执行匹配
        response = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": sample_service_data["agent_id"]
        })
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_matching_results(self, api_client, sample_demand_data):
        """测试22: 获取匹配结果"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 获取匹配结果
        response = await api_client.get(f"/matching/results/{demand['id']}")
        assert_response_success(response)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_create(self, api_client):
        """测试23: 创建协作"""
        response = await api_client.post("/collaborations", json={
            "goal": "Test collaboration goal",
            "participants": ["agent1", "agent2"]
        })
        assert_response_success(response, 201)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_update_status(self, api_client):
        """测试24: 更新协作状态"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test collaboration",
            "participants": ["agent1"]
        })
        collab = collab_resp.json()

        # 更新状态
        response = await api_client.put(
            f"/collaborations/{collab['session_id']}/status",
            json={"status": "active"}
        )
        assert_response_success(response)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_complete(self, api_client):
        """测试25: 完成协作"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test collaboration",
            "participants": ["agent1"]
        })
        collab = collab_resp.json()

        # 完成
        response = await api_client.put(
            f"/collaborations/{collab['session_id']}/complete",
            json={"result": {"success": True}}
        )
        assert_response_success(response)


@pytest.mark.matching
@pytest.mark.collaboration
@pytest.mark.integration
class TestDemandMatchingCollabIntegration:
    """需求-匹配-协作集成测试"""

    async def test_full_demand_matching_collaboration_flow(self, api_client, sample_agent_data, sample_demand_data, sample_service_data):
        """测试: 完整需求-匹配-协作流程"""
        agent_id = sample_agent_data["agent_id"]

        # 1. 创建Agent
        agent_resp = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(agent_resp, 201)

        # 2. 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        assert_response_success(demand_resp, 201)
        demand = demand_resp.json()

        # 3. 创建服务
        service_resp = await api_client.post("/services", json=sample_service_data)
        assert_response_success(service_resp, 201)

        # 4. 执行匹配
        match_resp = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": agent_id
        })
        assert_response_success(match_resp)

        # 5. 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Complete data analysis",
            "participants": [agent_id]
        })
        assert_response_success(collab_resp, 201)
        collab = collab_resp.json()

        # 6. 更新协作状态为进行中
        status_resp = await api_client.put(
            f"/collaborations/{collab['session_id']}/status",
            json={"status": "active"}
        )
        assert_response_success(status_resp)

        # 7. 完成协作
        complete_resp = await api_client.put(
            f"/collaborations/{collab['session_id']}/complete",
            json={"result": {"success": True, "output": "Analysis complete"}}
        )
        assert_response_success(complete_resp)


# ============================================================================
# ============================================================================
# 第六部分: 工作流测试 (workflows.py)
# ============================================================================
# ============================================================================

class TestWorkflow:
    """工作流测试"""

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_create(self, api_client, sample_workflow_data):
        """测试26: 创建工作流"""
        response = await api_client.post("/workflows", json=sample_workflow_data)
        assert_response_success(response, 201)

        data = response.json()
        assert_field_in_response(data, "name", sample_workflow_data["name"])

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_get(self, api_client, sample_workflow_data):
        """测试27: 获取工作流"""
        create_resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = create_resp.json()

        response = await api_client.get(f"/workflows/{workflow['id']}")
        assert_response_success(response)

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_list(self, api_client, sample_workflow_data):
        """测试28: 列出工作流"""
        await api_client.post("/workflows", json=sample_workflow_data)

        response = await api_client.get("/workflows")
        assert_response_success(response)

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_execute(self, api_client, sample_workflow_data):
        """测试29: 执行工作流"""
        create_resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = create_resp.json()

        response = await api_client.post(f"/workflows/{workflow['id']}/execute")
        assert_response_success(response)

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_update_status(self, api_client, sample_workflow_data):
        """测试30: 更新工作流状态"""
        create_resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = create_resp.json()

        response = await api_client.put(
            f"/workflows/{workflow['id']}/status",
            json={"status": "running"}
        )
        assert_response_success(response)


@pytest.mark.workflow
@pytest.mark.integration
class TestWorkflowIntegration:
    """工作流集成测试"""

    async def test_full_workflow_flow(self, api_client, sample_workflow_data):
        """测试: 完整工作流流程"""
        # 1. 创建
        create_resp = await api_client.post("/workflows", json=sample_workflow_data)
        assert_response_success(create_resp, 201)
        workflow = create_resp.json()

        # 2. 执行
        exec_resp = await api_client.post(f"/workflows/{workflow['id']}/execute")
        assert_response_success(exec_resp)

        # 3. 更新状态
        status_resp = await api_client.put(
            f"/workflows/{workflow['id']}/status",
            json={"status": "running"}
        )
        assert_response_success(status_resp)

        # 4. 完成
        complete_resp = await api_client.put(
            f"/workflows/{workflow['id']}/complete",
            json={"result": {"output": "Workflow complete"}}
        )
        assert_response_success(complete_resp)


# ============================================================================
# ============================================================================
# 第七部分: 治理测试 (governance.py)
# ============================================================================
# ============================================================================

class TestGovernance:
    """治理测试"""

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_create(self, api_client, sample_proposal_data):
        """测试31: 创建提案"""
        response = await api_client.post("/governance/proposals", json=sample_proposal_data)
        assert_response_success(response, 201)

        data = response.json()
        assert_field_in_response(data, "title", sample_proposal_data["title"])

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_list(self, api_client, sample_proposal_data):
        """测试32: 列出提案"""
        await api_client.post("/governance/proposals", json=sample_proposal_data)

        response = await api_client.get("/governance/proposals")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_vote(self, api_client, sample_proposal_data):
        """测试33: 投票"""
        # 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 投票
        response = await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "test_voter", "vote": 1, "weight": 1.0}
        )
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_execute(self, api_client, sample_proposal_data):
        """测试34: 执行提案"""
        # 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 执行
        response = await api_client.post(f"/governance/proposals/{proposal['id']}/execute")
        assert_response_success(response)


@pytest.mark.governance
@pytest.mark.integration
class TestGovernanceIntegration:
    """治理集成测试"""

    async def test_full_governance_flow(self, api_client, sample_proposal_data):
        """测试: 完整治理流程"""
        # 1. 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        assert_response_success(proposal_resp, 201)
        proposal = proposal_resp.json()

        # 2. 投票
        vote_resp = await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 1.0}
        )
        assert_response_success(vote_resp)

        # 3. 投票
        vote_resp2 = await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter2", "vote": 1, "weight": 1.0}
        )
        assert_response_success(vote_resp2)

        # 4. 执行提案
        exec_resp = await api_client.post(f"/governance/proposals/{proposal['id']}/execute")
        assert_response_success(exec_resp)


# ============================================================================
# ============================================================================
# 第八部分: 交易测试 (transactions.py)
# ============================================================================
# ============================================================================

class TestTransaction:
    """交易测试"""

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_create(self, api_client, sample_agent_data):
        """测试35: 创建交易"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        response = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": f"seller_{sample_agent_data['agent_id']}",
            "amount": 100.0,
            "title": "Test transaction"
        })
        assert_response_success(response, 201)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_list(self, api_client, sample_agent_data):
        """测试36: 列出交易"""
        # 创建交易
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller",
            "amount": 100.0
        })

        response = await api_client.get("/transactions")
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_escrow(self, api_client, sample_agent_data):
        """测试37: 托管交易"""
        # 创建交易
        await api_client.post("/agents", json=sample_agent_data)
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 托管
        response = await api_client.post(f"/transactions/{tx['id']}/escrow")
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_release(self, api_client, sample_agent_data):
        """测试38: 释放交易"""
        # 创建并托管交易
        await api_client.post("/agents", json=sample_agent_data)
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller",
            "amount": 100.0
        })
        tx = tx_resp.json()
        await api_client.post(f"/transactions/{tx['id']}/escrow")

        # 释放
        response = await api_client.post(f"/transactions/{tx['id']}/release")
        assert_response_success(response)


@pytest.mark.transaction
@pytest.mark.integration
class TestTransactionIntegration:
    """交易集成测试"""

    async def test_full_transaction_flow(self, api_client, sample_agent_data):
        """测试: 完整交易流程"""
        buyer_id = sample_agent_data["agent_id"]
        seller_id = f"seller_{uuid.uuid4().hex[:8]}"

        # 1. 创建Agent (买方)
        await api_client.post("/agents", json=sample_agent_data)

        # 2. 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "amount": 100.0,
            "title": "Test payment"
        })
        assert_response_success(tx_resp, 201)
        tx = tx_resp.json()

        # 3. 托管
        escrow_resp = await api_client.post(f"/transactions/{tx['id']}/escrow")
        assert_response_success(escrow_resp)

        # 4. 释放
        release_resp = await api_client.post(f"/transactions/{tx['id']}/release")
        assert_response_success(release_resp)


# ============================================================================
# ============================================================================
# 第九部分: 环境管理测试 (environments.py)
# ============================================================================
# ============================================================================

class TestEnvironment:
    """环境管理测试"""

    @pytest.mark.environment
    @pytest.mark.unit
    async def test_environment_create(self, api_client, sample_agent_data):
        """测试39: 创建环境"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建环境
        response = await api_client.post("/environments", json={
            "agent_id": sample_agent_data["agent_id"],
            "name": "TestEnvironment",
            "type": "development"
        })
        assert_response_success(response, 201)

    @pytest.mark.environment
    @pytest.mark.unit
    async def test_environment_list(self, api_client):
        """测试40: 列出环境"""
        response = await api_client.get("/environments")
        assert_response_success(response)

    @pytest.mark.environment
    @pytest.mark.unit
    async def test_environment_get(self, api_client, sample_agent_data):
        """测试41: 获取环境"""
        # 创建环境
        await api_client.post("/agents", json=sample_agent_data)
        env_resp = await api_client.post("/environments", json={
            "agent_id": sample_agent_data["agent_id"],
            "name": "TestEnv"
        })
        env = env_resp.json()

        response = await api_client.get(f"/environments/{env['id']}")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十部分: 学习洞察测试 (learning.py)
# ============================================================================
# ============================================================================

class TestLearning:
    """学习洞察测试"""

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_insight_create(self, api_client, sample_agent_data):
        """测试42: 创建学习洞察"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建洞察
        response = await api_client.post("/learning/insights", json={
            "agent_id": sample_agent_data["agent_id"],
            "insights": ["insight1", "insight2"],
            "strategy": "optimize"
        })
        assert_response_success(response, 201)

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_insight_list(self, api_client, sample_agent_data):
        """测试43: 列出学习洞察"""
        # 创建洞察
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/learning/insights", json={
            "agent_id": sample_agent_data["agent_id"],
            "insights": ["test"]
        })

        response = await api_client.get(f"/learning/insights/{sample_agent_data['agent_id']}")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十一部分: 网络探索测试 (network.py)
# ============================================================================
# ============================================================================

class TestNetwork:
    """网络探索测试"""

    @pytest.mark.network
    @pytest.mark.unit
    async def test_network_explore(self, api_client, sample_agent_data):
        """测试44: 探索网络"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post("/network/explore", json={
            "agent_id": sample_agent_data["agent_id"],
            "depth": 2
        })
        assert_response_success(response)

    @pytest.mark.network
    @pytest.mark.unit
    async def test_network_trust_score(self, api_client, sample_agent_data):
        """测试45: 查询信任分数"""
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.get(
            f"/network/trust/{sample_agent_data['agent_id']}"
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十二部分: 服务管理测试 (services.py)
# ============================================================================
# ============================================================================

class TestService:
    """服务管理测试"""

    @pytest.mark.unit
    async def test_service_create(self, api_client, sample_service_data):
        """测试46: 创建服务"""
        response = await api_client.post("/services", json=sample_service_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_service_list(self, api_client, sample_service_data):
        """测试47: 列出服务"""
        await api_client.post("/services", json=sample_service_data)

        response = await api_client.get("/services")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_service_get(self, api_client, sample_service_data):
        """测试48: 获取服务"""
        create_resp = await api_client.post("/services", json=sample_service_data)
        service = create_resp.json()

        response = await api_client.get(f"/services/{service['id']}")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_service_update(self, api_client, sample_service_data):
        """测试49: 更新服务"""
        create_resp = await api_client.post("/services", json=sample_service_data)
        service = create_resp.json()

        response = await api_client.put(
            f"/services/{service['id']}",
            json={"price": 300.0}
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十三部分: 系统/健康检查测试 (system.py)
# ============================================================================
# ============================================================================

class TestSystem:
    """系统测试"""

    @pytest.mark.unit
    async def test_health_check(self, api_client):
        """测试50: 健康检查"""
        response = await api_client.get("/system/health")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_system_status(self, api_client):
        """测试51: 系统状态"""
        response = await api_client.get("/system/status")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_system_metrics(self, api_client):
        """测试52: 系统指标"""
        response = await api_client.get("/system/metrics")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十四部分: 基因胶囊测试 (gene_capsule.py)
# ============================================================================
# ============================================================================

class TestGeneCapsule:
    """基因胶囊测试"""

    @pytest.mark.unit
    async def test_gene_capsule_create(self, api_client, sample_agent_data):
        """测试53: 创建基因胶囊"""
        # 先创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post("/gene-capsules", json={
            "agent_id": sample_agent_data["agent_id"],
            "name": "TestCapsule",
            "description": "Test capsule"
        })
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_gene_capsule_list(self, api_client):
        """测试54: 列出基因胶囊"""
        response = await api_client.get("/gene-capsules")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十五部分: Reputation声誉测试 (reputation.py)
# ============================================================================
# ============================================================================

class TestReputation:
    """声誉测试"""

    @pytest.mark.unit
    async def test_reputation_get(self, api_client, sample_agent_data):
        """测试55: 获取声誉"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.get(f"/reputation/{sample_agent_data['agent_id']}")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_reputation_update(self, api_client, sample_agent_data):
        """测试56: 更新声誉"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.put(
            f"/reputation/{sample_agent_data['agent_id']}",
            json={"reputation": 0.9}
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十六部分: Pre-Match谈判测试 (pre_match_negotiation.py)
# ============================================================================
# ============================================================================

class TestPreMatchNegotiation:
    """匹配前谈判测试"""

    @pytest.mark.unit
    async def test_negotiation_start(self, api_client):
        """测试57: 开始谈判"""
        response = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2",
            "context": {"demand_id": "demand1"}
        })
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_negotiation_respond(self, api_client):
        """测试58: 响应谈判"""
        # 开始谈判
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })
        negotiation = start_resp.json()

        # 响应
        response = await api_client.post(
            f"/pre-match/negotiations/{negotiation['session_id']}/respond",
            json={"accept": True}
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十七部分: Meta Agent匹配测试 (meta_agent_matching.py)
# ============================================================================
# ============================================================================

class TestMetaAgentMatching:
    """Meta Agent匹配测试"""

    @pytest.mark.unit
    async def test_meta_match(self, api_client, sample_demand_data):
        """测试59: Meta匹配"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        response = await api_client.post("/meta-agent/match", json={
            "demand_id": demand["id"]
        })
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十八部分: Predictions预测测试 (predictions.py)
# ============================================================================
# ============================================================================

class TestPredictions:
    """预测测试"""

    @pytest.mark.unit
    async def test_prediction_create(self, api_client, sample_agent_data):
        """测试60: 创建预测"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post("/predictions", json={
            "agent_id": sample_agent_data["agent_id"],
            "prediction_type": "behavior",
            "parameters": {"look_ahead": 10}
        })
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_prediction_list(self, api_client):
        """测试61: 列出预测"""
        response = await api_client.get("/predictions")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十九部分: Blockchain区块链测试 (blockchain.py)
# ============================================================================
# ============================================================================

class TestBlockchain:
    """区块链测试"""

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_get_balance(self, api_client):
        """测试62: 查询链上余额"""
        response = await api_client.get("/blockchain/balance/test_address")
        assert_response_success(response)

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_transaction_status(self, api_client):
        """测试63: 查询交易状态"""
        response = await api_client.get("/blockchain/tx/0x1234")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第二十部分: Registration注册测试 (registration.py)
# ============================================================================
# ============================================================================

class TestRegistration:
    """注册测试"""

    @pytest.mark.unit
    async def test_register_agent(self, api_client, sample_agent_data):
        """测试64: 注册Agent"""
        response = await api_client.post("/registration/register", json=sample_agent_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_register_status(self, api_client, sample_agent_data):
        """测试65: 查询注册状态"""
        # 先注册
        await api_client.post("/registration/register", json=sample_agent_data)

        response = await api_client.get(
            f"/registration/status/{sample_agent_data['agent_id']}"
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# E2E: 完整业务闭环端到端测试
# ============================================================================
# ============================================================================

@pytest.mark.e2e
class TestFullBusinessFlowE2E:
    """完整业务闭环E2E测试"""

    async def test_complete_agent_business_flow(self, api_client, sample_agent_data):
        """E2E测试: 完整Agent业务闭环"""
        agent_id = sample_agent_data["agent_id"]

        # 1. 注册Agent
        agent_resp = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(agent_resp, 201)

        # 2. 创建钱包
        wallet_resp = await api_client.post("/wallet", json={"agent_id": agent_id})
        assert_response_success(wallet_resp, 201)

        # 3. 质押
        stake_resp = await api_client.post("/staking/stake", json={
            "agent_id": agent_id,
            "amount": 1000.0
        })
        assert_response_success(stake_resp, 201)

        # 4. 发送心跳
        heartbeat_resp = await api_client.post(
            f"/agents/{agent_id}/heartbeat",
            json={"status": "online"}
        )
        assert_response_success(heartbeat_resp)

        # 5. 创建服务
        service_resp = await api_client.post("/services", json={
            "agent_id": agent_id,
            "service_name": "TestService",
            "category": "test"
        })
        assert_response_success(service_resp, 201)

        # 6. 创建环境
        env_resp = await api_client.post("/environments", json={
            "agent_id": agent_id,
            "name": "TestEnv"
        })
        assert_response_success(env_resp, 201)

        # 7. 创建学习洞察
        insight_resp = await api_client.post("/learning/insights", json={
            "agent_id": agent_id,
            "insights": ["insight1"]
        })
        assert_response_success(insight_resp, 201)

    async def test_complete_marketplace_flow(self, api_client, sample_agent_data, sample_demand_data):
        """E2E测试: 完整市场交易闭环"""
        # 1. 创建买方Agent
        buyer_resp = await api_client.post("/agents", json=sample_agent_data)
        buyer = buyer_resp.json()

        # 2. 创建卖方Agent
        seller_data = sample_agent_data.copy()
        seller_data["agent_id"] = f"seller_{uuid.uuid4().hex[:8]}"
        seller_resp = await api_client.post("/agents", json=seller_data)
        assert_response_success(seller_resp, 201)

        # 3. 买方发布需求
        demand_data = sample_demand_data.copy()
        demand_data["agent_id"] = buyer["agent_id"]
        demand_resp = await api_client.post("/demands", json=demand_data)
        assert_response_success(demand_resp, 201)
        demand = demand_resp.json()

        # 4. 卖方发布服务
        service_data = {
            "agent_id": seller_data["agent_id"],
            "service_name": "DataAnalysis",
            "category": "data_analysis",
            "price": 200.0
        }
        service_resp = await api_client.post("/services", json=service_data)
        assert_response_success(service_resp, 201)

        # 5. 执行匹配
        match_resp = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": seller_data["agent_id"]
        })
        assert_response_success(match_resp)

        # 6. 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Complete analysis",
            "participants": [buyer["agent_id"], seller_data["agent_id"]]
        })
        assert_response_success(collab_resp, 201)

        # 7. 完成协作
        collab = collab_resp.json()
        complete_resp = await api_client.put(
            f"/collaborations/{collab['session_id']}/complete",
            json={"result": {"success": True}}
        )
        assert_response_success(complete_resp)

        # 8. 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer["agent_id"],
            "seller_id": seller_data["agent_id"],
            "amount": 200.0,
            "demand_id": demand["id"]
        })
        assert_response_success(tx_resp, 201)

    async def test_complete_governance_flow(self, api_client):
        """E2E测试: 完整治理闭环"""
        # 1. 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json={
            "title": "Test Proposal",
            "description": "Test",
            "proposer_id": "proposer1",
            "quorum": 2
        })
        assert_response_success(proposal_resp, 201)
        proposal = proposal_resp.json()

        # 2. 投票
        for voter in ["voter1", "voter2"]:
            vote_resp = await api_client.post(
                f"/governance/proposals/{proposal['id']}/vote",
                json={"voter_id": voter, "vote": 1, "weight": 1.0}
            )
            assert_response_success(vote_resp)

        # 3. 执行提案
        exec_resp = await api_client.post(f"/governance/proposals/{proposal['id']}/execute")
        assert_response_success(exec_resp)


# ============================================================================
# ============================================================================
# 测试辅助函数
# ============================================================================

def assert_response_success(response, expected_status=200):
    """断言响应成功"""
    assert response.status_code == expected_status, (
        f"Expected {expected_status}, got {response.status_code}: {response.text}"
    )


def assert_field_in_response(response_json, field: str, expected_value=None):
    """断言响应包含指定字段"""
    assert field in response_json, f"Field '{field}' not in response: {response_json}"
    if expected_value is not None:
        assert response_json[field] == expected_value, (
            f"Field '{field}' mismatch: expected {expected_value}, got {response_json[field]}"
        )
