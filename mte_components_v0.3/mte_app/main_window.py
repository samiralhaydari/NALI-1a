from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from .lean_diagnostics import parse_lean_diagnostic
from .runners import LeanRunner, MatlabRunner, PythonRunner
from .session import MTESession
from .widgets import CodePanel


MATLAB_EXAMPLE = """x = linspace(-5,5,100);
y = x.^2 + 2*x + 1;
[minValue, index] = min(y);
xMinimum = x(index)
minValue
plot(x,y,'LineWidth',1.5)
grid on
title('Quadratic exploration')
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
        self.resize(1600, 950)

        self.current_session_path: Path | None = None
        self._dirty = False
        self._loading_session = False
        self._lean_output_buffer: list[str] = []
        self._last_lean_verified: bool | None = None
        self._pipeline_active = False
        self._pipeline_stage: str | None = None

        self.matlab_runner = MatlabRunner(self)
        self.python_runner = PythonRunner(timeout_ms=15_000, parent=self)
        self.lean_runner = LeanRunner(timeout_ms=20_000, parent=self)

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)

        title = QLabel("MATHEMATICAL THINKING ENGINE")
        title.setObjectName("appTitle")
        layout.addWidget(title)

        layout.addWidget(QLabel("Problem / Conjecture"))
        self.problem_editor = QPlainTextEdit()
        self.problem_editor.setMaximumHeight(90)
        self.problem_editor.setPlaceholderText(
            "State the engineering or mathematical problem that all three "
            "code lanes are investigating."
        )
        layout.addWidget(self.problem_editor)

        toolbar = QHBoxLayout()
        self.new_button = QPushButton("New")
        self.open_button = QPushButton("Open…")
        self.save_button = QPushButton("Save")
        self.run_all_button = QPushButton("Run All: MATLAB → Python → Lean ▶")
        self.reset_button = QPushButton("Reset Outputs")
        for button in (self.new_button, self.open_button, self.save_button):
            toolbar.addWidget(button)
        toolbar.addSpacing(14)
        toolbar.addWidget(self.run_all_button)
        toolbar.addWidget(self.reset_button)
        toolbar.addStretch(1)
        layout.addLayout(toolbar)

        self.matlab_panel = CodePanel(
            "MATLAB",
            "Computation / exploration",
            "▶ Run MATLAB",
            language="matlab",
            show_figures=True,
        )
        self.python_panel = CodePanel(
            "PYTHON",
            "Conjecture testing / executable translation",
            "▶ Run Python",
            language="python",
        )
        self.lean_panel = CodePanel(
            "LEAN 4",
            "Formal verification",
            "✓ Verify Lean",
            language="lean",
            show_diagnostics=True,
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.matlab_panel)
        splitter.addWidget(self.python_panel)
        splitter.addWidget(self.lean_panel)
        splitter.setSizes([540, 500, 560])
        layout.addWidget(splitter, 1)

        self.footer = QLabel("Ready")
        layout.addWidget(self.footer)

        self._wire_matlab_panel()
        self._wire_python_panel()
        self._wire_lean_panel()

        self.new_button.clicked.connect(self._new_session)
        self.open_button.clicked.connect(self._open_session)
        self.save_button.clicked.connect(self._save_session)
        self.run_all_button.clicked.connect(self._run_all)
        self.reset_button.clicked.connect(self._reset_outputs)
        self.lean_panel.diagnostic_location_requested.connect(
            self._jump_to_lean_diagnostic
        )

        self._create_actions()
        self._connect_dirty_tracking()
        self._apply_styles()
        self._load_default_session()

    # ---------- Menus / editor interaction ----------

    def _create_actions(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("&New", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._new_session)

        open_action = QAction("&Open…", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._open_session)

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._save_session)

        save_as_action = QAction("Save &As…", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._save_session_as)

        file_menu.addActions([new_action, open_action, save_action, save_as_action])

        edit_menu = self.menuBar().addMenu("&Edit")

        find_action = QAction("&Find", self)
        find_action.setShortcut(QKeySequence.StandardKey.Find)
        find_action.triggered.connect(lambda: self._show_find(replace=False))

        replace_action = QAction("&Replace", self)
        replace_action.setShortcut(QKeySequence("Ctrl+H"))
        replace_action.triggered.connect(lambda: self._show_find(replace=True))

        zoom_in_action = QAction("Zoom &In", self)
        zoom_in_action.setShortcut(QKeySequence.StandardKey.ZoomIn)
        zoom_in_action.triggered.connect(self._zoom_in_active)

        zoom_out_action = QAction("Zoom &Out", self)
        zoom_out_action.setShortcut(QKeySequence.StandardKey.ZoomOut)
        zoom_out_action.triggered.connect(self._zoom_out_active)

        reset_zoom_action = QAction("&Reset Zoom", self)
        reset_zoom_action.setShortcut(QKeySequence("Ctrl+0"))
        reset_zoom_action.triggered.connect(self._reset_zoom_active)

        edit_menu.addActions(
            [
                find_action,
                replace_action,
                zoom_in_action,
                zoom_out_action,
                reset_zoom_action,
            ]
        )

    def _active_panel(self) -> CodePanel:
        focused = self.focusWidget()
        for panel in (self.matlab_panel, self.python_panel, self.lean_panel):
            if panel.editor.hasFocus():
                return panel
            if focused is not None and panel.find_bar.isAncestorOf(focused):
                return panel
        return self.lean_panel

    def _show_find(self, replace: bool) -> None:
        panel = self._active_panel()
        panel.show_find(replace=replace)
        if replace:
            panel.find_bar.replace_edit.setFocus()

    def _zoom_in_active(self) -> None:
        self._active_panel().zoom_in()

    def _zoom_out_active(self) -> None:
        self._active_panel().zoom_out()

    def _reset_zoom_active(self) -> None:
        self._active_panel().reset_zoom()

    def _jump_to_lean_diagnostic(self, line: int, column: int) -> None:
        self.lean_panel.editor.goto_line_column(line, column)
        self.footer.setText(f"Lean diagnostic: line {line}, column {column}")

    # ---------- Dirty/session tracking ----------

    def _connect_dirty_tracking(self) -> None:
        for editor in (
            self.problem_editor,
            self.matlab_panel.editor,
            self.python_panel.editor,
            self.lean_panel.editor,
        ):
            editor.textChanged.connect(self._mark_dirty)

    def _mark_dirty(self) -> None:
        if self._loading_session:
            return
        if not self._dirty:
            self._dirty = True
            self._update_window_title()

    def _update_window_title(self) -> None:
        name = (
            self.current_session_path.name
            if self.current_session_path
            else "Untitled.mte"
        )
        marker = " *" if self._dirty else ""
        self.setWindowTitle(
            f"{name}{marker} — Mathematical Thinking Engine v0.3"
        )

    # ---------- Runner wiring ----------

    def _wire_matlab_panel(self) -> None:
        self.matlab_panel.run_requested.connect(self._run_matlab)
        self.matlab_panel.stop_requested.connect(self.matlab_runner.stop)
        self.matlab_runner.started.connect(self.matlab_panel.set_running)
        self.matlab_runner.output.connect(self.matlab_panel.append_output)
        self.matlab_runner.error_output.connect(self.matlab_panel.append_output)
        self.matlab_runner.figure_ready.connect(
            self.matlab_panel.figure_viewer.add_figure
        )
        self.matlab_runner.failed_to_start.connect(self._matlab_startup_failure)
        self.matlab_runner.finished.connect(self._finish_matlab)

    def _wire_python_panel(self) -> None:
        self.python_panel.run_requested.connect(self._run_python)
        self.python_panel.stop_requested.connect(self.python_runner.stop)
        self.python_runner.started.connect(self.python_panel.set_running)
        self.python_runner.output.connect(self.python_panel.append_output)
        self.python_runner.error_output.connect(self.python_panel.append_output)
        self.python_runner.failed_to_start.connect(self._python_startup_failure)
        self.python_runner.timed_out.connect(self._python_timeout)
        self.python_runner.finished.connect(self._finish_python)

    def _wire_lean_panel(self) -> None:
        self.lean_panel.run_requested.connect(self._run_lean)
        self.lean_panel.stop_requested.connect(self.lean_runner.stop)
        self.lean_runner.started.connect(self.lean_panel.set_running)
        self.lean_runner.output.connect(self._capture_lean_output)
        self.lean_runner.error_output.connect(self._capture_lean_output)
        self.lean_runner.failed_to_start.connect(self._lean_startup_failure)
        self.lean_runner.timed_out.connect(self._lean_timeout)
        self.lean_runner.finished.connect(self._finish_lean)

    # ---------- Individual execution ----------

    def _reject_manual_run_during_pipeline(self) -> bool:
        if not self._pipeline_active:
            return False
        self.footer.setText(
            f"Run All is in progress ({self._pipeline_stage}). "
            "Individual runs are temporarily gated."
        )
        return True

    def _run_matlab(self, *, from_pipeline: bool = False) -> None:
        if not from_pipeline and self._reject_manual_run_during_pipeline():
            return
        self.matlab_panel.clear_output()
        self.matlab_panel.figure_viewer.clear()
        self.matlab_runner.run_code(self.matlab_panel.editor.toPlainText())

    def _run_python(self, *, from_pipeline: bool = False) -> None:
        if not from_pipeline and self._reject_manual_run_during_pipeline():
            return
        self.python_panel.clear_output()
        self.python_runner.run_code(self.python_panel.editor.toPlainText())

    def _run_lean(self, *, from_pipeline: bool = False) -> None:
        if not from_pipeline and self._reject_manual_run_during_pipeline():
            return
        self._lean_output_buffer.clear()
        self._last_lean_verified = None
        self.lean_panel.clear_output()
        self.lean_panel.clear_diagnostic()
        self.lean_runner.run_code(self.lean_panel.editor.toPlainText())

    # ---------- Sequential Run All ----------

    def _run_all(self) -> None:
        if self._pipeline_active:
            self.footer.setText("Run All is already in progress.")
            return

        if (
            self.matlab_runner.is_running
            or self.python_runner.is_running
            or self.lean_runner.is_running
        ):
            QMessageBox.information(
                self,
                "Execution in progress",
                "Wait for the current individual execution to finish before "
                "starting Run All.",
            )
            return

        self._pipeline_active = True
        self._pipeline_stage = "MATLAB"
        self.run_all_button.setEnabled(False)
        self.footer.setText("Run All 1/3 — MATLAB exploration")
        self._run_matlab(from_pipeline=True)

    def _advance_pipeline_from_matlab(self) -> None:
        self._pipeline_stage = "Python"
        self.footer.setText("Run All 2/3 — Python conjecture testing")
        self._run_python(from_pipeline=True)

    def _advance_pipeline_from_python(self) -> None:
        self._pipeline_stage = "Lean"
        self.footer.setText("Run All 3/3 — Lean formal verification")
        self._run_lean(from_pipeline=True)

    def _complete_pipeline(self) -> None:
        self._pipeline_active = False
        self._pipeline_stage = None
        self.run_all_button.setEnabled(True)
        self.footer.setText(
            "Run All complete — MATLAB ✓  Python ✓  Lean ✓ VERIFIED"
        )

    def _abort_pipeline(self, stage: str, reason: str) -> None:
        if not self._pipeline_active:
            return
        self._pipeline_active = False
        self._pipeline_stage = None
        self.run_all_button.setEnabled(True)
        self.footer.setText(f"Run All stopped at {stage}: {reason}")

    # ---------- MATLAB completion ----------

    def _finish_matlab(self, exit_code: int, success: bool) -> None:
        if success:
            self.matlab_panel.set_success("Completed")
        else:
            self.matlab_panel.set_failure(f"Failed / exit {exit_code}")
        self._mark_dirty()

        if self._pipeline_active and self._pipeline_stage == "MATLAB":
            if success:
                self._advance_pipeline_from_matlab()
            else:
                self._abort_pipeline("MATLAB", f"exit code {exit_code}")

    def _matlab_startup_failure(self, message: str) -> None:
        self.matlab_panel.append_output(message + "\n")
        self.matlab_panel.set_failure("Unavailable")
        self._abort_pipeline("MATLAB", "runner unavailable")

    # ---------- Python completion ----------

    def _finish_python(self, exit_code: int, success: bool) -> None:
        if success:
            self.python_panel.set_success("Completed")
        else:
            self.python_panel.set_failure(f"Failed / exit {exit_code}")
        self._mark_dirty()

        if self._pipeline_active and self._pipeline_stage == "Python":
            if success:
                self._advance_pipeline_from_python()
            else:
                self._abort_pipeline("Python", f"exit code {exit_code}")

    def _python_startup_failure(self, message: str) -> None:
        self.python_panel.append_output(message + "\n")
        self.python_panel.set_failure("Unavailable")
        self._abort_pipeline("Python", "runner unavailable")

    def _python_timeout(self) -> None:
        self.python_panel.append_output("\nExecution timed out and was stopped.\n")
        self.python_panel.set_failure("Timed out")
        self._abort_pipeline("Python", "execution timed out")

    # ---------- Lean completion ----------

    def _capture_lean_output(self, text: str) -> None:
        self._lean_output_buffer.append(text)
        self.lean_panel.append_output(text)

    def _finish_lean(self, exit_code: int, success: bool) -> None:
        combined = "".join(self._lean_output_buffer)
        diagnostic = parse_lean_diagnostic(combined, exit_code)
        self._last_lean_verified = diagnostic.verified

        detail_parts = []
        if diagnostic.location_text:
            detail_parts.append(diagnostic.location_text)
        detail_parts.append(diagnostic.summary)
        if diagnostic.severity == "warning" and diagnostic.raw_message:
            detail_parts.append(f"Warning: {diagnostic.raw_message}")

        state = "success" if diagnostic.verified else "error"
        if diagnostic.severity == "warning":
            state = "warning"

        self.lean_panel.set_diagnostic(
            title=diagnostic.title,
            detail=" — ".join(detail_parts),
            state=state,
            line=diagnostic.line,
            column=diagnostic.column,
        )

        if diagnostic.verified:
            self.lean_panel.set_success("✓ VERIFIED")
        else:
            self.lean_panel.set_failure("✗ REJECTED")
        self._mark_dirty()

        if self._pipeline_active and self._pipeline_stage == "Lean":
            if diagnostic.verified:
                self._complete_pipeline()
            else:
                self._abort_pipeline("Lean", "proof rejected")

    def _lean_startup_failure(self, message: str) -> None:
        self.lean_panel.append_output(message + "\n")
        self.lean_panel.set_failure("Unavailable")
        self.lean_panel.set_diagnostic(
            title="Lean unavailable",
            detail=message,
            state="error",
        )
        self._abort_pipeline("Lean", "runner unavailable")

    def _lean_timeout(self) -> None:
        message = "Lean verification timed out and was stopped."
        self.lean_panel.append_output("\n" + message + "\n")
        self.lean_panel.set_failure("Timed out")
        self.lean_panel.set_diagnostic(
            title="Verification timed out",
            detail=message,
            state="warning",
        )
        self._abort_pipeline("Lean", "verification timed out")

    # ---------- Output/session controls ----------

    def _reset_outputs(self) -> None:
        if self._pipeline_active:
            self.footer.setText("Cannot reset outputs while Run All is active.")
            return
        self.matlab_panel.clear_output()
        self.matlab_panel.figure_viewer.clear()
        self.python_panel.clear_output()
        self.lean_panel.clear_output()
        self.lean_panel.clear_diagnostic()
        self._last_lean_verified = None
        self.footer.setText("Outputs cleared")
        self._mark_dirty()

    def _session_from_ui(self) -> MTESession:
        return MTESession(
            title=(
                self.current_session_path.stem
                if self.current_session_path
                else "Untitled Problem"
            ),
            problem=self.problem_editor.toPlainText(),
            matlab_code=self.matlab_panel.editor.toPlainText(),
            python_code=self.python_panel.editor.toPlainText(),
            lean_code=self.lean_panel.editor.toPlainText(),
            matlab_output=self.matlab_panel.output.toPlainText(),
            python_output=self.python_panel.output.toPlainText(),
            lean_output=self.lean_panel.output.toPlainText(),
            lean_verified=self._last_lean_verified,
        )

    def _apply_session_to_ui(self, session: MTESession) -> None:
        self._loading_session = True
        try:
            self.problem_editor.setPlainText(session.problem)
            self.matlab_panel.editor.setPlainText(session.matlab_code)
            self.python_panel.editor.setPlainText(session.python_code)
            self.lean_panel.editor.setPlainText(session.lean_code)
            self.matlab_panel.output.setPlainText(session.matlab_output)
            self.python_panel.output.setPlainText(session.python_output)
            self.lean_panel.output.setPlainText(session.lean_output)
            self.matlab_panel.figure_viewer.clear()
            self._last_lean_verified = session.lean_verified
            self.lean_panel.clear_diagnostic()

            if session.lean_verified is True:
                self.lean_panel.set_diagnostic(
                    title="✓ PREVIOUSLY VERIFIED",
                    detail=(
                        "This saved session records the Lean submission as "
                        "verified. Re-run Lean to regenerate source diagnostics."
                    ),
                    state="success",
                )
            elif session.lean_verified is False:
                self.lean_panel.set_diagnostic(
                    title="✗ PREVIOUSLY REJECTED",
                    detail=(
                        "This saved session records the Lean submission as "
                        "rejected. Re-run Lean to regenerate clickable diagnostics."
                    ),
                    state="error",
                )
        finally:
            self._loading_session = False

        self._dirty = False
        self._update_window_title()

    def _load_default_session(self) -> None:
        session = MTESession(
            problem="Determine and verify the minimum of x² + 2x + 1.",
            matlab_code=MATLAB_EXAMPLE,
            python_code=PYTHON_EXAMPLE,
            lean_code=LEAN_EXAMPLE,
        )
        self.current_session_path = None
        self._apply_session_to_ui(session)

    def _new_session(self) -> None:
        if not self._confirm_discard_or_save():
            return
        self.current_session_path = None
        self._load_default_session()
        self.footer.setText("New session")

    def _open_session(self) -> None:
        if not self._confirm_discard_or_save():
            return

        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "Open MTE Session",
            "",
            "MTE Session (*.mte);;JSON files (*.json);;All files (*)",
        )
        if not file_name:
            return

        try:
            session = MTESession.load(file_name)
        except Exception as exc:
            QMessageBox.critical(self, "Could not open session", str(exc))
            return

        self.current_session_path = Path(file_name)
        self._apply_session_to_ui(session)
        self.footer.setText(f"Opened {self.current_session_path.name}")

    def _save_session(self) -> bool:
        if self.current_session_path is None:
            return self._save_session_as()
        return self._write_session(self.current_session_path)

    def _save_session_as(self) -> bool:
        initial = str(self.current_session_path or Path("Untitled.mte"))
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "Save MTE Session",
            initial,
            "MTE Session (*.mte);;JSON files (*.json)",
        )
        if not file_name:
            return False

        path = Path(file_name)
        if not path.suffix:
            path = path.with_suffix(".mte")

        self.current_session_path = path
        return self._write_session(path)

    def _write_session(self, path: Path) -> bool:
        try:
            self._session_from_ui().save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Could not save session", str(exc))
            return False

        self._dirty = False
        self._update_window_title()
        self.footer.setText(f"Saved {path.name}")
        return True

    def _confirm_discard_or_save(self) -> bool:
        if not self._dirty:
            return True

        response = QMessageBox.question(
            self,
            "Unsaved changes",
            "Save changes to the current MTE session?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Save,
        )
        if response == QMessageBox.StandardButton.Cancel:
            return False
        if response == QMessageBox.StandardButton.Save:
            return self._save_session()
        return True

    def closeEvent(self, event) -> None:
        if not self._confirm_discard_or_save():
            event.ignore()
            return
        self.python_runner.stop()
        self.lean_runner.stop()
        self.matlab_runner.close()
        event.accept()

    def _apply_styles(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget { font-size: 13px; }
            #appTitle {
                font-size: 22px;
                font-weight: 700;
                padding: 4px 0 8px 0;
            }
            #panelTitle { font-size: 17px; font-weight: 700; }
            #panelSubtitle, #cursorLabel { font-size: 12px; }
            #statusLabel, #diagnosticTitle, #figureTitle { font-weight: 700; }
            QPlainTextEdit { border: 1px solid palette(mid); padding: 6px; }
            QPushButton { padding: 5px 9px; }
            #diagnosticFrame {
                border: 1px solid palette(mid);
                border-radius: 5px;
            }
            #diagnosticFrame[state="success"] {
                background: rgba(46, 125, 50, 35);
            }
            #diagnosticFrame[state="warning"] {
                background: rgba(178, 106, 0, 35);
            }
            #diagnosticFrame[state="error"] {
                background: rgba(176, 0, 32, 35);
            }
            """
        )
