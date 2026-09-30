import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class Domain:
    key: str
    name: str
    sources: list[dict]
    keywords: dict[str, float] = field(default_factory=dict)
    exclude: list[str] = field(default_factory=list)
    analyst_role: str = "行业分析师"
    framework: list[str] = field(default_factory=list)
    schedule: str | None = None
    channels: list[str] = field(default_factory=list)


def load_domains(path: str | None = None) -> dict[str, Domain]:
    path = path or os.getenv("INTEL_CONFIG", "config/domains.yaml")
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {k: Domain(key=k, **v) for k, v in raw["domains"].items()}


def env(name: str, default: str = "") -> str:
    return os.getenv(name, default)
