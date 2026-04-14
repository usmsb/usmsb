# -*- coding: utf-8 -*-
"""
LLM Client - 统一 LLM 客户端

支持多种 LLM 提供者：
- OpenAI (GPT-4, GPT-3.5)
- Anthropic (Claude)
- MiniMax (中文优化)

使用方式：
    client = LLMClient()
    
    # OpenAI
    result = client.complete("Hello", model="gpt-4")
    
    # MiniMax
    result = client.complete("你好", model="MiniMax")
"""

import os
import json
import requests
from typing import Any


class LLMClient:
    """
    统一 LLM 客户端
    
    支持：
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - MiniMax (GLM 系列)
    """
    
    def __init__(
        self,
        provider: str = "auto",
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        """
        初始化 LLM 客户端
        
        Args:
            provider: 提供者 ("openai", "anthropic", "minimax", "auto")
            api_key: API 密钥（默认从环境变量读取）
            base_url: 自定义 API 地址
        """
        self.provider = provider
        
        # API 密钥
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self.minimax_key = os.environ.get("MINIMAX_API_KEY")
        self.anthropic_key = os.environ.get("ANTHROPIC_API_KEY")
        
        # Base URLs
        self.base_urls = {
            "openai": base_url or "https://api.openai.com/v1",
            "anthropic": base_url or "https://api.anthropic.com/v1",
            "minimax": base_url or "https://api.minimax.chat/v1",
        }
    
    def complete(
        self,
        prompt: str,
        model: str | None = None,
        max_tokens: int = 1024,
        temperature: float = 0.7,
        system_prompt: str | None = None,
        **kwargs
    ) -> str:
        """
        生成文本补全
        
        Args:
            prompt: 用户提示
            model: 模型名称（自动选择最佳）
            max_tokens: 最大 token 数
            temperature: 温度（创造性）
            system_prompt: 系统提示
            
        Returns:
            str: 生成的文本
        """
        # 自动选择模型
        if model is None:
            model = self._select_model(prompt)
        
        # 根据模型选择提供者
        provider = self._get_provider(model)
        
        if provider == "openai":
            return self._openai_complete(prompt, model, max_tokens, temperature, system_prompt, **kwargs)
        elif provider == "anthropic":
            return self._anthropic_complete(prompt, model, max_tokens, temperature, system_prompt, **kwargs)
        elif provider == "minimax":
            return self._minimax_complete(prompt, model, max_tokens, temperature, system_prompt, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _select_model(self, prompt: str) -> str:
        """根据提示内容选择最佳模型"""
        # 如果有 MiniMax API Key 且是中文，使用 MiniMax
        if self.minimax_key and any(c >= '\u4e00' and c <= '\u9fff' for c in prompt):
            return "MiniMax"
        
        # 如果有 OpenAI API Key，使用 GPT-4
        if self.api_key:
            return "gpt-4"
        
        # 默认使用 MiniMax（如果有 key）
        if self.minimax_key:
            return "MiniMax"
        
        # 默认 GPT-3.5
        return "gpt-3.5-turbo"
    
    def _get_provider(self, model: str) -> str:
        """获取模型对应的提供者"""
        model_lower = model.lower()
        
        if "gpt" in model_lower or "openai" in model_lower:
            return "openai"
        elif "claude" in model_lower or "anthropic" in model_lower:
            return "anthropic"
        elif "minimax" in model_lower or "glm" in model_lower:
            return "minimax"
        else:
            return "openai"  # 默认
    
    def _openai_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
        **kwargs
    ) -> str:
        """OpenAI API 调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model if model else "gpt-3.5-turbo",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['openai']}/chat/completions",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[LLMClient] OpenAI API error: {e}")
            return f"[OpenAI Error: {e}]"
    
    def _anthropic_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
        **kwargs
    ) -> str:
        """Anthropic API 调用"""
        headers = {
            "x-api-key": self.anthropic_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "user", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        data = {
            "model": model if model else "claude-3-opus-20240229",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['anthropic']}/messages",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result["content"][0]["text"]
        except Exception as e:
            print(f"[LLMClient] Anthropic API error: {e}")
            return f"[Anthropic Error: {e}]"
    
    def _minimax_complete(
        self,
        prompt: str,
        model: str,
        max_tokens: int,
        temperature: float,
        system_prompt: str | None,
        **kwargs
    ) -> str:
        """MiniMax API 调用
        
        MiniMax API:
        - URL: https://api.minimax.chat/v1/text/chatcompletion_pro
        - Model: MiniMax-Text-01
        - Supports Chinese natively
        """
        if not self.minimax_key:
            # 如果没有 MiniMax key，回退到 OpenAI
            if self.api_key:
                return self._openai_complete(prompt, "gpt-3.5-turbo", max_tokens, temperature, system_prompt, **kwargs)
            return "[No MiniMax API Key]"
        
        headers = {
            "Authorization": f"Bearer {self.minimax_key}",
            "Content-Type": "application/json",
        }
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"sender_type": "BOT", "text": system_prompt})
        messages.append({"sender_type": "USER", "text": prompt})
        
        data = {
            "model": "MiniMax-Text-01",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            **kwargs
        }
        
        try:
            response = requests.post(
                f"{self.base_urls['minimax']}/text/chatcompletion_pro",
                headers=headers,
                json=data,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            
            # MiniMax 返回格式
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["messages"][-1]["text"]
            elif "chatcompletion" in result:
                return result["chatcompletion"]["choices"][-1]["messages"][-1]["text"]
            else:
                return str(result)
                
        except Exception as e:
            print(f"[LLMClient] MiniMax API error: {e}")
            # 回退到其他 provider
            if self.api_key:
                return self._openai_complete(prompt, "gpt-3.5-turbo", max_tokens, temperature, system_prompt, **kwargs)
            return f"[MiniMax Error: {e}]"
    
    def __repr__(self) -> str:
        return f"LLMClient(provider={self.provider or 'auto'})"
