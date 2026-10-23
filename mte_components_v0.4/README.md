# Mathematical Thinking Engine — Pedagogical Interaction Build v0.4

v0.4 adds the learning layer on top of the MATLAB → Python → Lean execution environment. The application now retains the student's path through the problem, not only the latest code and output.

## New in v0.4

### Attempt timeline

Every MATLAB, Python, and Lean execution creates an attempt record containing:

- attempt number
- local timestamp
- language/stage
- result/status
- short diagnostic summary
- exit code when available
- whether the attempt came from `Run All`
- source-code snapshot
- an output excerpt

Failed and rejected attempts remain in the timeline after later successes. Resetting output does **not** erase the learning trail.

### Cross-language evidence summary

The lower `Evidence Summary` tab distinguishes the roles of the three tools:

- MATLAB: computational/numerical exploration
- Python: executable conjecture testing
- Lean: formal verification

The summary deliberately does not call a successful MATLAB or Python run a proof. When Lean accepts a proof, the interface also reminds the student that the formal guarantee applies to the Lean theorem as written, so the formalisation still needs to match the original problem.

### Socratic hint panel

`Hints & Reflection` contains separate hint controls for MATLAB, Python, and Lean. The built-in v0.4 hint engine is deliberately conservative and question-based.

Examples include:

- Python `NameError`: asks where the name should have been defined/imported.
- MATLAB dimension mismatch: asks the student to inspect array dimensions and intended operations.
- Lean `unsolved goals`: asks the student to identify the exact goal and a smaller fact that would reduce it.
- Lean type mismatch: asks the student to compare expected and inferred types.

The hint component does not insert corrected source code or a completed Lean proof.

The current engine is deterministic/local. It creates the correct interface boundary for a later LLM-based Socratic agent without making the desktop prototype dependent on an external AI service.

### Student reflection

A persistent reflection field asks the student to compare:

1. what the computational evidence suggested;
2. what Lean established or rejected; and
3. what assumption, representation, or strategy changed between attempts.

Reflection is saved inside `.mte` sessions and included in exported submissions.

### Exportable submission package

Use `File → Export Submission…`, the toolbar button, or `Ctrl+Shift+E`.

The resulting ZIP contains:

```text
session.mte
report.md
attempts.json
reflection.txt
problem.txt
summary.json
sources/
    model.m
    conjecture_test.py
    proof.lean
outputs/
    matlab.txt
    python.txt
    lean.txt
figures/
    matlab_figure_01.png   # when current figures exist
    ...
```

`report.md` is a readable submission record with the problem, evidence summary, reflection, attempt timeline, and all three source-code segments.

### Backward-compatible sessions

Older v0.1–v0.3 `.mte` files can still be loaded. Missing v0.4 fields (`reflection`, `attempts`) receive safe defaults.

### Sandbox service abstraction

`mte_app/execution_backend.py` defines a small execution request/result protocol and a `SandboxExecutionBackend` interface. The current desktop build continues to use the local Qt runners, but this interface provides a clean future boundary for institutional container or remote-worker execution.

It is intentionally not a fake sandbox: `UnconfiguredRemoteSandbox` raises an explicit configuration error rather than pretending local execution is isolated.

## Existing capabilities retained from v0.3

- three line-numbered, syntax-highlighted editors
- MATLAB Engine execution
- isolated Python child process
- Lean 4 / Lake verification
- MATLAB embedded figure viewer
- clickable Lean error locations
- Find / Replace
- editor zoom
- `.mte` Open / Save / Save As
- sequential gated `MATLAB → Python → Lean` Run All

## Architecture

```text
Mathematical Thinking Engine v0.4
│
├── Problem / Conjecture
│
├── Execution workspace
│   ├── MATLAB editor → MatlabRunner → figures/output
│   ├── Python editor → PythonRunner → output
│   └── Lean editor   → LeanRunner → formal diagnostic
│
├── Pedagogical interaction layer
│   ├── Evidence Summary
│   ├── Attempt Timeline
│   └── Hints & Reflection
│
├── Session model
│   ├── source + output
│   ├── Lean verification state
│   ├── attempt history
│   └── reflection
│
└── Submission exporter
    └── ZIP: report + source + output + attempts + reflection + figures
```

## Installation

Requirements:

- Python 3
- PySide6
- Lean 4 for formal verification
- a Lean Lake/Mathlib project when using `import Mathlib`
- MATLAB plus MATLAB Engine for Python for MATLAB execution

Install Python dependencies:

```bash
python -m pip install -r requirements.txt
```

Run:

```bash
python app.py
```

### Lean project

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

## Security

Student code executes locally in this prototype. Do not deploy it as a public multi-user service without real isolation.

For institutional deployment, the execution backend should provide at least:

- container/VM isolation
- CPU/time/memory limits
- file-system boundaries
- network restrictions
- per-user/submission process ownership
- audit/event logging
- controlled MATLAB licensing and worker lifecycle

## Suggested v0.5

A coherent next build would focus on instructor/course functionality:

- assignment templates and starter code
- rubric-linked assessment view
- student identifiers / submission metadata
- comparison of attempts and code diffs
- instructor annotations
- batch export/import of `.mte` submissions
- optional LLM Socratic strategy agent behind the existing hint interface
- configurable local vs remote sandbox backend
