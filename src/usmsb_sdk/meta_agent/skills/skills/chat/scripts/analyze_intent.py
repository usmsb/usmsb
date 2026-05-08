#!/usr/bin/env python3
"""
分析用户消息意图

输入: 用户消息
输出: 意图类型和置信度
"""

import sys
import json


def analyze_intent(message: str) -> dict:
    """分析用户消息的意图"""
    message = message.lower().strip()

    # 简单规则匹配
    if any(kw in message for kw in ["什么", "怎么", "如何", "为什么", "who", "what", "how", "why"]):
        intent = "question"
    elif any(kw in message for kw in ["帮我", "请", "能不能", "可以帮我"]):
        intent = "request"
    elif any(kw in message for kw in ["谢谢", "感谢", "好的", "ok", "yes"]):
        intent = "acknowledgment"
    elif any(kw in message for kw in ["?", "？"]):
        intent = "question"
    else:
        intent = "chat"

    return {
        "intent": intent,
        "confidence": 0.8,
        "message_length": len(message),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        message = sys.argv[1]
    else:
        message = input("请输入消息: ")

    result = analyze_intent(message)
    print(json.dumps(result, ensure_ascii=False, indent=2))
