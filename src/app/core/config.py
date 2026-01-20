"""
Application configuration settings loaded from config.yaml
"""
import yaml
from pathlib import Path
from typing import List, Optional, Dict
from pydantic import BaseModel, AnyHttpUrl, field_validator


class DatabasePoolConfig(BaseModel):
    """Database connection pool configuration"""
    size: int = 10  # Number of connections to maintain
    max_overflow: int = 20  # Maximum overflow connections
    timeout: int = 30  # Seconds to wait for a connection
    recycle: int = 3600  # Seconds before recycling a connection
    echo: bool = False  # Log SQL queries


class DatabaseConfig(BaseModel):
    """Database configuration"""
    server: str
    user: str
    password: str
    db: str
    port: str = "5432"
    schema: str = "public"  # PostgreSQL schema name
    pool: DatabasePoolConfig = DatabasePoolConfig()
    
    @property
    def url(self) -> str:
        """Construct database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.server}:{self.port}/{self.db}"


class CRMConfig(BaseModel):
    """CRM API configuration"""
    base_url: str
    api_key: Optional[str] = None
    api_token: Optional[str] = None
    timeout: int = 30


class LLMConfig(BaseModel):
    """LLM API configuration (OpenAI-compatible)"""
    base_url: str = "https://api.openai.com/v1"
    api_key: Optional[str] = None
    model: str = "gpt-3.5-turbo"
    timeout: int = 60
    max_tokens: int = 1000
    temperature: float = 0.7
    stream: bool = False
    verify_ssl: bool = True  # Verify SSL certificates (set to False for self-signed certs)
    prompts_file: Optional[str] = None  # Path to prompts.yaml (defaults to project root)
    prompt_versions: Optional[Dict[str, str]] = None  # Override default prompt versions per category


class SecurityConfig(BaseModel):
    """Security configuration"""
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


class SalesAgentConfig(BaseModel):
    """Sales agent configuration"""
    id: str
    name: str
    specialization: Optional[str] = None
    expertise: Optional[str] = None
    experience_years: Optional[int] = None
    location: Optional[str] = None
    territory: Optional[str] = None
    current_workload: Optional[int] = None
    success_rate: Optional[int] = None
    vehicle_types: Optional[List[str]] = None
    communication_style: Optional[str] = None


class Settings(BaseModel):
    """Application settings loaded from config.yaml"""
    
    # Project settings
    project_name: str = "Carnance API"
    version: str = "1.0.0"
    description: str = "FastAPI REST API for CRM integration"
    api_v1_str: str = "/api/v1"
    
    # Database settings
    database: DatabaseConfig
    
    @property
    def DATABASE_URL(self) -> str:
        """Construct database URL"""
        return self.database.url
    
    # CRM API settings
    crm: CRMConfig
    
    # LLM API settings
    llm: LLMConfig = LLMConfig()
    
    # CORS settings
    backend_cors_origins: List[str] = []
    
    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, str):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        return []
    
    # Security settings
    security: SecurityConfig
    
    # Sales agents settings
    sales_agents: List[SalesAgentConfig] = []
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        case_sensitive = False


def load_config(config_path: Optional[str] = None) -> Settings:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to config.yaml file. If None, looks for config.yaml in:
                    1. Current directory
                    2. Project root (src/../config.yaml)
    
    Returns:
        Settings: Loaded and validated settings
    """
    if config_path is None:
        # Try current directory first
        current_dir = Path.cwd() / "config.yaml"
        if current_dir.exists():
            config_path = str(current_dir)
        else:
            # Try project root (assuming we're in src/app/core/)
            project_root = Path(__file__).parent.parent.parent.parent / "config.yaml"
            if project_root.exists():
                config_path = str(project_root)
            else:
                raise FileNotFoundError(
                    "config.yaml not found. Please create config.yaml in the project root."
                )
    
    config_file = Path(config_path)
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_file, "r") as f:
        config_data = yaml.safe_load(f)
    
    if config_data is None:
        raise ValueError("Configuration file is empty or invalid")
    
    return Settings(**config_data)


# Load settings on module import
settings = load_config()
