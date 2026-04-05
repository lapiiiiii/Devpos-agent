from pydantic_settings import BaseSettings
from typing import Optional
import os

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
if os.path.exists(dotenv_path):
    from dotenv import load_dotenv
    load_dotenv(dotenv_path)


class Settings(BaseSettings):
    app_name: str = "DevOps Agent"
    debug: bool = True

    openai_api_key: Optional[str] = None
    openai_base_url: str = "https://api.openai.com/v1"

    jira_url: Optional[str] = None
    jira_email: Optional[str] = None
    jira_api_token: Optional[str] = None

    github_token: Optional[str] = None
    github_owner: str = "your-github-owner"
    github_repo: str = "your-repo"

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0

    sqlite_path: str = "./data/devops_agent.db"
    chroma_path: str = "./data/chroma"

    log_level: str = "INFO"

    max_retries: int = 3
    request_timeout: int = 30

    class Config:
        env_file = ".env"
        extra = "allow"


settings = Settings()
