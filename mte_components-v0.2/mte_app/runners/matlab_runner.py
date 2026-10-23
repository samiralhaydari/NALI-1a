from __future__ import annotations

import io
import threading
import traceback

from PySide6.QtCore import QObject, Signal


class MatlabRunner(QObject):
    """Runs MATLAB code through MATLAB Engine in a worker thread."""

    started = Signal()
    output = Signal(str)
    error_output = Signal(str)
    finished = Signal(int, bool)
    failed_to_start = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._engine = None
        self._busy = False
        self._lock = threading.Lock()

    @property
    def is_running(self) -> bool:
        return self._busy

    def run_code(self, code: str) -> None:
        if self._busy:
            self.error_output.emit("MATLAB is already running a submission.\n")
            return

        self._busy = True
        self.started.emit()
        threading.Thread(
            target=self._worker,
            args=(code,),
            daemon=True,
        ).start()

    def stop(self) -> None:
        self.error_output.emit(
            "MATLAB cancellation is not implemented in component build v0.1.\n"
        )

    def close(self) -> None:
        with self._lock:
            if self._engine is not None:
                try:
                    self._engine.quit()
                except Exception:
                    pass
                finally:
                    self._engine = None

    def _worker(self, code: str) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        try:
            try:
                import matlab.engine
            except Exception as exc:
                self.failed_to_start.emit(
                    "MATLAB Engine for Python is unavailable. "
                    f"Import error: {exc}"
                )
                return

            with self._lock:
                if self._engine is None:
                    self.output.emit("Starting MATLAB engine...\n")
                    self._engine = matlab.engine.start_matlab()

                result = self._engine.evalc(
                    code,
                    nargout=1,
                    stdout=stdout,
                    stderr=stderr,
                )

            if stdout.getvalue():
                self.output.emit(stdout.getvalue())
            if result:
                self.output.emit(str(result))
                if not str(result).endswith("\n"):
                    self.output.emit("\n")
            if stderr.getvalue():
                self.error_output.emit(stderr.getvalue())

            self.finished.emit(0, True)
        except Exception:
            if stdout.getvalue():
                self.output.emit(stdout.getvalue())
            if stderr.getvalue():
                self.error_output.emit(stderr.getvalue())
            self.error_output.emit(traceback.format_exc())
            self.finished.emit(1, False)
        finally:
            self._busy = False
