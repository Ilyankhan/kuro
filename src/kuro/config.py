import os
from pathlib import Path
from pydantic import BaseModel, Field

class KuroConfig(BaseModel):
    """Central configuration for Kuro multi-agent modernization engine."""
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default="gemini-2.5-flash")
    docker_image: str = Field(default="kuro-sandbox")
    max_repair_cycles: int = Field(default=3)
    default_test_cases: int = Field(default=50)
    sandbox_timeout_seconds: int = Field(default=5)
    workspace_root: Path = Field(default_factory=lambda: Path("/tmp/kuro_workspace"))

settings = KuroConfig()
