"""
UI Tools
"""

from .registry import Tool


def get_ui_tools():
    return [
        Tool("generate_component", "生成UI组件", generate_component),
        Tool("manage_page", "页面管理", manage_page),
        Tool("call_api", "调用API", call_api),
    ]


async def register_tools(registry):
    for tool in get_ui_tools():
        registry.register(tool)


async def generate_component(params):
    ctype = params.get("type", "button")
    return {"component_type": ctype, "code": f"<{ctype} />"}


async def manage_page(params):
    return {"action": params.get("action"), "status": "success"}


async def call_api(params):
    return {"endpoint": params.get("endpoint"), "result": {}}
