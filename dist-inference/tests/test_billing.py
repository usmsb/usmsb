"""
Unit tests for Billing Engine
"""

import pytest
from global_scheduler.billing import BillingEngine, UserBalance


class TestBillingEngine:
    """Test cases for BillingEngine"""

    def setup_method(self):
        """Setup for each test method"""
        self.engine = BillingEngine()

    def test_get_balance_new_user(self):
        """Test getting balance for a new user"""
        balance = self.engine.get_balance("new_user")
        assert balance == 1000.0  # Default balance

    def test_get_balance_existing_user(self):
        """Test getting balance for an existing user"""
        self.engine.deposit("existing_user", 500.0)
        balance = self.engine.get_balance("existing_user")
        assert balance == 1500.0

    def test_deposit(self):
        """Test depositing Vibe"""
        self.engine.deposit("user1", 100.0)
        result = self.engine.get_balance("user1")
        assert result == 1100.0

    def test_charge_success(self):
        """Test successful charge"""
        user_id = "user_charge"
        initial_balance = self.engine.get_balance(user_id)
        charge_amount = 10.0

        result = self.engine.charge(user_id, charge_amount)

        assert result["charged"] == charge_amount
        expected_remaining = initial_balance - charge_amount
        assert abs(result["remaining"] - expected_remaining) < 0.001

    def test_charge_with_owed(self):
        """Test charge when user has existing debt"""
        user_id = "user_owed"

        # First, create a debt scenario by depositing then charging beyond balance
        self.engine.deposit(user_id, 10.0)
        # Set owed manually via get_balance to initialize
        self.engine.charge(user_id, 50.0)  # This creates owed

        # Reset balance to 0 to simulate the debt scenario
        self.engine.balances[user_id].vibe_balance = 0.0

        # Now charge when balance is 0 but there's owed
        result = self.engine.charge(user_id, 10.0)

        # Should use the existing owed + new charge
        assert result["new_owed"] >= 10.0

    def test_charge_partial_payment(self):
        """Test charge when balance is insufficient"""
        user_id = "user_partial"

        # Set a small balance directly
        self.engine.balances[user_id] = UserBalance(user_id=user_id, vibe_balance=5.0, owed_vibe=0.0)

        # Charge more than balance
        result = self.engine.charge(user_id, 10.0)

        # Should use all balance and create debt
        assert result["remaining"] == 0.0
        assert result["new_owed"] == 5.0

    def test_estimate_cost(self):
        """Test cost estimation"""
        cost = self.engine.estimate_cost("Qwen/Qwen2.5-7B-Instruct", 1000)
        # Expected: (500 + 1000) / 1000 * 0.001 (token) + 1 * 0.001 (gpu) = 0.0015 + 0.001 = 0.0025
        assert cost > 0

    def test_calculate_cost(self):
        """Test actual cost calculation"""
        cost = self.engine.calculate_cost(
            gpu_seconds=5.0,
            prompt_tokens=100,
            completion_tokens=50,
            gpu_count=1
        )
        # GPU: 5.0 * 1 * 0.001 = 0.005
        # Token: 150 / 1000 * 0.001 = 0.00015
        # Total: 0.00515
        expected = 0.00515
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_multi_gpu(self):
        """Test cost calculation with multiple GPUs"""
        cost = self.engine.calculate_cost(
            gpu_seconds=5.0,
            prompt_tokens=100,
            completion_tokens=50,
            gpu_count=4
        )
        # GPU: 5.0 * 4 * 0.001 = 0.02
        # Token: 150 / 1000 * 0.001 = 0.00015
        # Total: 0.02015
        expected = 0.02015
        assert abs(cost - expected) < 0.0001

    def test_calculate_node_reward(self):
        """Test GPU holder reward calculation"""
        reward = self.engine.calculate_node_reward(gpu_seconds=100.0, gpu_count=1)
        # Gross: 100 * 0.001 = 0.1
        # Net (after 30% fee): 0.1 * 0.7 = 0.07
        expected = 0.07
        assert abs(reward - expected) < 0.0001

    def test_calculate_node_reward_multi_gpu(self):
        """Test GPU holder reward with multiple GPUs"""
        reward = self.engine.calculate_node_reward(gpu_seconds=100.0, gpu_count=4)
        # Gross: 100 * 4 * 0.001 = 0.4
        # Net: 0.4 * 0.7 = 0.28
        expected = 0.28
        assert abs(reward - expected) < 0.0001

    def test_get_owed(self):
        """Test getting owed amount"""
        user_id = "user_get_owed"
        # Initialize via get_balance
        self.engine.get_balance(user_id)
        assert self.engine.get_owed(user_id) == 0.0

        # Create some debt by charging beyond balance
        self.engine.balances[user_id].vibe_balance = 10.0
        self.engine.charge(user_id, 50.0)
        assert self.engine.get_owed(user_id) == 40.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
