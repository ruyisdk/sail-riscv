#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The gate's data model: corpus, citation block, report, frozen excerpt.

Everything here is inert.  A :class:`Corpus` is a normalised AsciiDoc file, a
:class:`CitationBlock` is what R1 parses out of a module docstring, a
:class:`Report` is what one run collected.  The rules that judge those objects
live in :mod:`mmul_gen.spec_citations.rules`; nothing here decides whether a
template is compliant.

Loading belongs to the model on purpose: :func:`load_corpus` must produce exactly
the text R2 compares against, and :func:`corpora_from_manifest` must rebuild that
same shape from the frozen excerpts, so both inputs are indistinguishable
downstream.
"""

from __future__ import annotations

import ast
import bisect
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

from mmul_gen.spec_citations.constants import (
    ADOC_REF_PATTERN,
    FIELD_PATTERN,
    RANGE_PATTERN,
)


# --------------------------------------------------------------------------- #
# Errors
# --------------------------------------------------------------------------- #


class SpecEnvironmentError(RuntimeError):
    """The inputs the validator needs are missing or unusable (exit status 2)."""


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Corpus:
    """One ``src/*.adoc`` file, normalised, with an offset -> line map.

    ``text`` is the whole file after :func:`normalize`-per-line and single-space
    joining; ``starts`` maps a normalised offset to the 1-based source line it
    came from, so a match offset can be reported as a line number.
    """

    file: str
    path: Path
    text: str
    starts: tuple[tuple[int, int], ...]
    line_count: int

    def line_of(self, offset: int) -> int:
        """Return the 1-based source line number that contains ``offset``.

        A file whose lines are all blank has no entries in ``starts``; reporting
        line 1 is right, and it keeps a degenerate source from crashing a run.
        """
        if not self.starts:
            return 1
        index = bisect.bisect_right(self.starts, (offset, sys.maxsize)) - 1
        return self.starts[max(index, 0)][1]


@dataclass(frozen=True)
class CorpusMatch:
    """Where a normalised quote was found."""

    corpus: Corpus
    offset: int

    @property
    def line(self) -> int:
        return self.corpus.line_of(self.offset)


@dataclass(frozen=True)
class Candidate:
    """A near miss, printed to help an author find the real sentence."""

    file: str
    line: int
    offset: int
    ratio: float
    snippet: str


@dataclass(frozen=True)
class QuoteFailure:
    """Why a quote did not match, plus where the closest text is."""

    reason: str
    candidates: tuple[Candidate, ...]


@dataclass(frozen=True)
class DeclaredRange:
    """One ``<file>.adoc:<start>-<end>`` entry of a ``Spec:`` field."""

    file: str
    start: int
    end: int

    def __str__(self) -> str:
        return f"{self.file}:{self.start}-{self.end}"


@dataclass(frozen=True)
class CitationBlock:
    """The parsed citation block of one module docstring."""

    values: dict[str, str]
    duplicates: tuple[str, ...]

    def has(self, label: str) -> bool:
        return bool(self.values.get(label, "").strip())


@dataclass(frozen=True)
class Violation:
    """One failed template, with the rule that caught it and the context."""

    template: str
    rule: str
    detail: str
    lines: tuple[str, ...] = ()


@dataclass
class Report:
    """Everything one run has to say."""

    templates: int = 0
    compliant: list[tuple[str, str]] = field(default_factory=list)
    structural: list[str] = field(default_factory=list)
    violations: list[Violation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def denominator(self) -> int:
        """Validated templates = compliant + violating; structural ones excluded."""
        return len(self.compliant) + len(self.violations)

    def summary_line(self) -> str:
        denominator = self.denominator
        percent = 100.0 * len(self.compliant) / denominator if denominator else 0.0
        return (
            f"spec citations: compliant={len(self.compliant)} "
            f"structural={len(self.structural)} "
            f"violations={len(self.violations)}  "
            f"(coverage {len(self.compliant)}/{denominator} = {percent:.1f}%)"
        )


# --------------------------------------------------------------------------- #
# Corpus (R2 substrate)
# --------------------------------------------------------------------------- #


def normalize(text: str) -> str:
    """Strip inline backticks, collapse all whitespace runs, strip the ends.

    Applied identically to the quote and to the specification text, so a quote
    may (and usually does) re-wrap the sentence at different points.
    """
    return re.sub(r"\s+", " ", text.replace("`", "")).strip()


def load_corpus(spec_root: Path) -> dict[str, Corpus]:
    """Read every ``src/*.adoc`` into a normalised :class:`Corpus` by file name."""
    corpus: dict[str, Corpus] = {}
    for path in sorted((spec_root / "src").glob("*.adoc"), key=lambda p: p.name):
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise SpecEnvironmentError(
                f"cannot read specification source {path}: {error}; the corpus must be readable UTF-8 AsciiDoc"
            ) from error
        raw_lines = text.splitlines()
        parts: list[str] = []
        starts: list[tuple[int, int]] = []
        length = 0
        for lineno, raw in enumerate(raw_lines, 1):
            line = normalize(raw)
            if not line:
                continue
            if parts:
                parts.append(" ")
                length += 1
            starts.append((length, lineno))
            parts.append(line)
            length += len(line)
        corpus[path.name] = Corpus(
            file=path.name,
            path=path,
            text="".join(parts),
            starts=tuple(starts),
            line_count=len(raw_lines),
        )
    if not corpus:
        raise SpecEnvironmentError(f"no src/*.adoc files under {spec_root / 'src'}; cannot check any quote")
    return corpus


# --------------------------------------------------------------------------- #
# R1: citation block
# --------------------------------------------------------------------------- #


def read_module_docstring(path: Path) -> str:
    """Return the module docstring, raising ``SyntaxError`` on unparsable input."""
    return ast.get_docstring(ast.parse(path.read_text(encoding="utf-8"), filename=str(path))) or ""


def parse_citation_block(docstring: str) -> CitationBlock:
    """Parse ``Spec:``/``Quote:``/``Checks:`` out of a module docstring.

    A field starts at a line whose first non-blank token is the label; its value
    runs to the next field line or the end of the docstring (R1).  Continuation
    lines belong to the *occurrence* they follow, so a label that appears twice
    is detected as a duplicate instead of being folded into one long value.
    """
    occurrences: dict[str, list[list[str]]] = {}
    current: list[str] | None = None
    for line in docstring.splitlines():
        match = FIELD_PATTERN.match(line)
        if match:
            current = [match.group(2)]
            occurrences.setdefault(match.group(1), []).append(current)
        elif current is not None and line.strip():
            current.append(line)
        else:
            current = None

    values = {
        label: " ".join(part.strip() for occurrence in groups for part in occurrence).strip()
        for label, groups in occurrences.items()
    }
    duplicates = tuple(sorted(label for label, groups in occurrences.items() if len(groups) > 1))
    return CitationBlock(values=values, duplicates=duplicates)


def strip_quote_markers(value: str) -> str:
    """Remove one pair of enclosing double quotes, if present."""
    text = value.strip()
    if len(text) >= 2 and text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return text


def normalize_quote_value(value: str) -> str:
    """The comparison form of a ``Quote:`` value: markers stripped, normalised."""
    return normalize(strip_quote_markers(value))


def template_quote(path: Path) -> str:
    """The quote one template declares, in the exact form R2 compares."""
    block = parse_citation_block(read_module_docstring(path))
    return normalize_quote_value(block.values.get("Quote", ""))


# --------------------------------------------------------------------------- #
# R3: declared position, as a parsed field value
# --------------------------------------------------------------------------- #


def parse_spec_entries(value: str) -> tuple[list[DeclaredRange], list[str]]:
    """Split a ``Spec:`` value into declared ranges plus malformed entries."""
    declared: list[DeclaredRange] = []
    malformed: list[str] = []
    consumed: list[tuple[int, int]] = []
    for match in RANGE_PATTERN.finditer(value):
        declared.append(DeclaredRange(file=match.group(1), start=int(match.group(2)), end=int(match.group(3))))
        consumed.append((match.start(), match.end()))
    for match in ADOC_REF_PATTERN.finditer(value):
        if any(start <= match.start() < end for start, end in consumed):
            continue
        reference, tail = match.group(1), match.group(2)
        if tail.isdigit():
            line = int(tail)
            declared.append(DeclaredRange(file=reference, start=line, end=line))
            consumed.append((match.start(), match.end()))
        else:
            malformed.append(
                f"Spec entry {match.group(0)!r} is not '<file>.adoc:<start>-<end>'; "
                f"expected e.g. instruction_semantics.adoc:181-185"
            )
    return declared, malformed


# --------------------------------------------------------------------------- #
# Frozen manifest (the R2 substrate of a machine without the specification)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Excerpt:
    """One frozen quote: the specification file and line it was taken from."""

    file: str
    line: int
    text: str


def parse_excerpts(entries: object) -> list[Excerpt]:
    """Validate a manifest's excerpt list, raising on anything malformed."""
    if not isinstance(entries, list):
        raise SpecEnvironmentError("citation manifest has an unexpected shape: 'excerpts' must be a list")
    parsed: list[Excerpt] = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise SpecEnvironmentError(f"citation manifest excerpt is not an object: {entry!r}")
        try:
            parsed.append(
                Excerpt(
                    file=str(entry["file"]),
                    line=int(entry["line"]),
                    text=normalize(str(entry["text"])),
                )
            )
        except (KeyError, TypeError, ValueError) as error:
            raise SpecEnvironmentError(f"citation manifest excerpt {entry!r} is malformed: {error}") from error
    return parsed


def load_manifest(path: Path) -> dict[str, object]:
    """Read the frozen excerpt set, or raise :class:`SpecEnvironmentError`."""
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as error:
        raise SpecEnvironmentError(
            f"cannot read the frozen citation manifest {path}: {error}; "
            f"regenerate it with --emit-manifest against a specification checkout"
        ) from error
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as error:
        raise SpecEnvironmentError(f"citation manifest {path} is not valid JSON: {error}") from error
    if not isinstance(data, dict) or "excerpts" not in data or "files" not in data:
        raise SpecEnvironmentError(f"citation manifest {path} lacks the 'files'/'excerpts' keys")
    return data


def corpora_from_manifest(data: Mapping[str, object]) -> dict[str, Corpus]:
    """Synthesise the corpus map from the frozen excerpts.

    Each excerpt becomes a one-line :class:`Corpus`, so R2 keeps its exact
    semantics: the quote must be a contiguous run of the recorded text, and R3
    still sees the real source line the excerpt came from.
    """
    files = data["files"]
    excerpts = data["excerpts"]
    if not isinstance(files, dict) or not isinstance(excerpts, list):
        raise SpecEnvironmentError(
            "citation manifest has an unexpected shape: 'files' must be an object and 'excerpts' a list"
        )
    corpus: dict[str, Corpus] = {}
    for excerpt in parse_excerpts(excerpts):
        recorded = files.get(excerpt.file)
        length = int(recorded.get("length", excerpt.line)) if isinstance(recorded, dict) else excerpt.line
        existing = corpus.get(excerpt.file)
        if existing is None:
            corpus[excerpt.file] = Corpus(
                file=excerpt.file,
                path=Path(excerpt.file),
                text=excerpt.text,
                starts=((0, excerpt.line),),
                line_count=max(length, excerpt.line),
            )
        else:
            joined = f"{existing.text}\n\n{excerpt.text}"
            corpus[excerpt.file] = Corpus(
                file=excerpt.file,
                path=existing.path,
                text=joined,
                starts=existing.starts + ((len(existing.text) + 2, excerpt.line),),
                line_count=max(existing.line_count, excerpt.line),
            )
    if not corpus:
        raise SpecEnvironmentError("citation manifest holds no excerpt; the gate would pass vacuously")
    return corpus


def manifest_excerpt_texts(data: Mapping[str, object]) -> tuple[str, ...]:
    """The normalised text of every frozen excerpt, for the manifest-coverage gate."""
    return tuple(excerpt.text for excerpt in parse_excerpts(data["excerpts"]))
