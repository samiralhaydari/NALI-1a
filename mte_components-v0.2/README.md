# Mathematical Thinking Engine — Editor/Interaction Build v0.2

This build extends the v0.1 execution components with the first student-facing editor and session interaction layer.

## New in v0.2

- Line numbers in MATLAB, Python and Lean editors.
- Current-line highlighting and line/column cursor position.
- Language-aware syntax highlighting for MATLAB, Python and Lean 4.
- Structured Lean result card:
  - `✓ PROOF VERIFIED`
  - `✗ PROOF REJECTED`
  - line/column extraction from Lean diagnostics when available
  - warning state for accepted submissions that emit warnings.
- `.mte` session Open / Save / Save As.
- Keyboard shortcuts: Ctrl+N, Ctrl+O, Ctrl+S, Ctrl+Shift+S.
- Unsaved-change protection on New, Open and Exit.
- Saved sessions retain the problem, all three code inputs, all three outputs, and the latest Lean verification state.

## Architecture

```text
MTE Main Window
├── Session interaction
│   ├── New / Open / Save / Save As
│   └── dirty-state + unsaved-change protection
├── Problem / Conjecture
├── MATLAB CodePanel
│   ├── CodeEditor + line numbers
│   ├── MatlabHighlighter
│   └── MatlabRunner
├── Python CodePanel
│   ├── CodeEditor + line numbers
│   ├── PythonHighlighter
│   └── PythonRunner
└── Lean CodePanel
    ├── CodeEditor + line numbers
    ├── LeanHighlighter
    ├── LeanRunner
    └── Lean diagnostic parser/result card
```

## Requirements

- Python 3
- PySide6
- Lean 4 when Lean verification is required
- A Lean Lake project with Mathlib when source uses `import Mathlib`
- MATLAB + MATLAB Engine for Python when MATLAB execution is required

Install the GUI dependency:

```bash
python -m pip install -r requirements.txt
```

Launch:

```bash
python app.py
```

### Lean / Mathlib setup

Set `MTE_LEAN_PROJECT` to the folder containing your `lakefile.toml` or `lakefile.lean`.

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

With a project configured, the runner invokes `lake env lean`. Without one, it invokes `lean` directly.

## Session file

An `.mte` file is JSON and currently records:

```json
{
  "title": "Quadratic",
  "problem": "...",
  "matlab_code": "...",
  "python_code": "...",
  "lean_code": "...",
  "matlab_output": "...",
  "python_output": "...",
  "lean_output": "...",
  "lean_verified": true
}
```

## Verification behavior

A successful Lean process exit is shown as verified. A non-zero Lean exit is shown as rejected. The diagnostic parser extracts the first standard `file.lean:line:column: error:` message when available and presents its source location above the raw Lean output.

The raw Lean compiler/prover text is always retained so the student can debug rather than receiving a hidden automatic correction.

## Security note

This is still a trusted local-development/classroom prototype. Python, MATLAB and Lean submissions execute on the local computer. A public or multi-user deployment requires a separate sandboxing layer with CPU/memory/time limits, file-system isolation and network restrictions.

## Suggested v0.3

1. Embedded MATLAB plot/figure viewer.
2. Clickable Lean diagnostics that move the cursor to the failing line/column.
3. Find/replace and editor zoom.
4. Session history / attempt timeline.
5. Sequential Run-All workflow: MATLAB → Python → Lean.
6. Sandboxed execution service.
7. Socratic hint panel that explains errors without supplying the final proof.
