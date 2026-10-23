from __future__ import annotations

import sys

from .process_runner import ProcessRunner


class PythonRunner(ProcessRunner):
    """Executes a submitted Python fragment in a separate interpreter process."""

    def run_code(self, code: str) -> None:
        temp_path = self.make_temp_file(".py", code)
        self.start_process(
            sys.executable,
            ["-I", "-u", str(temp_path)],
            temporary_path=temp_path,
        )
