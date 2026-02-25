"""
Meta Agent 精准匹配系统 - E2E 测试

测试完整的用户场景：
1. 完整的面试对话流程
2. 展示 → 推荐 → 洽谈流程
3. 咨询 → 接受机会 → 匹配流程
4. 完整的 Agent 注册到匹配流程
"""

import pytest
import asyncio
import httpx
from datetime import datetime
from unittest.mock import patch
import json
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== E2E 测试配置 ====================

E2E_BASE_URL = os.getenv("E2E_BASE_URL", "http://127.0.0.1:8000")
E2E_TIMEOUT = float(os.getenv("E2E_TIMEOUT", "30.0"))


# ==================== E2E 测试类 ====================

class TestE2EMetaAgentInterview:
    """E2E tests for Meta Agent interview flow"""

    @pytest.mark.asyncio
    async def test_full_interview_flow(self):
        """
        测试完整的面试对话流程:
        1. 发起对话
        2. 多轮消息交互
        3. 提取能力画像
        4. 验证画像内容
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 发起对话
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": "e2e_agent_001",
                    "conversation_type": "introduction"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            conversation_id = data["conversation_id"]
            assert conversation_id is not None
            assert data["opening_message"] is not None

            # Step 2: 第一轮消息
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations/{conversation_id}/messages",
                json={"message": "我是一名数据分析专家，擅长机器学习和数据可视化。"}
            )
            assert response.status_code == 200
            assert "response" in response.json()

            # Step 3: 第二轮消息
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations/{conversation_id}/messages",
                json={"message": "我有5年的电商数据分析经验，完成过20+个预测项目。"}
            )
            assert response.status_code == 200

            # Step 4: 获取能力画像
            response = await client.get(
                f"{E2E_BASE_URL}/meta-agent/profiles/e2e_agent_001",
                params={"conversation_id": conversation_id}
            )
            assert response.status_code == 200
            profile = response.json()["profile"]
            assert profile is not None
            assert "core_capabilities" in profile

    @pytest.mark.asyncio
    async def test_showcase_recommend_flow(self):
        """
        测试展示到推荐的完整流程:
        1. Agent 分享展示
        2. 发起推荐请求
        3. 验证推荐结果
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 分享展示
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/showcase",
                json={
                    "agent_id": "e2e_agent_showcase",
                    "showcase": {
                        "type": "experience",
                        "title": "电商销售预测系统",
                        "description": "开发了一个电商销售预测系统，准确率达到92%",
                        "skills": ["数据分析", "机器学习", "Python"],
                        "outcome": "success",
                        "quality_score": 0.92
                    }
                }
            )
            assert response.status_code == 200

            # Step 2: 发起推荐请求
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/recommend",
                json={
                    "demand": {
                        "title": "电商预测项目",
                        "description": "需要一个电商销售预测系统",
                        "required_skills": ["数据分析", "机器学习"],
                        "category": "data_analysis"
                    },
                    "limit": 5
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "recommendations" in data


class TestE2EConsultationFlow:
    """E2E tests for consultation flow"""

    @pytest.mark.asyncio
    async def test_consultation_flow(self):
        """
        测试咨询流程:
        1. 发起咨询
        2. 验证响应
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/consult",
                json={
                    "agent_id": "e2e_agent_consult",
                    "question": "我应该如何提升我的可见性？"
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "response" in data
            assert len(data["response"]) > 0


class TestE2EOpportunityNotification:
    """E2E tests for opportunity notification"""

    @pytest.mark.asyncio
    async def test_opportunity_notification_flow(self):
        """
        测试机会通知流程:
        1. 先创建 agent 画像
        2. 发送机会通知
        3. 验证通知结果
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 创建画像（通过对话）
            await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": "e2e_agent_opportunity",
                    "conversation_type": "introduction"
                }
            )

            # Step 2: 发送机会通知
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/opportunities/notify",
                json={
                    "agent_id": "e2e_agent_opportunity",
                    "opportunity": {
                        "opportunity_id": "e2e_opp_001",
                        "type": "demand",
                        "title": "数据分析项目",
                        "description": "需要数据分析服务",
                        "counterpart_id": "client_001",
                        "counterpart_name": "Test Client",
                        "match_score": 0.85,
                        "required_capabilities": ["数据分析"]
                    }
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestE2EGeneCapsuleMatching:
    """E2E tests for Gene Capsule matching"""

    @pytest.mark.asyncio
    async def test_gene_capsule_matching_flow(self):
        """
        测试基因胶囊匹配流程:
        1. 添加基因胶囊经验
        2. 发起匹配请求
        3. 验证匹配结果
        """
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # Step 1: 添加基因胶囊经验
            response = await client.post(
                f"{E2E_BASE_URL}/gene-capsule/e2e_agent_genecap/experiences",
                json={
                    "task_type": "数据分析",
                    "task_description": "电商销售预测项目",
                    "techniques_used": ["机器学习", "时间序列分析"],
                    "outcome": "success",
                    "quality_score": 0.92,
                    "visibility": "public"
                }
            )

            if response.status_code not in [200, 201]:
                # 基因胶囊服务可能不可用，跳过测试
                pytest.skip("Gene Capsule service not available")
                return

            # Step 2: 发起匹配请求
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/match/gene-capsule",
                json={
                    "demand_description": "需要电商销售预测",
                    "required_skills": ["数据分析", "机器学习"],
                    "category": "data_analysis",
                    "limit": 5
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


class TestE2EErrorHandling:
    """E2E tests for error handling"""

    @pytest.mark.asyncio
    async def test_invalid_conversation_type(self):
        """Test invalid conversation type"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": "e2e_agent_error",
                    "conversation_type": "invalid_type"
                }
            )
            # 应该返回200（因为会fallback到introduction）或400
            assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_missing_agent_id(self):
        """Test missing agent_id"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={"conversation_type": "introduction"}
            )
            assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_nonexistent_conversation(self):
        """Test accessing nonexistent conversation"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations/nonexistent_id/messages",
                json={"message": "test"}
            )
            # 应该返回404或500
            assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_empty_message(self):
        """Test sending empty message"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # 先创建对话
            create_response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": "e2e_agent_empty",
                    "conversation_type": "introduction"
                }
            )
            conv_id = create_response.json()["conversation_id"]

            # 发送空消息
            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations/{conv_id}/messages",
                json={"message": ""}
            )
            # 应该接受（空消息也是有效消息）或拒绝
            assert response.status_code in [200, 400, 422]


class TestE2EPerformance:
    """E2E performance tests"""

    @pytest.mark.asyncio
    async def test_concurrent_conversations(self):
        """Test creating multiple conversations concurrently"""
        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            # 并发创建10个对话
            tasks = []
            for i in range(10):
                task = client.post(
                    f"{E2E_BASE_URL}/meta-agent/conversations",
                    json={
                        "agent_id": f"e2e_concurrent_{i}",
                        "conversation_type": "introduction"
                    }
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks)

            # 验证所有请求都成功
            for response in responses:
                assert response.status_code == 200
                assert response.json()["success"] is True

    @pytest.mark.asyncio
    async def test_response_time(self):
        """Test API response time"""
        import time

        async with httpx.AsyncClient(timeout=E2E_TIMEOUT) as client:
            start_time = time.time()

            response = await client.post(
                f"{E2E_BASE_URL}/meta-agent/conversations",
                json={
                    "agent_id": "e2e_timing",
                    "conversation_type": "introduction"
                }
            )

            elapsed = time.time() - start_time

            assert response.status_code == 200
            # 响应时间应该小于5秒
            assert elapsed < 5.0, f"Response took {elapsed} seconds"


# ==================== 测试运行器 ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
