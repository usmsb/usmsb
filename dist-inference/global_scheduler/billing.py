"""
Vibe Billing Engine
"""

from dataclasses import dataclass
from typing import Dict


@dataclass
class UserBalance:
    """User balance information"""
    user_id: str
    vibe_balance: float = 1000.0  # Vibe balance (default for testing)
    owed_vibe: float = 0.0  # Owed amount


class BillingEngine:
    """
    Vibe Billing Engine

    Billing rules:
    - GPU card time: 0.001 Vibe/second/GPU
    - Token: 0.001 Vibe/1K tokens
    - Platform fee: 30%
    """

    GPU_COST_PER_SECOND = 0.001  # Vibe/second/GPU
    TOKEN_COST_PER_1K = 0.001  # Vibe/1K tokens
    PLATFORM_FEE_RATIO = 0.30  # Platform takes 30%

    def __init__(self):
        self.balances: Dict[str, UserBalance] = {}

    def get_balance(self, user_id: str) -> float:
        """Get user balance (after deducting owed)"""
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)
        balance = self.balances[user_id]
        return balance.vibe_balance - balance.owed_vibe

    def get_owed(self, user_id: str) -> float:
        """Get user owed amount"""
        if user_id not in self.balances:
            return 0.0
        return self.balances[user_id].owed_vibe

    def estimate_cost(self, model_name: str, max_tokens: int) -> float:
        """
        Estimate cost

        Simplified: assumes 500 input tokens
        """
        estimated_tokens = 500 + max_tokens
        token_cost = (estimated_tokens / 1000) * self.TOKEN_COST_PER_1K

        # GPU card time estimate (simplified: assume 1 second)
        gpu_cost = 1.0 * self.GPU_COST_PER_SECOND

        return token_cost + gpu_cost

    def calculate_cost(
        self,
        gpu_seconds: float,
        prompt_tokens: int,
        completion_tokens: int,
        gpu_count: int = 1
    ) -> float:
        """
        Calculate actual cost

        Args:
            gpu_seconds: GPU usage in seconds
            prompt_tokens: Input token count
            completion_tokens: Output token count
            gpu_count: Number of GPU cards used
        """
        gpu_cost = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        total_tokens = prompt_tokens + completion_tokens
        token_cost = (total_tokens / 1000) * self.TOKEN_COST_PER_1K

        total = gpu_cost + token_cost
        print(f"[Billing] Cost calculation: GPU({gpu_seconds}s x {gpu_count})={gpu_cost:.6f}, "
              f"Token({total_tokens})={token_cost:.6f}, Total={total:.6f} Vibe")

        return total

    def charge(self, user_id: str, cost_vibe: float) -> Dict[str, float]:
        """
        Charge user

        Returns:
            {"charged": xxx, "remaining": yyy, "new_owed": zzz}
        """
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)

        balance = self.balances[user_id]
        total_cost = cost_vibe + balance.owed_vibe

        if balance.vibe_balance >= total_cost:
            # Enough to pay
            balance.vibe_balance -= total_cost
            balance.owed_vibe = 0.0
        else:
            # Pay with debt
            balance.owed_vibe = total_cost - balance.vibe_balance
            balance.vibe_balance = 0.0

        print(f"[Billing] Charged {cost_vibe:.6f} Vibe from {user_id}, "
              f"remaining: {balance.vibe_balance:.6f}, owed: {balance.owed_vibe:.6f}")

        return {
            "charged": cost_vibe,
            "remaining": balance.vibe_balance,
            "new_owed": balance.owed_vibe
        }

    def calculate_node_reward(self, gpu_seconds: float, gpu_count: int = 1) -> float:
        """
        Calculate GPU holder reward (after 30% platform fee)
        """
        gross = gpu_seconds * gpu_count * self.GPU_COST_PER_SECOND
        net = gross * (1 - self.PLATFORM_FEE_RATIO)
        return net

    def deposit(self, user_id: str, amount: float):
        """Deposit Vibe"""
        if user_id not in self.balances:
            self.balances[user_id] = UserBalance(user_id=user_id)
        self.balances[user_id].vibe_balance += amount
        print(f"[Billing] Deposited {amount} Vibe to {user_id}, "
              f"new balance: {self.balances[user_id].vibe_balance:.6f}")
