# Mathematical Thinking Engine — Rich Interaction Build v0.3

This build extends v0.2 with richer execution and editor interaction while preserving the three-lane MTE design.

## New in v0.3

### Embedded MATLAB figures

After MATLAB code runs, every open MATLAB figure is exported to a temporary PNG and displayed inside the MATLAB panel. The viewer supports multiple figures, Previous/Next navigation, Fit-to-width, and 100% view.

The MATLAB runner closes pre-existing figures before each submission so the viewer represents the current attempt. It first tries `exportgraphics` and falls back to `saveas`.

### Clickable Lean diagnostics

When Lean reports a standard source location such as:

```text
file.lean:5:3: error: ...
```

the structured diagnostic card shows a `Go to Ln 5, Col 3` button. Clicking it moves the Lean editor cursor directly to that location.

### Find / replace

Every MATLAB, Python and Lean editor has a Find control and reusable find/replace bar.

Keyboard shortcuts:

```text
Ctrl+F       Find
Ctrl+H       Replace
```

Supported operations: Next, Previous, Replace, Replace All, and Match case.

### Editor zoom

Each code pane has `−`, percentage, and `+` controls.

Keyboard shortcuts:

```text
Ctrl++       Zoom in
Ctrl+-       Zoom out
Ctrl+0       Reset zoom
```

### Sequential Run All

`Run All` now executes as a gated pipeline rather than three concurrent jobs:

```text
MATLAB
  ↓ success
Python
  ↓ success
Lean
  ↓ verified
Complete
```

Any failure stops the chain at that stage. This prevents an apparent end-to-end success when an earlier computational stage failed.

## Architecture

```text
MTE Main Window
│
├── Session controls
│   └── New / Open / Save / Save As
├── Problem / Conjecture
├── MATLAB CodePanel
│   ├── CodeEditor + FindReplaceBar + zoom
│   ├── MatlabHighlighter
│   ├── MatlabRunner
│   └── FigureViewer
├── Python CodePanel
│   ├── CodeEditor + FindReplaceBar + zoom
│   ├── PythonHighlighter
│   └── PythonRunner
├── Lean CodePanel
│   ├── CodeEditor + FindReplaceBar + zoom
│   ├── LeanHighlighter
│   ├── LeanRunner
│   └── clickable structured diagnostics
└── Sequential Run-All coordinator
    └── MATLAB → Python → Lean
```

## Requirements

- Python 3
- PySide6
- Lean 4 when Lean verification is required
- A Lean Lake project with Mathlib when source uses `import Mathlib`
- MATLAB + MATLAB Engine for Python when MATLAB execution is required

Install:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python app.py
```

## Lean / Mathlib

Set `MTE_LEAN_PROJECT` to a Lean Lake project if submitted source imports Mathlib.

Windows PowerShell:

```powershell
$env:MTE_LEAN_PROJECT="C:\path\to\lean-project"
python app.py
```

Linux/macOS:

```bash
export MTE_LEAN_PROJECT=/path/to/lean-project
python app.py
```

## MATLAB cancellation

MATLAB Engine does not provide the same simple hard-kill behavior as the QProcess runners. Hard cancellation is therefore still intentionally limited in this local prototype. A production deployment should run MATLAB in a separately managed worker process or sandbox.

## Security note

Student code executes on the local computer. This build is appropriate for trusted local/classroom prototyping, not an internet-facing multi-user service. Public deployment requires process/container isolation, CPU/memory quotas, file-system isolation, network restrictions, and audit logging.

## Suggested v0.4

The next coherent layer is pedagogical interaction: attempt/session timeline, cross-language result summary, Socratic hint panel, student reflection after verification, and an exportable submission/report package.
