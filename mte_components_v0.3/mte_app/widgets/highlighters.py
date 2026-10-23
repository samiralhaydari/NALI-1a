from __future__ import annotations

import keyword
import re

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.Bold)
    fmt.setFontItalic(italic)
    return fmt


class RegexHighlighter(QSyntaxHighlighter):
    def __init__(self, document, rules: list[tuple[str, QTextCharFormat]]):
        super().__init__(document)
        self.rules = [(QRegularExpression(pattern), fmt) for pattern, fmt in rules]

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self.rules:
            iterator = regex.globalMatch(text)
            while iterator.hasNext():
                match = iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)


KEYWORD = _fmt("#8e44ad", bold=True)
BUILTIN = _fmt("#2471a3")
STRING = _fmt("#2e7d32")
COMMENT = _fmt("#6c757d", italic=True)
NUMBER = _fmt("#b26a00")
DECLARATION = _fmt("#9c2f5d", bold=True)
TYPE = _fmt("#00695c")
OPERATOR = _fmt("#7d3c98")


def _word_rule(words: list[str] | tuple[str, ...] | set[str], fmt: QTextCharFormat):
    escaped = "|".join(sorted((re.escape(word) for word in words), key=len, reverse=True))
    return (rf"\b(?:{escaped})\b", fmt)


class PythonHighlighter(RegexHighlighter):
    def __init__(self, document):
        rules = [
            _word_rule(keyword.kwlist, KEYWORD),
            _word_rule(
                {
                    "print", "range", "len", "enumerate", "zip", "min", "max", "sum",
                    "abs", "round", "list", "dict", "set", "tuple", "int", "float", "str",
                    "bool", "type", "isinstance", "open", "map", "filter", "sorted",
                },
                BUILTIN,
            ),
            (r"\b(?:True|False|None)\b", TYPE),
            (r"\b(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?\b", NUMBER),
            (r"'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\"", STRING),
            (r"#.*$", COMMENT),
            (r"\b(?:def|class)\s+([A-Za-z_]\w*)", DECLARATION),
        ]
        super().__init__(document, rules)


class MatlabHighlighter(RegexHighlighter):
    KEYWORDS = {
        "break", "case", "catch", "classdef", "continue", "else", "elseif", "end",
        "for", "function", "global", "if", "otherwise", "parfor", "persistent", "return",
        "spmd", "switch", "try", "while", "methods", "properties", "events", "enumeration",
    }

    def __init__(self, document):
        rules = [
            _word_rule(self.KEYWORDS, KEYWORD),
            _word_rule(
                {
                    "plot", "linspace", "zeros", "ones", "size", "length", "min", "max",
                    "sum", "mean", "disp", "fprintf", "sqrt", "sin", "cos", "tan", "abs",
                    "syms", "solve", "simplify", "diff", "int", "subs",
                },
                BUILTIN,
            ),
            (r"\b(?:\d+(?:\.\d*)?|\.\d+)(?:[eEdD][+-]?\d+)?\b", NUMBER),
            (r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"", STRING),
            (r"%.*$", COMMENT),
            (r"\bfunction\b.*$", DECLARATION),
        ]
        super().__init__(document, rules)


class LeanHighlighter(RegexHighlighter):
    KEYWORDS = {
        "abbrev", "axiom", "by", "class", "def", "deriving", "do", "else", "example",
        "extends", "for", "forall", "fun", "if", "import", "in", "inductive", "instance",
        "let", "match", "namespace", "open", "opaque", "partial", "private", "protected",
        "section", "structure", "theorem", "then", "variable", "where", "with", "end",
    }

    TACTICS = {
        "apply", "assumption", "cases", "constructor", "exact", "intro", "intros", "left",
        "linarith", "nlinarith", "norm_num", "omega", "positivity", "rfl", "right", "ring",
        "ring_nf", "simp", "simpa", "subst", "rw", "aesop", "contradiction", "induction",
    }

    TYPES = {"Nat", "Int", "Rat", "Real", "Bool", "Prop", "Type", "ℕ", "ℤ", "ℚ", "ℝ"}

    def __init__(self, document):
        rules = [
            _word_rule(self.KEYWORDS, KEYWORD),
            _word_rule(self.TACTICS, BUILTIN),
            _word_rule(self.TYPES, TYPE),
            (r"\b(?:theorem|lemma|def|example|structure|inductive)\s+([A-Za-z_][\w']*)", DECLARATION),
            (r"\b\d+(?:\.\d+)?\b", NUMBER),
            (r'"(?:\\.|[^"\\])*"', STRING),
            (r"--.*$", COMMENT),
            (r"(:=|=>|→|←|↔|≤|≥|≠|∧|∨|¬|∈|∉|⊢)", OPERATOR),
        ]
        super().__init__(document, rules)
