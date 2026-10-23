from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class ExecutionRequest:
    language: str
    source: str
    timeout_seconds: int = 20
    project_hint: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int | None = None
    metadata: dict | None = None


class SandboxExecutionBackend(Protocol):
    """Interface for a future institutional/container execution service.

    The desktop v0.4 build still uses its local Qt runners. This protocol keeps
    the UI/pedagogy layer from being tied permanently to local execution.
    """

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        ...


class UnconfiguredRemoteSandbox:
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        raise RuntimeError(
            "Remote sandbox execution is not configured. The v0.4 desktop build "
            "uses local MATLAB/Python/Lean runners by default."
        )
