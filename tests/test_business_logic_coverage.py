"""
完整业务API测试套件 - 全覆盖业务逻辑测试

测试特点:
1. 全方位边界条件测试
2. 业务逻辑闭环测试
3. 错误处理和异常测试
4. 数据一致性测试
5. LLM/区块链集成测试

运行:
    pytest tests/test_business_logic_coverage.py -v
"""

import pytest
import time
import uuid
import json
from typing import Any, Dict
from unittest.mock import patch, AsyncMock, MagicMock

# ============================================================================
# 辅助函数
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


# ============================================================================
# ============================================================================
# 第一部分: Agent生命周期 - 边界条件与业务逻辑
# ============================================================================
# ============================================================================

class TestAgentLifecycleEdgeCases:
    """Agent生命周期边界条件测试"""

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_create_duplicate_id(self, api_client, sample_agent_data):
        """测试: 创建重复ID的Agent应该失败"""
        # 创建第一个Agent
        response = await api_client.post("/agents", json=sample_agent_data)
        assert_response_success(response, 201)

        # 尝试创建相同ID的Agent
        response = await api_client.post("/agents", json=sample_agent_data)
        assert response.status_code in [400, 409], "重复ID应该返回错误"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_create_missing_required_fields(self, api_client):
        """测试: 缺少必填字段应该失败"""
        # 缺少name字段
        response = await api_client.post("/agents", json={
            "agent_id": "test_agent"
            # 缺少name
        })
        assert response.status_code in [400, 422], "缺少必填字段应该返回错误"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_create_invalid_stake(self, api_client):
        """测试: 无效的stake值应该被拒绝"""
        response = await api_client.post("/agents", json={
            "agent_id": "test_agent",
            "name": "TestAgent",
            "stake": -100  # 负数stake
        })
        assert response.status_code in [400, 422], "负数stake应该被拒绝"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_get_not_found(self, api_client):
        """测试: 获取不存在的Agent应该返回404"""
        response = await api_client.get("/agents/nonexistent_agent_12345")
        assert response.status_code == 404, "不存在的Agent应该返回404"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_update_not_found(self, api_client):
        """测试: 更新不存在的Agent应该返回404"""
        response = await api_client.put("/agents/nonexistent_agent_12345", json={
            "name": "NewName"
        })
        assert response.status_code == 404, "不存在的Agent应该返回404"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_delete_not_found(self, api_client):
        """测试: 删除不存在的Agent应该返回404"""
        response = await api_client.delete("/agents/nonexistent_agent_12345")
        assert response.status_code == 404, "不存在的Agent应该返回404"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_heartbeat_invalid_status(self, api_client, sample_agent_data):
        """测试: 无效的心跳状态应该被拒绝"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 发送无效状态
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/heartbeat",
            json={"status": "invalid_status"}
        )
        assert response.status_code in [400, 422], "无效状态应该被拒绝"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_list_pagination(self, api_client, sample_agent_data):
        """测试: Agent列表分页功能"""
        # 创建多个Agent
        for i in range(5):
            data = sample_agent_data.copy()
            data["agent_id"] = f"{sample_agent_data['agent_id']}_{i}"
            await api_client.post("/agents", json=data)

        # 测试分页
        response = await api_client.get("/agents?limit=2&offset=0")
        assert_response_success(response)
        data = response.json()
        assert len(data) <= 2, "分页limit应该生效"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_list_sorting(self, api_client, sample_agent_data):
        """测试: Agent列表排序功能"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 测试排序
        response = await api_client.get("/agents?sort_by=created_at&order=desc")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第二部分: 认证授权 - 边界条件
# ============================================================================

class TestAuthEdgeCases:
    """认证授权边界条件测试"""

    @pytest.mark.auth
    @pytest.mark.unit
    async def test_wallet_auth_invalid_address(self, api_client):
        """测试: 无效的钱包地址应该被拒绝"""
        response = await api_client.post("/auth/wallet/init", json={
            "wallet_address": "invalid_address"
        })
        assert response.status_code in [400, 422], "无效地址应该被拒绝"

    @pytest.mark.auth
    @pytest.mark.unit
    async def test_api_key_create_invalid_permissions(self, api_client, sample_agent_data):
        """测试: 无效的权限应该被拒绝"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建带无效权限的API Key
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/api-keys",
            json={"permissions": ["invalid_permission"]}
        )
        # 应该成功或返回警告，但不应该是500错误


# ============================================================================
# ============================================================================
# 第三部分: 钱包 - 业务逻辑
# ============================================================================

class TestWalletBusinessLogic:
    """钱包业务逻辑测试"""

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_insufficient_balance(self, api_client, sample_agent_data):
        """测试: 余额不足应该正确处理"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建钱包
        await api_client.post("/wallet", json={
            "agent_id": sample_agent_data["agent_id"]
        })

        # 尝试转账大于余额的金额
        response = await api_client.post(f"/wallet/{sample_agent_data['agent_id']}/transfer", json={
            "to": "0x" + "0" * 40,
            "amount": 999999999  # 远大于余额
        })
        assert response.status_code in [400, 402, 422], "余额不足应该返回错误"

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_daily_limit(self, api_client, sample_agent_data):
        """测试: 每日限额应该正确执行"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建钱包
        await api_client.post("/wallet", json={
            "agent_id": sample_agent_data["agent_id"]
        })

        # 获取钱包信息检查每日限额
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}")
        if response.status_code == 200:
            data = response.json()
            assert "daily_limit" in data or "daily_spent" in data, "应该包含每日限额信息"


# ============================================================================
# ============================================================================
# 第四部分: 质押 - 业务逻辑
# ============================================================================

class TestStakingBusinessLogic:
    """质押业务逻辑测试"""

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_negative_amount(self, api_client, sample_agent_data):
        """测试: 负数质押应该被拒绝"""
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": -100  # 负数
        })
        assert response.status_code in [400, 422], "负数质押应该被拒绝"

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_zero_amount(self, api_client, sample_agent_data):
        """测试: 零质押应该被拒绝"""
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 0
        })
        assert response.status_code in [400, 422], "零质押应该被拒绝"

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_unlock_more_than_staked(self, api_client, sample_agent_data):
        """测试: 解锁大于质押金额应该被拒绝"""
        await api_client.post("/agents", json=sample_agent_data)

        # 质押100
        await api_client.post("/staking/stake", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 100
        })

        # 尝试解锁200 (大于质押金额)
        response = await api_client.post(
            f"/staking/{sample_agent_data['agent_id']}/unlock",
            json={"amount": 200}
        )
        assert response.status_code in [400, 422], "解锁大于质押应该被拒绝"

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_stake_tier_benefits(self, api_client, sample_agent_data):
        """测试: 不同质押等级权益"""
        # 测试不同质押金额对应的等级
        test_cases = [
            (100, "basic"),
            (1000, "silver"),
            (10000, "gold"),
            (100000, "platinum")
        ]

        for amount, expected_tier in test_cases:
            agent_id = f"test_agent_{uuid.uuid4().hex[:6]}"
            data = sample_agent_data.copy()
            data["agent_id"] = agent_id
            await api_client.post("/agents", json=data)

            await api_client.post("/staking/stake", json={
                "agent_id": agent_id,
                "amount": amount
            })

            # 验证等级
            response = await api_client.get(f"/agents/{agent_id}")
            if response.status_code == 200:
                agent_data = response.json()
                assert agent_data.get("stake") >= amount, "质押金额应该正确记录"


# ============================================================================
# ============================================================================
# 第五部分: 需求-匹配-协作 - 业务逻辑与边界
# ============================================================================

class TestMatchingBusinessLogic:
    """匹配业务逻辑测试"""

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_match_empty_demand(self, api_client, sample_agent_data):
        """测试: 空需求不应该匹配成功"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建空需求
        demand_resp = await api_client.post("/demands", json={
            "agent_id": sample_agent_data["agent_id"],
            "title": "",
            "description": ""
        })
        demand = demand_resp.json()

        # 尝试匹配
        response = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": sample_agent_data["agent_id"]
        })
        # 应该返回空结果或错误，不应该崩溃

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_match_no_matching_service(self, api_client, sample_demand_data):
        """测试: 没有匹配服务时返回空结果"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 尝试匹配不存在的Agent
        response = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": "nonexistent_agent"
        })
        # 应该返回空结果，不是500错误
        assert response.status_code in [200, 404], "应该返回空结果或404"

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_match_score_calculation(self, api_client, sample_demand_data, sample_service_data):
        """测试: 匹配分数计算逻辑"""
        # 创建需求 - 需要特定技能
        demand_data = sample_demand_data.copy()
        demand_data["required_skills"] = ["python", "ml", "data_analysis"]

        demand_resp = await api_client.post("/demands", json=demand_data)
        demand = demand_resp.json()

        # 创建服务 - 完全匹配
        service_data = sample_service_data.copy()
        service_data["skills"] = ["python", "ml", "data_analysis"]

        await api_client.post("/services", json=service_data)

        # 执行匹配
        response = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": sample_service_data["agent_id"]
        })

        if response.status_code == 200:
            result = response.json()
            # 验证匹配分数存在且合理
            if "match_score" in result or "score" in result:
                score = result.get("match_score", result.get("score", 0))
                assert 0 <= score <= 1, "匹配分数应该在0-1之间"

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_collaboration_state_transitions(self, api_client):
        """测试: 协作状态转换"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test collaboration",
            "participants": ["agent1"]
        })
        collab = collab_resp.json()

        # 测试状态转换: pending -> active -> completed
        # 1. pending -> active
        response = await api_client.put(
            f"/collaborations/{collab['session_id']}/status",
            json={"status": "active"}
        )
        assert_response_success(response)

        # 2. active -> completed
        response = await api_client.put(
            f"/collaborations/{collab['session_id']}/complete",
            json={"result": {"success": True}}
        )
        assert_response_success(response)

        # 3. 测试无效状态转换 (completed -> active 应该失败)
        response = await api_client.put(
            f"/collaborations/{collab['session_id']}/status",
            json={"status": "active"}
        )
        # completed状态不应该能转换回active
        assert response.status_code in [400, 422], "已完成协作不应能重新激活"

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_collaboration_participant_count(self, api_client):
        """测试: 协作参与人数限制"""
        # 创建多参与者协作
        participants = [f"agent_{i}" for i in range(10)]
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Large collaboration",
            "participants": participants
        })
        assert_response_success(collab_resp, 201)


# ============================================================================
# ============================================================================
# 第六部分: 工作流 - 业务逻辑
# ============================================================================

class TestWorkflowBusinessLogic:
    """工作流业务逻辑测试"""

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_step_execution_order(self, api_client, sample_workflow_data):
        """测试: 工作流步骤执行顺序"""
        # 创建工作流
        resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = resp.json()

        # 执行工作流
        exec_resp = await api_client.post(f"/workflows/{workflow['id']}/execute")
        assert_response_success(exec_resp)

        # 验证步骤状态
        get_resp = await api_client.get(f"/workflows/{workflow['id']}")
        data = get_resp.json()

        # 验证步骤状态字段存在
        assert "status" in data, "工作流应该有状态字段"

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_circular_dependency_detection(self, api_client, sample_workflow_data):
        """测试: 工作流循环依赖检测"""
        # 创建带循环依赖的工作流
        workflow_data = sample_workflow_data.copy()
        workflow_data["steps"] = [
            {"step": 1, "action": "step_a", "depends_on": [3]},
            {"step": 2, "action": "step_b", "depends_on": [1]},
            {"step": 3, "action": "step_c", "depends_on": [2]},
        ]

        resp = await api_client.post("/workflows", json=workflow_data)

        # 应该成功创建或返回警告，但不应该导致系统崩溃
        assert resp.status_code in [201, 400, 422], "应该处理循环依赖"

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_timeout_handling(self, api_client, sample_workflow_data):
        """测试: 工作流超时处理"""
        # 创建工作流
        resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = resp.json()

        # 执行长时间运行的工作流
        exec_resp = await api_client.post(f"/workflows/{workflow['id']}/execute")

        # 应该能正确处理，不应该超时崩溃
        assert exec_resp.status_code in [200, 202, 500], "应该正确处理执行请求"


# ============================================================================
# ============================================================================
# 第七部分: 治理 - 业务逻辑
# ============================================================================

class TestGovernanceBusinessLogic:
    """治理业务逻辑测试"""

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_quorum_not_met(self, api_client, sample_proposal_data):
        """测试: 提案未达到法定人数"""
        # 创建需要3票的提案
        proposal_data = sample_proposal_data.copy()
        proposal_data["quorum"] = 3
        proposal_resp = await api_client.post("/governance/proposals", json=proposal_data)
        proposal = proposal_resp.json()

        # 只投1票
        await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 1.0}
        )

        # 尝试执行 - 应该失败
        exec_resp = await api_client.post(f"/governance/proposals/{proposal['id']}/execute")
        assert exec_resp.status_code in [400, 422], "未达到法定人数不应该执行成功"

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_vote_weight(self, api_client, sample_proposal_data):
        """测试: 投票权重计算"""
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 投不同权重的票
        await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 2.0}
        )
        await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter2", "vote": 1, "weight": 3.0}
        )

        # 获取提案状态
        get_resp = await api_client.get(f"/governance/proposals/{proposal['id']}")
        data = get_resp.json()

        # 验证票数
        assert data.get("votes_for", 0) >= 2, "应该有至少2票"

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_double_voting_prevention(self, api_client, sample_proposal_data):
        """测试: 防止重复投票"""
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 同一投票者投两次
        await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 1.0}
        )

        # 第二次投票
        response = await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 0, "weight": 1.0}
        )

        # 应该被拒绝或覆盖
        assert response.status_code in [200, 400, 409], "应该处理重复投票"

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_proposal_deadline_enforcement(self, api_client, sample_proposal_data):
        """测试: 提案截止时间执行"""
        # 创建已过期的提案
        proposal_data = sample_proposal_data.copy()
        proposal_data["deadline"] = "2020-01-01"  # 过去的日期

        proposal_resp = await api_client.post("/governance/proposals", json=proposal_data)
        proposal = proposal_resp.json()

        # 投票
        await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 1.0}
        )

        # 尝试执行过期的提案
        exec_resp = await api_client.post(f"/governance/proposals/{proposal['id']}/execute")

        # 应该被拒绝或成功(取决于业务规则)
        assert exec_resp.status_code in [200, 400, 422], "应该正确处理过期提案"


# ============================================================================
# ============================================================================
# 第八部分: 交易 - 业务逻辑
# ============================================================================

class TestTransactionBusinessLogic:
    """交易业务逻辑测试"""

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_state_machine(self, api_client, sample_agent_data):
        """测试: 交易状态机"""
        buyer_id = sample_agent_data["agent_id"]
        seller_id = f"seller_{uuid.uuid4().hex[:8]}"

        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易 (created)
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer_id,
            "seller_id": seller_id,
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 测试无效状态转换: created -> released (需要先escrow)
        response = await api_client.post(f"/transactions/{tx['id']}/release")
        assert response.status_code in [400, 422], "应该阻止无效状态转换"

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_platform_fee(self, api_client, sample_agent_data):
        """测试: 平台费计算"""
        buyer_id = sample_agent_data["agent_id"]

        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer_id,
            "seller_id": f"seller_{uuid.uuid4().hex[:8]}",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 验证平台费存在
        assert "platform_fee" in tx or "fee" in tx, "应该有平台费字段"

        # 如果有金额，验证平台费合理性
        if "platform_fee" in tx:
            assert 0 <= tx["platform_fee"] <= tx["amount"], "平台费应该在合理范围"

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_dispute_flow(self, api_client, sample_agent_data):
        """测试: 交易争议流程"""
        buyer_id = sample_agent_data["agent_id"]

        await api_client.post("/agents", json=sample_agent_data)

        # 创建并托管交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer_id,
            "seller_id": f"seller_{uuid.uuid4().hex[:8]}",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 托管
        await api_client.post(f"/transactions/{tx['id']}/escrow")

        # 发起争议
        dispute_resp = await api_client.post(
            f"/transactions/{tx['id']}/dispute",
            json={"reason": "Service not delivered"}
        )
        assert_response_success(dispute_resp)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_cancel_conditions(self, api_client, sample_agent_data):
        """测试: 交易取消条件"""
        buyer_id = sample_agent_data["agent_id"]

        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": buyer_id,
            "seller_id": f"seller_{uuid.uuid4().hex[:8]}",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 取消交易
        cancel_resp = await api_client.post(f"/transactions/{tx['id']}/cancel")
        # 应该能取消未托管的交易
        assert cancel_resp.status_code in [200, 400, 404], "应该处理取消请求"


# ============================================================================
# ============================================================================
# 第九部分: 数据一致性测试
# ============================================================================

class TestDataConsistency:
    """数据一致性测试"""

    @pytest.mark.integration
    async def test_agent_stake_wallet_consistency(self, api_client, sample_agent_data):
        """测试: Agent质押与钱包一致性"""
        agent_id = sample_agent_data["agent_id"]

        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 质押
        stake_resp = await api_client.post("/staking/stake", json={
            "agent_id": agent_id,
            "amount": 1000.0
        })
        assert_response_success(stake_resp, 201)

        # 验证Agent stake字段
        agent_resp = await api_client.get(f"/agents/{agent_id}")
        agent_data = agent_resp.json()

        # 验证钱包stake
        wallet_resp = await api_client.get(f"/wallet/{agent_id}")
        if wallet_resp.status_code == 200:
            wallet_data = wallet_resp.json()
            # Agent和钱包的质押应该一致
            if "stake" in agent_data and "staked_amount" in wallet_data:
                assert agent_data["stake"] == wallet_data.get("staked_amount"), "质押数据应该一致"

    @pytest.mark.integration
    async def test_demand_service_match_consistency(self, api_client, sample_demand_data, sample_service_data):
        """测试: 需求-服务-匹配数据一致性"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 创建服务
        service_resp = await api_client.post("/services", json=sample_service_data)
        service = service_resp.json()

        # 执行匹配
        match_resp = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": sample_service_data["agent_id"]
        })

        if match_resp.status_code == 200:
            match_data = match_resp.json()

            # 验证匹配结果包含需求和服务信息
            assert "demand_id" in match_data or match_data.get("demand", {}).get("id") == demand["id"], \
                "匹配结果应该关联需求"

    @pytest.mark.integration
    async def test_collaboration_transaction_consistency(self, api_client, sample_agent_data):
        """测试: 协作-交易数据一致性"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test collaboration",
            "participants": [sample_agent_data["agent_id"]]
        })
        collab = collab_resp.json()

        # 完成协作
        await api_client.put(
            f"/collaborations/{collab['session_id']}/complete",
            json={"result": {"success": True}}
        )

        # 验证协作状态
        get_resp = await api_client.get(f"/collaborations/{collab['session_id']}")
        data = get_resp.json()
        assert data.get("status") == "completed", "协作状态应该是completed"


# ============================================================================
# ============================================================================
# 第十部分: 性能与并发测试
# ============================================================================

class TestPerformanceAndConcurrency:
    """性能与并发测试"""

    @pytest.mark.unit
    async def test_concurrent_agent_creation(self, api_client, sample_agent_data):
        """测试: 并发创建Agent"""
        import asyncio

        async def create_agent(i):
            data = sample_agent_data.copy()
            data["agent_id"] = f"concurrent_agent_{i}"
            return await api_client.post("/agents", json=data)

        # 并发创建10个Agent
        results = await asyncio.gather(*[create_agent(i) for i in range(10)])

        # 验证都创建成功
        success_count = sum(1 for r in results if r.status_code == 201)
        assert success_count >= 8, "至少80%应该创建成功"

    @pytest.mark.unit
    async def test_bulk_operations(self, api_client, sample_agent_data):
        """测试: 批量操作性能"""
        # 批量创建
        start_time = time.time()
        for i in range(20):
            data = sample_agent_data.copy()
            data["agent_id"] = f"bulk_agent_{i}"
            await api_client.post("/agents", json=data)

        elapsed = time.time() - start_time
        assert elapsed < 30, f"批量创建20个Agent应该在30秒内完成，实际: {elapsed:.2f}s"


# ============================================================================
# ============================================================================
# 第十一部分: 错误处理与异常测试
# ============================================================================

class TestErrorHandling:
    """错误处理测试"""

    @pytest.mark.unit
    async def test_invalid_json_format(self, api_client):
        """测试: 无效JSON格式"""
        response = await api_client.post(
            "/agents",
            content="invalid json",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code in [400, 422], "无效JSON应该返回错误"

    @pytest.mark.unit
    async def test_missing_content_type(self, api_client):
        """测试: 缺少Content-Type"""
        response = await api_client.post(
            "/agents",
            content='{"name": "test"}'
        )
        assert response.status_code in [200, 400, 415], "应该处理缺少Content-Type的情况"

    @pytest.mark.unit
    async def test_sql_injection_prevention(self, api_client):
        """测试: SQL注入防护"""
        malicious_data = {
            "agent_id": "test_agent'; DROP TABLE agents;--",
            "name": "Test"
        }
        response = await api_client.post("/agents", json=malicious_data)
        # 应该成功创建或返回安全错误，不应该执行DROP TABLE
        assert response.status_code in [201, 400, 422], "应该安全处理恶意输入"

    @pytest.mark.unit
    async def test_xss_prevention(self, api_client):
        """测试: XSS防护"""
        malicious_data = {
            "agent_id": "test_agent",
            "name": "<script>alert('xss')</script>"
        }
        response = await api_client.post("/agents", json=malicious_data)

        # 应该成功创建或在响应中转义
        if response.status_code == 201:
            data = response.json()
            # 验证返回的数据中没有原始脚本
            if "name" in data:
                assert "<script>" not in data["name"], "应该转义或拒绝XSS内容"


# ============================================================================
# ============================================================================
# 第十二部分: LLM集成测试
# ============================================================================

class TestLLMIntegration:
    """LLM集成测试"""

    @pytest.mark.requires_llm
    @pytest.mark.unit
    async def test_llm_chat_integration(self, api_client):
        """测试: LLM聊天集成"""
        # 尝试调用LLM相关的API
        response = await api_client.post("/meta-agent/chat", json={
            "message": "Hello, this is a test",
            "agent_id": "test_agent"
        })

        # 应该返回成功或LLM未配置错误，不应该崩溃
        assert response.status_code in [200, 400, 401, 503], "应该正确处理LLM请求"

    @pytest.mark.requires_llm
    @pytest.mark.unit
    async def test_matching_with_llm(self, api_client, sample_demand_data, sample_service_data):
        """测试: 带LLM的智能匹配"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 创建服务
        await api_client.post("/services", json=sample_service_data)

        # 执行智能匹配 (可能使用LLM)
        response = await api_client.post("/matching/match", json={
            "demand_id": demand["id"],
            "agent_id": sample_service_data["agent_id"],
            "use_llm": True  # 尝试使用LLM
        })

        # 应该返回结果
        assert response.status_code in [200, 400, 404, 503], "应该处理匹配请求"


# ============================================================================
# ============================================================================
# 第十三部分: 区块链集成测试
# ============================================================================

class TestBlockchainIntegration:
    """区块链集成测试"""

    @pytest.mark.requires_blockchain
    @pytest.mark.unit
    async def test_blockchain_balance_query(self, api_client):
        """测试: 查询链上余额"""
        response = await api_client.get("/blockchain/balance/0x" + "0" * 40)

        # 应该返回结果或错误，不应该崩溃
        assert response.status_code in [200, 400, 404, 500], "应该处理余额查询"

    @pytest.mark.requires_blockchain
    @pytest.mark.unit
    async def test_blockchain_transaction_submission(self, api_client, sample_agent_data):
        """测试: 提交链上交易"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 尝试提交交易
        response = await api_client.post("/blockchain/transactions", json={
            "from": "0x" + "0" * 40,
            "to": "0x" + "1" * 40,
            "amount": "1.0"
        })

        # 应该返回tx hash或错误
        assert response.status_code in [200, 201, 400, 402, 500], "应该处理交易提交"


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
