"""
IPFS Tools
"""

from .registry import Tool


def get_ipfs_tools():
    return [
        Tool("upload_to_ipfs", "上传到IPFS", upload_to_ipfs),
        Tool("download_from_ipfs", "从IPFS下载", download_from_ipfs),
        Tool("sync_to_ipfs", "同步到IPFS", sync_to_ipfs),
    ]


async def register_tools(registry):
    for tool in get_ipfs_tools():
        registry.register(tool)


async def upload_to_ipfs(params):
    return {"cid": "Qmxxx", "size": 1024}


async def download_from_ipfs(params):
    return {"content": "data", "cid": params.get("cid")}


async def sync_to_ipfs(params):
    return {"status": "success", "cid": "Qmxxx"}
