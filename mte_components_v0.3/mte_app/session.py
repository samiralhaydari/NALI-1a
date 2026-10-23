from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


@dataclass
class MTESession:
    title: str = "Untitled Problem"
    problem: str = ""
    matlab_code: str = ""
    python_code: str = ""
    lean_code: str = ""
    matlab_output: str = ""
    python_output: str = ""
    lean_output: str = ""
    lean_verified: bool | None = None

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.write_text(json.dumps(asdict(self), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "MTESession":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(**data)
