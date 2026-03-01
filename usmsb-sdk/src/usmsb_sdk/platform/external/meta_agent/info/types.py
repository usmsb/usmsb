from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from enum import Enum


class InfoNeedType(Enum):
    CREDENTIAL = "credential"
    ACCOUNT = "account"
    URL = "url"
    REFERENCE = "reference"
    CONTEXT = "context"
    PARAM = "param"
    OTHER = "other"


@dataclass
class InfoNeed:
    need_id: str
    name: str
    info_type: InfoNeedType
    description: str
    format_hint: str = ""
    validation_hint: str = ""
    required: bool = True
    source: str = "llm"
    need_tool_validation: bool = False
    tool_name: str = ""
    fulfilled: bool = False
    value: Optional[str] = None


@dataclass
class RetrievalIntent:
    info_type: str
    description: str
    format_hint: str = ""
    validation_hint: str = ""
    need_tool_validation: bool = False
    tool_name: str = ""


@dataclass
class CandidateMessage:
    message_id: str
    content: str
    role: str
    timestamp: float
    conversation_title: str = ""


@dataclass
class ExtractedInfo:
    value: str
    confidence: float
    source_message_id: str
    reasoning: str


@dataclass
class ValidationResult:
    is_valid: bool
    validated_value: Optional[str] = None
    method: str = ""
    error: str = ""
    reasoning: str = ""
