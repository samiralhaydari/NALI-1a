from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
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
    reflection: str = ""
    attempts: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "MTESession":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        known = {item.name for item in fields(cls)}
        filtered = {key: value for key, value in data.items() if key in known}
        # Older .mte sessions do not contain v0.4 pedagogical fields; dataclass
        # defaults make them load without migration dialogs.
        return cls(**filtered)
