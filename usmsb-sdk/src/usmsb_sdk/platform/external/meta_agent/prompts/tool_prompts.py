"""
工具提示词 - 动态生成工具使用说明
"""

TOOL_DESCRIPTIONS = {
    "platform": {
        "category": "平台管理",
        "tools": {
            "get_system_status": {
                "description": "获取系统运行状态",
                "usage": "当用户询问系统健康状态、运行情况时使用",
                "params": {},
                "example": "get_system_status()",
            },
            "get_platform_info": {
                "description": "获取平台基本信息",
                "usage": "当用户想了解平台概况时使用",
                "params": {},
                "example": "get_platform_info()",
            },
        },
    },
    "blockchain": {
        "category": "区块链操作",
        "tools": {
            "get_balance": {
                "description": "查询钱包余额",
                "usage": "当用户询问代币余额时使用",
                "params": {"address": "钱包地址"},
                "example": "get_balance(address='0x...')",
            },
            "get_transaction": {
                "description": "查询交易详情",
                "usage": "当用户查询交易状态时使用",
                "params": {"tx_hash": "交易哈希"},
                "example": "get_transaction(tx_hash='0x...')",
            },
            "stake_tokens": {
                "description": "质押代币",
                "usage": "当用户执行质押操作时使用",
                "params": {"amount": "质押数量", "token": "代币类型"},
                "example": "stake_tokens(amount=100, token='VIBE')",
            },
            "vote_proposal": {
                "description": "对提案投票",
                "usage": "当用户参与治理投票时使用",
                "params": {"proposal_id": "提案ID", "support": "是否支持"},
                "example": "vote_proposal(proposal_id=1, support=True)",
            },
        },
    },
    "database": {
        "category": "数据操作",
        "tools": {
            "query_data": {
                "description": "查询数据库",
                "usage": "当用户需要查询结构化数据时使用",
                "params": {"query": "查询语句或条件"},
                "example": "query_data(query='SELECT * FROM agents')",
            },
            "insert_data": {
                "description": "插入数据",
                "usage": "当用户需要保存数据时使用",
                "params": {"table": "表名", "data": "数据字典"},
                "example": "insert_data(table='users', data={'name': 'Alice'})",
            },
        },
    },
    "ipfs": {
        "category": "分布式存储",
        "tools": {
            "upload_to_ipfs": {
                "description": "上传文件到 IPFS",
                "usage": "当用户需要存储文件到 IPFS 时使用",
                "params": {"file_path": "文件路径或内容"},
                "example": "upload_to_ipfs(file_path='/data/file.json')",
            },
            "get_from_ipfs": {
                "description": "从 IPFS 获取内容",
                "usage": "当用户需要获取 IPFS 内容时使用",
                "params": {"cid": "内容标识符"},
                "example": "get_from_ipfs(cid='Qm...')",
            },
        },
    },
    "governance": {
        "category": "治理管理",
        "tools": {
            "create_proposal": {
                "description": "创建治理提案",
                "usage": "当用户发起治理提案时使用",
                "params": {"title": "提案标题", "description": "提案描述"},
                "example": "create_proposal(title='提案标题', description='提案内容')",
            },
            "get_proposals": {
                "description": "获取提案列表",
                "usage": "当用户查询治理提案时使用",
                "params": {"status": "提案状态过滤"},
                "example": "get_proposals(status='active')",
            },
        },
    },
    "monitor": {
        "category": "系统监控",
        "tools": {
            "get_metrics": {
                "description": "获取系统指标",
                "usage": "当用户查看系统性能时使用",
                "params": {"metric_type": "指标类型"},
                "example": "get_metrics(metric_type='cpu')",
            },
            "get_logs": {
                "description": "获取系统日志",
                "usage": "当用户排查问题时使用",
                "params": {"level": "日志级别", "limit": "数量限制"},
                "example": "get_logs(level='error', limit=100)",
            },
        },
    },
    "ui": {
        "category": "界面交互",
        "tools": {
            "navigate": {
                "description": "导航到页面",
                "usage": "当用户需要跳转到特定页面时使用",
                "params": {"page": "页面路径"},
                "example": "navigate(page='/app/dashboard')",
            },
            "show_notification": {
                "description": "显示通知",
                "usage": "当需要通知用户时使用",
                "params": {"message": "通知内容", "type": "通知类型"},
                "example": "show_notification(message='操作成功', type='success')",
            },
        },
    },
}


def get_tool_prompt(tools: list) -> str:
    """
    根据可用工具列表生成工具使用说明

    Args:
        tools: 可用工具名称列表

    Returns:
        工具使用说明文本
    """
    prompt_parts = ["## 可用工具\n"]

    for tool_name in tools:
        for category, info in TOOL_DESCRIPTIONS.items():
            if tool_name in info.get("tools", {}):
                tool_info = info["tools"][tool_name]
                prompt_parts.append(f"### {tool_name}")
                prompt_parts.append(f"- 描述: {tool_info['description']}")
                prompt_parts.append(f"- 用途: {tool_info['usage']}")
                if tool_info.get("params"):
                    prompt_parts.append(f"- 参数: {tool_info['params']}")
                prompt_parts.append(f"- 示例: `{tool_info['example']}`")
                prompt_parts.append("")
                break

    return "\n".join(prompt_parts)


def get_all_tools_prompt() -> str:
    """生成所有工具的完整说明"""
    prompt_parts = ["## 工具库\n"]

    for category, info in TOOL_DESCRIPTIONS.items():
        prompt_parts.append(f"\n### {info['category']}\n")
        for tool_name, tool_info in info.get("tools", {}).items():
            prompt_parts.append(f"- **{tool_name}**: {tool_info['description']}")

    return "\n".join(prompt_parts)
