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
            "stake": {
                "description": "质押代币 - 将用户的 VIBE 代币进行质押以获得投票权和奖励",
                "usage": "当用户说要质押、stake、抵押代币时必须使用此工具",
                "params": {"amount": "质押数量（VIBE）"},
                "example": "stake(amount=100)",
            },
            "unstake": {
                "description": "解除质押 - 将已质押的 VIBE 代币解除质押",
                "usage": "当用户说要解除质押、unstake时使用",
                "params": {"amount": "解除质押数量（VIBE）"},
                "example": "unstake(amount=50)",
            },
            "vote": {
                "description": "投票 - 对治理提案进行投票",
                "usage": "当用户说要投票、vote时使用",
                "params": {"proposal_id": "提案ID", "support": "是否支持(true/false)"},
                "example": "vote(proposal_id=1, support=True)",
            },
            "vote_proposal": {
                "description": "对提案投票",
                "usage": "当用户参与治理投票时使用",
                "params": {"proposal_id": "提案ID", "support": "是否支持"},
                "example": "vote_proposal(proposal_id=1, support=True)",
            },
            "submit_proposal": {
                "description": "提交治理提案",
                "usage": "当用户要提交提案时使用",
                "params": {"title": "提案标题", "description": "提案描述", "content": "提案内容"},
                "example": "submit_proposal(title='标题', description='描述')",
            },
            "list_proposals": {
                "description": "列出所有治理提案",
                "usage": "当用户要查看提案列表时使用",
                "params": {},
                "example": "list_proposals()",
            },
            "get_vote_power": {
                "description": "获取投票权",
                "usage": "当用户要查看自己的投票权时使用",
                "params": {},
                "example": "get_vote_power()",
            },
            "delegate_vote": {
                "description": "委托投票权",
                "usage": "当用户要委托投票权时使用",
                "params": {"delegate": "被委托的钱包地址"},
                "example": "delegate_vote(delegate='0x...')",
            },
        },
    },
    "database": {
        "category": "数据操作",
        "tools": {
            "query_db": {
                "description": "查询数据库 - 执行 SQL SELECT 查询",
                "usage": "当用户要查询数据库时使用",
                "params": {"query": "SQL 查询语句"},
                "example": "query_db(query='SELECT * FROM users LIMIT 10')",
            },
            "insert_db": {
                "description": "插入数据 - 向数据库表插入新数据",
                "usage": "当用户要插入数据时使用",
                "params": {"table": "表名", "data": "数据字典"},
                "example": "insert_db(table='users', data={'name': 'Alice'})",
            },
            "update_db": {
                "description": "更新数据 - 修改数据库中现有数据",
                "usage": "当用户要更新数据时使用",
                "params": {"table": "表名", "data": "更新的数据", "where": "条件"},
                "example": "update_db(table='users', data={'name': 'Bob'}, where='id=1')",
            },
            "delete_db": {
                "description": "删除数据 - 从数据库删除数据",
                "usage": "当用户要删除数据时使用",
                "params": {"table": "表名", "where": "删除条件"},
                "example": "delete_db(table='users', where='id=1')",
            },
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
    "web": {
        "category": "网络访问",
        "tools": {
            "search_web": {
                "description": "搜索互联网获取实时信息",
                "usage": "当用户需要查询实时信息、新闻、天气、股票、资料等，以及其他需要上网使用搜索引擎搜索资料的场景时使用",
                "params": {
                    "query": "搜索关键词",
                    "engine": "搜索引擎(可选)",
                    "num_results": "结果数量(可选)",
                },
                "example": "search_web(query='深圳天气')",
            },
            "fetch_url": {
                "description": "获取指定网页的完整内容",
                "usage": "当需要获取网页HTML内容、API响应、文件内容时使用",
                "params": {"url": "目标URL", "method": "请求方法(可选)", "headers": "请求头(可选)"},
                "example": "fetch_url(url='https://example.com')",
            },
            "parse_html": {
                "description": "解析HTML内容，提取指定元素",
                "usage": "当需要从HTML中提取特定信息（如标题、链接、价格等）时使用",
                "params": {
                    "html": "HTML内容",
                    "selector": "CSS选择器",
                    "attribute": "提取属性(可选)",
                },
                "example": "parse_html(html='<html>...', selector='.title')",
            },
            "download_file": {
                "description": "下载远程文件到本地",
                "usage": "当需要下载文件、文档、图片等资源时使用",
                "params": {
                    "url": "远程文件URL",
                    "destination": "本地保存路径(可选)",
                    "overwrite": "是否覆盖(可选)",
                },
                "example": "download_file(url='https://example.com/file.pdf')",
            },
            "get_headers": {
                "description": "获取网页响应头信息",
                "usage": "状态、Content当需要检查网页-Type、认证信息等时使用",
                "params": {"url": "目标URL"},
                "example": "get_headers(url='https://example.com')",
            },
        },
    },
    "system": {
        "category": "系统操作",
        "tools": {
            "execute_command": {
                "description": "执行命令行命令",
                "usage": "当需要运行终端命令、系统操作时使用",
                "params": {"command": "命令内容", "cwd": "工作目录(可选)"},
                "example": "execute_command(command='ls -la')",
            },
            "run_program": {
                "description": "运行程序或脚本文件",
                "usage": "当需要执行可执行文件或脚本时使用",
                "params": {"program": "程序路径", "args": "参数(可选)"},
                "example": "run_program(program='/path/to/script.py')",
            },
            "read_file": {
                "description": "读取文件内容",
                "usage": "当需要查看文件内容时使用",
                "params": {"file_path": "文件路径"},
                "example": "read_file(file_path='/workspace/myfile.txt')",
            },
            "write_file": {
                "description": "写入或创建文件",
                "usage": "当需要保存内容到文件时使用",
                "params": {"file_path": "文件路径", "content": "文件内容"},
                "example": "write_file(file_path='/workspace/test.txt', content='Hello')",
            },
            "list_directory": {
                "description": "列出目录内容",
                "usage": "当需要查看目录中有哪些文件时使用",
                "params": {"path": "目录路径"},
                "example": "list_directory(path='/workspace')",
            },
            "create_directory": {
                "description": "创建目录",
                "usage": "当需要创建新目录时使用",
                "params": {"path": "目录路径"},
                "example": "create_directory(path='/workspace/newfolder')",
            },
            "delete_file": {
                "description": "删除文件或目录",
                "usage": "当需要删除文件时使用",
                "params": {"path": "文件或目录路径"},
                "example": "delete_file(path='/workspace/old.txt')",
            },
            "search_files": {
                "description": "搜索文件",
                "usage": "当需要在目录中查找特定文件时使用",
                "params": {"pattern": "搜索模式", "path": "搜索目录(可选)"},
                "example": "search_files(pattern='*.py')",
            },
            "get_file_info": {
                "description": "获取文件信息",
                "usage": "当需要查看文件大小、修改时间等元数据时使用",
                "params": {"file_path": "文件路径"},
                "example": "get_file_info(file_path='/workspace/test.txt')",
            },
            "copy_file": {
                "description": "复制文件或目录",
                "usage": "当需要复制文件时使用",
                "params": {"source": "源路径", "destination": "目标路径"},
                "example": "copy_file(source='/a.txt', destination='/b.txt')",
            },
            "move_file": {
                "description": "移动或重命名文件",
                "usage": "当需要移动或重命名文件时使用",
                "params": {"source": "源路径", "destination": "目标路径"},
                "example": "move_file(source='/old.txt', destination='/new.txt')",
            },
        },
    },
    "execution": {
        "category": "代码执行",
        "tools": {
            "execute_python": {
                "description": "执行Python代码并返回结果",
                "usage": "当需要执行Python代码进行计算、数据处理、测试等时使用",
                "params": {"code": "Python代码"},
                "example": "execute_python(code='print(1+1)')",
            },
            "execute_javascript": {
                "description": "执行JavaScript代码",
                "usage": "当需要执行JavaScript代码时使用（需要Node.js环境）",
                "params": {"code": "JavaScript代码"},
                "example": "execute_javascript(code='console.log(1+1)')",
            },
            "browser_open": {
                "description": "打开浏览器并访问URL",
                "usage": "当需要通过浏览器自动化操作网页时使用",
                "params": {"url": "目标URL"},
                "example": "browser_open(url='https://example.com')",
            },
            "browser_click": {
                "description": "点击页面元素",
                "usage": "当需要模拟点击按钮、链接等元素时使用",
                "params": {"selector": "CSS选择器"},
                "example": "browser_click(selector='#submit-btn')",
            },
            "browser_fill": {
                "description": "填写表单输入框",
                "usage": "当需要填写表单字段时使用",
                "params": {"selector": "CSS选择器", "value": "填写内容"},
                "example": "browser_fill(selector='#username', value='admin')",
            },
            "browser_get_content": {
                "description": "获取浏览器当前页面内容",
                "usage": "当需要获取页面渲染后的内容时使用",
                "params": {},
                "example": "browser_get_content()",
            },
            "browser_screenshot": {
                "description": "截取浏览器页面截图",
                "usage": "当需要保存页面截图时使用",
                "params": {"path": "保存路径(可选)"},
                "example": "browser_screenshot(path='/workspace/screenshot.png')",
            },
            "browser_close": {
                "description": "关闭浏览器",
                "usage": "当需要关闭浏览器会话时使用",
                "params": {},
                "example": "browser_close()",
            },
            "parse_skill_md": {
                "description": "解析skills.md文件提取技能定义",
                "usage": "当需要加载和管理自定义技能时使用",
                "params": {"file_path": "文件路径(可选)"},
                "example": "parse_skill_md(file_path='/workspace/skills.md')",
            },
            "execute_skill": {
                "description": "执行指定名称的技能",
                "usage": "当需要执行已加载的自定义技能时使用",
                "params": {"skill_name": "技能名称", "params": "技能参数(可选)"},
                "example": "execute_skill(skill_name='my_skill', params={})",
            },
            "list_skills": {
                "description": "列出所有已加载的技能",
                "usage": "当需要查看可用技能列表时使用",
                "params": {},
                "example": "list_skills()",
            },
        },
    },
    "system_agents": {
        "category": "系统Agent服务",
        "tools": {
            "search_agents": {
                "description": "搜索注册Agent",
                "usage": "当用户需要查找特定类型的Agent时使用",
                "params": {"query": "搜索关键词", "category": "分类(可选)"},
                "example": "search_agents(query='python')",
            },
            "recommend_agents": {
                "description": "推荐合适的Agent",
                "usage": "当需要根据需求推荐最合适的Agent时使用",
                "params": {"task_description": "任务描述"},
                "example": "recommend_agents(task_description='需要Python开发')",
            },
            "rate_agent": {
                "description": "给Agent评分",
                "usage": "当用户需要对Agent服务进行评价时使用",
                "params": {"agent_id": "Agent ID", "rating": "评分", "comment": "评价(可选)"},
                "example": "rate_agent(agent_id='agent_001', rating=5)",
            },
            "get_agent_profile": {
                "description": "获取Agent能力画像",
                "usage": "当需要查看Agent的详细能力介绍时使用",
                "params": {"agent_id": "Agent ID"},
                "example": "get_agent_profile(agent_id='agent_001')",
            },
            "get_all_agent_profiles": {
                "description": "获取所有Agent画像",
                "usage": "当需要查看平台所有Agent列表时使用",
                "params": {},
                "example": "get_all_agent_profiles()",
            },
            "consult_agent": {
                "description": "咨询Agent获取建议",
                "usage": "当需要向特定Agent咨询问题获取专业建议时使用",
                "params": {"agent_id": "Agent ID", "question": "咨询问题"},
                "example": "consult_agent(agent_id='agent_001', question='如何优化代码')",
            },
            "route_message": {
                "description": "路由消息到指定Agent",
                "usage": "当需要将消息转发给特定Agent处理时使用",
                "params": {"agent_id": "目标Agent ID", "message": "消息内容"},
                "example": "route_message(agent_id='agent_001', message='你好')",
            },
        },
    },
    "precise_matching": {
        "category": "精准匹配服务",
        "tools": {
            "interview_agent": {
                "description": "与Agent进行面试式对话",
                "usage": "当需要深入了解Agent能力、测试Agent响应时使用",
                "params": {"agent_id": "Agent ID", "questions": "问题列表"},
                "example": "interview_agent(agent_id='agent_001', questions=['你会什么？'])",
            },
            "send_agent_message": {
                "description": "向Agent发送消息获取响应",
                "usage": "当需要与Agent进行对话交互时使用",
                "params": {"agent_id": "Agent ID", "message": "消息内容"},
                "example": "send_agent_message(agent_id='agent_001', message='帮我写代码')",
            },
            "receive_agent_showcase": {
                "description": "接收Agent展示的案例或能力",
                "usage": "当Agent主动展示其能力、案例时接收使用",
                "params": {"agent_id": "Agent ID", "showcase": "展示内容"},
                "example": "receive_agent_showcase(agent_id='agent_001', showcase={})",
            },
            "recommend_agents_for_demand": {
                "description": "为需求推荐最合适的Agent",
                "usage": "当用户描述具体需求需要推荐Agent时使用",
                "params": {"demand": "需求描述"},
                "example": "recommend_agents_for_demand(demand='需要前端开发')",
            },
            "match_by_gene_capsule": {
                "description": "基于基因胶囊精准匹配Agent",
                "usage": "当需要基于能力基因精准匹配Agent时使用",
                "params": {"gene_capsule": "能力基因"},
                "example": "match_by_gene_capsule(gene_capsule='python,web')",
            },
            "generate_recommendation_explanation": {
                "description": "生成推荐解释",
                "usage": "当需要了解为什么推荐某个Agent时使用",
                "params": {"agent_id": "Agent ID", "demand": "需求描述"},
                "example": "generate_recommendation_explanation(agent_id='agent_001', demand='开发')",
            },
            "proactively_notify_opportunity": {
                "description": "主动通知Agent商业机会",
                "usage": "当发现有Agent匹配的商机时主动通知使用",
                "params": {"agent_id": "Agent ID", "opportunity": "机会描述"},
                "example": "proactively_notify_opportunity(agent_id='agent_001', opportunity={})",
            },
            "scan_opportunities": {
                "description": "扫描平台商业机会",
                "usage": "当需要扫描平台上的潜在商业机会时使用",
                "params": {"criteria": "筛选条件(可选)"},
                "example": "scan_opportunities(criteria={'type': 'development'})",
            },
            "auto_match_and_notify": {
                "description": "自动匹配并通知",
                "usage": "当需要自动匹配需求与Agent并发送通知时使用",
                "params": {"demand": "需求描述"},
                "example": "auto_match_and_notify(demand='需要Python开发')",
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
        for _category, info in TOOL_DESCRIPTIONS.items():
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

    for _category, info in TOOL_DESCRIPTIONS.items():
        prompt_parts.append(f"\n### {info['category']}\n")
        for tool_name, tool_info in info.get("tools", {}).items():
            prompt_parts.append(f"- **{tool_name}**: {tool_info['description']}")

    return "\n".join(prompt_parts)
