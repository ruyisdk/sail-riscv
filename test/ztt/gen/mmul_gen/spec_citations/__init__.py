#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Machine-checkable specification citations for the Ztt test templates.

Every template under ``mmul_gen/templates/`` must open with a citation block in
its **module docstring** (``ast.get_docstring``, not a class docstring and not a
code comment)::

    \"\"\"<one-line summary of what the template tests.>

    Spec:    instruction_semantics.adoc:181-185 (section 6.2.2)
    Quote:   "Among standard datatypes, ... are standard floating-point datatypes"
    Checks:  a standard-integer source tuple must set amestatus.UN ...

    <the rest of the docstring, unchanged>
    \"\"\"

Rules (final wording; where this package and the design doc disagree, this
package wins):

R1  Field presence.  The module docstring must contain the three fields
    ``Spec:``, ``Quote:`` and ``Checks:`` at the start of a line (leading
    whitespace allowed).  A field's value is its own line plus every following
    line up to the next field line or the end of the docstring.  A missing field
    is a violation and names the file and the missing field(s); a duplicated
    field is a violation too.

R2  Verbatim quote.  ``Quote:`` must appear as a contiguous run of text in one
    of ``<spec-root>/src/*.adoc``.  Both sides are normalised identically:
    inline backticks removed, every run of whitespace (newlines included)
    collapsed to one space, ends stripped.  Two hard constraints on top:
    (a) the normalised quote is at least 40 characters ("too short to be a
    criterion"); (b) it contains no ``...`` or ``…`` (an ellipsis means the
    quote was truncated, so it cannot be verbatim).  On failure the three
    closest specification positions are printed with file, line and ratio.

R3  Declared position.  Every ``<file>.adoc:<start>-<end>`` in ``Spec:`` must
    name a file that exists in ``<spec-root>/src/`` and a range inside that
    file (``1 <= start <= end <= lines``).  Those two are hard failures.  The
    *soft* check asks whether the quote really occurs inside the declared
    range; when it does not, a ``WARN line-drift:`` line naming the range and the
    line the quote really occurs on is printed, but the template still counts as
    compliant (the quote is the truth, the line numbers are a hint).

R4  Fail fast on a broken environment.  A missing specification repository, a
    missing ``src/*.adoc`` set, a missing template directory, an ``--only``
    pattern that matches nothing, or a selection made only of structural files
    prints one explicit ERROR block and exits with status 2.  Nothing is
    skipped, nothing degrades silently, and no run may report ``0/0``.

R5  Structural exclusion.  ``STRUCTURAL_SKIP = {"__init__.py", "base.py"}``:
    these two files are neither validated nor counted in the denominator, and
    the report prints ``structural=2``.  There is no waiver list and no other
    way to opt out of validation.

R6  One summary line, exactly::

        spec citations: compliant=N structural=M violations=K  (coverage N/(N+K) = xx.x%)

    followed by nothing else on that line; violation details are printed one
    block per file, ``-v`` additionally prints each compliant quote.

R7  Deterministic output.  Templates are visited in file-name order, corpus
    files in path order, and candidates are ordered by ratio then position, so
    two runs over the same inputs print byte-identical output.

Failure modes this tool is built to make visible, not to hide:

* a template with no citation block at all -> R1 violation, never "compliant";
* a template whose ``Quote:`` was retyped from memory -> R2 violation with
  candidates, which is the whole point of the exercise;
* a ``Spec:`` whose file name or range is stale or misspelled -> R3 violation;
* a ``Quote:`` that only matches because backticks and AsciiDoc line breaks
  were normalised -> compliant, and that is intended (R2 normalises both sides);
* a ``Quote:`` placed after ``Checks:`` swallows the trailing prose of the
  docstring into the quote, because a field runs to the next field line (R1);
  keep the block order ``Spec: -> Quote: -> Checks:`` and put prose after it;
* running under ``unittest`` discovery: the test methods fail with the same
  detail text the CLI prints, and an R4 environment error fails the test rather
  than skipping it.

Where the code is:

* :mod:`mmul_gen.spec_citations.constants` -- paths, labels, grammar, widths;
* :mod:`mmul_gen.spec_citations.model` -- corpus, citation block, report, the
  frozen excerpt, and the loaders that build them;
* :mod:`mmul_gen.spec_citations.environment` -- which templates, which
  specification, which corpus (R4);
* :mod:`mmul_gen.spec_citations.rules` -- R1/R2/R3 and the report renderer;
* :mod:`mmul_gen.spec_citations.manifest` -- freeze the excerpts, re-check them;
* :mod:`mmul_gen.spec_citations.cli` -- the options and the exit codes.

Usage (works both as a command line and as an imported/unittest-collected
module)::

    python3 -B -m mmul_gen.spec_citations [--templates DIR] [--spec-root DIR]
                                          [--only GLOB ...] [-v]
    python3 -B -m mmul_gen.spec_citations --emit-manifest mmul_gen/tests/spec_citations_v0_6.json

Exit status: 0 = no violations, 1 = violations, 2 = environment error.
"""

from __future__ import annotations

from mmul_gen.spec_citations.cli import build_parser, main
from mmul_gen.spec_citations.constants import (
    DEFAULT_MANIFEST,
    DEFAULT_SPEC_ROOT,
    DEFAULT_TEMPLATES,
    FIELD_LABELS,
    MANIFEST_NAME,
    MIN_QUOTE_CHARS,
    SPEC_ROOT_ENV_VAR,
    STRUCTURAL_SKIP,
)
from mmul_gen.spec_citations.environment import (
    resolve_spec_root,
    resolve_spec_root_optional,
    resolve_templates,
    select_templates,
)
from mmul_gen.spec_citations.manifest import emit_manifest, verify_manifest_against_spec
from mmul_gen.spec_citations.model import (
    Candidate,
    CitationBlock,
    Corpus,
    CorpusMatch,
    DeclaredRange,
    Excerpt,
    QuoteFailure,
    Report,
    SpecEnvironmentError,
    Violation,
    corpora_from_manifest,
    load_corpus,
    load_manifest,
    manifest_excerpt_texts,
    normalize,
    normalize_quote_value,
    parse_citation_block,
    parse_excerpts,
    parse_spec_entries,
    read_module_docstring,
    strip_quote_markers,
    template_quote,
)
from mmul_gen.spec_citations.rules import (
    check_declared_ranges,
    check_quote,
    closest_candidates,
    format_report,
    line_drift_warning,
    run_validation,
    validate_template,
)

__all__ = [
    "Candidate",
    "CitationBlock",
    "Corpus",
    "CorpusMatch",
    "DEFAULT_MANIFEST",
    "DEFAULT_SPEC_ROOT",
    "DEFAULT_TEMPLATES",
    "DeclaredRange",
    "Excerpt",
    "FIELD_LABELS",
    "MANIFEST_NAME",
    "MIN_QUOTE_CHARS",
    "QuoteFailure",
    "Report",
    "SPEC_ROOT_ENV_VAR",
    "STRUCTURAL_SKIP",
    "SpecEnvironmentError",
    "Violation",
    "build_parser",
    "check_declared_ranges",
    "check_quote",
    "closest_candidates",
    "corpora_from_manifest",
    "emit_manifest",
    "format_report",
    "line_drift_warning",
    "load_corpus",
    "load_manifest",
    "main",
    "manifest_excerpt_texts",
    "normalize",
    "normalize_quote_value",
    "parse_citation_block",
    "parse_excerpts",
    "parse_spec_entries",
    "read_module_docstring",
    "resolve_spec_root",
    "resolve_spec_root_optional",
    "resolve_templates",
    "run_validation",
    "select_templates",
    "strip_quote_markers",
    "template_quote",
    "validate_template",
    "verify_manifest_against_spec",
]
