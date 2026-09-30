from dataclasses import dataclass
import hashlib


@dataclass
class Item:
    url: str
    title: str
    summary: str
    source: str
    published: str  # ISO8601 或空
    domain: str
    score: float = 0.0

    @property
    def id(self) -> str:
        return hashlib.sha1(f"{self.domain}|{self.url}".encode()).hexdigest()[:16]
