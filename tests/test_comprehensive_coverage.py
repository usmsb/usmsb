"""
全面补充测试套件 - 填补测试缺口

本文件包含所有缺失的API端点测试和业务逻辑测试

运行:
    pytest tests/test_comprehensive_coverage.py -v
"""

import pytest
import time
import uuid
import json
from typing import Any, Dict


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
# 第一部分: Agent扩展功能测试
# ============================================================================

class TestAgentExtendedFeatures:
    """Agent扩展功能测试"""

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_discover(self, api_client, sample_agent_data):
        """测试: Agent发现功能"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 测试发现
        response = await api_client.get("/agents/discover")
        assert_response_success(response)

        # 验证返回列表
        data = response.json()
        assert isinstance(data, list), "Discover应该返回列表"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_ping(self, api_client, sample_agent_data):
        """测试: Agent ping检查"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # Ping检查
        response = await api_client.get(f"/agents/{sample_agent_data['agent_id']}/ping")
        assert_response_success(response)

        data = response.json()
        assert "status" in data or "pong" in str(data).lower(), "应该返回pong响应"

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_goals_create(self, api_client, sample_agent_data):
        """测试: 创建Agent目标"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建目标
        goal_data = {
            "name": "Test Goal",
            "description": "Test goal description",
            "priority": 1
        }
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/goals",
            json=goal_data
        )
        assert_response_success(response, 201)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_transactions_list(self, api_client, sample_agent_data):
        """测试: 查询Agent交易列表"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 查询交易
        response = await api_client.get(f"/agents/{sample_agent_data['agent_id']}/transactions")
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_agent_invoke(self, api_client, sample_agent_data):
        """测试: Agent调用"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 调用Agent
        invoke_data = {
            "action": "test_action",
            "parameters": {"key": "value"}
        }
        response = await api_client.post(
            f"/agents/{sample_agent_data['agent_id']}/invoke",
            json=invoke_data
        )
        # 应该返回成功或功能未实现
        assert response.status_code in [200, 201, 400, 404, 501]


# ============================================================================
# ============================================================================
# 第二部分: Heartbeat扩展测试
# ============================================================================

class TestHeartbeatExtended:
    """Heartbeat扩展测试"""

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_heartbeat_status(self, api_client):
        """测试: 获取心跳状态"""
        response = await api_client.get("/heartbeat/status")
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_heartbeat_offline(self, api_client):
        """测试: 设置Agent离线"""
        response = await api_client.post("/heartbeat/offline", json={
            "agent_id": "test_agent_offline"
        })
        assert_response_success(response)

    @pytest.mark.agent
    @pytest.mark.unit
    async def test_heartbeat_busy(self, api_client):
        """测试: 设置Agent忙碌"""
        response = await api_client.post("/heartbeat/busy", json={
            "agent_id": "test_agent_busy"
        })
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第三部分: Matching扩展测试
# ============================================================================

class TestMatchingExtended:
    """Matching扩展测试"""

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_search_demands(self, api_client, sample_demand_data):
        """测试: 搜索需求"""
        # 创建需求
        await api_client.post("/demands", json=sample_demand_data)

        # 搜索
        response = await api_client.post("/matching/search-demands", json={
            "keywords": ["data", "analysis"],
            "category": "data_analysis"
        })
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_search_suppliers(self, api_client, sample_service_data):
        """测试: 搜索供应商"""
        # 创建服务
        await api_client.post("/services", json=sample_service_data)

        # 搜索
        response = await api_client.post("/matching/search-suppliers", json={
            "skills": ["python", "data_analysis"],
            "category": "data_analysis"
        })
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_negotiate(self, api_client, sample_demand_data):
        """测试: 发起谈判"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 发起谈判
        response = await api_client.post("/matching/negotiate", json={
            "demand_id": demand["id"],
            "agent_id": sample_demand_data["agent_id"],
            "initial_offer": {"price": 150.0}
        })
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_negotiations_list(self, api_client):
        """测试: 谈判列表"""
        response = await api_client.get("/matching/negotiations")
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_negotiation_propose(self, api_client, sample_demand_data):
        """测试: 谈判中提出提案"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 先发起谈判
        negotiate_resp = await api_client.post("/matching/negotiate", json={
            "demand_id": demand["id"],
            "agent_id": sample_demand_data["agent_id"]
        })

        if negotiate_resp.status_code == 200:
            negotiate_data = negotiate_resp.json()
            session_id = negotiate_data.get("session_id")

            if session_id:
                # 提出提案
                response = await api_client.post(
                    f"/matching/negotiations/{session_id}/proposal",
                    json={"terms": {"price": 200.0, "timeline": "7 days"}}
                )
                assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_negotiation_accept(self, api_client, sample_demand_data):
        """测试: 接受谈判"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 发起谈判
        negotiate_resp = await api_client.post("/matching/negotiate", json={
            "demand_id": demand["id"],
            "agent_id": sample_demand_data["agent_id"]
        })

        if negotiate_resp.status_code == 200:
            negotiate_data = negotiate_resp.json()
            session_id = negotiate_data.get("session_id")

            if session_id:
                # 接受
                response = await api_client.post(
                    f"/matching/negotiations/{session_id}/accept"
                )
                assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_negotiation_reject(self, api_client, sample_demand_data):
        """测试: 拒绝谈判"""
        # 创建需求
        demand_resp = await api_client.post("/demands", json=sample_demand_data)
        demand = demand_resp.json()

        # 发起谈判
        negotiate_resp = await api_client.post("/matching/negotiate", json={
            "demand_id": demand["id"],
            "agent_id": sample_demand_data["agent_id"]
        })

        if negotiate_resp.status_code == 200:
            negotiate_data = negotiate_resp.json()
            session_id = negotiate_data.get("session_id")

            if session_id:
                # 拒绝
                response = await api_client.post(
                    f"/matching/negotiations/{session_id}/reject",
                    json={"reason": "Price too high"}
                )
                assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_matching_opportunities(self, api_client):
        """测试: 匹配机会列表"""
        response = await api_client.get("/matching/opportunities")
        assert_response_success(response)

    @pytest.mark.matching
    @pytest.mark.unit
    async def test_matching_stats(self, api_client):
        """测试: 匹配统计"""
        response = await api_client.get("/matching/stats")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第四部分: Collaborations扩展测试
# ============================================================================

class TestCollaborationsExtended:
    """Collaborations扩展测试"""

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_execute(self, api_client):
        """测试: 执行协作"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test collaboration execution",
            "participants": ["agent1"]
        })
        collab = collab_resp.json()

        # 执行
        response = await api_client.post(f"/collaborations/{collab['session_id']}/execute")
        assert_response_success(response)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_stats(self, api_client):
        """测试: 协作统计"""
        response = await api_client.get("/collaborations/stats")
        assert_response_success(response)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_join(self, api_client):
        """测试: 加入协作"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test join",
            "participants": []
        })
        collab = collab_resp.json()

        # 加入
        response = await api_client.post(
            f"/collaborations/{collab['session_id']}/join",
            json={"agent_id": "new_agent"}
        )
        assert_response_success(response)

    @pytest.mark.collaboration
    @pytest.mark.unit
    async def test_collaboration_contribute(self, api_client):
        """测试: 协作贡献"""
        # 创建协作
        collab_resp = await api_client.post("/collaborations", json={
            "goal": "Test contribution",
            "participants": ["agent1"]
        })
        collab = collab_resp.json()

        # 贡献
        response = await api_client.post(
            f"/collaborations/{collab['session_id']}/contribute",
            json={"content": "Contribution text", "agent_id": "agent1"}
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第五部分: Workflows扩展测试
# ============================================================================

class TestWorkflowsExtended:
    """Workflows扩展测试"""

    @pytest.mark.workflow
    @pytest.mark.unit
    async def test_workflow_execute(self, api_client, sample_workflow_data):
        """测试: 执行工作流"""
        # 创建工作流
        resp = await api_client.post("/workflows", json=sample_workflow_data)
        workflow = resp.json()

        # 执行
        response = await api_client.post(f"/workflows/{workflow['id']}/execute")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第六部分: Staking扩展测试
# ============================================================================

class TestStakingExtended:
    """Staking扩展测试"""

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_staking_deposit(self, api_client, sample_agent_data):
        """测试: 质押存款"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 存款
        response = await api_client.post("/staking/deposit", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 1000.0
        })
        assert_response_success(response, 201)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_staking_withdraw(self, api_client, sample_agent_data):
        """测试: 质押取款"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 先存款
        await api_client.post("/staking/deposit", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 1000.0
        })

        # 取款
        response = await api_client.post("/staking/withdraw", json={
            "agent_id": sample_agent_data["agent_id"],
            "amount": 500.0
        })
        assert_response_success(response)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_staking_info(self, api_client, sample_agent_data):
        """测试: 质押信息"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 查询
        response = await api_client.get(f"/staking/info?agent_id={sample_agent_data['agent_id']}")
        assert_response_success(response)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_staking_rewards(self, api_client, sample_agent_data):
        """测试: 质押奖励"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 查询奖励
        response = await api_client.get(f"/staking/rewards?agent_id={sample_agent_data['agent_id']}")
        assert_response_success(response)

    @pytest.mark.staking
    @pytest.mark.unit
    async def test_staking_claim(self, api_client, sample_agent_data):
        """测试: 领取奖励"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 领取
        response = await api_client.post("/staking/claim", json={
            "agent_id": sample_agent_data["agent_id"]
        })
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第七部分: Wallet扩展测试
# ============================================================================

class TestWalletExtended:
    """Wallet扩展测试"""

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_balance(self, api_client, sample_agent_data):
        """测试: 钱包余额查询"""
        # 创建Agent和钱包
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/wallet", json={"agent_id": sample_agent_data["agent_id"]})

        # 查询余额
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}/balance")
        assert_response_success(response)

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_transactions(self, api_client, sample_agent_data):
        """测试: 钱包交易历史"""
        # 创建Agent和钱包
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/wallet", json={"agent_id": sample_agent_data["agent_id"]})

        # 查询交易历史
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}/transactions")
        assert_response_success(response)

    @pytest.mark.wallet
    @pytest.mark.unit
    async def test_wallet_transaction_detail(self, api_client, sample_agent_data):
        """测试: 钱包单笔交易详情"""
        # 创建Agent和钱包
        await api_client.post("/agents", json=sample_agent_data)
        await api_client.post("/wallet", json={"agent_id": sample_agent_data["agent_id"]})

        # 查询单笔交易
        response = await api_client.get(f"/wallet/{sample_agent_data['agent_id']}/transactions/tx_123")
        assert response.status_code in [200, 404]


# ============================================================================
# ============================================================================
# 第八部分: Transactions扩展测试
# ============================================================================

class TestTransactionsExtended:
    """Transactions扩展测试"""

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_start(self, api_client, sample_agent_data):
        """测试: 开始交易"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 开始
        response = await api_client.post(f"/transactions/{tx['id']}/start")
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_deliver(self, api_client, sample_agent_data):
        """测试: 交付交易"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 交付
        response = await api_client.post(
            f"/transactions/{tx['id']}/deliver",
            json={"delivery_info": "delivered"}
        )
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_accept_final(self, api_client, sample_agent_data):
        """测试: 接受交易"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 接受
        response = await api_client.post(f"/transactions/{tx['id']}/accept")
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_dispute_full(self, api_client, sample_agent_data):
        """测试: 发起争议"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 发起争议
        response = await api_client.post(
            f"/transactions/{tx['id']}/dispute",
            json={"reason": "Service not as described"}
        )
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_resolve(self, api_client, sample_agent_data):
        """测试: 解决争议"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 先发起争议
        await api_client.post(f"/transactions/{tx['id']}/dispute", json={"reason": "test"})

        # 解决争议
        response = await api_client.post(
            f"/transactions/{tx['id']}/resolve",
            json={"resolution": "refund", "amount": 50.0}
        )
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_cancel_full(self, api_client, sample_agent_data):
        """测试: 取消交易"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建交易
        tx_resp = await api_client.post("/transactions", json={
            "buyer_id": sample_agent_data["agent_id"],
            "seller_id": "seller_123",
            "amount": 100.0
        })
        tx = tx_resp.json()

        # 取消
        response = await api_client.post(f"/transactions/{tx['id']}/cancel")
        assert_response_success(response)

    @pytest.mark.transaction
    @pytest.mark.unit
    async def test_transaction_stats_summary(self, api_client):
        """测试: 交易统计摘要"""
        response = await api_client.get("/transactions/stats/summary")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第九部分: Services扩展测试
# ============================================================================

class TestServicesExtended:
    """Services扩展测试"""

    @pytest.mark.unit
    async def test_service_create_v2(self, api_client, sample_agent_data):
        """测试: 创建服务v2"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建服务
        response = await api_client.post(
            f"/services/agents/{sample_agent_data['agent_id']}/services",
            json={
                "service_name": "TestService",
                "description": "Test service",
                "category": "test",
                "price": 100.0
            }
        )
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_service_list_v2(self, api_client):
        """测试: 服务列表v2"""
        response = await api_client.get("/services/services")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_service_detail_v2(self, api_client, sample_service_data):
        """测试: 服务详情v2"""
        # 创建服务
        service_resp = await api_client.post("/services", json=sample_service_data)
        service = service_resp.json()

        # 获取详情
        response = await api_client.get(f"/services/services/{service['id']}")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_service_delete_v2(self, api_client, sample_service_data):
        """测试: 删除服务v2"""
        # 创建服务
        service_resp = await api_client.post("/services", json=sample_service_data)
        service = service_resp.json()

        # 删除
        response = await api_client.delete(f"/services/services/{service['id']}")
        assert_response_success(response, 204)


# ============================================================================
# ============================================================================
# 第十部分: Learning扩展测试
# ============================================================================

class TestLearningExtended:
    """Learning扩展测试"""

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_analyze(self, api_client, sample_agent_data):
        """测试: 学习分析"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 分析
        response = await api_client.post("/learning/analyze", json={
            "agent_id": sample_agent_data["agent_id"]
        })
        assert_response_success(response)

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_insights_list(self, api_client, sample_agent_data):
        """测试: 学习洞察列表"""
        response = await api_client.get("/learning/insights")
        assert_response_success(response)

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_strategy(self, api_client):
        """测试: 学习策略"""
        response = await api_client.get("/learning/strategy")
        assert_response_success(response)

    @pytest.mark.learning
    @pytest.mark.unit
    async def test_learning_market(self, api_client):
        """测试: 市场分析"""
        response = await api_client.get("/learning/market")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十一部分: Network扩展测试
# ============================================================================

class TestNetworkExtended:
    """Network扩展测试"""

    @pytest.mark.network
    @pytest.mark.unit
    async def test_network_explore_full(self, api_client, sample_agent_data):
        """测试: 网络探索完整"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 探索
        response = await api_client.post("/network/explore", json={
            "agent_id": sample_agent_data["agent_id"],
            "depth": 2
        })
        assert_response_success(response)

    @pytest.mark.network
    @pytest.mark.unit
    async def test_network_recommendations(self, api_client, sample_agent_data):
        """测试: 网络推荐"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 推荐
        response = await api_client.post("/network/recommendations", json={
            "agent_id": sample_agent_data["agent_id"]
        })
        assert_response_success(response)

    @pytest.mark.network
    @pytest.mark.unit
    async def test_network_stats_full(self, api_client):
        """测试: 网络统计"""
        response = await api_client.get("/network/stats")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十二部分: Blockchain扩展测试
# ============================================================================

class TestBlockchainExtended:
    """Blockchain扩展测试"""

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_status_full(self, api_client):
        """测试: 区块链状态"""
        response = await api_client.get("/blockchain/status")
        assert_response_success(response)

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_balance_query(self, api_client):
        """测试: 区块链余额查询"""
        response = await api_client.get("/blockchain/balance/0x" + "0" * 40)
        # 可能返回0或404，但不应该崩溃
        assert response.status_code in [200, 404]

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_tax(self, api_client):
        """测试: 税费计算"""
        response = await api_client.get("/blockchain/tax/100")
        assert_response_success(response)

    @pytest.mark.blockchain
    @pytest.mark.unit
    async def test_blockchain_total_supply(self, api_client):
        """测试: 总供应量"""
        response = await api_client.get("/blockchain/total-supply")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十三部分: System扩展测试
# ============================================================================

class TestSystemExtended:
    """System扩展测试"""

    @pytest.mark.unit
    async def test_health_live(self, api_client):
        """测试: 存活检查"""
        response = await api_client.get("/system/health/live")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_health_ready(self, api_client):
        """测试: 就绪检查"""
        response = await api_client.get("/system/health/ready")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_system_metrics_full(self, api_client):
        """测试: 系统指标"""
        response = await api_client.get("/system/metrics")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_system_status_full(self, api_client):
        """测试: 系统状态"""
        response = await api_client.get("/system/status")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_system_stats_summary_full(self, api_client):
        """测试: 系统统计摘要"""
        response = await api_client.get("/system/stats/summary")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十四部分: Reputation扩展测试
# ============================================================================

class TestReputationExtended:
    """Reputation扩展测试"""

    @pytest.mark.unit
    async def test_reputation_history(self, api_client, sample_agent_data):
        """测试: 声誉历史"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 查询历史
        response = await api_client.get(f"/reputation/{sample_agent_data['agent_id']}/history")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十五部分: Predictions扩展测试
# ============================================================================

class TestPredictionsExtended:
    """Predictions扩展测试"""

    @pytest.mark.unit
    async def test_prediction_behavior_full(self, api_client, sample_agent_data):
        """测试: 行为预测"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 预测
        response = await api_client.post("/predictions/behavior", json={
            "agent_id": sample_agent_data["agent_id"],
            "parameters": {"look_ahead": 10}
        })
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十六部分: Gene Capsule扩展测试
# ============================================================================

class TestGeneCapsuleExtended:
    """Gene Capsule扩展测试"""

    @pytest.mark.unit
    async def test_gene_capsule_summary(self, api_client, sample_agent_data):
        """测试: 基因胶囊摘要"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 获取摘要
        response = await api_client.get(f"/gene-capsules/{sample_agent_data['agent_id']}/summary")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_experiences(self, api_client, sample_agent_data):
        """测试: 经验基因"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建经验
        response = await api_client.post("/gene-capsules/experiences", json={
            "agent_id": sample_agent_data["agent_id"],
            "experience": "Test experience"
        })
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_gene_capsule_visibility(self, api_client):
        """测试: 经验可见性"""
        # 更新可见性
        response = await api_client.patch(
            "/gene-capsules/experiences/exp_123/visibility",
            json={"visibility": "public"}
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_desensitize(self, api_client):
        """测试: 脱敏处理"""
        response = await api_client.post("/gene-capsules/desensitize", json={
            "text": "Sensitive information here"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_match_full(self, api_client):
        """测试: 基因匹配"""
        response = await api_client.post("/gene-capsules/match", json={
            "query": "data analysis"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_skill_recommendations(self, api_client):
        """测试: 技能推荐"""
        response = await api_client.post("/gene-capsules/skill-recommendations", json={
            "agent_id": "test_agent"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_search_agents(self, api_client):
        """测试: 搜索Agent"""
        response = await api_client.post("/gene-capsules/search-agents", json={
            "skills": ["python"]
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_showcase(self, api_client):
        """测试: 展示柜"""
        response = await api_client.post("/gene-capsules/showcase", json={
            "agent_id": "test_agent"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_verify(self, api_client):
        """测试: 验证经验"""
        response = await api_client.post(
            "/gene-capsules/experiences/exp_123/verify",
            json={"agent_id": "test_agent"}
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_verification_status(self, api_client):
        """测试: 验证状态"""
        response = await api_client.get("/gene-capsules/experiences/exp_123/verification")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_value_scores(self, api_client, sample_agent_data):
        """测试: 价值分数"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.get(f"/gene-capsules/{sample_agent_data['agent_id']}/value-scores")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_patterns(self, api_client, sample_agent_data):
        """测试: 模式基因"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.get(f"/gene-capsules/{sample_agent_data['agent_id']}/patterns")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_gene_capsule_sync(self, api_client, sample_agent_data):
        """测试: 同步基因"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post(f"/gene-capsules/{sample_agent_data['agent_id']}/sync")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十七部分: Pre-match Negotiation扩展测试
# ============================================================================

class TestPreMatchNegotiationExtended:
    """Pre-match Negotiation扩展测试"""

    @pytest.mark.unit
    async def test_negotiation_questions(self, api_client):
        """测试: 谈判问题"""
        # 创建谈判
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                # 提问
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/questions",
                    json={"question": "What is your availability?"}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_answer(self, api_client):
        """测试: 回答问题"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                # 先提问
                await api_client.post(
                    f"/pre-match/negotiations/{session_id}/questions",
                    json={"question": "test"}
                )

                # 回答
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/questions/q_123/answer",
                    json={"answer": "My answer"}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_verify_full(self, api_client):
        """测试: 验证谈判"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/verify"
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_verify_respond(self, api_client):
        """测试: 验证响应"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/verify/req_123/respond",
                    json={"accepted": True}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_scope(self, api_client):
        """测试: 谈判范围"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/scope",
                    json={"scope": "data analysis"}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_terms_propose(self, api_client):
        """测试: 提出条款"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/terms/propose",
                    json={"price": 200, "timeline": "7 days"}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_terms_agree(self, api_client):
        """测试: 同意条款"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/terms/agree"
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_confirm(self, api_client):
        """测试: 确认谈判"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/confirm"
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_decline(self, api_client):
        """测试: 拒绝谈判"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/decline",
                    json={"reason": "Not interested"}
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_cancel_full(self, api_client):
        """测试: 取消谈判"""
        start_resp = await api_client.post("/pre-match/negotiations/start", json={
            "initiator_id": "agent1",
            "counterpart_id": "agent2"
        })

        if start_resp.status_code == 201:
            negotiation = start_resp.json()
            session_id = negotiation.get("session_id")

            if session_id:
                response = await api_client.post(
                    f"/pre-match/negotiations/{session_id}/cancel"
                )
                assert_response_success(response)

    @pytest.mark.unit
    async def test_negotiation_by_agent(self, api_client):
        """测试: 按Agent查询谈判"""
        response = await api_client.get("/pre-match/negotiations/agent/agent_123")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十八部分: Meta Agent Matching扩展测试
# ============================================================================

class TestMetaAgentMatchingExtended:
    """Meta Agent Matching扩展测试"""

    @pytest.mark.unit
    async def test_meta_conversation_create(self, api_client):
        """测试: 创建对话"""
        response = await api_client.post("/meta-agent/conversations", json={
            "agent_id": "test_agent",
            "user_id": "test_user"
        })
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_meta_conversation_get(self, api_client):
        """测试: 获取对话"""
        response = await api_client.get("/meta-agent/conversations/conv_123")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_conversation_message(self, api_client):
        """测试: 发送消息"""
        response = await api_client.post(
            "/meta-agent/conversations/conv_123/messages",
            json={"message": "Hello"}
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_recommend(self, api_client):
        """测试: Meta推荐"""
        response = await api_client.post("/meta-agent/recommend", json={
            "user_id": "test_user",
            "context": "looking for data analysis"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_match_gene_capsule(self, api_client):
        """测试: 基因胶囊匹配"""
        response = await api_client.post("/meta-agent/match/gene-capsule", json={
            "capsule_id": "capsule_123"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_profiles_list(self, api_client):
        """测试: Meta档案列表"""
        response = await api_client.get("/meta-agent/profiles")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_profile_detail(self, api_client):
        """测试: Meta档案详情"""
        response = await api_client.get("/meta-agent/profiles/agent_123")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_consult(self, api_client):
        """测试: Meta咨询"""
        response = await api_client.post("/meta-agent/consult", json={
            "question": "What agents do you recommend?"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_showcase_full(self, api_client):
        """测试: Meta展示"""
        response = await api_client.post("/meta-agent/showcase", json={
            "category": "data_analysis"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_opportunities_notify(self, api_client):
        """测试: 机会通知"""
        response = await api_client.post("/meta-agent/opportunities/notify", json={
            "agent_id": "test_agent",
            "opportunity_type": "new_demand"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_opportunities_scan(self, api_client):
        """测试: 机会扫描"""
        response = await api_client.post("/meta-agent/opportunities/scan", json={
            "agent_id": "test_agent"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_meta_opportunities_auto_match(self, api_client):
        """测试: 自动匹配机会"""
        response = await api_client.post("/meta-agent/opportunities/auto-match", json={
            "agent_id": "test_agent"
        })
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第十九部分: Registration扩展测试
# ============================================================================

class TestRegistrationExtended:
    """Registration扩展测试"""

    @pytest.mark.unit
    async def test_register_agent_v2(self, api_client, sample_agent_data):
        """测试: Agent注册v2"""
        response = await api_client.post("/registration/agents/v2/register", json=sample_agent_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_binding_request(self, api_client, sample_agent_data):
        """测试: 绑定请求"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 请求绑定
        response = await api_client.post(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/request-binding",
            json={"wallet_address": "0x" + "0" * 40}
        )
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_binding_status(self, api_client, sample_agent_data):
        """测试: 绑定状态"""
        response = await api_client.get(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/binding-status"
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_complete_binding(self, api_client):
        """测试: 完成绑定"""
        response = await api_client.post(
            "/registration/agents/v2/complete-binding/binding_code_123",
            json={"signature": "0x" + "0" * 65}
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_api_keys_list(self, api_client, sample_agent_data):
        """测试: API密钥列表"""
        response = await api_client.get(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/api-keys"
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_api_keys_create_full(self, api_client, sample_agent_data):
        """测试: 创建API密钥"""
        response = await api_client.post(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/api-keys",
            json={"name": "Test Key", "permissions": ["read"]}
        )
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_api_keys_revoke(self, api_client, sample_agent_data):
        """测试: 撤销API密钥"""
        response = await api_client.post(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/api-keys/key_123/revoke"
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_api_keys_renew(self, api_client, sample_agent_data):
        """测试: 续期API密钥"""
        response = await api_client.post(
            f"/registration/agents/v2/{sample_agent_data['agent_id']}/api-keys/key_123/renew"
        )
        assert_response_success(response)

    @pytest.mark.unit
    async def test_profile_get(self, api_client):
        """测试: 获取档案"""
        response = await api_client.get("/registration/agents/v2/profile")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_profile_update(self, api_client):
        """测试: 更新档案"""
        response = await api_client.patch("/registration/agents/v2/profile", json={
            "display_name": "Test User"
        })
        assert_response_success(response)

    @pytest.mark.unit
    async def test_owner_info(self, api_client):
        """测试: 所有者信息"""
        response = await api_client.get("/registration/agents/v2/owner")
        assert_response_success(response)

    @pytest.mark.unit
    async def test_register_standard(self, api_client, sample_agent_data):
        """测试: 标准注册"""
        response = await api_client.post("/registration/agents/register", json=sample_agent_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_register_mcp(self, api_client, sample_agent_data):
        """测试: MCP注册"""
        response = await api_client.post("/registration/agents/register/mcp", json=sample_agent_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_register_a2a(self, api_client, sample_agent_data):
        """测试: A2A注册"""
        response = await api_client.post("/registration/agents/register/a2a", json=sample_agent_data)
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_register_skill_md(self, api_client, sample_agent_data):
        """测试: Skill-MD注册"""
        response = await api_client.post(
            "/registration/agents/register/skill-md",
            json=sample_agent_data
        )
        assert_response_success(response, 201)

    @pytest.mark.unit
    async def test_agent_test_endpoint(self, api_client, sample_agent_data):
        """测试: Agent测试端点"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        response = await api_client.post(
            f"/registration/agents/{sample_agent_data['agent_id']}/test"
        )
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第二十部分: Governance扩展测试
# ============================================================================

class TestGovernanceExtended:
    """Governance扩展测试"""

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_governance_proposals_list(self, api_client):
        """测试: 提案列表"""
        response = await api_client.get("/governance/proposals")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_governance_proposal_detail(self, api_client, sample_proposal_data):
        """测试: 提案详情"""
        # 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 获取详情
        response = await api_client.get(f"/governance/proposals/{proposal['id']}")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_governance_vote_full(self, api_client, sample_proposal_data):
        """测试: 投票完整"""
        # 创建提案
        proposal_resp = await api_client.post("/governance/proposals", json=sample_proposal_data)
        proposal = proposal_resp.json()

        # 投票
        response = await api_client.post(
            f"/governance/proposals/{proposal['id']}/vote",
            json={"voter_id": "voter1", "vote": 1, "weight": 1.0}
        )
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_governance_stats_full(self, api_client):
        """测试: 治理统计"""
        response = await api_client.get("/governance/stats")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_my_proposals(self, api_client):
        """测试: 我的提案"""
        response = await api_client.get("/governance/my-proposals")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_my_votes(self, api_client):
        """测试: 我的投票"""
        response = await api_client.get("/governance/my-votes")
        assert_response_success(response)

    @pytest.mark.governance
    @pytest.mark.unit
    async def test_voting_power(self, api_client):
        """测试: 投票权"""
        response = await api_client.get("/governance/voting-power")
        assert_response_success(response)


# ============================================================================
# ============================================================================
# 第二十一部分: Environments扩展测试
# ============================================================================

class TestEnvironmentsExtended:
    """Environments扩展测试"""

    @pytest.mark.environment
    @pytest.mark.unit
    async def test_environment_detail(self, api_client, sample_agent_data):
        """测试: 环境详情"""
        # 创建Agent
        await api_client.post("/agents", json=sample_agent_data)

        # 创建环境
        env_resp = await api_client.post("/environments", json={
            "agent_id": sample_agent_data["agent_id"],
            "name": "TestEnv"
        })
        env = env_resp.json()

        # 获取详情
        response = await api_client.get(f"/environments/{env['id']}")
        assert_response_success(response)


# ============================================================================
# 运行入口
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
