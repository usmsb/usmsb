"""
网页操作工具

提供网页抓取、浏览器控制等能力
"""

import json
import logging
from typing import Any
from urllib.parse import urlparse

import aiohttp

logger = logging.getLogger(__name__)


def get_web_tools() -> list:
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


async def fetch_url(params: dict) -> dict[str, Any]:
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

    except TimeoutError:
        return {"status": "error", "message": f"请求超时 ({timeout}秒)"}
    except Exception as e:
        logger.error(f"Fetch URL failed: {e}")
        return {"status": "error", "message": str(e)}


async def parse_html(params: dict) -> dict[str, Any]:
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


async def search_web(params: dict) -> dict[str, Any]:
    """
    搜索网页

    Args:
        params: 参数字典，包含:
            - query: 搜索关键词
            - engine: 搜索引擎 (duckduckgo/google/bing)
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
        elif engine == "bing":
            return await _search_bing(query, num_results)
        else:
            return {"status": "error", "message": f"不支持的搜索引擎: {engine}"}
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return {"status": "error", "message": str(e)}


async def _search_duckduckgo(query: str, num_results: int) -> dict[str, Any]:
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

        # 如果 DuckDuckGo 返回空结果，尝试使用 Bing
        if not results:
            return await _search_bing(query, num_results)

        return {
            "status": "success",
            "engine": "duckduckgo",
            "query": query,
            "results": results,
            "count": len(results),
        }

    except ImportError:
        return await _search_bing(query, num_results)
    except Exception as e:
        # DuckDuckGo 在某些地区可能无法访问，尝试 Bing
        logger.warning(f"DuckDuckGo search failed: {e}")
        return await _search_bing(query, num_results)


async def _search_fallback(query: str, num_results: int) -> dict[str, Any]:
    """备用搜索方法：使用 Bing"""
    return await _search_bing(query, num_results)

    # 检测是否是天气查询
    query_lower = query.lower()
    is_weather = "天气" in query or "weather" in query_lower

    if is_weather:
        # 尝试从天气网站获取数据
        try:
            # 使用中国天气网
            city = ""
            if "深圳" in query:
                city = "shenzhen"
            elif "北京" in query:
                city = "beijing"
            elif "上海" in query:
                city = "shanghai"
            elif "广州" in query:
                city = "guangzhou"
            else:
                # 提取城市名
                import re

                match = re.search(r"([\u4e00-\u9fa5]+)", query)
                if match:
                    city = match.group(1)

            # 尝试访问天气网站
            weather_urls = [
                f"https://www.weather.com.cn/weather/{city}.shtml",
                f"https://www.sohu.com/a/search?wd={query}",
                f"https://www.baidu.com/s?wd={query}",
            ]

            for url in weather_urls:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            url,
                            timeout=aiohttp.ClientTimeout(total=10),
                            headers={"User-Agent": "Mozilla/5.0"},
                        ) as resp:
                            if resp.status == 200:
                                content = await resp.text()
                                return {
                                    "status": "success",
                                    "engine": "direct",
                                    "query": query,
                                    "results": [
                                        {
                                            "title": "天气查询",
                                            "url": url,
                                            "snippet": f"从 {url} 获取的天气数据",
                                        }
                                    ],
                                    "count": 1,
                                    "raw_content": content[:5000],  # 返回部分原始内容
                                }
                except Exception as e2:
                    logger.warning(f"Weather site fetch failed: {e2}")
                    continue

        except Exception as e:
            logger.warning(f"Weather search fallback failed: {e}")

    # 如果都不是天气查询，尝试使用 Baidu/Bing API 的公开端点
    return {
        "status": "success",
        "engine": "fallback",
        "query": query,
        "results": [
            {
                "title": f"关于 {query} 的搜索结果",
                "url": f"https://www.baidu.com/s?wd={query}",
                "snippet": "请访问百度搜索获取更多信息",
            }
        ],
        "count": 1,
    }


async def _search_google(query: str, num_results: int) -> dict[str, Any]:
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


async def _search_bing(query: str, num_results: int) -> dict[str, Any]:
    """使用 Bing 搜索（通过抓取网页）"""
    import aiohttp

    try:
        # 使用 Bing 搜索结果页面
        url = f"https://www.bing.com/search?q={query}&setlang=zh-CN"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, timeout=aiohttp.ClientTimeout(total=15), headers=headers
            ) as resp:
                if resp.status != 200:
                    return {"status": "error", "message": f"Bing 请求失败: {resp.status}"}

                html = await resp.text()

        # 解析 Bing 搜索结果
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")

        results = []
        # Bing 结果容器
        for item in soup.select("li.b_algo")[:num_results]:
            title_elem = item.select_one("h2 a")
            snippet_elem = item.select_one("div.b_caption p")

            if title_elem:
                title = title_elem.get_text(strip=True)
                url = title_elem.get("href", "")
                snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""

                results.append(
                    {
                        "title": title,
                        "url": url,
                        "snippet": snippet,
                    }
                )

        if not results:
            # 尝试备用解析方式
            for item in soup.select(".b_ans .b_ans_topvcomp, .b_ans .b_ansitem")[:num_results]:
                title_elem = item.select_one("a")
                if title_elem:
                    results.append(
                        {
                            "title": title_elem.get_text(strip=True),
                            "url": title_elem.get("href", ""),
                            "snippet": "",
                        }
                    )

        if not results:
            return await _search_fallback(query, num_results)

        return {
            "status": "success",
            "engine": "bing",
            "query": query,
            "results": results,
            "count": len(results),
        }

    except ImportError:
        return {"status": "error", "message": "需要安装 aiohttp"}
    except Exception as e:
        logger.warning(f"Bing search failed: {e}")
        return await _search_fallback(query, num_results)


async def download_file(params: dict) -> dict[str, Any]:
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


async def get_headers(params: dict) -> dict[str, Any]:
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
        filtered_kwargs = {k: v for k, v in kwargs.items() if k != "session"}
        # Web handlers expect params as a dict, not individual kwargs
        return await self.handler(params=filtered_kwargs)

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
        }

    def to_function_schema(self, provider: str = "anthropic") -> dict[str, Any]:
        """转换为 Function Calling 的 JSON Schema 格式"""
        # MiniMax uses Anthropic-compatible format
        if provider in ("anthropic", "minimax"):
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

    def _get_parameters(self) -> dict[str, Any]:
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

    def _get_required_parameters(self) -> list[str]:
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
