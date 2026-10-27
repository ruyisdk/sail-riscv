#!/usr/bin/env python3
#
# Copyright (c) Qualcomm Technologies, Inc. and/or its subsidiaries.
# SPDX-License-Identifier: BSD-3-Clause-Clear
#
"""Unittest entry point for the specification-citation gate.

The gate itself is :mod:`mmul_gen.spec_citations`; what stays here is the surface
``unittest`` discovery collects, plus the ``-m`` command line the design doc
quotes::

    python3 -B -m mmul_gen.tests.test_spec_citations [--templates DIR]
                                                     [--spec-root DIR] [--only GLOB ...] [-v]

Five cases, one per promise the gate makes:

* every non-structural template is compliant (R1 .. R3);
* the frozen manifest covers every template's quote -- this is the CI gate, and
  it needs no specification checkout;
* with a checkout present the frozen excerpts are still verbatim; without one the
  case is skipped and says so, because the manifest is all there is to check;
* the summary line keeps its exact shape and denominator (R6);
* the structural exclusion set is exactly ``STRUCTURAL_SKIP`` (R5).

When run as a script this module *is* the command line: exit status 0 = no
violations, 1 = violations, 2 = environment error.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Sequence

from mmul_gen.spec_citations import (
    DEFAULT_MANIFEST,
    DEFAULT_TEMPLATES,
    MANIFEST_NAME,
    SPEC_ROOT_ENV_VAR,
    STRUCTURAL_SKIP,
    Report,
    SpecEnvironmentError,
    format_report,
    load_manifest,
    main,
    manifest_excerpt_texts,
    resolve_spec_root,
    resolve_spec_root_optional,
    resolve_templates,
    run_validation,
    select_templates,
    template_quote,
    verify_manifest_against_spec,
)


class SpecCitationTest(unittest.TestCase):
    """Unittest view of the same checks, so discovery works unchanged."""

    templates: Path = DEFAULT_TEMPLATES
    spec_root: Path | None = None
    patterns: Sequence[str] = ()

    def _report(self) -> Report:
        """Validate the configured tree, failing the case on an R4 error."""
        try:
            return run_validation(
                resolve_templates(self.templates),
                resolve_spec_root(self.spec_root),
                self.patterns,
            )
        except SpecEnvironmentError as error:
            self.fail(f"spec-citation environment error: {error}")

    def test_every_template_cites_the_specification(self) -> None:
        """Every non-structural template quotes a real AME v0.6 sentence."""
        report = self._report()
        if report.violations:
            self.fail("specification citations are not compliant:\n" + format_report(report))

    def test_every_template_quote_is_frozen_in_the_manifest(self) -> None:
        """The checked-in excerpt set must contain every template's quote.

        This is the CI gate: it needs no specification checkout, so a template
        that changes or adds a quote without regenerating the manifest fails
        here, and the manifest diff is what a reviewer reads.
        """
        frozen = set(manifest_excerpt_texts(load_manifest(DEFAULT_MANIFEST)))
        missing: list[str] = []
        for path in select_templates(DEFAULT_TEMPLATES, ()):
            if path.name in STRUCTURAL_SKIP:
                continue
            quote = template_quote(path)
            if quote not in frozen:
                missing.append(f"{path.name}: {quote[:70]!r}")
        self.assertEqual(missing, [], "template quote(s) missing from " + MANIFEST_NAME)

    def test_frozen_excerpts_still_match_the_specification(self) -> None:
        """With a checkout present, the frozen excerpts must still be verbatim."""
        spec_root = resolve_spec_root_optional()
        if spec_root is None:
            self.skipTest(f"no specification checkout (${{{SPEC_ROOT_ENV_VAR}}} unset); manifest-only mode")
        data = load_manifest(DEFAULT_MANIFEST)
        problems = verify_manifest_against_spec(data, spec_root)
        self.assertEqual(problems, [], "frozen citation manifest drifted from the specification")

    def test_summary_line_format(self) -> None:
        """R6: the summary line keeps its exact shape and denominator."""
        report = Report()
        report.compliant.append(("templates/a.py", "quote"))
        report.structural.extend(["__init__.py", "base.py"])
        self.assertRegex(
            report.summary_line(),
            r"^spec citations: compliant=1 structural=2 violations=0  "
            r"\(coverage 1/1 = 100\.0%\)$",
        )

    def test_structural_exclusions_are_exactly_two(self) -> None:
        """R5: only __init__.py and base.py are exempt, and both are reported."""
        report = self._report()
        self.assertEqual(
            sorted(report.structural),
            sorted(STRUCTURAL_SKIP),
            "structural exclusions changed; the set is part of the rule, not a debt ledger",
        )


if __name__ == "__main__":
    sys.exit(main())
