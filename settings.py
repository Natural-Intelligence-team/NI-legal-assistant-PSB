import math
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values


@dataclass(frozen=True)
class Settings:
    base_url: str = ""
    api_key: str = field(default="", repr=False)
    model: str = ""
    temperature: float = 0.0
    max_tokens: int = 2200
    timeout: float = 40.0
    data_dir: Path = Path("data")
    max_workers: int = 4

    @classmethod
    def from_env(cls) -> "Settings":
        local = dotenv_values(Path(__file__).resolve().parent / ".env")

        def read(*names: str, default: str = "") -> str:
            for values in (os.environ, local):
                for name in names:
                    value = (values.get(name) or "").strip()
                    if value and value != name:
                        return value
            return default

        def number(key: str, default: float, lower: float, upper: float) -> float:
            try:
                value = float(read(key, default=str(default)))
            except ValueError:
                return default
            return min(upper, max(lower, value)) if math.isfinite(value) else default

        def integer(key: str, default: int, lower: int, upper: int) -> int:
            try:
                value = int(read(key, default=str(default)))
            except ValueError:
                return default
            return min(upper, max(lower, value))

        return cls(
            base_url=read("LLM_BASE_URL", "OPENAI_BASE_URL").rstrip("/"),
            api_key=read("LLM_API_KEY", "OPENAI_API_KEY"),
            model=read("LLM_MODEL", "OPENAI_MODEL", "GEN_MODEL"),
            temperature=number("TEMPERATURE", 0.0, 0.0, 2.0),
            max_tokens=integer("MAX_TOKENS", 2200, 128, 8192),
            timeout=number("LLM_TIMEOUT", 40.0, 1.0, 90.0),
            data_dir=Path(read("DATA_DIR", default="data")),
            max_workers=integer("MAX_WORKERS", 4, 1, 8),
        )

    @property
    def model_configured(self) -> bool:
        return bool(self.base_url and self.api_key and self.model)
