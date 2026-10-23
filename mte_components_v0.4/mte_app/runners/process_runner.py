from __future__ import annotations

from pathlib import Path
import tempfile

from PySide6.QtCore import QObject, QProcess, QTimer, Signal


class ProcessRunner(QObject):
    """Reusable non-blocking child-process runner."""

    started = Signal()
    output = Signal(str)
    error_output = Signal(str)
    finished = Signal(int, bool)
    failed_to_start = Signal(str)
    timed_out = Signal()

    def __init__(self, timeout_ms: int = 15_000, parent: QObject | None = None):
        super().__init__(parent)
        self.timeout_ms = timeout_ms
        self._process = QProcess(self)
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)

        self._process.readyReadStandardOutput.connect(self._read_stdout)
        self._process.readyReadStandardError.connect(self._read_stderr)
        self._process.started.connect(self._on_started)
        self._process.finished.connect(self._on_finished)
        self._process.errorOccurred.connect(self._on_error)
        self._timer.timeout.connect(self._on_timeout)

        self._temporary_path: Path | None = None

    @property
    def is_running(self) -> bool:
        return self._process.state() != QProcess.ProcessState.NotRunning

    def start_process(
        self,
        program: str,
        arguments: list[str],
        *,
        working_directory: str | None = None,
        temporary_path: Path | None = None,
    ) -> None:
        if self.is_running:
            self.error_output.emit("A process is already running.\n")
            return

        self._temporary_path = temporary_path
        if working_directory:
            self._process.setWorkingDirectory(working_directory)

        self._process.setProgram(program)
        self._process.setArguments(arguments)
        self._process.start()
        self._timer.start(self.timeout_ms)

    def stop(self) -> None:
        if self.is_running:
            self._process.kill()

    def _on_started(self) -> None:
        self.started.emit()

    def _read_stdout(self) -> None:
        text = bytes(self._process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.output.emit(text)

    def _read_stderr(self) -> None:
        text = bytes(self._process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        if text:
            self.error_output.emit(text)

    def _on_finished(self, exit_code: int, _exit_status) -> None:
        self._timer.stop()
        self._read_stdout()
        self._read_stderr()
        self.finished.emit(exit_code, exit_code == 0)
        self._cleanup_temp()

    def _on_error(self, error) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self._timer.stop()
            self.failed_to_start.emit(
                f"Could not start executable: {self._process.program()}"
            )
            self._cleanup_temp()

    def _on_timeout(self) -> None:
        if self.is_running:
            self.timed_out.emit()
            self._process.kill()

    def _cleanup_temp(self) -> None:
        if self._temporary_path:
            try:
                self._temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
            self._temporary_path = None

    @staticmethod
    def make_temp_file(
        suffix: str,
        code: str,
        *,
        directory: str | None = None,
    ) -> Path:
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            prefix="mte_",
            delete=False,
            dir=directory,
            encoding="utf-8",
        )
        try:
            handle.write(code)
        finally:
            handle.close()
        return Path(handle.name)
