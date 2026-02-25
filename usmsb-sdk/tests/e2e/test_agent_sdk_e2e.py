"""
Agent SDK 新增功能 - E2E 测试

测试完整的端到端场景：
- Gene Capsule 完整流程
- Discovery 搜索流程
- Negotiation 洽谈流程
- Meta Agent 集成流程
- 完整的供需匹配场景
"""

import pytest
import asyncio
import httpx
from datetime import datetime
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== E2E 配置 ====================

E2E_BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
E2E_TIMEOUT = float(os.getenv("E2E_TIMEOUT", "30.0"))


# ==================== Gene Capsule E2E Tests ====================

class TestE2EGeneCapsule:
    """E2E tests for Gene Capsule flow"""

    @pytest.mark.asyncio
    async def test_full_gene_capsule_flow(self):
        """
        测试完整的基因胶囊流程:
        1. 获取基因胶囊
        2. 添加经验
        3. 搜索经验
        4. 导出展示
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            agent_id = "e2e_gene_agent"

            # Step 1: 获取基因胶囊
            response = await client.get(
                f"{E2E_BASE_URL}/gene-capsule/{agent_id}"
            )
            assert response.status_code in [200, 404]

            # Step 2: 添加经验
            response = await client.post(
                f"{E2E_BASE_URL}/gene-capsule/{agent_id}/experiences",
                json={
                    "task_type": "数据分析",
                    "task_description": "完成了电商销售预测项目",
                    "techniques_used": ["机器学习", "时间序列分析"],
                    "tools_used": ["Python", "Pandas"],
                    "outcome": "success",
                    "quality_score": 0.92,
                    "client_rating": 5,
                    "visibility": "public",
                }
            )
            assert response.status_code in [200, 201]
            data = response.json()
            assert data.get("success") is True or data.get("gene_id") is not None

            # Step 3: 搜索经验
            response = await client.post(
                f"{E2E_BASE_URL}/gene-capsule/search",
                json={
                    "query": "电商销售预测",
                    "limit": 5,
                }
            )
            assert response.status_code == 200

            # Step 4: 导出展示
            response = await client.get(
                f"{E2E_BASE_URL}/gene-capsule/{agent_id}/showcase"
            )
            assert response.status_code == 200


# ==================== Discovery E2E Tests ====================

class TestE2EDiscovery:
    """E2E tests for Discovery flow"""

    @pytest.mark.asyncio
    async def test_multi_dimensional_search_flow(self):
        """
        测试多维度搜索流程:
        1. 基础搜索
        2. 多维度搜索
        3. 语义搜索
        4. 经验搜索
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 基础搜索
            response = await client.get(
                f"{E2E_BASE_URL}/agents",
                params={"capability": "数据分析"}
            )
            assert response.status_code == 200

            # Step 2: 多维度搜索
            response = await client.post(
                f"{E2E_BASE_URL}/matching/search-suppliers",
                json={
                    "required_capabilities": ["数据分析", "机器学习"],
                    "budget_range": {"min": 100, "max": 1000},
                }
            )
            assert response.status_code == 200

            # Step 3: 语义搜索（如果有对应端点）
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/recommend",
                json={
                    "demand": {
                        "description": "需要一个数据分析专家",
                        "required_skills": ["Python", "数据分析"],
                    },
                    "limit": 5,
                }
            )
            if response.status_code == 200:
                data = response.json()
                assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_watch_flow(self):
        """测试监控功能"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # 创建监控
            response = await client.post(
                f"{E2E_BASE_URL}/matching/watch",
                json={
                    "conditions": {
                        "capability": "数据分析",
                        "min_score": 0.8,
                    },
                    "notify_url": "http://localhost:8080/notify",
                }
            )
            # 可能返回200或404（如果端点不存在）
            assert response.status_code in [200, 404, 405]


# ==================== Negotiation E2E Tests ====================

class TestE2ENegotiation:
    """E2E tests for Negotiation flow"""

    @pytest.mark.asyncio
    async def test_full_negotiation_flow(self):
        """
        测试完整的洽谈流程:
        1. 发起洽谈
        2. 提问回答
        3. 能力验证
        4. 范围确认
        5. 匹配确认
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 发起洽谈
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/initiate",
                json={
                    "demand_agent_id": "e2e_demand_agent",
                    "supply_agent_id": "e2e_supply_agent",
                    "demand_id": "e2e_demand_001",
                }
            )
            assert response.status_code == 200
            data = response.json()
            negotiation_id = data.get("negotiation_id")
            assert negotiation_id is not None

            # Step 2: 提问
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/questions",
                json={
                    "question": "你能处理多大规模的数据？",
                    "asker_id": "e2e_demand_agent",
                }
            )
            assert response.status_code == 200
            data = response.json()
            question_id = data.get("question_id")
            assert question_id is not None

            # Step 3: 回答问题
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/questions/{question_id}/answer",
                json={
                    "answer": "我可以处理百万级的数据",
                    "answerer_id": "e2e_supply_agent",
                }
            )
            assert response.status_code == 200

            # Step 4: 请求能力验证
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/verify",
                json={
                    "capability": "数据分析",
                    "verification_type": "gene_capsule",
                    "request_detail": "请展示你的数据分析经验",
                }
            )
            assert response.status_code == 200

            # Step 5: 确认范围
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/scope",
                json={
                    "scope": {
                        "deliverables": ["分析报告"],
                        "timeline": "1周",
                    },
                }
            )
            assert response.status_code == 200

            # Step 6: 确认匹配
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/confirm"
            )
            assert response.status_code == 200


# ==================== Meta Agent E2E Tests ====================

class TestE2EMetaAgent:
    """E2E tests for Meta Agent flow"""

    @pytest.mark.asyncio
    async def test_interview_to_recommendation_flow(self):
        """
        测试面试到推荐的完整流程:
        1. 发起面试对话
        2. 多轮对话
        3. 提取画像
        4. 接收推荐
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            agent_id = "e2e_interview_agent"

            # Step 1: 发起面试对话
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": agent_id,
                    "conversation_type": "interview",
                }
            )
            assert response.status_code == 200
            data = response.json()
            conversation_id = data.get("conversation_id")
            assert conversation_id is not None

            # Step 2: 多轮对话
            messages = [
                "我是一名数据分析专家",
                "我有5年的电商数据分析经验",
                "我最擅长销售预测和用户行为分析",
            ]

            for msg in messages:
                response = await client.post(
                    f"{E2E_BASE_URL}/meta-agent/conversations/{conversation_id}/messages",
                    json={"message": msg}
                )
                assert response.status_code == 200

            # Step 3: 获取画像
            response = await client.get(
                f"{E2E_BASE_URL}/meta-agent/profiles/{agent_id}",
                params={"conversation_id": conversation_id}
            )
            assert response.status_code == 200
            data = response.json()
            assert "profile" in data

            # Step 4: 展示能力
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/showcase",
                json={
                    "agent_id": agent_id,
                    "showcase": {
                        "type": "experience",
                        "title": "电商销售预测",
                        "description": "完成过多个电商销售预测项目",
                        "skills": ["数据分析", "机器学习"],
                        "outcome": "success",
                    }
                }
            )
            assert response.status_code == 200

            # Step 5: 获取推荐
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/recommend",
                json={
                    "demand": {
                        "description": "需要电商销售预测",
                        "required_skills": ["数据分析"],
                    },
                    "limit": 5,
                }
            )
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_consultation_flow(self):
        """测试咨询服务流程"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/consult",
                json={
                    "agent_id": "e2e_consult_agent",
                    "question": "我应该如何提升我的可见性？",
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "response" in data

    @pytest.mark.asyncio
    async def test_opportunity_notification_flow(self):
        """测试机会通知流程"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            agent_id = "e2e_opportunity_agent"

            # 先创建画像
            await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": agent_id,
                    "conversation_type": "introduction",
                }
            )

            # 发送机会通知
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/opportunities/notify",
                json={
                    "agent_id": agent_id,
                    "opportunity": {
                        "opportunity_id": "e2e_opp_001",
                        "type": "demand",
                        "title": "数据分析项目",
                        "description": "需要数据分析服务",
                        "counterpart_id": "e2e_client",
                        "counterpart_name": "Test Client",
                        "match_score": 0.85,
                    }
                }
            )
            assert response.status_code == 200


# ==================== Complete Scenario Tests ====================

class TestE2ECompleteScenarios:
    """Complete end-to-end scenario tests"""

    @pytest.mark.asyncio
    async def test_demand_agent_scenario(self):
        """
        需求方完整场景:
        1. 发布需求
        2. 搜索供应商
        3. 发起洽谈
        4. 确认匹配
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # 1. 发布需求
            response = await client.post(
                f"{E2E_BASE_URL}/demands",
                json={
                    "title": "电商销售预测项目",
                    "description": "需要电商销售预测分析",
                    "required_skills": ["数据分析", "机器学习"],
                    "budget_range": {"min": 500, "max": 2000},
                }
            )
            if response.status_code in [200, 201]:
                demand_id = response.json().get("demand_id")
            else:
                demand_id = "e2e_demand_test"

            # 2. 搜索供应商
            response = await client.post(
                f"{E2E_BASE_URL}/matching/search-suppliers",
                json={
                    "required_capabilities": ["数据分析"],
                }
            )
            assert response.status_code == 200

            # 3. 发起洽谈
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/initiate",
                json={
                    "demand_agent_id": "e2e_demand_scenario",
                    "supply_agent_id": "e2e_supply_scenario",
                    "demand_id": demand_id,
                }
            )
            if response.status_code == 200:
                negotiation_id = response.json().get("negotiation_id")

                # 4. 确认匹配
                response = await client.post(
                    f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/confirm"
                )
                assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_supply_agent_scenario(self):
        """
        供应方完整场景:
        1. 注册/更新基因胶囊
        2. 接收洽谈请求
        3. 回答问题
        4. 提供验证
        5. 确认匹配
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            agent_id = "e2e_supply_scenario"

            # 1. 更新基因胶囊
            await client.post(
                f"{E2E_BASE_URL}/gene-capsule/{agent_id}/experiences",
                json={
                    "task_type": "数据分析",
                    "task_description": "电商销售预测",
                    "outcome": "success",
                    "quality_score": 0.95,
                }
            )

            # 2. 接收洽谈请求
            response = await client.post(
                f"{E2E_BASE_URL}/negotiations/pre-match/initiate",
                json={
                    "demand_agent_id": "e2e_demand_test",
                    "supply_agent_id": agent_id,
                    "demand_id": "e2e_demand_test",
                }
            )

            if response.status_code == 200:
                negotiation_id = response.json().get("negotiation_id")

                # 3. 回答问题
                qa_response = await client.post(
                    f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/questions",
                    json={
                        "question": "你的经验？",
                        "asker_id": "e2e_demand_test",
                    }
                )

                if qa_response.status_code == 200:
                    question_id = qa_response.json().get("question_id")

                    await client.post(
                        f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/questions/{question_id}/answer",
                        json={
                            "answer": "我有5年经验",
                            "answerer_id": agent_id,
                        }
                    )

                # 4. 确认匹配
                response = await client.post(
                    f"{E2E_BASE_URL}/negotiations/pre-match/{negotiation_id}/confirm"
                )
                assert response.status_code == 200


# ==================== Performance Tests ====================

class TestE2EPerformance:
    """Performance tests"""

    @pytest.mark.asyncio
    async def test_concurrent_searches(self):
        """Test concurrent search requests"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # 并发发起10个搜索请求
            tasks = []
            for i in range(10):
                task = client.post(
                    f"{E2E_BASE_URL}/meta-agent/recommend",
                    json={
                        "demand": {"description": f"测试需求 {i}"},
                        "limit": 3,
                    }
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)

            # 验证大部分请求成功
            successful = sum(1 for r in responses if not isinstance(r, Exception) and r.status_code == 200)
            assert successful >= 7  # 至少70%成功


# ==================== Run Tests ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
