#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""The rules: R1 field presence, R2 verbatim quote, R3 declared position.

This is the only layer that decides whether a template is compliant.  It reads a
:class:`~mmul_gen.spec_citations.model.Corpus`,
:class:`~mmul_gen.spec_citations.model.CitationBlock` and template paths, and
builds a :class:`~mmul_gen.spec_citations.model.Report`; the rendering of that
report (:func:`format_report`) lives here too so the summary line (R6) cannot
drift away from the rule that produces it.

Order matters to an author, and it is the order below: a missing field is
reported before a bad quote, a bad quote before a bad range, and a range that is
merely stale (the quote occurs outside it) is a warning, not a violation -- the
quote is the truth, the line numbers are a hint.
"""

from __future__ import annotations

import difflib
import re
from pathlib import Path
from typing import Mapping, Sequence

from mmul_gen.spec_citations.constants import (
    CHECKS_DISPLAY_CHARS,
    DEFAULT_MANIFEST,
    DRIFT_PHRASE,
    ELLIPSES,
    FIELD_LABELS,
    MIN_QUOTE_CHARS,
    QUOTE_DISPLAY_CHARS,
    SNIPPET_CHARS,
    SPEC_DISPLAY_CHARS,
    STRUCTURAL_SKIP,
    VERBOSE_QUOTE_CHARS,
)
from mmul_gen.spec_citations.environment import select_templates
from mmul_gen.spec_citations.model import (
    Candidate,
    CitationBlock,
    Corpus,
    CorpusMatch,
    DeclaredRange,
    QuoteFailure,
    Report,
    SpecEnvironmentError,
    Violation,
    corpora_from_manifest,
    load_corpus,
    load_manifest,
    normalize,
    normalize_quote_value,
    parse_citation_block,
    parse_spec_entries,
    read_module_docstring,
    strip_quote_markers,
)


def _singlespace(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _clip(value: str, limit: int) -> str:
    """Shorten a field value for a failure block.

    Only the *display* is shortened; every rule runs on the full value.  A
    ``Checks:`` field runs to the end of the docstring (R1), so it would
    otherwise dump the template's whole prose into the report.
    """
    text = _singlespace(value)
    return text if len(text) <= limit else text[:limit].rstrip() + " …"


def _ellipsis_probe(needle: str) -> str:
    """Return the longest ellipsis-free fragment, for candidate hunting only."""
    fragments = [needle]
    for ellipsis in ELLIPSES:
        fragments = [piece for fragment in fragments for piece in fragment.split(ellipsis)]
    return max(fragments, key=len)


def closest_candidates(needle: str, corpus: Mapping[str, Corpus], limit: int = 3) -> tuple[Candidate, ...]:
    """Return the ``limit`` positions of ``corpus`` whose text is closest to ``needle``.

    Per file, ``difflib`` yields every common block between the quote and the
    normalised specification text; the five largest blocks anchor candidate
    windows, and a real ``SequenceMatcher.ratio()`` on each window ranks them.
    ``autojunk`` must be off: the specification files are large enough that
    ``difflib`` would otherwise junk the spaces and collapse every block to a
    single character, which reports nonsense candidates.
    """
    found: list[Candidate] = []
    for name in sorted(corpus):
        entry = corpus[name]
        matcher = difflib.SequenceMatcher(None, needle, entry.text, autojunk=False)
        anchors = sorted(matcher.get_matching_blocks(), key=lambda block: -block.size)[:5]
        pad = max(len(needle) // 4, 20)
        for anchor in anchors:
            start = anchor.b
            window = entry.text[max(0, start - pad) : start + len(needle) + pad]
            ratio = difflib.SequenceMatcher(None, needle, window, autojunk=False).ratio()
            snippet = _singlespace(window)
            # reports start mid-word when padded to the left; drop the fragment
            if start > 0 and " " in snippet:
                snippet = snippet.split(" ", 1)[1]
            if len(snippet) > SNIPPET_CHARS:
                snippet = snippet[:SNIPPET_CHARS].rstrip() + " …"
            found.append(
                Candidate(
                    file=name,
                    line=entry.line_of(start),
                    offset=start,
                    ratio=ratio,
                    snippet=snippet,
                )
            )

    found.sort(key=lambda candidate: (-candidate.ratio, candidate.file, candidate.offset))
    selected: list[Candidate] = []
    for candidate in found:
        too_close = any(
            candidate.file == chosen.file and abs(candidate.offset - chosen.offset) <= len(needle) // 2
            for chosen in selected
        )
        if too_close:
            continue
        selected.append(candidate)
        if len(selected) == limit:
            break
    return tuple(selected)


def check_quote(value: str, corpus: Mapping[str, Corpus]) -> tuple[CorpusMatch | None, QuoteFailure | None]:
    """Match a ``Quote:`` value against the corpus (R2).

    Returns ``(match, None)`` on success, ``(None, failure)`` on failure.  The
    three hard constraints are checked in the order an author can act on them:
    ellipsis, then length, then the verbatim substring search.
    """
    core = strip_quote_markers(value)
    needle = normalize(core)

    if any(ellipsis in core for ellipsis in ELLIPSES):
        return None, QuoteFailure(
            reason=(
                f"quote contains an ellipsis ({'/'.join(ELLIPSES)}): the sentence was "
                f"truncated, so it is not verbatim; quote it in full"
            ),
            candidates=closest_candidates(_ellipsis_probe(needle), corpus),
        )

    if len(needle) < MIN_QUOTE_CHARS:
        return None, QuoteFailure(
            reason=(
                f"quote is {len(needle)} characters after normalisation, below the "
                f"{MIN_QUOTE_CHARS}-character floor: too short to be a criterion, "
                f"quote the sentence that states the rule"
            ),
            candidates=closest_candidates(needle, corpus),
        )

    for name in sorted(corpus):
        offset = corpus[name].text.find(needle)
        if offset >= 0:
            return CorpusMatch(corpus=corpus[name], offset=offset), None

    return None, QuoteFailure(
        reason=(
            "quote does not occur verbatim in any src/*.adoc file after normalisation "
            "(backticks removed, whitespace collapsed)"
        ),
        candidates=closest_candidates(needle, corpus),
    )


def check_declared_ranges(value: str, corpus: Mapping[str, Corpus]) -> tuple[list[DeclaredRange], list[str]]:
    """Hard part of R3: every declared file exists and every range fits it."""
    declared, problems = parse_spec_entries(value)
    if not declared and not problems:
        problems.append(f"Spec field names no '<file>.adoc:<start>-<end>' citation: {value!r}")
    for entry in declared:
        source = corpus.get(entry.file)
        if source is None:
            problems.append(f"Spec names {entry.file}, which is not a top-level file in <spec-root>/src/*.adoc")
            continue
        if not 1 <= entry.start <= entry.end:
            problems.append(
                f"Spec range {entry} is not a valid interval (expected 1 <= start <= end <= {source.line_count})"
            )
        elif entry.end > source.line_count:
            problems.append(f"Spec range {entry} is outside {entry.file} (file has {source.line_count} lines)")
    return declared, problems


def line_drift_warning(
    template: str,
    declared: Sequence[DeclaredRange],
    match: CorpusMatch,
    needle: str = "",
) -> str | None:
    """Soft part of R3: does *any* occurrence of the quote fall in a declared range?

    The same sentence often appears on several instruction pages (a shared
    paragraph), so the first match is not necessarily the one the author meant.
    """
    offsets = [found.start() for found in re.finditer(re.escape(needle), match.corpus.text)] if needle else []
    actual_lines = [match.corpus.line_of(offset) for offset in offsets] or [match.line]
    same_file = [entry for entry in declared if entry.file == match.corpus.file]
    if any(entry.start <= line <= entry.end for line in actual_lines for entry in same_file):
        return None
    if same_file:
        shown = ", ".join(str(entry) for entry in same_file)
    elif declared:
        shown = f"{match.corpus.file}:{declared[0].start}-{declared[0].end}"
    else:
        shown = f"{match.corpus.file}:?"
    return f"WARN line-drift: {shown} {DRIFT_PHRASE} {', '.join(str(line) for line in actual_lines)}"


def _unparsable_violation(name: str, error: Exception, detail: str) -> tuple[list[Violation], list[str], None]:
    """The R0 violation for a template whose docstring cannot be read."""
    return ([Violation(template=name, rule="R0", detail=f"{detail}: {error}")], [], None)


def _missing_fields_violation(name: str, block: CitationBlock) -> tuple[list[Violation], list[str], None]:
    """The R1 violation for fields that are absent, naming the ones that are not."""
    missing = [label for label in FIELD_LABELS if not block.has(label)]
    have = ", ".join(label for label in FIELD_LABELS if block.has(label)) or "none"
    detail = f"missing field(s): {', '.join(missing)}"
    if block.duplicates:
        detail += f"; duplicated field(s): {', '.join(block.duplicates)}"
    return (
        [
            Violation(
                template=name,
                rule="R1",
                detail=detail,
                lines=(
                    f"have:      {have}",
                    f"expected:  {' -> '.join(FIELD_LABELS)}, at the top of the module docstring",
                ),
            )
        ],
        [],
        None,
    )


def _duplicate_fields_violation(name: str, block: CitationBlock) -> tuple[list[Violation], list[str], None]:
    """The R1 violation for a field that appears twice."""
    return (
        [
            Violation(
                template=name,
                rule="R1",
                detail=f"duplicated field(s): {', '.join(block.duplicates)}",
                lines=(f"expected:  one {' / '.join(FIELD_LABELS)} block per docstring",),
            )
        ],
        [],
        None,
    )


def _quote_violation(
    name: str,
    spec_value: str,
    quote_value: str,
    failure: QuoteFailure,
) -> tuple[list[Violation], list[str], None]:
    """The R2 violation: why the quote missed, and the closest real sentences."""
    detail_lines = [
        f"Spec:    {_clip(spec_value, SPEC_DISPLAY_CHARS)}",
        f"Quote:   {_clip(quote_value, QUOTE_DISPLAY_CHARS)}",
        f"Reason:  {failure.reason}",
    ]
    for candidate in failure.candidates:
        detail_lines.append(f"Closest (ratio {candidate.ratio:.2f}) {candidate.file}:{candidate.line}")
        detail_lines.append(f"  {candidate.snippet}")
    return (
        [
            Violation(
                template=name,
                rule="R2",
                detail="quote not found in the AME v0.6 sources",
                lines=tuple(detail_lines),
            )
        ],
        [],
        None,
    )


def _range_violation(
    name: str,
    spec_value: str,
    quote_value: str,
    checks_value: str,
    problems: Sequence[str],
) -> tuple[list[Violation], list[str], None]:
    """The R3 violation: a declared file or range that the corpus contradicts."""
    return (
        [
            Violation(
                template=name,
                rule="R3",
                detail="; ".join(problems),
                lines=(
                    f"Spec:    {_clip(spec_value, SPEC_DISPLAY_CHARS)}",
                    f"Quote:   {_clip(quote_value, QUOTE_DISPLAY_CHARS)}",
                    f"Checks:  {_clip(checks_value, CHECKS_DISPLAY_CHARS)}",
                ),
            )
        ],
        [],
        None,
    )


# --------------------------------------------------------------------------- #
# Per-template validation
# --------------------------------------------------------------------------- #


def validate_template(path: Path, corpus: Mapping[str, Corpus]) -> tuple[list[Violation], list[str], str | None]:
    """Validate one template.

    Returns ``(violations, warnings, normalised_quote)``; the quote is ``None``
    unless the template is fully compliant.
    """
    name = f"templates/{path.name}"

    try:
        docstring = read_module_docstring(path)
    except (OSError, UnicodeDecodeError) as error:
        detail = "template cannot be read as UTF-8 Python"
        return _unparsable_violation(name, error, detail)
    except SyntaxError as error:
        detail = "template does not parse, so it has no docstring to check"
        return _unparsable_violation(name, error, detail)

    block = parse_citation_block(docstring)

    if not all(block.has(label) for label in FIELD_LABELS):
        return _missing_fields_violation(name, block)

    if block.duplicates:
        return _duplicate_fields_violation(name, block)

    spec_value = block.values["Spec"]
    quote_value = block.values["Quote"]
    checks_value = block.values["Checks"]

    match, failure = check_quote(quote_value, corpus)
    if failure is not None or match is None:
        assert failure is not None
        return _quote_violation(name, spec_value, quote_value, failure)

    declared, problems = check_declared_ranges(spec_value, corpus)
    if problems:
        return _range_violation(name, spec_value, quote_value, checks_value, problems)

    quote = normalize_quote_value(quote_value)
    drift = line_drift_warning(name, declared, match, quote)
    warnings = [f"{drift}  ({name})"] if drift is not None else []
    return [], warnings, quote


# --------------------------------------------------------------------------- #
# Driver
# --------------------------------------------------------------------------- #


def run_validation(
    templates: Path,
    spec_root: Path | None,
    patterns: Sequence[str] = (),
    manifest: Path | None = None,
) -> Report:
    """Validate every selected template; structural files are excluded (R5).

    The corpus comes from the specification checkout when one is available, and
    otherwise from the frozen excerpt manifest, so the gate never passes
    vacuously on a machine without the specification.
    """
    if spec_root is not None:
        corpus = load_corpus(spec_root)
    else:
        corpus = corpora_from_manifest(load_manifest(manifest or DEFAULT_MANIFEST))
    selected = select_templates(templates, patterns)
    validated = [path for path in selected if path.name not in STRUCTURAL_SKIP]
    if not validated:
        raise SpecEnvironmentError(
            f"nothing to validate: of {len(selected)} selected template(s) under "
            f"{templates}, every one is in STRUCTURAL_SKIP {sorted(STRUCTURAL_SKIP)}; "
            f"widening --only is the fix, exiting 2 rather than reporting 0/0"
        )
    report = Report()
    for path in selected:
        report.templates += 1
        if path.name in STRUCTURAL_SKIP:
            report.structural.append(path.name)
            continue
        violations, warnings, quote = validate_template(path, corpus)
        report.violations.extend(violations)
        report.warnings.extend(warnings)
        if quote is not None:
            report.compliant.append((f"templates/{path.name}", quote))
    return report


def format_report(report: Report, verbose: bool = False) -> str:
    """Render a report: details first, the R6 summary line last."""
    lines: list[str] = []
    for violation in report.violations:
        lines.append(f"FAIL {violation.template} [{violation.rule}] {violation.detail}")
        lines.extend(f"  {line}" for line in violation.lines)
    for warning in report.warnings:
        lines.append(warning)
    if verbose:
        for name, quote in report.compliant:
            shown = quote
            if len(shown) > VERBOSE_QUOTE_CHARS:
                shown = shown[:VERBOSE_QUOTE_CHARS]
            lines.append(f"OK   {name}  {shown!r}")
        for name in report.structural:
            lines.append(f"SKIP templates/{name}  structural (not validated, not counted)")
    lines.append(report.summary_line())
    return "\n".join(lines)
