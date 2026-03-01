"""
Demo 可视化工具

提供场景运行时的可视化输出和日志记录。
"""

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from pathlib import Path


class DemoVisualizer:
    """
    Demo 可视化器

    功能：
    - 控制台彩色输出
    - 消息日志记录
    - 场景状态追踪
    - HTML 报告生成
    """

    # ANSI 颜色代码
    COLORS = {
        "reset": "\033[0m",
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "bold": "\033[1m",
        "dim": "\033[2m",
    }

    def __init__(
        self,
        scenario_name: str,
        enable_console: bool = True,
        enable_html: bool = True,
    ):
        self.scenario_name = scenario_name
        self.enable_console = enable_console
        self.enable_html = enable_html

        # 日志目录
        self.log_dir = Path(__file__).parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)

        # 消息历史
        self.messages: List[Dict] = []
        self.events: List[Dict] = []
        self.agent_states: Dict[str, Dict] = {}

    def _colorize(self, text: str, color: str) -> str:
        """添加颜色"""
        if not self.enable_console:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def log_message(self, message: Any):
        """记录消息"""
        msg_dict = self._message_to_dict(message)
        self.messages.append(msg_dict)

        if self.enable_console:
            self._print_message(msg_dict)

    def _message_to_dict(self, message: Any) -> Dict:
        """转换消息为字典"""
        if hasattr(message, "to_dict"):
            return message.to_dict()
        if isinstance(message, dict):
            return message
        return {
            "sender": "unknown",
            "receiver": "unknown",
            "content": str(message),
            "timestamp": datetime.now().isoformat(),
        }

    def _print_message(self, msg: Dict):
        """打印消息到控制台"""
        sender = msg.get("sender", "unknown")
        receiver = msg.get("receiver", "unknown")
        content = msg.get("content", "")
        msg_type = msg.get("message_type", "text")

        icons = {
            "text": "💬",
            "task": "📋",
            "result": "✅",
            "error": "❌",
        }
        icon = icons.get(msg_type, "📨")

        content_str = str(content)
        if len(content_str) > 60:
            content_str = content_str[:57] + "..."

        print(f"  {icon} {sender} → {receiver}: {content_str}")

    def log_event(self, event_type: str, data: Dict):
        """记录事件"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "data": data,
        }
        self.events.append(event)

        if self.enable_console:
            self._print_event(event)

    def _print_event(self, event: Dict):
        """打印事件到控制台"""
        event_type = event.get("type", "unknown")
        data = event.get("data", {})

        icons = {
            "start": "🚀",
            "stop": "🛑",
            "agent_join": "➕",
            "task_start": "▶️",
            "task_complete": "✅",
            "milestone": "🎯",
        }
        icon = icons.get(event_type, "📌")

        print(f"  {icon} [{event_type}] {str(data)[:50]}")

    def update_agent_state(self, agent_name: str, state: Dict):
        """更新 Agent 状态"""
        self.agent_states[agent_name] = {
            "timestamp": datetime.now().isoformat(),
            **state,
        }

    def print_header(self, title: str):
        """打印标题"""
        if self.enable_console:
            print("\n" + "=" * 60)
            print(f"  {self._colorize(title, 'bold')}")
            print("=" * 60 + "\n")

    def print_section(self, title: str):
        """打印章节"""
        if self.enable_console:
            print(f"\n--- {self._colorize(title, 'cyan')} ---\n")

    def print_summary(self):
        """打印摘要"""
        if not self.enable_console:
            return

        print("\n" + "=" * 60)
        print(f"  {self._colorize('场景摘要', 'bold')}: {self.scenario_name}")
        print("=" * 60)
        print(f"  消息总数: {len(self.messages)}")
        print(f"  事件总数: {len(self.events)}")
        print(f"  Agent 数量: {len(self.agent_states)}")
        print("\n  Agent 状态:")
        for agent, state in self.agent_states.items():
            print(f"    - {agent}: {state.get('status', 'unknown')}")
        print("=" * 60 + "\n")

    def generate_html_report(self) -> str:
        """生成 HTML 报告"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = self.log_dir / f"{self.scenario_name}_{timestamp}.html"

        html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Demo Report: {self.scenario_name}</title>
    <style>
        body {{ font-family: sans-serif; max-width: 1000px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007bff; padding-bottom: 10px; }}
        .summary {{ background: #f5f5f5; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .message {{ padding: 10px; border-left: 3px solid #007bff; margin: 10px 0; background: #fafafa; }}
    </style>
</head>
<body>
    <h1>🎬 Demo Report: {self.scenario_name}</h1>
    <div class="summary">
        <p><strong>消息总数:</strong> {len(self.messages)}</p>
        <p><strong>事件总数:</strong> {len(self.events)}</p>
        <p><strong>Agent 数量:</strong> {len(self.agent_states)}</p>
    </div>
    <h2>Messages</h2>
    {self._generate_messages_html()}
</body>
</html>"""

        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)

        return str(html_file)

    def _generate_messages_html(self) -> str:
        """生成消息 HTML"""
        html = ""
        for msg in self.messages[:50]:
            html += f"""<div class="message">
                <strong>{msg.get('sender', 'unknown')}</strong> →
                <strong>{msg.get('receiver', 'unknown')}</strong>:
                {str(msg.get('content', ''))[:100]}
            </div>"""
        return html
