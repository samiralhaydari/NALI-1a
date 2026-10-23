from __future__ import annotations

import io
from pathlib import Path
import shutil
import tempfile
import threading
import traceback

from PySide6.QtCore import QObject, Signal


class MatlabRunner(QObject):
    """Runs MATLAB code through MATLAB Engine and exports open figures as PNG."""

    started = Signal()
    output = Signal(str)
    error_output = Signal(str)
    figure_ready = Signal(str)
    finished = Signal(int, bool)
    failed_to_start = Signal(str)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._engine = None
        self._busy = False
        self._lock = threading.Lock()
        self._figure_dir: Path | None = None

    @property
    def is_running(self) -> bool:
        return self._busy

    def run_code(self, code: str) -> None:
        if self._busy:
            self.error_output.emit("MATLAB is already running a submission.\n")
            return
        self._busy = True
        self._reset_figure_dir()
        self.started.emit()
        threading.Thread(target=self._worker, args=(code,), daemon=True).start()

    def stop(self) -> None:
        self.error_output.emit(
            "MATLAB cancellation is not implemented in component build v0.3.\n"
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
        self._cleanup_figure_dir()

    def _reset_figure_dir(self) -> None:
        self._cleanup_figure_dir()
        self._figure_dir = Path(tempfile.mkdtemp(prefix="mte_matlab_figures_"))

    def _cleanup_figure_dir(self) -> None:
        if self._figure_dir and self._figure_dir.exists():
            shutil.rmtree(self._figure_dir, ignore_errors=True)
        self._figure_dir = None

    def _capture_figures(self) -> None:
        if self._engine is None or self._figure_dir is None:
            return
        matlab_dir = str(self._figure_dir).replace("\\", "/").replace("'", "''")
        capture = f"""
__mte_figs__ = findall(groot,'Type','figure');
for __mte_k__ = 1:numel(__mte_figs__)
    __mte_path__ = fullfile('{matlab_dir}', sprintf('figure_%02d.png', __mte_k__));
    try
        exportgraphics(__mte_figs__(__mte_k__), __mte_path__, 'Resolution', 150);
    catch
        saveas(__mte_figs__(__mte_k__), __mte_path__);
    end
end
clear __mte_figs__ __mte_k__ __mte_path__;
"""
        self._engine.eval(capture, nargout=0)
        for path in sorted(self._figure_dir.glob("figure_*.png")):
            self.figure_ready.emit(str(path))

    def _worker(self, code: str) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        emitted_finished = False
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
                self._engine.eval("close all force;", nargout=0)
                result = self._engine.evalc(
                    code,
                    nargout=1,
                    stdout=stdout,
                    stderr=stderr,
                )
                self._capture_figures()

            if stdout.getvalue():
                self.output.emit(stdout.getvalue())
            if result:
                self.output.emit(str(result))
                if not str(result).endswith("\n"):
                    self.output.emit("\n")
            if stderr.getvalue():
                self.error_output.emit(stderr.getvalue())
            self.finished.emit(0, True)
            emitted_finished = True
        except Exception:
            if stdout.getvalue():
                self.output.emit(stdout.getvalue())
            if stderr.getvalue():
                self.error_output.emit(stderr.getvalue())
            self.error_output.emit(traceback.format_exc())
            self.finished.emit(1, False)
            emitted_finished = True
        finally:
            self._busy = False
            # failed_to_start is intentionally separate from finished.
            _ = emitted_finished
