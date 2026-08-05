from functools import lru_cache

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "llm-ops-assistant-backend"
    app_version: str = "0.3.0"
    app_env: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000
    cors_origins: str = "http://127.0.0.1:5173"

    mysql_host: str = "127.0.0.1"
    mysql_port: int = 3306
    mysql_user: str = ""
    mysql_password: SecretStr = SecretStr("")
    mysql_database: str = ""

    jwt_secret_key: SecretStr = SecretStr("")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120

    initial_admin_username: str = ""
    initial_admin_display_name: str = ""
    initial_admin_password: SecretStr = SecretStr("")
    initial_admin_enabled: bool = False

    dify_base_url: str = "https://api.dify.ai/v1"
    dify_app_api_key: SecretStr = SecretStr("")
    dify_timeout_seconds: int = 60

    @field_validator("dify_base_url")
    @classmethod
    def normalize_dify_base_url(cls, value: str) -> str:
        normalized = value.strip().rstrip("/")
        if not normalized:
            raise ValueError("DIFY_BASE_URL 不能为空")
        return normalized

    @model_validator(mode="after")
    def validate_security_config(self) -> "Settings":
        if self.app_env.lower() not in {"development", "test"}:
            if not self.jwt_secret_key.get_secret_value():
                raise ValueError("非开发环境必须配置 JWT_SECRET_KEY")
        if self.jwt_algorithm != "HS256":
            raise ValueError("阶段 2 仅允许 JWT_ALGORITHM=HS256")
        if self.access_token_expire_minutes != 120:
            raise ValueError("阶段 2 Access Token 有效期必须为 120 分钟")
        if self.dify_timeout_seconds != 60:
            raise ValueError("阶段 3 Dify 超时必须为 60 秒")
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_configured(self) -> bool:
        return all(
            (
                self.mysql_host,
                self.mysql_user,
                self.mysql_password.get_secret_value(),
                self.mysql_database,
            )
        )

    @property
    def database_url(self) -> URL:
        return URL.create(
            drivername="mysql+pymysql",
            username=self.mysql_user,
            password=self.mysql_password.get_secret_value(),
            host=self.mysql_host,
            port=self.mysql_port,
            database=self.mysql_database,
            query={"charset": "utf8mb4"},
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
