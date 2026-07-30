# SPDX-License-Identifier: MIT
# Copyright (c) 2026 HKUDS/OpenHarness Integration for USMSB
# MemoryAdapter - OpenHarness Memory System Integration

"""
OpenHarness MemoryAdapter for USMSB.

This adapter wraps the OpenHarness memory system to provide:
- Persistent memory storage (file-based markdown)
- Memory indexing and search
- Context compaction for long conversations
- Session management
- Memory templates

The adapter provides a unified interface to OH's memory files while
supporting USMSB's multi-tier memory architecture (working, episodic, semantic).

Usage:
    >>> adapter = MemoryAdapter(cwd="/path/to/project")
    >>> adapter.store("user_preferences", {"theme": "dark"})
    >>> prefs = adapter.retrieve("user_preferences")
    >>> memories = adapter.search("preferences")
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator

try:
    from openharness.memory.manager import (
        list_memory_files,
        add_memory_entry,
        remove_memory_entry,
    )
    from openharness.memory.paths import (
        get_project_memory_dir,
        get_memory_entrypoint,
    )
    from openharness.memory.types import MemoryHeader
    from openharness.memory.search import find_relevant_memories
    OPENHARNESS_AVAILABLE = True
except ImportError:
    OPENHARNESS_AVAILABLE = False
    list_memory_files = None
    add_memory_entry = None
    remove_memory_entry = None
    get_project_memory_dir = None
    get_memory_entrypoint = None
    MemoryHeader = None
    find_relevant_memories = None

from usmsb_sdk.adapters.openharness.config import MemoryConfig
from usmsb_sdk.adapters.openharness.exceptions import (
    MemoryAccessError,
    OpenHarnessNotAvailableError,
)

log = logging.getLogger(__name__)


@dataclass
class MemoryEntry:
    """
    A memory entry stored in the memory system.
    
    Attributes:
        key: Unique identifier for the memory
        value: The memory content
        memory_type: Type of memory (working, episodic, semantic)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        metadata: Additional metadata
    """
    key: str
    value: Any
    memory_type: str = "general"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key": self.key,
            "value": self.value,
            "memory_type": self.memory_type,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryEntry":
        """Create from dictionary."""
        return cls(
            key=data["key"],
            value=data["value"],
            memory_type=data.get("memory_type", "general"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class MemoryIndex:
    """
    Index of all memory entries.
    
    This is stored as MEMORY.md in the project directory.
    """
    entries: dict[str, MemoryEntry] = field(default_factory=dict)
    updated_at: float = field(default_factory=time.time)

    def to_markdown(self) -> str:
        """Generate MEMORY.md content."""
        lines = ["# Memory Index\n"]
        lines.append(f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.updated_at))}\n")
        
        # Group by type
        by_type: dict[str, list[MemoryEntry]] = {}
        for entry in self.entries.values():
            by_type.setdefault(entry.memory_type, []).append(entry)
        
        for memory_type, entries in sorted(by_type.items()):
            lines.append(f"## {memory_type.replace('_', ' ').title()}\n")
            for entry in entries:
                lines.append(f"- [{entry.key}]({self._slugify(entry.key)}.md): {self._preview(entry.value)}")
            lines.append("")
        
        return "\n".join(lines)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to filename-safe slug."""
        import re
        return re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")

    @staticmethod
    def _preview(value: Any, max_len: int = 100) -> str:
        """Generate preview of value."""
        text = json.dumps(value, ensure_ascii=False)
        if len(text) > max_len:
            return text[:max_len] + "..."
        return text


class MemoryAdapter:
    """
    OpenHarness Memory Manager Adapter.
    
    This adapter wraps OH's file-based memory system and extends it with:
    - Structured memory entries (JSON)
    - Memory indexing
    - Search functionality
    - Context compaction
    - USMSB memory types (working, episodic, semantic)
    
    The adapter stores memory as:
    - Individual JSON files per entry in the memory directory
    - MEMORY.md index file for navigation
    
    Example:
        >>> adapter = MemoryAdapter(cwd="/path/to/project")
        >>> 
        >>> # Store a memory
        >>> adapter.store("user_preferences", {"theme": "dark"}, memory_type="semantic")
        >>> 
        >>> # Retrieve it
        >>> prefs = adapter.retrieve("user_preferences")
        >>> 
        >>> # Search memories
        >>> results = adapter.search("theme")
    """

    def __init__(
        self,
        cwd: str | Path = ".",
        config: MemoryConfig | None = None,
    ):
        """
        Initialize MemoryAdapter.
        
        Args:
            cwd: Current working directory for memory storage
            config: Memory configuration
        """
        if not OPENHARNESS_AVAILABLE:
            raise OpenHarnessNotAvailableError()
        
        self._cwd = Path(cwd).resolve()
        self._config = config or MemoryConfig()
        self._memory_dir = Path(self._config.persist_path).expanduser().resolve()
        
        # Create memory directory if needed
        self._memory_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing index
        self._index = self._load_index()
        
        # Track access for compaction decisions
        self._access_counts: dict[str, int] = {}
        self._last_access: dict[str, float] = {}
        
        log.info(
            "MemoryAdapter initialized at %s with %d entries",
            self._memory_dir,
            len(self._index.entries),
        )

    @property
    def memory_dir(self) -> Path:
        """Return the memory directory path."""
        return self._memory_dir

    @property
    def entry_count(self) -> int:
        """Return number of memory entries."""
        return len(self._index.entries)

    def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """
        Store a memory entry.
        
        This creates/updates a JSON file in the memory directory and
        updates the MEMORY.md index.
        
        Args:
            key: Unique identifier for this memory
            value: The memory content (must be JSON-serializable)
            memory_type: Type of memory (working, episodic, semantic, general)
            metadata: Additional metadata to store
            
        Raises:
            MemoryAccessError: If storage fails
        """
        try:
            now = time.time()
            
            # Check if entry exists
            existing = self._index.entries.get(key)
            created_at = existing.created_at if existing else now
            
            # Create entry
            entry = MemoryEntry(
                key=key,
                value=value,
                memory_type=memory_type,
                created_at=created_at,
                updated_at=now,
                metadata=metadata or {},
            )
            
            # Write to file
            file_path = self._memory_dir / f"{self._slugify(key)}.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(entry.to_dict(), f, ensure_ascii=False, indent=2)
            
            # Update index
            self._index.entries[key] = entry
            self._index.updated_at = now
            self._save_index()
            
            log.debug("Stored memory entry: %s", key)
            
        except Exception as e:
            raise MemoryAccessError(
                operation="store",
                message=str(e),
                path=key,
            )

    def retrieve(
        self,
        key: str,
        default: Any = None,
        update_access: bool = True,
    ) -> Any:
        """
        Retrieve a memory entry by key.
        
        Args:
            key: Memory key to retrieve
            default: Default value if key not found
            update_access: Whether to update access statistics
            
        Returns:
            The memory value, or default if not found
        """
        if update_access:
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
            self._last_access[key] = time.time()
        
        entry = self._index.entries.get(key)
        if entry is None:
            return default
        
        # Try to load from file if not in index
        if entry.value is None:
            file_path = self._memory_dir / f"{self._slugify(key)}.json"
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8") as f:
                        data = json.load(f)
                    entry = MemoryEntry.from_dict(data)
                    self._index.entries[key] = entry
                except Exception:
                    return default
        
        return entry.value if entry else default

    def retrieve_entry(self, key: str) -> MemoryEntry | None:
        """
        Retrieve full memory entry (including metadata).
        
        Args:
            key: Memory key
            
        Returns:
            MemoryEntry or None if not found
        """
        return self._index.entries.get(key)

    def delete(self, key: str) -> bool:
        """
        Delete a memory entry.
        
        Args:
            key: Memory key to delete
            
        Returns:
            True if deleted, False if not found
        """
        try:
            # Remove file
            file_path = self._memory_dir / f"{self._slugify(key)}.json"
            if file_path.exists():
                file_path.unlink()
            
            # Remove from index
            if key in self._index.entries:
                del self._index.entries[key]
                self._index.updated_at = time.time()
                self._save_index()
                return True
            
            return False
            
        except Exception as e:
            raise MemoryAccessError(
                operation="delete",
                message=str(e),
                path=key,
            )

    def search(
        self,
        query: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """
        Search memory entries.
        
        This performs a simple text search across keys, values, and metadata.
        
        Args:
            query: Search query string
            memory_type: Optional filter by memory type
            limit: Maximum number of results
            
        Returns:
            List of matching MemoryEntry objects
        """
        results = []
        query_lower = query.lower()
        
        for entry in self._index.entries.values():
            # Filter by type
            if memory_type and entry.memory_type != memory_type:
                continue
            
            # Search in key
            if query_lower in entry.key.lower():
                results.append(entry)
                continue
            
            # Search in value
            value_str = json.dumps(entry.value, ensure_ascii=False).lower()
            if query_lower in value_str:
                results.append(entry)
                continue
            
            # Search in metadata
            metadata_str = json.dumps(entry.metadata, ensure_ascii=False).lower()
            if query_lower in metadata_str:
                results.append(entry)
        
        # Sort by relevance (key match > value match) and recency
        def relevance(entry: MemoryEntry) -> tuple[int, float]:
            key_match = query_lower in entry.key.lower()
            return (1 if key_match else 0, entry.updated_at)
        
        results.sort(key=relevance, reverse=True)
        
        return results[:limit]

    def list_entries(
        self,
        memory_type: str | None = None,
        include_metadata: bool = False,
    ) -> list[dict[str, Any]]:
        """
        List all memory entries.
        
        Args:
            memory_type: Optional filter by type
            include_metadata: Whether to include full metadata
            
        Returns:
            List of memory entry summaries
        """
        entries = []
        
        for entry in self._index.entries.values():
            if memory_type and entry.memory_type != memory_type:
                continue
            
            data = {
                "key": entry.key,
                "memory_type": entry.memory_type,
                "updated_at": entry.updated_at,
                "access_count": self._access_counts.get(entry.key, 0),
            }
            
            if include_metadata:
                data["metadata"] = entry.metadata
                data["created_at"] = entry.created_at
            
            entries.append(data)
        
        # Sort by most recently updated
        entries.sort(key=lambda x: x["updated_at"], reverse=True)
        
        return entries

    def compact(self, threshold: int | None = None) -> int:
        """
        Compact memory by removing old entries.
        
        This keeps frequently accessed entries and removes stale ones.
        
        Args:
            threshold: Maximum number of entries to keep
            
        Returns:
            Number of entries removed
        """
        threshold = threshold or self._config.max_memory_files
        removed = 0
        
        if len(self._index.entries) <= threshold:
            return 0
        
        # Score entries by relevance
        now = time.time()
        scores = []
        
        for key, entry in self._index.entries.items():
            access_count = self._access_counts.get(key, 0)
            last_access = self._last_access.get(key, 0)
            
            # Higher score = more important
            score = (
                access_count * 10 +  # Access frequency
                (now - entry.updated_at) / 3600 * -0.5 +  # Recency bonus
                (now - last_access) / 3600 * -0.3  # Recent access bonus
            )
            
            scores.append((key, score))
        
        # Keep top threshold entries
        scores.sort(key=lambda x: x[1], reverse=True)
        keep_keys = set(k for k, _ in scores[:threshold])
        
        # Delete entries not in keep set
        for key in list(self._index.entries.keys()):
            if key not in keep_keys:
                self.delete(key)
                removed += 1
        
        log.info("Memory compaction removed %d entries", removed)
        
        return removed

    def get_prompt_section(self, max_lines: int = 200) -> str:
        """
        Generate memory section for system prompt.
        
        This creates the memory content that should be included
        in system prompts for context.
        
        Args:
            max_lines: Maximum lines to include
            
        Returns:
            Formatted memory section string
        """
        lines = [
            "# Memory",
            f"- Persistent memory directory: {self._memory_dir}",
            "- Use this directory to store durable user or project context.",
            "",
        ]
        
        # Add index entries
        if self._index.entries:
            lines.append("## Current Memory Index\n")
            
            by_type: dict[str, list[MemoryEntry]] = {}
            for entry in self._index.entries.values():
                by_type.setdefault(entry.memory_type, []).append(entry)
            
            for memory_type in sorted(by_type.keys()):
                lines.append(f"### {memory_type.replace('_', ' ').title()}")
                for entry in by_type[memory_type]:
                    preview = MemoryIndex._preview(entry.value, max_len=80)
                    lines.append(f"- {entry.key}: {preview}")
                lines.append("")
        
        # Add entrypoint content if exists
        entrypoint = get_memory_entrypoint(self._cwd) if OPENHARNESS_AVAILABLE else None
        if entrypoint and entrypoint.exists():
            content_lines = entrypoint.read_text(encoding="utf-8").splitlines()[:max_lines]
            if content_lines:
                lines.extend(["", "## MEMORY.md", "```md", *content_lines, "```"])
        
        return "\n".join(lines[:max_lines])

    def _load_index(self) -> MemoryIndex:
        """Load or create memory index."""
        index_path = self._memory_dir / "memory_index.json"
        
        if index_path.exists():
            try:
                with open(index_path, encoding="utf-8") as f:
                    data = json.load(f)
                
                entries = {
                    k: MemoryEntry.from_dict(v)
                    for k, v in data.get("entries", {}).items()
                }
                
                return MemoryIndex(
                    entries=entries,
                    updated_at=data.get("updated_at", time.time()),
                )
            except Exception as e:
                log.warning("Failed to load memory index: %s", e)
        
        return MemoryIndex()

    def _save_index(self) -> None:
        """Save memory index to disk."""
        index_path = self._memory_dir / "memory_index.json"
        
        data = {
            "updated_at": self._index.updated_at,
            "entries": {
                k: v.to_dict() for k, v in self._index.entries.items()
            },
        }
        
        with open(index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to filename-safe slug."""
        import re
        return re.sub(r"[^a-zA-Z0-9]+", "_", text.lower()).strip("_")

    def get_statistics(self) -> dict[str, Any]:
        """Get memory statistics."""
        total_access = sum(self._access_counts.values())
        
        by_type: dict[str, int] = {}
        for entry in self._index.entries.values():
            by_type[entry.memory_type] = by_type.get(entry.memory_type, 0) + 1
        
        return {
            "total_entries": len(self._index.entries),
            "total_accesses": total_access,
            "entries_by_type": by_type,
            "memory_dir": str(self._memory_dir),
            "config_max_entries": self._config.max_memory_files,
        }
