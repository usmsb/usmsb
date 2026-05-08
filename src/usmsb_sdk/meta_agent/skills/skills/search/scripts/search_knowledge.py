#!/usr/bin/env python3
"""
搜索内部知识库

输入: 搜索关键词
输出: 匹配的文档片段
"""

import sys
import json


def search_knowledge(query: str, knowledge_base: list = None) -> dict:
    """搜索内部知识库"""
    if knowledge_base is None:
        # 默认知识库（实际应从上下文获取）
        knowledge_base = [
            {"title": "USMSB SDK 文档", "content": "USMSB 是一个多层级 Agent 系统..."},
            {"title": "MetaAgent 指南", "content": "MetaAgent 是 L5 集体智能层..."},
        ]

    results = []
    query_lower = query.lower()

    for doc in knowledge_base:
        if query_lower in doc["content"].lower() or query_lower in doc["title"].lower():
            results.append(doc)

    return {
        "query": query,
        "results": results,
        "total": len(results),
    }


if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = input("请输入搜索关键词: ")

    result = search_knowledge(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
