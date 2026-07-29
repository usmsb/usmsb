#!/usr/bin/env python3.14
"""Keep every USMSB physical LLM/embedding call behind a telemetry gateway."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_ROOTS = (ROOT / "src" / "usmsb_sdk", ROOT / "dist-inference")
APPROVED = {
    (ROOT / path).resolve()
    for path in {
        "src/usmsb_sdk/adapters/openharness/query_adapter.py",
        "src/usmsb_sdk/intelligence_adapters/llm/glm_adapter.py",
        "src/usmsb_sdk/intelligence_adapters/llm/minimax_adapter.py",
        "src/usmsb_sdk/intelligence_adapters/llm/openai_adapter.py",
        "src/usmsb_sdk/meta_agent/llm_client.py",
        "dist-inference/node_executor/executor.py",
        "dist-inference/node_executor/vllm_engine.py",
    }
}
SDK_ROOTS = {
    "anthropic",
    "cohere",
    "google.genai",
    "google.generativeai",
    "groq",
    "mistralai",
    "openai",
    "volcenginesdkarkruntime",
    "zhipuai",
}
SDK_SUFFIXES = {
    "chat.completions.create",
    "chat.completions.stream",
    "embeddings.create",
    "embeddings.with_raw_response.create",
    "messages.create",
    "messages.stream",
    "responses.create",
    "responses.parse",
    "responses.stream",
}
HTTP_SUFFIXES = {
    ".delete",
    ".fetch",
    ".get",
    ".patch",
    ".post",
    ".put",
    ".request",
    ".send",
    ".urlopen",
}
ENDPOINTS = {
    "/chat/completions",
    "/embeddings",
    "/v1/chat/completions",
    "/v1/embeddings",
    "/v1/messages",
    "/v1/responses",
    "/text/chatcompletion",
}
HOSTS = {
    "api.anthropic.com",
    "api.cohere.ai",
    "api.groq.com",
    "api.minimax.chat",
    "api.minimaxi.com",
    "api.mistral.ai",
    "api.openai.com",
    "generativelanguage.googleapis.com",
    "open.bigmodel.cn",
}


def attribute_name(node: ast.AST) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts)).lower()


class Guard(ast.NodeVisitor):
    def __init__(self) -> None:
        self.bindings: dict[str, set[str]] = {}
        self.findings: list[tuple[int, str]] = []

    def markers(self, node: ast.AST | None) -> set[str]:
        if node is None:
            return set()
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return {node.value.lower()}
        if isinstance(node, ast.Name):
            return {node.id.lower(), *self.bindings.get(node.id, set())}
        if isinstance(node, ast.Attribute):
            name = attribute_name(node)
            return (
                {node.attr.lower(), name}
                | self.bindings.get(name, set())
                | self.markers(node.value)
            )
        if isinstance(node, ast.FormattedValue):
            return self.markers(node.value)
        markers: set[str] = set()
        for child in ast.iter_child_nodes(node):
            markers.update(self.markers(child))
        return markers

    def add(self, node: ast.AST, reason: str) -> None:
        self.findings.append((int(getattr(node, "lineno", 1)), reason))

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        markers = self.markers(node.value)
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.bindings[target.id] = markers
            elif isinstance(target, ast.Attribute):
                self.bindings[attribute_name(target)] = markers
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        if isinstance(node.target, ast.Name):
            self.bindings[node.target.id] = self.markers(node.value)
        elif isinstance(node.target, ast.Attribute):
            self.bindings[attribute_name(node.target)] = self.markers(node.value)
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:  # noqa: N802
        for alias in node.names:
            if any(alias.name == root or alias.name.startswith(f"{root}.") for root in SDK_ROOTS):
                self.add(node, f"direct provider SDK import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # noqa: N802
        module = node.module or ""
        if any(module == root or module.startswith(f"{root}.") for root in SDK_ROOTS):
            self.add(node, f"direct provider SDK import: {module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        name = attribute_name(node.func)
        callable_markers = {name, *self.bindings.get(name, set())}
        if any(
            candidate.endswith(suffix)
            for candidate in callable_markers
            for suffix in SDK_SUFFIXES
        ):
            self.add(node, f"direct provider SDK call: {name}")
        if name in {"__import__", "importlib.import_module"} and node.args:
            imported = self.markers(node.args[0])
            if any(
                any(value == root or value.startswith(f"{root}.") for root in SDK_ROOTS)
                for value in imported
            ):
                self.add(node, "dynamic provider SDK import")
        root = name.split(".", 1)[0]
        if root not in {"app", "router", "api_router", "blueprint"} and any(
            name.endswith(suffix) for suffix in HTTP_SUFFIXES
        ):
            targets: list[ast.AST] = []
            if node.args:
                targets.append(node.args[0])
            if name.endswith(".request") and len(node.args) > 1:
                targets.append(node.args[1])
            for keyword in node.keywords:
                if keyword.arg in {"url", "endpoint", "path"}:
                    targets.append(keyword.value)
            markers: set[str] = set()
            for target in targets:
                markers.update(self.markers(target))
            if isinstance(node.func, ast.Attribute) and not name.endswith(".get"):
                markers.update(self.markers(node.func.value))
            joined = " ".join(markers)
            paths = {value.split("?", 1)[0].rstrip("/") for value in markers}
            endpoint = any(
                path.endswith(item)
                or (item == "/text/chatcompletion" and item in path)
                for path in paths
                for item in ENDPOINTS
            )
            provider_host = any(item in joined for item in HOSTS)
            dynamic = any(
                ("llm" in item or "model" in item or "provider" in item)
                and any(token in item for token in ("url", "endpoint", "base"))
                for item in markers
            )
            if endpoint or provider_host or dynamic:
                self.add(node, f"direct provider HTTP call: {name}")
        self.generic_visit(node)


def main() -> int:
    findings: list[tuple[Path, int, str]] = []
    for root in SOURCE_ROOTS:
        for path in sorted(root.rglob("*.py")):
            if "tests" in path.parts or "__pycache__" in path.parts or path.resolve() in APPROVED:
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            except SyntaxError as exc:
                findings.append((path, int(exc.lineno or 1), f"cannot parse: {exc.msg}"))
                continue
            visitor = Guard()
            visitor.visit(tree)
            findings.extend((path, line, reason) for line, reason in visitor.findings)
    if findings:
        print("Direct LLM provider bypasses detected:", file=sys.stderr)
        for path, line, reason in findings:
            print(f"  {path.relative_to(ROOT)}:{line}: {reason}", file=sys.stderr)
        return 1
    print("USMSB LLM provider bypass check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
