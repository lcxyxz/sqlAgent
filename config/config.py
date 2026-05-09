# src/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator, model_validator
from typing import Literal, Optional

class DatabaseConfig(BaseSettings):
    provider: Literal["mysql", "sqlite"] = "mysql"
    
    # MySQL 特定配置
    host: Optional[str] = None
    port: Optional[int] = None
    user: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None
    
    # SQLite 特定配置
    sqlite_path: Optional[str] = None

    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    @model_validator(mode='after')
    def validate_db_config(self):
        """根据 provider 验证必填项"""
        if self.provider == "mysql":
            if not all([self.host, self.user, self.database]):
                raise ValueError("MySQL 配置缺少必要字段: host, user, database")
            # 设置默认端口如果未提供
            if self.port is None:
                self.port = 3306
        elif self.provider == "sqlite":
            if not self.sqlite_path:
                raise ValueError("SQLite 配置缺少必要字段: sqlite_path")
        return self

    def get_connection_params(self) -> dict:
        """获取数据库连接参数
        """
        if self.provider == "sqlite":
            return {
                "provider": "sqlite",
                "sqlite_db_path": self.sqlite_path
            }
        else: # mysql
            return {
                "provider": "mysql",
                "host": self.host,
                "port": self.port,
                "user": self.user,
                "password": self.password or "",
                "database": self.database
            }

class LLMConfig(BaseSettings):
    api_key: str
    model: str = "qwen3.5-122b-a10b"
    base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    temperature: float = 0.0
    max_tokens: int = 2000
    timeout: int = 60

    model_config = SettingsConfigDict(env_prefix="LLM_", env_file=".env", extra="ignore")

    @field_validator("api_key")
    def validate_api_key(cls, v):
        if not v:
            raise ValueError("LLM 配置缺少必要字段: api_key")
        return v
    
    @field_validator("model")
    def validate_model(cls, v):
        if not v:
            raise ValueError("LLM 配置缺少必要字段: model")
        return v
    
    @field_validator("base_url")
    def validate_base_url(cls, v):
        if not v:
            raise ValueError("LLM 配置缺少必要字段: base_url")
        return v
    
    def get_config_params(self) -> dict:
        """获取 LLM 配置参数
        """
        return {
            "api_key": self.api_key,
            "model": self.model,
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": self.timeout
        }

class AppConfig(BaseSettings):
    db: DatabaseConfig = DatabaseConfig()
    llm: LLMConfig = LLMConfig()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = AppConfig()



