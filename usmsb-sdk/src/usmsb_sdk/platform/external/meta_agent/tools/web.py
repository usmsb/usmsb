"""
网页操作工具

提供网页抓取、浏览器控制等能力
"""

import asyncio
import json
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urljoin

logger = logging.getLogger(__name__)


def get_web_tools() -> List:
    """获取网页工具列表"""
    return [
        {
            "name": "fetch_url",
            "description": "获取网页内容，支持 HTML、JSON、文本等",
            "handler": fetch_url,
        },
        {
            "name": "parse_html",
            "description": "解析 HTML 内容，提取指定元素",
            "handler": parse_html,
        },
        {
            "name": "search_web",
            "description": "搜索网页内容",
            "handler": search_web,
        },
        {
            "name": "download_file",
            "description": "下载远程文件",
            "handler": download_file,
        },
        {
            "name": "get_headers",
            "description": "获取网页响应头",
            "handler": get_headers,
        },
    ]


async def fetch_url(params: dict) -> Dict[str, Any]:
    """
    获取网页内容

    Args:
        params: 参数字典，包含:
            - url: 目标 URL
            - method: HTTP 方法
            - headers: 自定义请求头
            - timeout: 超时时间

    Returns:
        网页内容
    """
    url = params.get("url", "")
    method = params.get("method", "GET")
    headers = params.get("headers")
    timeout = params.get("timeout", 30)
    import aiohttp

    # URL 安全检查
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return {"status": "error", "message": "只支持 HTTP/HTTPS 协议"}

    default_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    if headers:
        default_headers.update(headers)

    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method, url, headers=default_headers, timeout=aiohttp.ClientTimeout(total=timeout)
            ) as response:
                content_type = response.headers.get("Content-Type", "")

                # 根据内容类型处理
                if "application/json" in content_type:
                    content = await response.json()
                    text = json.dumps(content, indent=2, ensure_ascii=False)
                else:
                    text = await response.text()

                return {
                    "status": "success",
                    "url": url,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                    "content_type": content_type,
                    "content": text[:50000],  # 限制内容长度
                    "content_length": len(text),
                }

    except asyncio.TimeoutError:
        return {"status": "error", "message": f"请求超时 ({timeout}秒)"}
    except Exception as e:
        logger.error(f"Fetch URL failed: {e}")
        return {"status": "error", "message": str(e)}


async def parse_html(params: dict) -> Dict[str, Any]:
    """
    解析 HTML 内容

    Args:
        params: 参数字典，包含:
            - html: HTML 内容
            - selector: CSS 选择器
            - attribute: 要提取的属性

    Returns:
        解析结果
    """
    html = params.get("html", "")
    selector = params.get("selector", "")
    attribute = params.get("attribute")
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(selector)

        if not elements:
            return {
                "status": "success",
                "selector": selector,
                "results": [],
                "count": 0,
            }

        results = []
        for elem in elements[:50]:  # 限制数量
            if attribute:
                results.append(elem.get(attribute, ""))
            else:
                results.append(elem.get_text(strip=True))

        return {
            "status": "success",
            "selector": selector,
            "attribute": attribute,
            "results": results,
            "count": len(results),
        }

    except ImportError:
        return {"status": "error", "message": "需要安装 beautifulsoup4: pip install beautifulsoup4"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


async def search_web(params: dict) -> Dict[str, Any]:
    """
    搜索网页

    Args:
        params: 参数字典，包含:
            - query: 搜索关键词
            - engine: 搜索引擎
            - num_results: 返回结果数量
    """
    query = params.get("query", "")
    engine = params.get("engine", "duckduckgo")
    num_results = params.get("num_results", 10)
    try:
        if engine == "duckduckgo":
            return await _search_duckduckgo(query, num_results)
        elif engine == "google":
            return await _search_google(query, num_results)
        else:
            return {"status": "error", "message": f"不支持的搜索引擎: {engine}"}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"status": "error", "message": str(e)}


async def _search_duckduckgo(query: str, num_results: int) -> Dict[str, Any]:
    """使用 DuckDuckGo 搜索"""
    try:
        from duckduckgo_search import DDGS

        results = []
        ddgs = DDGS()
        for r in ddgs.text(query, max_results=num_results):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("href", ""),
                    "snippet": r.get("body", ""),
                }
            )

        return {
            "status": "success",
            "engine": "duckduckgo",
            "query": query,
            "results": results,
            "count": len(results),
        }

    except ImportError:
        # 降级到使用 fetch_url
        url = f"https://html.duckduckgo.com/html/?q={query}"
        result = await fetch_url(url)

        if result["status"] == "success":
            parse_result = await parse_html(result["content"], ".result__snippet")
            return {
                "status": "success",
                "engine": "duckduckgo",
                "query": query,
                "results": [{"snippet": r} for r in parse_result.get("results", [])],
                "count": parse_result.get("count", 0),
            }

        return {"status": "error", "message": "搜索失败，请安装 duckduckgo-search"}


async def _search_google(query: str, num_results: int) -> Dict[str, Any]:
    """使用 Google 搜索（需要安装 google-search）"""
    try:
        from googlesearch import search as google_search

        results = []
        for url in google_search(query, num_results=num_results):
            results.append(
                {
                    "url": url,
                    "title": "",  # Google 不返回标题
                    "snippet": "",
                }
            )

        return {
            "status": "success",
            "engine": "google",
            "query": query,
            "results": results,
            "count": len(results),
        }

    except ImportError:
        return {"status": "error", "message": "需要安装 google-search"}


async def download_file(params: dict) -> Dict[str, Any]:
    """
    下载远程文件

    Args:
        params: 参数字典，包含:
            - url: 远程文件 URL
            - destination: 本地保存路径
            - overwrite: 是否覆盖已存在的文件
    """
    url = params.get("url", "")
    destination = params.get("destination", "")
    overwrite = params.get("overwrite", False)
    import aiohttp

    # URL 安全检查
    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return {"status": "error", "message": "只支持 HTTP/HTTPS"}

    # 检查目标路径
    import os

    if os.path.exists(destination) and not overwrite:
        return {"status": "error", "message": f"文件已存在: {destination}"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"status": "error", "message": f"HTTP {response.status}"}

                # 确保目录存在
                os.makedirs(os.path.dirname(destination) or ".", exist_ok=True)

                # 写入文件
                content = await response.read()
                with open(destination, "wb") as f:
                    f.write(content)

                return {
                    "status": "success",
                    "url": url,
                    "destination": destination,
                    "size": len(content),
                }

    except Exception as e:
        return {"status": "error", "message": str(e)}


async def get_headers(params: dict) -> Dict[str, Any]:
    """
    获取网页响应头

    Args:
        params: 参数字典，包含:
            - url: 目标 URL
    """
    url = params.get("url", "")
    import aiohttp

    parsed = urlparse(url)
    if parsed.scheme not in ["http", "https"]:
        return {"status": "error", "message": "只支持 HTTP/HTTPS"}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.head(url) as response:
                return {
                    "status": "success",
                    "url": url,
                    "status_code": response.status,
                    "headers": dict(response.headers),
                }
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WebTool:
    """网页工具类（兼容 Tool 接口）"""

    def __init__(self, name: str, description: str, handler):
        self.name = name
        self.description = description
        self.handler = handler
        self.requires_session = False  # Web 工具不需要 session

    async def execute(self, **kwargs):
        # Web 工具不需要 session，过滤掉它
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != 'session'}
        # Web handlers expect params as a dict, not individual kwargs
        return await self.handler(params=filtered_kwargs)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
        }

    def to_function_schema(self, provider: str = "anthropic") -> Dict[str, Any]:
        """转换为 Function Calling 的 JSON Schema 格式"""
        if provider == "anthropic":
            return {
                "name": self.name,
                "description": self.description,
                "input_schema": {
                    "type": "object",
                    "properties": self._get_parameters(),
                    "required": self._get_required_parameters(),
                },
            }
        else:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": {
                        "type": "object",
                        "properties": self._get_parameters(),
                        "required": self._get_required_parameters(),
                    },
                },
            }

    def _get_parameters(self) -> Dict[str, Any]:
        """获取工具参数定义"""
        params_map = {
            "fetch_url": {
                "url": {"type": "string", "description": "目标 URL"},
                "method": {"type": "string", "description": "HTTP 方法 (GET/POST)"},
                "headers": {"type": "object", "description": "自定义请求头"},
                "timeout": {"type": "integer", "description": "超时时间（秒）"},
            },
            "parse_html": {
                "html": {"type": "string", "description": "HTML 内容"},
                "selector": {"type": "string", "description": "CSS 选择器"},
                "attribute": {"type": "string", "description": "要提取的属性名"},
            },
            "search_web": {
                "query": {"type": "string", "description": "搜索关键词"},
                "engine": {"type": "string", "description": "搜索引擎 (duckduckgo/google)"},
                "num_results": {"type": "integer", "description": "返回结果数量"},
            },
            "download_file": {
                "url": {"type": "string", "description": "远程文件 URL"},
                "destination": {"type": "string", "description": "本地保存路径"},
                "overwrite": {"type": "boolean", "description": "是否覆盖已存在的文件"},
            },
            "get_headers": {
                "url": {"type": "string", "description": "目标 URL"},
            },
        }
        return params_map.get(self.name, {})

    def _get_required_parameters(self) -> List[str]:
        """获取必需的参数列表"""
        required_map = {
            "fetch_url": ["url"],
            "parse_html": ["html", "selector"],
            "search_web": ["query"],
            "download_file": ["url", "destination"],
            "get_headers": ["url"],
        }
        return required_map.get(self.name, [])


def get_web_tool_objects():
    """获取网页工具对象列表"""
    tools = [
        WebTool(
            name="fetch_url",
            description="获取网页内容，支持 HTML、JSON、文本等",
            handler=fetch_url,
        ),
        WebTool(
            name="parse_html",
            description="解析 HTML 内容，提取指定元素",
            handler=parse_html,
        ),
        WebTool(
            name="search_web",
            description="搜索网页内容",
            handler=search_web,
        ),
        WebTool(
            name="download_file",
            description="下载远程文件",
            handler=download_file,
        ),
        WebTool(
            name="get_headers",
            description="获取网页响应头",
            handler=get_headers,
        ),
    ]
    return tools


async def register_tools(registry):
    """注册网页工具"""
    for tool in get_web_tool_objects():
        registry.register(tool)
