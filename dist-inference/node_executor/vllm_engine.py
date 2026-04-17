"""
vLLM Engine Wrapper
"""

import os
from typing import List, Dict, Optional, Any
import asyncio
from threading import Thread
import time

try:
    from vllm import LLM, SamplingParams
    VLLM_AVAILABLE = True
except ImportError:
    VLLM_AVAILABLE = False
    LLM = None
    SamplingParams = None


# VRAM estimation table (GB)
VRAM_ESTIMATES = {
    "Qwen/Qwen2.5-7B-Instruct": 14,
    "Qwen/Qwen2.5-14B-Instruct": 28,
    "Qwen/Qwen2.5-72B-Instruct": 145,
    "THUDM/CogVideoX-5b": 48,
    "tencent/HunyuanVideo": 80,
}


def estimate_vram(model_name: str) -> int:
    """Estimate model VRAM requirement"""
    return VRAM_ESTIMATES.get(model_name, 20)


class VLLMEngine:
    """
    vLLM Engine Wrapper

    Provides:
    - Model loading/unloading
    - Sync/async inference
    """

    def __init__(
        self,
        tensor_parallel_size: int = 1,
        gpu_memory_utilization: float = 0.9
    ):
        self.tensor_parallel_size = tensor_parallel_size
        self.gpu_memory_utilization = gpu_memory_utilization
        self.llm = None
        self.loaded_model_name: Optional[str] = None
        self._loading = False

    def is_available(self) -> bool:
        """Check if vLLM is available"""
        return VLLM_AVAILABLE

    def get_supported_models(self) -> List[str]:
        """Get list of supported models"""
        return list(VRAM_ESTIMATES.keys())

    def load_model(self, model_name: str):
        """
        Load model (mock mode when vLLM not available)
        """
        if self._loading:
            raise RuntimeError("Model loading in progress")

        if self.loaded_model_name == model_name:
            print(f"[VLLM] Model already loaded: {model_name}")
            return

        if not VLLM_AVAILABLE:
            # Mock mode: just mark as loaded
            print(f"[VLLM] Mock mode: marking {model_name} as loaded (vLLM not available)")
            self.loaded_model_name = model_name
            return

        print(f"[VLLM] Loading model: {model_name}")

        self._loading = True
        try:
            # Resolve model path
            model_path = self._resolve_model_path(model_name)

            self.llm = LLM(
                model=model_path,
                tensor_parallel_size=self.tensor_parallel_size,
                gpu_memory_utilization=self.gpu_memory_utilization,
                trust_remote_code=True,
                enforce_eager=False  # Allow CUDA graph
            )
            self.loaded_model_name = model_name
            print(f"[VLLM] Model loaded: {model_name}")

        finally:
            self._loading = False

    def _resolve_model_path(self, model_name: str) -> str:
        """Resolve model path"""
        # HuggingFace model
        return model_name

    def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Synchronous generation (mock mode when vLLM not available)
        """

        # Mock mode: return fake response when vLLM not available
        if not self.llm:
            content = f"[Mock] Processed: {messages[-1].get('content', '')}"
            prompt_tokens = 10
            completion_tokens = 20
            return {
                "content": content,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": prompt_tokens + completion_tokens
                }
            }

        # Convert messages to prompt
        prompt = self._messages_to_prompt(messages)

        sampling_params = SamplingParams(
            temperature=temperature,
            max_tokens=max_tokens,
            stop=None
        )

        outputs = self.llm.generate([prompt], sampling_params)
        output = outputs[0]

        return {
            "content": output.outputs[0].text,
            "usage": {
                "prompt_tokens": len(output.prompt_token_ids),
                "completion_tokens": len(output.outputs[0].token_ids),
                "total_tokens": len(output.prompt_token_ids) + len(output.outputs[0].token_ids)
            }
        }

    async def generate_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        Async generation (execute sync vLLM call in thread pool)
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.generate(messages, temperature, max_tokens)
        )

    def _messages_to_prompt(self, messages: List[Dict[str, str]]) -> str:
        """
        Convert OpenAI messages format to prompt

        Simplified implementation, should use tokenizer in production
        """
        prompt = ""
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "system":
                prompt += f"System: {content}\n"
            elif role == "user":
                prompt += f"User: {content}\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n"
        prompt += "Assistant: "
        return prompt
