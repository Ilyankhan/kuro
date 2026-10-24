import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables from project root .env file
_env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)

class KuroConfig(BaseModel):
    """Central configuration for Kuro multi-agent modernization engine."""
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default="gemini-3.8-flash")
    docker_image: str = Field(default="kuro-sandbox")
    max_repair_cycles: int = Field(default=3)
    default_test_cases: int = Field(default=50)
    sandbox_timeout_seconds: int = Field(default=5)
    workspace_root: Path = Field(default_factory=lambda: Path("/tmp/kuro_workspace"))

settings = KuroConfig()
