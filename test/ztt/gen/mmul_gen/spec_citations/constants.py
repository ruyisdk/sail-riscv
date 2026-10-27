#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Fixed inputs of the citation gate: paths, labels, grammar, display widths.

Everything here is a constant of the *contract* stated in
:mod:`mmul_gen.spec_citations` (R1 .. R7), not a tuning knob: the three field
labels, the 40-character quote floor, the two structural exclusions, the
``<file>.adoc:<start>-<end>`` grammar, and the width a failure block clips a
field to.
"""

from __future__ import annotations

import re
from pathlib import Path

#: Default template directory (the Ztt/AME generator templates).
DEFAULT_TEMPLATES = Path(__file__).resolve().parent.parent / "templates"

#: Default specification checkout (riscv-attached-matrix-extension, tag v0.6).
DEFAULT_SPEC_ROOT = Path("/home/trdthg/repo/sail/worktree/ame/riscv-attached-matrix-extension")

#: Environment variable that overrides the specification checkout.
SPEC_ROOT_ENV_VAR = "AME_SPEC_ROOT"

#: Frozen excerpt set, checked in next to the gate's unittest entry point.  It
#: lets the gate run in CI (no specification checkout there) and still notices a
#: template that drifts from the reviewed sentence.  Regenerate with
#: ``--emit-manifest`` whenever a quote changes or the specification is bumped,
#: then re-review the diff.
MANIFEST_NAME = "spec_citations_v0_6.json"

#: The manifest loaded when no ``--manifest`` is given.
DEFAULT_MANIFEST = Path(__file__).resolve().parent.parent / "tests" / MANIFEST_NAME

#: Version string recorded in the manifest.
MANIFEST_VERSION = "v0.6"

#: Files that are structurally excluded: neither validated nor counted.
#: ``__init__.py`` is a re-export index, ``base.py`` the abstract contract.
STRUCTURAL_SKIP: frozenset[str] = frozenset({"__init__.py", "base.py"})

#: Required citation fields, in their documented order.
FIELD_LABELS: tuple[str, ...] = ("Spec", "Quote", "Checks")

#: Shortest acceptable normalised quote; below this it is a fragment, not a criterion.
MIN_QUOTE_CHARS = 40

#: Characters that mark a truncated quote.
ELLIPSES: tuple[str, ...] = ("...", "…")

FIELD_PATTERN = re.compile(r"^[ \t]*(Spec|Quote|Checks):[ \t]*(.*)$")

#: ``file.adoc:start-end``; the dash may be an ASCII hyphen or an en dash.
RANGE_PATTERN = re.compile(r"([A-Za-z0-9_.+\-]+\.adoc):(\d+)\s*[-\u2013]\s*(\d+)")

#: Any ``foo.adoc:`` reference, used to catch a malformed one that RANGE_PATTERN missed.
ADOC_REF_PATTERN = re.compile(r"([A-Za-z0-9_.+\-/]+\.adoc):([^\s,;)\]]*)")

SNIPPET_CHARS = 100
VERBOSE_QUOTE_CHARS = 60
SPEC_DISPLAY_CHARS = 200
QUOTE_DISPLAY_CHARS = 240
CHECKS_DISPLAY_CHARS = 120

#: The words the R3 line-drift warning puts between the declared range and the
#: line the quote really occurs on.  They are part of the printed contract, so
#: they are spelled as escapes: the sources stay ASCII while the warning keeps
#: the exact bytes the rule documents.
DRIFT_PHRASE = "\u5f15\u6587\u5b9e\u9645\u5728"
