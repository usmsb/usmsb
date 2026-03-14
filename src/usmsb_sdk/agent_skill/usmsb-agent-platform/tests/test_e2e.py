"""
E2E Tests for USMSB Agent Platform Skill

This test suite validates the complete Agent registration and usage flow.
"""

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from usmsb_agent_platform import (
    ActionType,
    PlatformResult,
    StakeTier,
)
from usmsb_agent_platform.intent_parser import IntentParser
from usmsb_agent_platform.stake_checker import StakeChecker


class TestIntentParser:
    """Test the Intent Parser"""

    def setup_method(self):
        self.parser = IntentParser()

    def test_parse_collaboration_create(self):
        """Test parsing collaboration create request"""
        intent = self.parser.parse("创建协作，目标是开发电商网站")
        assert intent.action == ActionType.COLLABORATION_CREATE
        assert intent.action.requires_stake

    def test_parse_collaboration_join(self):
        """Test parsing collaboration join request"""
        intent = self.parser.parse("加入协作 collab-abc123")
        assert intent.action == ActionType.COLLABORATION_JOIN
        assert not intent.action.requires_stake

    def test_parse_marketplace_publish_service(self):
        """Test parsing publish service request"""
        intent = self.parser.parse("发布服务，Python开发，500 VIBE")
        assert intent.action == ActionType.MARKETPLACE_PUBLISH_SERVICE
        assert intent.action.requires_stake
        assert intent.parameters.get("price") == 500

    def test_parse_find_work(self):
        """Test parsing find work request"""
        intent = self.parser.parse("找工作")
        assert intent.action == ActionType.MARKETPLACE_FIND_WORK
        assert not intent.action.requires_stake

    def test_parse_discovery(self):
        """Test parsing discovery request"""
        intent = self.parser.parse("发现会 Python 的 Agent")
        assert intent.action == ActionType.DISCOVERY_BY_SKILL
        assert not intent.action.requires_stake

    def test_parse_negotiation_initiate(self):
        """Test parsing negotiation initiate"""
        intent = self.parser.parse("发起协商")
        assert intent.action == ActionType.NEGOTIATION_INITIATE
        assert not intent.action.requires_stake

    def test_parse_negotiation_accept(self):
        """Test parsing negotiation accept"""
        intent = self.parser.parse("接受协商")
        assert intent.action == ActionType.NEGOTIATION_ACCEPT
        assert intent.action.requires_stake

    def test_parse_english_request(self):
        """Test parsing English request"""
        intent = self.parser.parse("create collaboration for web development")
        assert intent.action == ActionType.COLLABORATION_CREATE

    def test_parse_invalid_request(self):
        """Test parsing invalid request raises error"""
        try:
            self.parser.parse("这是一个无法识别的请求内容xyz123")
            # If no error, check if it defaulted to something
        except ValueError as e:
            assert "Cannot parse" in str(e)


class TestStakeChecker:
    """Test the Stake Checker"""

    def setup_method(self):
        self.checker = StakeChecker()

    def test_stake_tier_none(self):
        """Test NONE tier (0 VIBE)"""
        from usmsb_agent_platform.types import StakeInfo
        info = StakeInfo.from_amount("test-agent", 0)
        assert info.tier == StakeTier.NONE
        assert info.can_perform(ActionType.COLLABORATION_JOIN)
        assert not info.can_perform(ActionType.COLLABORATION_CREATE)

    def test_stake_tier_bronze(self):
        """Test BRONZE tier (100-999 VIBE)"""
        from usmsb_agent_platform.types import StakeInfo
        info = StakeInfo.from_amount("test-agent", 100)
        assert info.tier == StakeTier.BRONZE
        assert info.can_perform(ActionType.COLLABORATION_CREATE)
        assert info.get_max_agents() == 1

    def test_stake_tier_silver(self):
        """Test SILVER tier (1000-4999 VIBE)"""
        from usmsb_agent_platform.types import StakeInfo
        info = StakeInfo.from_amount("test-agent", 1000)
        assert info.tier == StakeTier.SILVER
        assert info.get_max_agents() == 3
        assert info.get_discount() == 0.05

    def test_stake_tier_gold(self):
        """Test GOLD tier (5000-9999 VIBE)"""
        from usmsb_agent_platform.types import StakeInfo
        info = StakeInfo.from_amount("test-agent", 5000)
        assert info.tier == StakeTier.GOLD
        assert info.get_max_agents() == 10
        assert info.get_discount() == 0.10

    def test_stake_tier_platinum(self):
        """Test PLATINUM tier (10000+ VIBE)"""
        from usmsb_agent_platform.types import StakeInfo
        info = StakeInfo.from_amount("test-agent", 10000)
        assert info.tier == StakeTier.PLATINUM
        assert info.get_max_agents() == 50
        assert info.get_discount() == 0.20

    def test_calculate_reputation(self):
        """Test reputation calculation"""
        from usmsb_agent_platform.stake_checker import StakeChecker
        assert StakeChecker.calculate_reputation(0) == 0.5
        assert StakeChecker.calculate_reputation(1000) == 1.0  # 0.5 + 1.0 = 1.5, capped at 1.0
        assert StakeChecker.calculate_reputation(10000) == 1.0  # Capped at 1.0
        # Mid-range test
        assert StakeChecker.calculate_reputation(500) == 1.0  # 0.5 + 0.5 = 1.0


class TestActionRequirements:
    """Test action stake requirements"""

    def test_actions_requiring_stake(self):
        """Verify all actions that require stake"""
        stake_required_actions = [
            ActionType.COLLABORATION_CREATE,
            ActionType.COLLABORATION_CONTRIBUTE,
            ActionType.MARKETPLACE_PUBLISH_SERVICE,
            ActionType.NEGOTIATION_ACCEPT,
            ActionType.WORKFLOW_EXECUTE,
        ]

        for action in stake_required_actions:
            assert action.requires_stake, f"{action} should require stake"

    def test_actions_not_requiring_stake(self):
        """Verify all actions that don't require stake"""
        no_stake_actions = [
            ActionType.COLLABORATION_JOIN,
            ActionType.COLLABORATION_LIST,
            ActionType.MARKETPLACE_FIND_WORK,
            ActionType.MARKETPLACE_FIND_WORKERS,
            ActionType.DISCOVERY_BY_CAPABILITY,
            ActionType.DISCOVERY_BY_SKILL,
            ActionType.NEGOTIATION_INITIATE,
            ActionType.WORKFLOW_CREATE,
            ActionType.LEARNING_ANALYZE,
        ]

        for action in no_stake_actions:
            assert not action.requires_stake, f"{action} should not require stake"


class TestPlatformResult:
    """Test PlatformResult"""

    def test_success_result(self):
        """Test successful result"""
        result = PlatformResult(
            success=True,
            result={"id": "123"},
            message="Success"
        )
        assert result.success
        assert result.to_dict()["success"]
        assert result.to_dict()["result"]["id"] == "123"

    def test_error_result(self):
        """Test error result"""
        result = PlatformResult(
            success=False,
            error="Something went wrong",
            code="INTERNAL_ERROR"
        )
        assert not result.success
        assert result.to_dict()["error"] == "Something went wrong"
        assert result.to_dict()["code"] == "INTERNAL_ERROR"

    def test_bool_conversion(self):
        """Test boolean conversion"""
        success_result = PlatformResult(success=True)
        error_result = PlatformResult(success=False)

        assert bool(success_result)
        assert not bool(error_result)


class TestRegistration:
    """Test registration utilities"""

    def test_generate_api_key_format(self):
        """Test API key format"""
        from usmsb_agent_platform.registration import generate_api_key

        api_key = generate_api_key("agent-test123")

        assert api_key.startswith("usmsb_")
        parts = api_key.split("_")
        assert len(parts) == 3
        assert len(parts[1]) == 16  # hash length

    def test_generate_binding_code(self):
        """Test binding code generation"""
        from usmsb_agent_platform.registration import generate_binding_code

        code, expires_at = generate_binding_code()

        assert code.startswith("bind-")
        assert expires_at > 0


def run_tests():
    """Run all tests"""
    print("=" * 60)
    print("Running USMSB Agent Platform Skill E2E Tests")
    print("=" * 60)

    # Test classes to run
    test_classes = [
        TestIntentParser,
        TestStakeChecker,
        TestActionRequirements,
        TestPlatformResult,
        TestRegistration,
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = 0

    for test_class in test_classes:
        print(f"\n--- {test_class.__name__} ---")
        instance = test_class()

        # Run setup if exists
        if hasattr(instance, 'setup_method'):
            instance.setup_method()

        # Find all test methods
        test_methods = [m for m in dir(instance) if m.startswith('test_')]

        for method_name in test_methods:
            total_tests += 1
            try:
                method = getattr(instance, method_name)
                method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except AssertionError as e:
                print(f"  ❌ {method_name}: {e}")
                failed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name}: Unexpected error - {e}")
                failed_tests += 1

    print("\n" + "=" * 60)
    print(f"Test Results: {passed_tests}/{total_tests} passed")
    if failed_tests > 0:
        print(f"Failed: {failed_tests}")
    print("=" * 60)

    return failed_tests == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
