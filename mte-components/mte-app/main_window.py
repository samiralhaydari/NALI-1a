from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .runners import LeanRunner, MatlabRunner, PythonRunner
from .widgets import CodePanel


MATLAB_EXAMPLE = """x = linspace(-5,5,100);
y = x.^2 + 2*x + 1;
[minValue, index] = min(y);
xMinimum = x(index)
minValue
"""

PYTHON_EXAMPLE = """def f(x):
    return x**2 + 2*x + 1

for x in [-3, -2, -1, 0, 1]:
    print(x, f(x))
"""

LEAN_EXAMPLE = """import Mathlib

theorem square_nonnegative (x : ℝ) :
    0 ≤ x^2 := by
  positivity
"""


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mathematical Thinking Engine — Components v0.1")
        self.resize(1500, 900)

        self.matlab_runner = MatlabRunner(self)
        self.python_runner = PythonRunner(timeout_ms=15_000, parent=self)
        self.lean_runner = LeanRunner(timeout_ms=20_000, parent=self)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        title = QLabel("MATHEMATICAL THINKING ENGINE")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        problem_label = QLabel("Problem / Conjecture")
        self.problem_editor = QPlainTextEdit()
        self.problem_editor.setMaximumHeight(90)
        self.problem_editor.setPlaceholderText(
            "State the engineering or mathematical problem that all three "
            "code lanes are investigating."
        )
        self.problem_editor.setPlainText(
            "Determine and verify the minimum of x² + 2x + 1."
        )
        layout.addWidget(problem_label)
        layout.addWidget(self.problem_editor)

        toolbar = QHBoxLayout()
        self.run_all_button = QPushButton("Run All ▶")
        self.reset_button = QPushButton("Reset Outputs")
        toolbar.addWidget(self.run_all_button)
        toolbar.addWidget(self.reset_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.matlab_panel = CodePanel(
            "MATLAB",
            "Computation / exploration",
            "▶ Run MATLAB",
        )
        self.python_panel = CodePanel(
            "PYTHON",
            "Conjecture testing / executable translation",
            "▶ Run Python",
        )
        self.lean_panel = CodePanel(
            "LEAN 4",
            "Formal verification",
            "✓ Verify Lean",
        )

        self.matlab_panel.editor.setPlainText(MATLAB_EXAMPLE)
        self.python_panel.editor.setPlainText(PYTHON_EXAMPLE)
        self.lean_panel.editor.setPlainText(LEAN_EXAMPLE)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.matlab_panel)
        splitter.addWidget(self.python_panel)
        splitter.addWidget(self.lean_panel)
        splitter.setSizes([500, 500, 500])
        layout.addWidget(splitter, 1)

        self.footer = QLabel(
            "Status: MATLAB ready   |   Python ready   |   Lean ready"
        )
        layout.addWidget(self.footer)

        self._wire_panel(
            self.matlab_panel,
            self.matlab_runner,
            self._run_matlab,
            success_text="Completed",
        )
        self._wire_panel(
            self.python_panel,
            self.python_runner,
            self._run_python,
            success_text="Completed",
        )
        self._wire_panel(
            self.lean_panel,
            self.lean_runner,
            self._run_lean,
            success_text="✓ VERIFIED",
        )

        self.run_all_button.clicked.connect(self._run_all)
        self.reset_button.clicked.connect(self._reset_outputs)

        self._apply_styles()

    def _wire_panel(self, panel, runner, run_callable, success_text: str) -> None:
        panel.run_requested.connect(run_callable)
        panel.stop_requested.connect(runner.stop)

        runner.started.connect(panel.set_running)
        runner.output.connect(panel.append_output)
        runner.error_output.connect(panel.append_output)
        runner.failed_to_start.connect(
            lambda message, p=panel: self._startup_failure(p, message)
        )
        if hasattr(runner, "timed_out"):
            runner.timed_out.connect(
                lambda p=panel: self._timeout_failure(p)
            )
        runner.finished.connect(
            lambda exit_code, success, p=panel, s=success_text:
                self._finish_panel(p, exit_code, success, s)
        )

    def _run_matlab(self) -> None:
        self.matlab_panel.clear_output()
        self.matlab_runner.run_code(self.matlab_panel.editor.toPlainText())

    def _run_python(self) -> None:
        self.python_panel.clear_output()
        self.python_runner.run_code(self.python_panel.editor.toPlainText())

    def _run_lean(self) -> None:
        self.lean_panel.clear_output()
        self.lean_runner.run_code(self.lean_panel.editor.toPlainText())

    def _run_all(self) -> None:
        self._run_matlab()
        self._run_python()
        self._run_lean()

    def _reset_outputs(self) -> None:
        self.matlab_panel.clear_output()
        self.python_panel.clear_output()
        self.lean_panel.clear_output()
        self.footer.setText(
            "Status: MATLAB ready   |   Python ready   |   Lean ready"
        )

    @staticmethod
    def _finish_panel(
        panel,
        exit_code: int,
        success: bool,
        success_text: str,
    ) -> None:
        if success:
            panel.set_success(success_text)
        else:
            panel.set_failure(f"✗ REJECTED / exit {exit_code}")

    @staticmethod
    def _startup_failure(panel, message: str) -> None:
        panel.append_output(message + "\\n")
        panel.set_failure("Unavailable")

    @staticmethod
    def _timeout_failure(panel) -> None:
        panel.append_output("\\nExecution timed out and was stopped.\\n")
        panel.set_failure("Timed out")

    def closeEvent(self, event) -> None:
        self.python_runner.stop()
        self.lean_runner.stop()
        self.matlab_runner.close()
        super().closeEvent(event)

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                font-size: 13px;
            }
            #appTitle {
                font-size: 22px;
                font-weight: 700;
                padding: 4px 0 8px 0;
            }
            #panelTitle {
                font-size: 17px;
                font-weight: 700;
            }
            #panelSubtitle {
                font-size: 12px;
            }
            #statusLabel {
                font-weight: 600;
            }
            QPlainTextEdit {
                border: 1px solid palette(mid);
                padding: 6px;
            }
            QPushButton {
                padding: 6px 12px;
            }
            """
        )
