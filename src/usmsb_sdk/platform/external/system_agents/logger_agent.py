"""
Logger Agent Module

Provides centralized logging capabilities including:
    - Log collection from multiple sources
    - Log filtering and search
    - Log analysis and aggregation
    - Log export and archival

Skills:
    - log: Record a log entry
    - query: Query logs with filters
    - export: Export logs to file
    - analyze: Analyze log patterns
"""

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set
import asyncio
import json
import logging
import os
import re
from collections import defaultdict

from usmsb_sdk.agent_sdk.agent_config import (
    AgentConfig,
    CapabilityDefinition,
    SkillDefinition,
    SkillParameter,
)
from usmsb_sdk.agent_sdk.communication import Message, MessageType, Session
from usmsb_sdk.platform.external.system_agents.base_system_agent import (
    BaseSystemAgent,
    SystemAgentConfig,
    SystemAgentPermission,
)


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class LogEntry:
    """Represents a single log entry"""

    def __init__(
        self,
        log_id: str,
        level: LogLevel,
        source: str,
        message: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ):
        self.log_id = log_id
        self.level = level
        self.source = source
        self.message = message
        self.timestamp = timestamp or datetime.now()
        self.metadata = metadata or {}
        self.tags = tags or []
        self.processed = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "log_id": self.log_id,
            "level": self.level.value,
            "source": self.source,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
            "tags": self.tags,
            "processed": self.processed,
        }

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict())

    def matches_filter(
        self,
        level_filter: Optional[Set[LogLevel]] = None,
        source_filter: Optional[Set[str]] = None,
        message_pattern: Optional[str] = None,
        tags_filter: Optional[Set[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> bool:
        """Check if entry matches filter criteria"""
        if level_filter and self.level not in level_filter:
            return False

        if source_filter and self.source not in source_filter:
            return False

        if message_pattern and not re.search(message_pattern, self.message, re.IGNORECASE):
            return False

        if tags_filter and not tags_filter.intersection(set(self.tags)):
            return False

        if start_time and self.timestamp < start_time:
            return False

        if end_time and self.timestamp > end_time:
            return False

        return True


class LogStatistics:
    """Statistics for log analysis"""

    def __init__(self):
        self.total_entries = 0
        self.by_level: Dict[LogLevel, int] = defaultdict(int)
        self.by_source: Dict[str, int] = defaultdict(int)
        self.by_hour: Dict[int, int] = defaultdict(int)
        self.error_count = 0
        self.warning_count = 0
        self.first_entry: Optional[datetime] = None
        self.last_entry: Optional[datetime] = None
        self.top_sources: List[tuple] = []
        self.common_patterns: List[tuple] = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "total_entries": self.total_entries,
            "by_level": {k.value: v for k, v in self.by_level.items()},
            "by_source": dict(self.by_source),
            "by_hour": dict(self.by_hour),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "first_entry": self.first_entry.isoformat() if self.first_entry else None,
            "last_entry": self.last_entry.isoformat() if self.last_entry else None,
            "top_sources": self.top_sources,
            "common_patterns": self.common_patterns,
        }


class LogBuffer:
    """Circular buffer for log storage"""

    def __init__(self, max_size: int = 10000):
        self.max_size = max_size
        self._buffer: List[LogEntry] = []
        self._index = 0

    def append(self, entry: LogEntry) -> None:
        """Add entry to buffer"""
        if len(self._buffer) < self.max_size:
            self._buffer.append(entry)
        else:
            self._buffer[self._index] = entry
            self._index = (self._index + 1) % self.max_size

    def get_all(self) -> List[LogEntry]:
        """Get all entries in chronological order"""
        if len(self._buffer) < self.max_size:
            return list(self._buffer)

        # Buffer is full, need to reorder
        return self._buffer[self._index:] + self._buffer[:self._index]

    def get_recent(self, count: int) -> List[LogEntry]:
        """Get most recent entries"""
        all_entries = self.get_all()
        return all_entries[-count:]

    def clear(self) -> None:
        """Clear the buffer"""
        self._buffer.clear()
        self._index = 0

    def __len__(self) -> int:
        return len(self._buffer)


class LoggerAgent(BaseSystemAgent):
    """
    Centralized logging agent for log collection, analysis, and management.

    This agent provides comprehensive logging services including:
    - Log collection from multiple sources
    - Advanced filtering and search
    - Statistical analysis
    - Export and archival capabilities

    Skills:
        - log: Record a log entry
        - query: Query logs with filters
        - export: Export logs to file
        - analyze: Analyze log patterns

    Example:
        config = AgentConfig(
            agent_id="logger-001",
            name="CentralLogger",
            # ... other config
        )
        logger_agent = LoggerAgent(config)
        await logger_agent.start()

        # Log an entry
        await logger_agent.call_skill("log", {
            "level": "info",
            "source": "my-agent",
            "message": "Task completed successfully",
            "tags": ["task", "success"]
        })
    """

    SYSTEM_AGENT_TYPE = "logger"

    def __init__(
        self,
        config: AgentConfig,
        system_config: Optional[SystemAgentConfig] = None,
    ):
        """Initialize the logger agent"""
        super().__init__(config, system_config)

        # Log storage
        self._log_buffer = LogBuffer(max_size=50000)
        self._log_counter = 0
        self._log_lock = asyncio.Lock()

        # Archive settings
        self._archive_path = "./logs/archive"
        self._archive_enabled = True
        self._archive_interval = timedelta(hours=24)

        # Statistics cache
        self._stats_cache: Optional[LogStatistics] = None
        self._stats_cache_time: Optional[datetime] = None

        # Pattern tracking for analysis
        self._pattern_counts: Dict[str, int] = defaultdict(int)

        # Register logger skills
        self._register_logger_skills()

    def _register_logger_skills(self) -> None:
        """Register logger skills"""
        skills = [
            SkillDefinition(
                name="log",
                description="Record a log entry",
                parameters=[
                    SkillParameter(
                        name="level",
                        type="string",
                        description="Log level",
                        required=True,
                        enum=["debug", "info", "warning", "error", "critical"],
                    ),
                    SkillParameter(
                        name="source",
                        type="string",
                        description="Source identifier",
                        required=True,
                    ),
                    SkillParameter(
                        name="message",
                        type="string",
                        description="Log message",
                        required=True,
                    ),
                    SkillParameter(
                        name="metadata",
                        type="object",
                        description="Additional metadata",
                        required=False,
                    ),
                    SkillParameter(
                        name="tags",
                        type="array",
                        description="Tags for categorization",
                        required=False,
                    ),
                ],
                returns="dict",
                tags=["logging", "recording"],
            ),
            SkillDefinition(
                name="query",
                description="Query logs with filters",
                parameters=[
                    SkillParameter(
                        name="levels",
                        type="array",
                        description="Filter by log levels",
                        required=False,
                    ),
                    SkillParameter(
                        name="sources",
                        type="array",
                        description="Filter by sources",
                        required=False,
                    ),
                    SkillParameter(
                        name="message_pattern",
                        type="string",
                        description="Regex pattern for message",
                        required=False,
                    ),
                    SkillParameter(
                        name="tags",
                        type="array",
                        description="Filter by tags (any match)",
                        required=False,
                    ),
                    SkillParameter(
                        name="start_time",
                        type="string",
                        description="Start time (ISO format)",
                        required=False,
                    ),
                    SkillParameter(
                        name="end_time",
                        type="string",
                        description="End time (ISO format)",
                        required=False,
                    ),
                    SkillParameter(
                        name="limit",
                        type="integer",
                        description="Maximum results",
                        required=False,
                        default=100,
                    ),
                    SkillParameter(
                        name="offset",
                        type="integer",
                        description="Result offset for pagination",
                        required=False,
                        default=0,
                    ),
                    SkillParameter(
                        name="sort_order",
                        type="string",
                        description="Sort order: 'asc' or 'desc'",
                        required=False,
                        default="desc",
                        enum=["asc", "desc"],
                    ),
                ],
                returns="dict",
                tags=["query", "search"],
            ),
            SkillDefinition(
                name="export",
                description="Export logs to file",
                parameters=[
                    SkillParameter(
                        name="format",
                        type="string",
                        description="Export format",
                        required=False,
                        default="json",
                        enum=["json", "csv", "txt"],
                    ),
                    SkillParameter(
                        name="levels",
                        type="array",
                        description="Filter by log levels",
                        required=False,
                    ),
                    SkillParameter(
                        name="sources",
                        type="array",
                        description="Filter by sources",
                        required=False,
                    ),
                    SkillParameter(
                        name="start_time",
                        type="string",
                        description="Start time (ISO format)",
                        required=False,
                    ),
                    SkillParameter(
                        name="end_time",
                        type="string",
                        description="End time (ISO format)",
                        required=False,
                    ),
                    SkillParameter(
                        name="output_path",
                        type="string",
                        description="Output file path",
                        required=False,
                    ),
                ],
                returns="dict",
                tags=["export", "file"],
            ),
            SkillDefinition(
                name="analyze",
                description="Analyze log patterns and statistics",
                parameters=[
                    SkillParameter(
                        name="analysis_type",
                        type="string",
                        description="Type of analysis",
                        required=False,
                        default="summary",
                        enum=["summary", "patterns", "anomalies", "trends"],
                    ),
                    SkillParameter(
                        name="time_range",
                        type="integer",
                        description="Time range in hours",
                        required=False,
                        default=24,
                    ),
                    SkillParameter(
                        name="source",
                        type="string",
                        description="Analyze specific source",
                        required=False,
                    ),
                ],
                returns="dict",
                tags=["analysis", "statistics"],
            ),
        ]

        for skill in skills:
            self.register_skill(skill)

    # ==================== Lifecycle Methods ====================

    async def initialize(self) -> None:
        """Initialize the logger agent"""
        self.logger.info("Initializing Logger Agent")

        # Register capabilities
        capabilities = [
            CapabilityDefinition(
                name="log_collection",
                description="Collect logs from multiple sources",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="log_query",
                description="Query and search logs",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="log_analysis",
                description="Analyze log patterns",
                version="1.0.0",
            ),
            CapabilityDefinition(
                name="log_export",
                description="Export logs to various formats",
                version="1.0.0",
            ),
        ]

        for cap in capabilities:
            self.add_capability(cap)

        # Create archive directory if needed
        if self._archive_enabled:
            os.makedirs(self._archive_path, exist_ok=True)

    async def handle_message(
        self,
        message: Message,
        session: Optional[Session] = None
    ) -> Optional[Message]:
        """Handle incoming messages"""
        await self.audit_operation("message_received", {
            "message_type": message.type.value if hasattr(message.type, 'value') else str(message.type),
            "sender": message.sender_id,
        })

        content = message.content if isinstance(message.content, dict) else {"data": message.content}

        # Handle log entries from other agents
        if content.get("type") == "log_entry":
            await self._record_log_entry(
                level=content.get("level", "info"),
                source=message.sender_id,
                message=content.get("message", ""),
                metadata=content.get("metadata"),
                tags=content.get("tags"),
            )
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "logged"},
            )

        # Handle bulk log submissions
        if content.get("type") == "bulk_log":
            entries = content.get("entries", [])
            for entry in entries:
                await self._record_log_entry(
                    level=entry.get("level", "info"),
                    source=entry.get("source", message.sender_id),
                    message=entry.get("message", ""),
                    metadata=entry.get("metadata"),
                    tags=entry.get("tags"),
                )
            return Message(
                type=MessageType.RESPONSE,
                sender_id=self.agent_id,
                receiver_id=message.sender_id,
                content={"status": "logged", "count": len(entries)},
            )

        return None

    async def execute_skill(self, skill_name: str, params: Dict[str, Any]) -> Any:
        """Execute logger skills"""
        await self.audit_operation("skill_execution", {
            "skill": skill_name,
        })

        if skill_name == "log":
            return await self._skill_log(params)
        elif skill_name == "query":
            return await self._skill_query(params)
        elif skill_name == "export":
            return await self._skill_export(params)
        elif skill_name == "analyze":
            return await self._skill_analyze(params)
        else:
            raise ValueError(f"Unknown skill: {skill_name}")

    async def shutdown(self) -> None:
        """Shutdown the logger agent"""
        self.logger.info("Shutting down Logger Agent")

        # Archive remaining logs
        if self._archive_enabled and len(self._log_buffer) > 0:
            await self._archive_logs()

    # ==================== Skill Implementations ====================

    async def _skill_log(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute log skill"""
        level_str = params.get("level", "info")
        source = params.get("source", "unknown")
        message = params.get("message")
        metadata = params.get("metadata")
        tags = params.get("tags", [])

        if not message:
            raise ValueError("message is required")

        entry = await self._record_log_entry(
            level=level_str,
            source=source,
            message=message,
            metadata=metadata,
            tags=tags,
        )

        return {
            "status": "success",
            "log_id": entry.log_id,
            "timestamp": entry.timestamp.isoformat(),
        }

    async def _skill_query(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute query skill"""
        levels = params.get("levels")
        sources = params.get("sources")
        message_pattern = params.get("message_pattern")
        tags = params.get("tags")
        start_time_str = params.get("start_time")
        end_time_str = params.get("end_time")
        limit = params.get("limit", 100)
        offset = params.get("offset", 0)
        sort_order = params.get("sort_order", "desc")

        # Parse time filters
        start_time = None
        end_time = None
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str)

        # Convert filters to sets
        level_filter = {LogLevel(l) for l in levels} if levels else None
        source_filter = set(sources) if sources else None
        tags_filter = set(tags) if tags else None

        # Query logs
        all_entries = self._log_buffer.get_all()

        # Filter entries
        filtered = [
            entry for entry in all_entries
            if entry.matches_filter(
                level_filter=level_filter,
                source_filter=source_filter,
                message_pattern=message_pattern,
                tags_filter=tags_filter,
                start_time=start_time,
                end_time=end_time,
            )
        ]

        # Sort
        reverse = sort_order == "desc"
        filtered.sort(key=lambda e: e.timestamp, reverse=reverse)

        # Total count before pagination
        total_count = len(filtered)

        # Paginate
        paginated = filtered[offset:offset + limit]

        return {
            "total_count": total_count,
            "returned_count": len(paginated),
            "offset": offset,
            "limit": limit,
            "entries": [e.to_dict() for e in paginated],
        }

    async def _skill_export(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute export skill"""
        self.require_permission(SystemAgentPermission.CONFIGURE)

        format_type = params.get("format", "json")
        levels = params.get("levels")
        sources = params.get("sources")
        start_time_str = params.get("start_time")
        end_time_str = params.get("end_time")
        output_path = params.get("output_path")

        # Parse time filters
        start_time = None
        end_time = None
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str)

        # Convert filters
        level_filter = {LogLevel(l) for l in levels} if levels else None
        source_filter = set(sources) if sources else None

        # Get filtered entries
        all_entries = self._log_buffer.get_all()
        filtered = [
            entry for entry in all_entries
            if entry.matches_filter(
                level_filter=level_filter,
                source_filter=source_filter,
                start_time=start_time,
                end_time=end_time,
            )
        ]

        # Generate output path if not provided
        if not output_path:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extension = {"json": "json", "csv": "csv", "txt": "log"}[format_type]
            output_path = os.path.join(self._archive_path, f"logs_export_{timestamp}.{extension}")

        # Export based on format
        if format_type == "json":
            content = json.dumps([e.to_dict() for e in filtered], indent=2)
        elif format_type == "csv":
            lines = ["log_id,timestamp,level,source,message"]
            for entry in filtered:
                msg = entry.message.replace('"', '""')
                lines.append(f'{entry.log_id},{entry.timestamp.isoformat()},{entry.level.value},"{entry.source}","{msg}"')
            content = "\n".join(lines)
        else:  # txt
            lines = []
            for entry in filtered:
                lines.append(f"[{entry.timestamp.isoformat()}] [{entry.level.value.upper():8}] [{entry.source}] {entry.message}")
            content = "\n".join(lines)

        # Write to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)

        await self.audit_operation("logs_exported", {
            "format": format_type,
            "entry_count": len(filtered),
            "output_path": output_path,
        })

        return {
            "status": "success",
            "format": format_type,
            "entry_count": len(filtered),
            "output_path": output_path,
            "file_size_bytes": len(content.encode("utf-8")),
        }

    async def _skill_analyze(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute analyze skill"""
        analysis_type = params.get("analysis_type", "summary")
        time_range = params.get("time_range", 24)
        source_filter = params.get("source")

        cutoff_time = datetime.now() - timedelta(hours=time_range)

        # Get entries within time range
        all_entries = self._log_buffer.get_all()
        entries = [
            e for e in all_entries
            if e.timestamp >= cutoff_time and (not source_filter or e.source == source_filter)
        ]

        if analysis_type == "summary":
            return self._analyze_summary(entries, time_range)
        elif analysis_type == "patterns":
            return self._analyze_patterns(entries)
        elif analysis_type == "anomalies":
            return self._analyze_anomalies(entries)
        elif analysis_type == "trends":
            return self._analyze_trends(entries, time_range)
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

    # ==================== Internal Methods ====================

    async def _record_log_entry(
        self,
        level: str,
        source: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> LogEntry:
        """Record a log entry"""
        async with self._log_lock:
            self._log_counter += 1
            log_id = f"log-{self._log_counter:08d}"

            try:
                log_level = LogLevel(level.lower())
            except ValueError:
                log_level = LogLevel.INFO

            entry = LogEntry(
                log_id=log_id,
                level=log_level,
                source=source,
                message=message,
                metadata=metadata,
                tags=tags or [],
            )

            self._log_buffer.append(entry)

            # Update pattern tracking
            self._update_pattern_tracking(message)

            # Invalidate stats cache
            self._stats_cache = None

            # Log to internal logger as well
            if log_level == LogLevel.DEBUG:
                self.logger.debug(f"[{source}] {message}")
            elif log_level == LogLevel.INFO:
                self.logger.info(f"[{source}] {message}")
            elif log_level == LogLevel.WARNING:
                self.logger.warning(f"[{source}] {message}")
            elif log_level == LogLevel.ERROR:
                self.logger.error(f"[{source}] {message}")
            elif log_level == LogLevel.CRITICAL:
                self.logger.critical(f"[{source}] {message}")

            return entry

    def _update_pattern_tracking(self, message: str) -> None:
        """Track common message patterns"""
        # Simple pattern extraction (first few words)
        words = message.split()[:5]
        if len(words) >= 2:
            pattern = " ".join(words[:3])
            self._pattern_counts[pattern] += 1

    def _analyze_summary(self, entries: List[LogEntry], time_range: int) -> Dict[str, Any]:
        """Generate summary statistics"""
        stats = LogStatistics()

        for entry in entries:
            stats.total_entries += 1
            stats.by_level[entry.level] += 1
            stats.by_source[entry.source] += 1
            stats.by_hour[entry.timestamp.hour] += 1

            if entry.level == LogLevel.ERROR or entry.level == LogLevel.CRITICAL:
                stats.error_count += 1
            elif entry.level == LogLevel.WARNING:
                stats.warning_count += 1

            if stats.first_entry is None or entry.timestamp < stats.first_entry:
                stats.first_entry = entry.timestamp
            if stats.last_entry is None or entry.timestamp > stats.last_entry:
                stats.last_entry = entry.timestamp

        # Top sources
        stats.top_sources = sorted(
            stats.by_source.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        # Common patterns
        stats.common_patterns = sorted(
            self._pattern_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]

        return {
            "analysis_type": "summary",
            "time_range_hours": time_range,
            "statistics": stats.to_dict(),
        }

    def _analyze_patterns(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Analyze log patterns"""
        # Group by message patterns
        pattern_groups: Dict[str, List[LogEntry]] = defaultdict(list)

        for entry in entries:
            # Create pattern key from first words
            words = entry.message.split()[:3]
            if words:
                pattern_key = " ".join(words)
                pattern_groups[pattern_key].append(entry)

        # Sort by frequency
        sorted_patterns = sorted(
            pattern_groups.items(),
            key=lambda x: len(x[1]),
            reverse=True
        )[:20]

        return {
            "analysis_type": "patterns",
            "total_patterns": len(pattern_groups),
            "top_patterns": [
                {
                    "pattern": pattern,
                    "count": len(group),
                    "sources": list(set(e.source for e in group)),
                    "levels": list(set(e.level.value for e in group)),
                    "sample_message": group[0].message if group else None,
                }
                for pattern, group in sorted_patterns
            ],
        }

    def _analyze_anomalies(self, entries: List[LogEntry]) -> Dict[str, Any]:
        """Detect log anomalies"""
        anomalies = []

        # Check for error spikes
        error_times: Dict[int, int] = defaultdict(int)
        for entry in entries:
            if entry.level in (LogLevel.ERROR, LogLevel.CRITICAL):
                hour_key = entry.timestamp.hour
                error_times[hour_key] += 1

        # Calculate average
        if error_times:
            avg_errors = sum(error_times.values()) / len(error_times)
            threshold = avg_errors * 2  # 2x average is anomalous

            for hour, count in error_times.items():
                if count > threshold:
                    anomalies.append({
                        "type": "error_spike",
                        "hour": hour,
                        "count": count,
                        "average": avg_errors,
                        "deviation": (count - avg_errors) / avg_errors if avg_errors > 0 else 0,
                    })

        # Check for unusual sources
        source_counts: Dict[str, int] = defaultdict(int)
        for entry in entries:
            source_counts[entry.source] += 1

        if source_counts:
            avg_count = sum(source_counts.values()) / len(source_counts)
            for source, count in source_counts.items():
                if count > avg_count * 5:  # 5x average
                    anomalies.append({
                        "type": "high_volume_source",
                        "source": source,
                        "count": count,
                        "average": avg_count,
                    })

        return {
            "analysis_type": "anomalies",
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
        }

    def _analyze_trends(self, entries: List[LogEntry], time_range: int) -> Dict[str, Any]:
        """Analyze log trends over time"""
        # Group by hour
        hourly_data: Dict[int, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

        for entry in entries:
            hour = entry.timestamp.hour
            hourly_data[hour]["total"] += 1
            hourly_data[hour][entry.level.value] += 1

        # Calculate trends
        hours = sorted(hourly_data.keys())
        if len(hours) >= 2:
            first_half = hours[:len(hours) // 2]
            second_half = hours[len(hours) // 2:]

            first_total = sum(hourly_data[h]["total"] for h in first_half)
            second_total = sum(hourly_data[h]["total"] for h in second_half)

            if first_total > 0:
                trend_percentage = ((second_total - first_total) / first_total) * 100
            else:
                trend_percentage = 0
        else:
            trend_percentage = 0

        return {
            "analysis_type": "trends",
            "time_range_hours": time_range,
            "trend_percentage": trend_percentage,
            "trend_direction": "increasing" if trend_percentage > 10 else "decreasing" if trend_percentage < -10 else "stable",
            "hourly_breakdown": [
                {
                    "hour": hour,
                    "total": data["total"],
                    "by_level": {k: v for k, v in data.items() if k != "total"},
                }
                for hour, data in sorted(hourly_data.items())
            ],
        }

    async def _archive_logs(self) -> None:
        """Archive current logs to file"""
        if not self._archive_enabled:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_file = os.path.join(self._archive_path, f"logs_archive_{timestamp}.json")

        entries = self._log_buffer.get_all()
        content = json.dumps([e.to_dict() for e in entries], indent=2)

        with open(archive_file, "w", encoding="utf-8") as f:
            f.write(content)

        self.logger.info(f"Archived {len(entries)} logs to {archive_file}")

    # ==================== Public Helper Methods ====================

    def get_log_count(self) -> int:
        """Get total log count"""
        return len(self._log_buffer)

    def clear_logs(self) -> None:
        """Clear all logs (requires admin permission)"""
        self.require_permission(SystemAgentPermission.ADMIN)
        self._log_buffer.clear()
        self._pattern_counts.clear()
        self._stats_cache = None
        self.logger.info("All logs cleared")

    def set_buffer_size(self, max_size: int) -> None:
        """Set the maximum buffer size"""
        self.require_permission(SystemAgentPermission.CONFIGURE)
        old_buffer = self._log_buffer
        self._log_buffer = LogBuffer(max_size=max_size)

        # Copy existing entries
        for entry in old_buffer.get_all():
            self._log_buffer.append(entry)

        self.logger.info(f"Buffer size changed to {max_size}")
