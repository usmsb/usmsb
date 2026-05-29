"""
Google A2A AgentCard 类型 - 对齐官方 Spec 1.0
"""

from typing import Any

from pydantic import BaseModel, Field


class AgentCapabilities(BaseModel):
    """
    Agent 能力 - 对齐官方 AgentCapabilities
    """

    streaming: bool = True  # 支持 SSE 流式推送
    push_notifications: bool = False  # 支持推送通知
    extensions: list["AgentExtension"] = Field(default_factory=list)  # 扩展列表
    extended_agent_card: bool = False  # 支持扩展 AgentCard


class AgentExtension(BaseModel):
    """
    Agent 扩展
    """

    uri: str = ""
    description: str = ""
    required: bool = False
    params: dict[str, Any] = Field(default_factory=dict)


class AgentProvider(BaseModel):
    """
    Agent 提供者
    """

    url: str = ""
    organization: str = ""


class AgentInterface(BaseModel):
    """
    Agent 接口
    """

    url: str = ""
    protocol_binding: str = ""
    tenant: str = ""
    protocol_version: str = ""


class AgentSkill(BaseModel):
    """
    Agent 技能 - 对齐官方 AgentSkill
    """

    id: str = ""
    name: str = ""
    description: str = ""
    tags: list[str] = Field(default_factory=list)  # 技能标签
    examples: list[str] = Field(default_factory=list)  # 使用示例
    input_modes: list[str] = Field(default_factory=list)  # 支持的输入模式
    output_modes: list[str] = Field(default_factory=list)  # 支持的输出模式
    security_requirements: list["SecurityRequirement"] = Field(default_factory=list)


class SecurityRequirement(BaseModel):
    """
    安全要求
    """

    schemes: dict[str, list[str]] = Field(default_factory=dict)


class SecurityScheme(BaseModel):
    """
    安全方案 - 对齐官方 SecurityScheme
    """

    api_key_security_scheme: "APIKeySecurityScheme | None" = None
    http_auth_security_scheme: "HTTPAuthSecurityScheme | None" = None
    oauth2_security_scheme: "OAuth2SecurityScheme | None" = None
    open_id_connect_security_scheme: "OpenIdConnectSecurityScheme | None" = None
    mtls_security_scheme: "MutualTlsSecurityScheme | None" = None


class APIKeySecurityScheme(BaseModel):
    """API Key 安全方案"""

    description: str = ""
    location: str = ""  # "header" | "query" | "cookie"
    name: str = ""


class HTTPAuthSecurityScheme(BaseModel):
    """HTTP Auth 安全方案"""

    description: str = ""
    scheme: str = ""  # "basic" | "bearer" | ...
    bearer_format: str = ""


class OAuth2SecurityScheme(BaseModel):
    """OAuth2 安全方案"""

    description: str = ""
    flows: "OAuthFlows" = Field(default_factory=lambda: OAuthFlows())
    oauth2_metadata_url: str = ""


class OAuthFlows(BaseModel):
    """OAuth2 Flows"""

    authorization_code: "AuthorizationCodeOAuthFlow | None" = None
    client_credentials: "ClientCredentialsOAuthFlow | None" = None
    implicit: "ImplicitOAuthFlow | None" = None
    password: "PasswordOAuthFlow | None" = None
    device_code: "DeviceCodeOAuthFlow | None" = None


class AuthorizationCodeOAuthFlow(BaseModel):
    """授权码 OAuth Flow"""

    authorization_url: str = ""
    token_url: str = ""
    refresh_url: str = ""
    scopes: dict[str, str] = Field(default_factory=dict)
    pkce_required: bool = False


class ClientCredentialsOAuthFlow(BaseModel):
    """客户端凭证 OAuth Flow"""

    token_url: str = ""
    refresh_url: str = ""
    scopes: dict[str, str] = Field(default_factory=dict)


class ImplicitOAuthFlow(BaseModel):
    """隐式 OAuth Flow"""

    authorization_url: str = ""
    refresh_url: str = ""
    scopes: dict[str, str] = Field(default_factory=dict)


class PasswordOAuthFlow(BaseModel):
    """密码 OAuth Flow"""

    token_url: str = ""
    refresh_url: str = ""
    scopes: dict[str, str] = Field(default_factory=dict)


class DeviceCodeOAuthFlow(BaseModel):
    """设备码 OAuth Flow"""

    device_authorization_url: str = ""
    token_url: str = ""
    refresh_url: str = ""
    scopes: dict[str, str] = Field(default_factory=dict)


class OpenIdConnectSecurityScheme(BaseModel):
    """OpenID Connect 安全方案"""

    description: str = ""
    open_id_connect_url: str = ""


class MutualTlsSecurityScheme(BaseModel):
    """mTLS 安全方案"""

    description: str = ""


class AgentCardSignature(BaseModel):
    """
    Agent Card 签名
    """

    protected: str = ""
    signature: str = ""
    header: dict[str, Any] = Field(default_factory=dict)


class AgentCard(BaseModel):
    """
    Agent Card - 对齐官方 AgentCard

    用于 Agent 发现和协作。
    端点: GET /.well-known/agent.json

    Example:
        card = AgentCard(
            name="Coding Agent",
            description="Expert at code generation and review",
            version="1.0",
            provider=AgentProvider(organization="USMSB"),
            capabilities=AgentCapabilities(streaming=True),
            skills=[
                AgentSkill(
                    id="python_coding",
                    name="Python Coding",
                    description="Write clean, efficient Python code",
                    tags=["python", "coding"],
                    examples=["Write a FastAPI endpoint"],
                )
            ],
        )
    """

    name: str = ""
    description: str = ""
    supported_interfaces: list[AgentInterface] = Field(default_factory=list)
    provider: AgentProvider = Field(default_factory=AgentProvider)
    version: str = "1.0"
    documentation_url: str = ""
    capabilities: AgentCapabilities = Field(default_factory=AgentCapabilities)
    security_schemes: dict[str, SecurityScheme] = Field(default_factory=dict)
    security_requirements: list[SecurityRequirement] = Field(default_factory=list)
    default_input_modes: list[str] = Field(default_factory=lambda: ["text"])
    default_output_modes: list[str] = Field(default_factory=lambda: ["text"])
    skills: list[AgentSkill] = Field(default_factory=list)
    signatures: list[AgentCardSignature] = Field(default_factory=list)
    icon_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return self.model_dump(mode="json")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AgentCard":
        """从字典创建"""
        return cls.model_validate(data)
