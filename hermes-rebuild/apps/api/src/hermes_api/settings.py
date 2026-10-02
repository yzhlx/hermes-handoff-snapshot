from typing import Literal

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="HERMES_", env_file=".env", extra="ignore")
    environment: Literal["development", "test", "production"] = "development"
    database_url: str = "sqlite:///./hermes-development.db"
    allowed_origin: str = "http://127.0.0.1:5173"
    cookie_secure: bool = False
    session_hours: int = 24
    attachment_storage: Literal["local", "s3"] = "local"
    attachment_local_root: str = ""
    attachment_s3_bucket: str = ""
    attachment_s3_endpoint: str = ""
    attachment_s3_region: str = ""
    attachment_s3_access_key: SecretStr = SecretStr("")
    attachment_s3_secret_key: SecretStr = SecretStr("")
    attachment_max_pending_per_owner: int = 10
    # 单用户模式：没有会话时自动以唯一用户身份建立登录会话。
    # 目的是让本机 / 自用部署打开即是书房，不必输账号密码。
    # 鉴权、owner 隔离、CSRF 全部照旧，只是省掉登录这一步。
    # 生产环境强制禁止（见下方校验），避免把公网部署变成无鉴权。
    single_user_mode: bool = False

    # AI provider（OpenAI 兼容）。三者齐全才启用真实模型，否则回落确定性 MockModel。
    # 密钥只从环境变量 / 凭据管理器读，绝不入库、不进日志。
    # 变量名与云上部署保持一致（PROVIDER_*），便于同一套 compose env 复用。
    provider_base_url: str = ""
    provider_api_key: SecretStr = SecretStr("")
    provider_model: str = ""
    # 只有确认模型真的支持图片输入时才置 true；否则界面不得暗示可以拍照识题。
    provider_supports_image: bool = False
    provider_timeout_seconds: int = 60
    # 推理型模型（deepseek-flash 等）先产出 reasoning_content 且与正文共用这份预算；
    # 给太小会导致 content 为空字符串。默认 2048 覆盖推理 + 正文。
    provider_max_tokens: int = 2048

    @model_validator(mode="after")
    def production_guards(self):
        if self.environment == "production":
            if self.single_user_mode:
                raise ValueError("Production cannot enable single-user auto sign-in.")
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires PostgreSQL psycopg.")
            if not self.cookie_secure or not self.allowed_origin.startswith("https://"):
                raise ValueError("Production requires secure cookies and an HTTPS origin.")
            if self.attachment_storage != "s3" or not self.attachment_s3_bucket:
                raise ValueError("Production requires configured private S3 attachment storage.")
        if not 1 <= self.session_hours <= 168:
            raise ValueError("Session lifetime must be 1-168 hours.")
        return self
