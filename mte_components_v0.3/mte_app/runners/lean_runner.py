from __future__ import annotations

import os
from pathlib import Path
import shutil

from .process_runner import ProcessRunner


class LeanRunner(ProcessRunner):
    """Checks Lean 4 source with Lean directly or through a Lake project."""

    def __init__(
        self,
        project_directory: str | None = None,
        timeout_ms: int = 20_000,
        parent=None,
    ):
        super().__init__(timeout_ms=timeout_ms, parent=parent)
        self.project_directory = (
            project_directory or os.environ.get("MTE_LEAN_PROJECT") or None
        )

    def run_code(self, code: str) -> None:
        if self.project_directory:
            project = Path(self.project_directory).expanduser().resolve()
            if not project.exists():
                self.failed_to_start.emit(
                    f"Lean project directory does not exist: {project}"
                )
                return
            if shutil.which("lake") is None:
                self.failed_to_start.emit(
                    "Could not find 'lake' on PATH. Install Lean via elan or "
                    "configure PATH."
                )
                return

            temp_path = self.make_temp_file(
                ".lean",
                code,
                directory=str(project),
            )
            self.start_process(
                "lake",
                ["env", "lean", temp_path.name],
                working_directory=str(project),
                temporary_path=temp_path,
            )
            return

        if shutil.which("lean") is None:
            self.failed_to_start.emit(
                "Could not find 'lean' on PATH. Install Lean 4, or set "
                "MTE_LEAN_PROJECT to a Lake project."
            )
            return

        temp_path = self.make_temp_file(".lean", code)
        self.start_process(
            "lean",
            [str(temp_path)],
            temporary_path=temp_path,
        )
